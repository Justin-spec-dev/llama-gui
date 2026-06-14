"""Tests for ResourceMonitor — uses real psutil, mocks pynvml when needed."""
from __future__ import annotations

import os
import time

import psutil
import pytest

from llama_app.core.monitor import ResourceMonitor, Sample


def _monitor_with_pid(pid: int) -> ResourceMonitor:
    return ResourceMonitor(get_pid=lambda: pid)


def test_sample_dataclass_fields():
    s = Sample(
        cpu_total=12.5,
        cpu_proc=3.1,
        mem_total_gb=8.0,
        mem_proc_gb=2.0,
        gpu_util=50.0,
        vram_gb=4.0,
        timestamp=0.0,
    )
    assert s.cpu_total == 12.5
    assert s.gpu_util == 50.0


def test_monitor_emits_sample_with_current_pid(qtbot):
    """The monitor should produce at least one sample with the current PID."""
    samples: list[Sample] = []
    mon = _monitor_with_pid(os.getpid())
    mon.sample.connect(lambda d: samples.append(Sample(**d)))
    mon.start()
    qtbot.waitUntil(lambda: len(samples) >= 1, timeout=3000)
    mon.stop()
    assert samples[0].cpu_total >= 0.0
    assert samples[0].mem_total_gb > 0.0


def test_monitor_emits_process_gone_when_pid_invalid(qtbot):
    gone_count = [0]
    mon = _monitor_with_pid(99999)  # unlikely-to-exist PID
    mon.process_gone.connect(lambda: gone_count.__setitem__(0, gone_count[0] + 1))
    mon.start()
    # First sample should detect the dead PID and emit
    qtbot.waitUntil(lambda: gone_count[0] >= 1, timeout=3000)
    mon.stop()


def test_monitor_handles_missing_pynvml_gracefully(qtbot, monkeypatch):
    """If pynvml import fails, gpu fields are None — no exception."""
    import llama_app.core.monitor as monitor_mod

    def fake_init() -> None:
        raise ImportError("no nvidia")

    monkeypatch.setattr(monitor_mod, "_init_nvml", fake_init)
    samples: list[Sample] = []
    mon = _monitor_with_pid(os.getpid())
    mon.sample.connect(lambda d: samples.append(Sample(**d)))
    mon.start()
    qtbot.waitUntil(lambda: len(samples) >= 1, timeout=3000)
    mon.stop()
    assert samples[0].gpu_util is None
    assert samples[0].vram_gb is None