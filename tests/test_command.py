"""Tests for safe command-line display formatting."""
from __future__ import annotations

import subprocess

from llama_app.core.command import format_display_command, redact_args


def test_format_display_command_redacts_sensitive_values():
    arguments = [
        "--api-key",
        "api-secret",
        "--host",
        "127.0.0.1",
        "--hf-token",
        "hf-secret",
    ]

    display = format_display_command("llama-server.exe", arguments)

    assert display == subprocess.list2cmdline(
        [
            "llama-server.exe",
            "--api-key",
            "********",
            "--host",
            "127.0.0.1",
            "--hf-token",
            "********",
        ]
    )
    assert "api-secret" not in display
    assert "hf-secret" not in display


def test_format_display_command_quotes_windows_paths_with_spaces():
    display = format_display_command(
        r"C:\Program Files\llama.cpp\llama-server.exe",
        ["--model", r"C:\My Models\model.gguf"],
    )

    assert display == subprocess.list2cmdline(
        [
            r"C:\Program Files\llama.cpp\llama-server.exe",
            "--model",
            r"C:\My Models\model.gguf",
        ]
    )
    assert '"C:\\Program Files\\llama.cpp\\llama-server.exe"' in display
    assert '"C:\\My Models\\model.gguf"' in display


def test_redact_args_does_not_mutate_input():
    arguments = ["--api-key", "api-secret", "--port", "8080"]

    redacted = redact_args(arguments)

    assert arguments == ["--api-key", "api-secret", "--port", "8080"]
    assert redacted == ["--api-key", "********", "--port", "8080"]
    assert redacted is not arguments
