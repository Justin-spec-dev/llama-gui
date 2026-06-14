"""Tests for SpeedTester — uses a tiny in-process HTTP echo server."""
from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from llama_app.core.speedtest import SpeedTester


class _StreamingChatHandler(BaseHTTPRequestHandler):
    """Emits a fake OpenAI-compatible streaming response with 5 chunks."""

    def log_message(self, format, *args):  # silence stderr
        return

    def do_POST(self):  # noqa: N802
        if self.path != "/v1/chat/completions":
            self.send_response(404)
            self.end_headers()
            return
        # Read body (we don't need its content)
        length = int(self.headers.get("Content-Length", 0))
        self.rfile.read(length)

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        for i in range(5):
            chunk = {
                "choices": [
                    {"delta": {"content": f"tok{i} "}}
                ]
            }
            self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode())
            self.wfile.flush()
            time.sleep(0.01)
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()


@pytest.fixture
def fake_server():
    server = HTTPServer(("127.0.0.1", 0), _StreamingChatHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield port
    server.shutdown()
    server.server_close()


def test_speed_tester_returns_valid_result(qtbot, fake_server):
    port = fake_server
    tester = SpeedTester()
    result_holder: dict = {}

    def on_finished(d):
        result_holder.update(d)

    def on_failed(msg):
        result_holder["error"] = msg

    tester.finished.connect(on_finished)
    tester.failed.connect(on_failed)
    tester.run("127.0.0.1", port, None, "hello world", max_tokens=10)

    qtbot.waitUntil(lambda: bool(result_holder), timeout=10000)
    assert "error" not in result_holder
    assert result_holder["tokens"] == 5
    assert result_holder["elapsed_s"] > 0
    assert result_holder["first_token_ms"] >= 0
    assert result_holder["tokens_per_sec"] > 0


def test_speed_tester_handles_connection_error(qtbot):
    tester = SpeedTester()
    failed: list[str] = []

    def on_failed(msg):
        failed.append(msg)

    tester.failed.connect(on_failed)
    # Use a port that almost certainly isn't listening
    tester.run("127.0.0.1", 1, None, "hi")

    qtbot.waitUntil(lambda: bool(failed), timeout=10000)
    assert failed
