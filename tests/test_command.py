"""Tests for safe command-line display formatting."""
from __future__ import annotations

import subprocess

import pytest

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


@pytest.mark.parametrize(
    ("flag", "secret", "arguments", "expected"),
    [
        (
            "--api-key",
            "api-secret",
            ["--api-key", "api-secret", "--port", "8080"],
            ["--api-key", "********", "--port", "8080"],
        ),
        (
            "--api-key",
            "api-secret",
            ["--api-key=api-secret", "--port", "8080"],
            ["--api-key=********", "--port", "8080"],
        ),
        (
            "--hf-token",
            "hf-secret",
            ["--hf-token", "hf-secret", "--port", "8080"],
            ["--hf-token", "********", "--port", "8080"],
        ),
        (
            "--hf-token",
            "hf-secret",
            ["--hf-token=hf-secret", "--port", "8080"],
            ["--hf-token=********", "--port", "8080"],
        ),
    ],
)
def test_redact_args_masks_sensitive_values_without_mutating_input(
    flag, secret, arguments, expected
):
    original = arguments.copy()

    redacted = redact_args(arguments)

    assert arguments == original
    assert redacted == expected
    assert secret not in redacted
    assert all(secret not in argument for argument in redacted)
    assert redacted[0].startswith(flag)
    assert redacted is not arguments
