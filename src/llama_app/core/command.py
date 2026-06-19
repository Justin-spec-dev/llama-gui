"""Helpers for safely formatting commands for display."""
from __future__ import annotations

import subprocess
from collections.abc import Sequence


_SENSITIVE_FLAGS = frozenset({"--api-key", "--hf-token"})


def redact_args(arguments: Sequence[str]) -> list[str]:
    """Return a copy of arguments with sensitive flag values masked."""
    redacted = list(arguments)
    for index, argument in enumerate(arguments[:-1]):
        if argument in _SENSITIVE_FLAGS:
            redacted[index + 1] = "********"
    return redacted


def format_display_command(program: str, arguments: Sequence[str]) -> str:
    """Format a redacted command using Windows command-line quoting rules."""
    return subprocess.list2cmdline([program, *redact_args(arguments)])
