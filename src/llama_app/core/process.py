"""Wraps ``QProcess`` to manage a llama-server child process.

Provides:
    * Start/stop with graceful termination (SIGTERM-equivalent, then SIGKILL).
    * Streaming stdout/stderr into a Qt signal.
    * State machine: STOPPED -> STARTING -> LOADING -> READY -> (STOPPED | ERROR).
    * Optional /health polling to detect READY state.
"""
from __future__ import annotations

import os
import time
from enum import Enum
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, QTimer, Signal


class ServerState(str, Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    LOADING = "loading"
    READY = "ready"
    ERROR = "error"


class ServerProcess(QObject):
    state_changed = Signal(str)  # ServerState.value
    log_received = Signal(str)
    pid_changed = Signal(int)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._proc = QProcess(self)
        self._proc.readyReadStandardOutput.connect(self._on_stdout)
        self._proc.readyReadStandardError.connect(self._on_stderr)
        self._proc.errorOccurred.connect(self._on_error)
        self._proc.finished.connect(self._on_finished)
        self._proc.started.connect(self._on_started)
        self._state: ServerState = ServerState.STOPPED
        self._health_url: str | None = None
        self._health_timer: QTimer | None = None
        self._health_deadline: float = 0.0
        self._stderr_buf: str = ""
        self._stdout_buf: str = ""

    # --- public API ---

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
        """Start the process. Optionally begin /health polling."""
        if self.is_running():
            raise RuntimeError("ServerProcess is already running")
        self._stderr_buf = ""
        self._stdout_buf = ""
        self._set_state(ServerState.STARTING)
        if cwd:
            self._proc.setWorkingDirectory(cwd)
        self._proc.start(program, arguments)
        self._health_url = health_url
        if health_url:
            self._health_deadline = time.monotonic() + health_timeout_s
            self._health_timer = QTimer(self)
            self._health_timer.timeout.connect(self._check_health)
            self._health_timer.start(500)
            self._set_state(ServerState.LOADING)

    def stop(self, timeout_ms: int = 5000) -> None:
        """Politely terminate, then force-kill after ``timeout_ms``."""
        if not self.is_running():
            return
        if self._health_timer:
            self._health_timer.stop()
            self._health_timer = None
        self._proc.terminate()
        if not self._proc.waitForFinished(timeout_ms):
            self._proc.kill()
            self._proc.waitForFinished(2000)

    def send_log_marker(self, marker: str) -> None:
        """Echo a synthetic line into the log (for [CMD] banners)."""
        self.log_received.emit(marker)

    # --- internal ---

    def _set_state(self, new: ServerState) -> None:
        if new != self._state:
            self._state = new
            self.state_changed.emit(new.value)

    def _on_started(self) -> None:
        pid = self.pid()
        if pid is not None:
            self.pid_changed.emit(pid)
        if not self._health_url:
            # No health URL configured; treat started as ready.
            self._set_state(ServerState.READY)

    def _on_stdout(self) -> None:
        chunk = bytes(self._proc.readAllStandardOutput()).decode(
            "utf-8", errors="replace"
        )
        self._stdout_buf += chunk
        for line in self._consume_lines(is_stderr=False):
            self.log_received.emit(line)

    def _on_stderr(self) -> None:
        chunk = bytes(self._proc.readAllStandardError()).decode(
            "utf-8", errors="replace"
        )
        self._stderr_buf += chunk
        for line in self._consume_lines(is_stderr=True):
            self.log_received.emit(line)

    def _consume_lines(self, is_stderr: bool) -> list[str]:
        buf_attr = "_stderr_buf" if is_stderr else "_stdout_buf"
        buf = getattr(self, buf_attr)
        lines: list[str] = []
        while "\n" in buf:
            line, buf = buf.split("\n", 1)
            prefix = "[stderr] " if is_stderr else ""
            lines.append(prefix + line)
        setattr(self, buf_attr, buf)
        return lines

    def _on_error(self, err: QProcess.ProcessError) -> None:
        self.log_received.emit(f"[error] QProcess error: {err}")
        self._set_state(ServerState.ERROR)

    def _on_finished(self, exit_code: int, exit_status: QProcess.ExitStatus) -> None:
        # Flush remaining buffer content
        for attr, is_stderr in (("_stdout_buf", False), ("_stderr_buf", True)):
            remaining = getattr(self, attr)
            if remaining:
                prefix = "[stderr] " if is_stderr else ""
                self.log_received.emit(prefix + remaining)
                setattr(self, attr, "")
        self._set_state(ServerState.STOPPED)
        if self._health_timer:
            self._health_timer.stop()
            self._health_timer = None
        self.pid_changed.emit(0)

    def _check_health(self) -> None:
        if not self._health_url:
            return
        if time.monotonic() > self._health_deadline:
            self.log_received.emit("[health] timeout — server did not become ready")
            self._set_state(ServerState.ERROR)
            self.stop()
            return
        # Lazy import to avoid hard dep at module import time
        import urllib.request
        import urllib.error

        try:
            with urllib.request.urlopen(self._health_url, timeout=1) as r:
                if 200 <= r.status < 300:
                    self._set_state(ServerState.READY)
                    if self._health_timer:
                        self._health_timer.stop()
        except (urllib.error.URLError, ConnectionError, OSError):
            pass  # not ready yet
