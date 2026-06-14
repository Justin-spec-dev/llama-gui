"""Background resource sampler (CPU/RAM/VRAM/GPU%).

Uses ``psutil`` for CPU and memory. Tries ``pynvml`` for NVIDIA GPU stats;
falls back gracefully to ``None`` if the import or device query fails.
"""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from typing import Callable

from PySide6.QtCore import QObject, QTimer, Signal


def _init_nvml():
    """Import and initialize pynvml. Raise on failure."""
    import pynvml

    pynvml.nvmlInit()
    return pynvml


@dataclass
class Sample:
    cpu_total: float
    cpu_proc: float | None
    mem_total_gb: float
    mem_proc_gb: float | None
    gpu_util: float | None
    vram_gb: float | None
    timestamp: float


class ResourceMonitor(QObject):
    sample = Signal(dict)        # Sample.asdict()
    process_gone = Signal()

    def __init__(self, get_pid: Callable[[], int | None], interval_ms: int = 1000):
        super().__init__()
        self._get_pid = get_pid
        self._interval_ms = interval_ms
        self._timer: QTimer | None = None
        self._pynvml = None
        self._nvml_handle = None
        try:
            self._pynvml = _init_nvml()
            self._nvml_handle = self._pynvml.nvmlDeviceGetHandleByIndex(0)
        except Exception:
            self._pynvml = None
            self._nvml_handle = None

    def start(self) -> None:
        if self._timer:
            return
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._sample)
        self._timer.start(self._interval_ms)
        # Prime so the first emission isn't delayed by interval_ms
        self._sample()

    def stop(self) -> None:
        if self._timer:
            self._timer.stop()
            self._timer = None

    def _sample(self) -> None:
        import psutil

        pid = self._get_pid()
        cpu_total = psutil.cpu_percent()
        mem_total_gb = psutil.virtual_memory().used / (1024 ** 3)
        cpu_proc: float | None = None
        mem_proc_gb: float | None = None

        if pid is not None and psutil.pid_exists(pid):
            try:
                p = psutil.Process(pid)
                cpu_proc = p.cpu_percent()
                mem_proc_gb = p.memory_info().rss / (1024 ** 3)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                self.process_gone.emit()
        elif pid is not None and not psutil.pid_exists(pid):
            self.process_gone.emit()

        gpu_util: float | None = None
        vram_gb: float | None = None
        if self._pynvml is not None and self._nvml_handle is not None:
            try:
                util = self._pynvml.nvmlDeviceGetUtilizationRates(self._nvml_handle)
                mem = self._pynvml.nvmlDeviceGetMemoryInfo(self._nvml_handle)
                gpu_util = float(util.gpu)
                vram_gb = mem.used / (1024 ** 3)
            except Exception:
                gpu_util = None
                vram_gb = None

        sample = Sample(
            cpu_total=cpu_total,
            cpu_proc=cpu_proc,
            mem_total_gb=mem_total_gb,
            mem_proc_gb=mem_proc_gb,
            gpu_util=gpu_util,
            vram_gb=vram_gb,
            timestamp=time.time(),
        )
        self.sample.emit(asdict(sample))