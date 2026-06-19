"""Tests for ServerProcess — start, stop, log streaming.

We exercise the real ``QProcess`` machinery by spawning the current Python
interpreter and verifying state transitions and log capture on every platform.
"""
from __future__ import annotations

import sys
import time

from PySide6.QtCore import QObject, QProcess, Signal

from llama_app.core.process import LaunchSpec, ServerProcess, ServerState


def _make_proc() -> ServerProcess:
    return ServerProcess()


def test_initial_state_is_stopped():
    p = _make_proc()
    assert p.state == ServerState.STOPPED
    assert not p.is_running()
    assert p.pid() is None


def test_state_transitions_to_starting(qtbot):
    p = _make_proc()
    states: list[str] = []
    p.state_changed.connect(lambda s: states.append(s))
    p.start(sys.executable, ["-c", "import time; time.sleep(0.5)"])
    qtbot.waitUntil(lambda: p.state != ServerState.STOPPED, timeout=3000)
    assert p.state in {ServerState.STARTING, ServerState.LOADING, ServerState.READY}
    p.stop(timeout_ms=2000)


def test_log_streaming_receives_stdout(qtbot):
    p = _make_proc()
    received: list[str] = []
    p.log_received.connect(lambda s: received.append(s))
    p.start(sys.executable, ["-c", "print('HELLO_FROM_TEST', flush=True)"])
    qtbot.waitUntil(lambda: any("HELLO_FROM_TEST" in s for s in received), timeout=5000)
    assert any("HELLO_FROM_TEST" in s for s in received)
    p.stop(timeout_ms=2000)


def test_stop_returns_to_stopped_state(qtbot):
    p = _make_proc()
    p.start(sys.executable, ["-c", "import time; time.sleep(10)"])
    qtbot.waitUntil(lambda: p.is_running(), timeout=3000)
    p.stop(timeout_ms=500)
    qtbot.waitUntil(lambda: p.state == ServerState.STOPPED, timeout=3000)
    assert p.state == ServerState.STOPPED
    assert p.pid() is None


def test_launch_spec_is_frozen_and_normalizes_arguments():
    spec = LaunchSpec("server", ("--port", "8080"), None, None, 30)
    assert spec.arguments == ("--port", "8080")
    try:
        spec.program = "other"
    except Exception as exc:
        assert type(exc).__name__ == "FrozenInstanceError"
    else:
        raise AssertionError("LaunchSpec must be frozen")


def test_stop_returns_promptly_and_requested_exit_is_stopped(qtbot):
    p = _make_proc()
    p.start(sys.executable, ["-c", "import time; time.sleep(30)"])
    qtbot.waitUntil(p.is_running, timeout=3000)

    started = time.perf_counter()
    p.stop(timeout_ms=1000)
    elapsed = time.perf_counter() - started

    assert elapsed < 0.2
    qtbot.waitUntil(lambda: p.state == ServerState.STOPPED, timeout=3000)


def test_unexpected_nonzero_exit_is_error_and_logged(qtbot):
    p = _make_proc()
    logs: list[str] = []
    p.log_received.connect(logs.append)

    p.start(sys.executable, ["-c", "raise SystemExit(7)"])

    qtbot.waitUntil(lambda: not p.is_running(), timeout=5000)
    assert p.state == ServerState.ERROR
    assert any("unexpected exit" in line and "7" in line for line in logs)


def test_failed_start_remains_error_after_finished_signal(qtbot):
    p = _make_proc()
    p.start("definitely-not-a-real-llama-server-executable", [])

    qtbot.waitUntil(lambda: p.state == ServerState.ERROR, timeout=5000)
    p._on_finished(-1, QProcess.CrashExit)
    assert p.state == ServerState.ERROR


def test_restart_starts_exactly_one_replacement(qtbot):
    p = _make_proc()
    logs: list[str] = []
    p.log_received.connect(logs.append)
    p.start(sys.executable, ["-c", "import time; time.sleep(30)"])
    qtbot.waitUntil(p.is_running, timeout=3000)

    p.restart(
        sys.executable,
        ["-c", "print('REPLACEMENT', flush=True)"],
        stop_timeout_ms=1000,
    )

    qtbot.waitUntil(lambda: any("REPLACEMENT" in x for x in logs), timeout=5000)
    qtbot.waitUntil(lambda: not p.is_running(), timeout=5000)
    assert sum("REPLACEMENT" in x for x in logs) == 1


def test_restart_when_stopped_starts_immediately(qtbot):
    p = _make_proc()
    logs: list[str] = []
    p.log_received.connect(logs.append)

    p.restart(sys.executable, ["-c", "print('NOW', flush=True)"])

    qtbot.waitUntil(lambda: any("NOW" in x for x in logs), timeout=5000)


def test_partial_stdout_and_stderr_are_flushed_with_prefix(qtbot):
    p = _make_proc()
    logs: list[str] = []
    p.log_received.connect(logs.append)
    code = "import sys; sys.stdout.write('OUT'); sys.stderr.write('ERR')"
    p.start(sys.executable, ["-c", code])

    qtbot.waitUntil(lambda: not p.is_running(), timeout=5000)
    assert "OUT" in logs
    assert "[stderr] ERR" in logs


class _FakeReply(QObject):
    finished = Signal()

    def __init__(self, status: int):
        super().__init__()
        self.status = status
        self.aborted = False
        self.deleted = False

    def attribute(self, _attribute):
        return self.status

    def abort(self):
        self.aborted = True

    def deleteLater(self):
        self.deleted = True


class _FakeNetworkManager:
    def __init__(self, reply: _FakeReply):
        self.reply = reply
        self.requests = []

    def get(self, request):
        self.requests.append(request)
        return self.reply


def test_health_request_has_one_active_reply_and_2xx_sets_ready(qtbot):
    reply = _FakeReply(204)
    manager = _FakeNetworkManager(reply)
    p = ServerProcess(network_manager=manager)
    p.start(
        sys.executable,
        ["-c", "import time; time.sleep(30)"],
        health_url="http://127.0.0.1:1/health",
    )
    qtbot.waitUntil(p.is_running, timeout=3000)

    p._check_health()
    p._check_health()
    assert len(manager.requests) == 1

    reply.finished.emit()
    assert p.state == ServerState.READY
    assert reply.deleted
    p.stop(timeout_ms=100)


def test_stop_aborts_active_health_reply(qtbot):
    reply = _FakeReply(0)
    p = ServerProcess(network_manager=_FakeNetworkManager(reply))
    p.start(
        sys.executable,
        ["-c", "import time; time.sleep(30)"],
        health_url="http://127.0.0.1:1/health",
    )
    qtbot.waitUntil(p.is_running, timeout=3000)
    p._check_health()

    p.stop(timeout_ms=100)

    assert reply.aborted
