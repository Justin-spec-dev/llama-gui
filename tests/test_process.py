"""Tests for ServerProcess — start, stop, log streaming.

We exercise the real ``QProcess`` machinery by spawning a benign command
(``/bin/sh -c 'echo hello'`` or ``/bin/sleep``) and verifying state
transitions and log capture.
"""
from __future__ import annotations

import sys
import time

import pytest

from llama_app.core.process import ServerProcess, ServerState


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
    p.start("/bin/sh", ["-c", "sleep 0.5"])
    qtbot.waitUntil(lambda: p.state != ServerState.STOPPED, timeout=3000)
    assert p.state in {ServerState.STARTING, ServerState.LOADING, ServerState.READY}
    p.stop(timeout_ms=2000)


def test_log_streaming_receives_stdout(qtbot):
    p = _make_proc()
    received: list[str] = []
    p.log_received.connect(lambda s: received.append(s))
    p.start("/bin/sh", ["-c", "echo HELLO_FROM_TEST"])
    qtbot.waitUntil(lambda: any("HELLO_FROM_TEST" in s for s in received), timeout=5000)
    assert any("HELLO_FROM_TEST" in s for s in received)
    p.stop(timeout_ms=2000)


def test_stop_returns_to_stopped_state(qtbot):
    p = _make_proc()
    p.start("/bin/sh", ["-c", "sleep 10"])
    qtbot.waitUntil(lambda: p.is_running(), timeout=3000)
    p.stop(timeout_ms=3000)
    qtbot.waitUntil(lambda: p.state == ServerState.STOPPED, timeout=3000)
    assert p.state == ServerState.STOPPED
    assert p.pid() is None
