"""Speed test against a running llama-server.

Sends a streaming chat-completion request and measures:
    * ``tokens``         — number of SSE chunks received
    * ``elapsed_s``      — total wall time
    * ``first_token_ms`` — time until the first content delta
    * ``tokens_per_sec`` — ``tokens / (elapsed_s - first_token_s)``
"""
from __future__ import annotations

import json
import time
from typing import Optional

import httpx
from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal


def _run_speed_test(
    host: str,
    port: int,
    api_key: Optional[str],
    prompt: str,
    max_tokens: int,
    on_finished,
    on_failed,
) -> None:
    url = f"http://{host}:{port}/v1/chat/completions"
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    payload = {
        "model": "any",
        "messages": [{"role": "user", "content": prompt}],
        "stream": True,
        "max_tokens": max_tokens,
    }
    t_start = time.perf_counter()
    t_first: float | None = None
    tokens = 0
    try:
        with httpx.stream("POST", url, json=payload, headers=headers, timeout=30) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if not line.startswith("data: "):
                    continue
                if line == "data: [DONE]":
                    break
                if t_first is None:
                    t_first = time.perf_counter() - t_start
                tokens += 1
    except (httpx.HTTPError, OSError) as e:
        on_failed(str(e))
        return
    t_total = time.perf_counter() - t_start
    t_first = t_first if t_first is not None else t_total
    decode_time = max(t_total - t_first, 1e-6)
    on_finished(
        {
            "tokens": tokens,
            "elapsed_s": t_total,
            "first_token_ms": t_first * 1000.0,
            "tokens_per_sec": tokens / decode_time,
        }
    )


class _SpeedTestTask(QRunnable):
    def __init__(
        self,
        host: str,
        port: int,
        api_key: Optional[str],
        prompt: str,
        max_tokens: int,
        on_finished,
        on_failed,
    ):
        super().__init__()
        self._host = host
        self._port = port
        self._api_key = api_key
        self._prompt = prompt
        self._max_tokens = max_tokens
        self._on_finished = on_finished
        self._on_failed = on_failed

    def run(self) -> None:  # invoked on a worker thread
        _run_speed_test(
            self._host,
            self._port,
            self._api_key,
            self._prompt,
            self._max_tokens,
            self._on_finished,
            self._on_failed,
        )


class SpeedTester(QObject):
    finished = Signal(dict)
    failed = Signal(str)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._pool = QThreadPool.globalInstance()

    def run(
        self,
        host: str,
        port: int,
        api_key: Optional[str],
        prompt: str,
        max_tokens: int = 200,
    ) -> None:
        task = _SpeedTestTask(
            host,
            port,
            api_key,
            prompt,
            max_tokens,
            self.finished.emit,
            self.failed.emit,
        )
        self._pool.start(task)
