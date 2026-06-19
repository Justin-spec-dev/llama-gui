"""Asynchronous ``QProcess`` lifecycle management for llama-server."""
from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum

from PySide6.QtCore import QObject, QProcess, QTimer, Signal
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest


class ServerState(str, Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    LOADING = "loading"
    READY = "ready"
    ERROR = "error"


@dataclass(frozen=True)
class LaunchSpec:
    program: str
    arguments: tuple[str, ...]
    cwd: str | None
    health_url: str | None
    health_timeout_s: float


class ServerProcess(QObject):
    state_changed = Signal(str)
    log_received = Signal(str)
    pid_changed = Signal(int)

    def __init__(
        self,
        parent: QObject | None = None,
        network_manager: QNetworkAccessManager | None = None,
    ):
        super().__init__(parent)
        self._proc = QProcess(self)
        self._proc.readyReadStandardOutput.connect(self._on_stdout)
        self._proc.readyReadStandardError.connect(self._on_stderr)
        self._proc.errorOccurred.connect(self._on_error)
        self._proc.finished.connect(self._on_finished)
        self._proc.started.connect(self._on_started)
        self._network_manager = network_manager or QNetworkAccessManager(self)
        self._state = ServerState.STOPPED
        self._health_url: str | None = None
        self._health_timer: QTimer | None = None
        self._health_reply: QNetworkReply | None = None
        self._health_deadline = 0.0
        self._stderr_buf = ""
        self._stdout_buf = ""
        self._stop_requested = False
        self._error_latched = False
        self._pending_launch: LaunchSpec | None = None
        self._launch_generation = 0

    @property
    def state(self) -> ServerState:
        return self._state

    def is_running(self) -> bool:
        return self._proc.state() != QProcess.NotRunning

    def pid(self) -> int | None:
        pid = int(self._proc.processId())
        return pid if pid > 0 else None

    def start(
        self,
        program: str,
        arguments: list[str],
        cwd: str | None = None,
        health_url: str | None = None,
        health_timeout_s: int = 30,
    ) -> None:
        """Start a process and optionally poll its health endpoint."""
        if self.is_running():
            raise RuntimeError("ServerProcess is already running")
        spec = LaunchSpec(
            program, tuple(arguments), cwd, health_url, health_timeout_s
        )
        self._launch_generation += 1
        self._stop_requested = False
        self._error_latched = False
        self._stderr_buf = ""
        self._stdout_buf = ""
        self._cleanup_health()
        self._health_url = spec.health_url
        self._health_deadline = (
            time.monotonic() + spec.health_timeout_s if spec.health_url else 0.0
        )
        self._proc.setWorkingDirectory(spec.cwd or "")
        self._set_state(ServerState.STARTING)
        if spec.health_url:
            self._health_timer = QTimer(self)
            self._health_timer.timeout.connect(self._check_health)
            self._health_timer.start(500)
            self._set_state(ServerState.LOADING)
        self._proc.start(spec.program, list(spec.arguments))

    def stop(self, timeout_ms: int = 5000) -> None:
        """Request termination and schedule a non-blocking force-kill."""
        if not self.is_running():
            return
        self._stop_requested = True
        self._cleanup_health()
        generation = self._launch_generation
        self._proc.terminate()
        QTimer.singleShot(
            timeout_ms, lambda: self._force_kill_if_running(generation)
        )

    def restart(
        self,
        program: str,
        arguments: list[str],
        cwd: str | None = None,
        health_url: str | None = None,
        health_timeout_s: int = 30,
        stop_timeout_ms: int = 5000,
    ) -> None:
        """Replace the running process once its asynchronous stop completes."""
        self._pending_launch = LaunchSpec(
            program, tuple(arguments), cwd, health_url, health_timeout_s
        )
        if self.is_running():
            self.stop(stop_timeout_ms)
        else:
            self._start_pending()

    def send_log_marker(self, marker: str) -> None:
        self.log_received.emit(marker)

    def _set_state(self, new: ServerState) -> None:
        if new != self._state:
            self._state = new
            self.state_changed.emit(new.value)

    def _on_started(self) -> None:
        pid = self.pid()
        if pid is not None:
            self.pid_changed.emit(pid)
        if not self._health_url:
            self._set_state(ServerState.READY)

    def _on_stdout(self) -> None:
        chunk = bytes(self._proc.readAllStandardOutput()).decode(
            "utf-8", errors="replace"
        )
        self._stdout_buf += chunk
        for line in self._consume_lines(False):
            self.log_received.emit(line)

    def _on_stderr(self) -> None:
        chunk = bytes(self._proc.readAllStandardError()).decode(
            "utf-8", errors="replace"
        )
        self._stderr_buf += chunk
        for line in self._consume_lines(True):
            self.log_received.emit(line)

    def _consume_lines(self, is_stderr: bool) -> list[str]:
        buf_attr = "_stderr_buf" if is_stderr else "_stdout_buf"
        buf = getattr(self, buf_attr)
        lines: list[str] = []
        while "\n" in buf:
            line, buf = buf.split("\n", 1)
            lines.append(("[stderr] " if is_stderr else "") + line)
        setattr(self, buf_attr, buf)
        return lines

    def _on_error(self, err: QProcess.ProcessError) -> None:
        self.log_received.emit(f"[error] QProcess error: {err}")
        if self._stop_requested and err != QProcess.FailedToStart:
            return
        self._error_latched = True
        self._set_state(ServerState.ERROR)

    def _on_finished(self, exit_code: int, exit_status: QProcess.ExitStatus) -> None:
        for attr, is_stderr in (("_stdout_buf", False), ("_stderr_buf", True)):
            remaining = getattr(self, attr)
            if remaining:
                self.log_received.emit(
                    ("[stderr] " if is_stderr else "") + remaining
                )
                setattr(self, attr, "")
        self._cleanup_health()
        if self._error_latched:
            self._set_state(ServerState.ERROR)
        elif self._stop_requested:
            self._set_state(ServerState.STOPPED)
        else:
            self.log_received.emit(
                f"[error] unexpected exit: code={exit_code}, status={exit_status}"
            )
            self._error_latched = True
            self._set_state(ServerState.ERROR)
        self.pid_changed.emit(0)
        if self._pending_launch is not None:
            QTimer.singleShot(0, self._start_pending)

    def _force_kill_if_running(self, generation: int) -> None:
        if generation == self._launch_generation and self.is_running():
            self._proc.kill()

    def _start_pending(self) -> None:
        if self.is_running() or self._pending_launch is None:
            return
        spec = self._pending_launch
        self._pending_launch = None
        self.start(
            spec.program,
            list(spec.arguments),
            spec.cwd,
            spec.health_url,
            spec.health_timeout_s,
        )

    def _cleanup_health(self) -> None:
        if self._health_timer:
            self._health_timer.stop()
            self._health_timer.deleteLater()
            self._health_timer = None
        if self._health_reply is not None:
            reply = self._health_reply
            self._health_reply = None
            reply.abort()
            reply.deleteLater()

    def _check_health(self) -> None:
        if not self._health_url:
            return
        if time.monotonic() > self._health_deadline:
            self.log_received.emit("[health] timeout - server did not become ready")
            self._error_latched = True
            self._set_state(ServerState.ERROR)
            self.stop()
            return
        if self._health_reply is not None:
            return
        request = QNetworkRequest(self._health_url)
        request.setTransferTimeout(1000)
        reply = self._network_manager.get(request)
        self._health_reply = reply
        reply.finished.connect(lambda: self._on_health_finished(reply))

    def _on_health_finished(self, reply: QNetworkReply) -> None:
        if reply is not self._health_reply:
            return
        self._health_reply = None
        status = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
        reply.deleteLater()
        if status is not None and 200 <= int(status) < 300:
            self._set_state(ServerState.READY)
            if self._health_timer:
                self._health_timer.stop()
