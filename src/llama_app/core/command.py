"""Helpers for safely formatting commands for display."""
from __future__ import annotations

import subprocess
from collections.abc import Sequence


_SENSITIVE_FLAGS = frozenset({"--api-key", "--hf-token"})


def redact_args(arguments: Sequence[str]) -> list[str]:
    """Return a copy of arguments with sensitive flag values masked."""
    redacted = list(arguments)
    for index, argument in enumerate(arguments):
        if argument in _SENSITIVE_FLAGS and index + 1 < len(arguments):
            redacted[index + 1] = "********"
        elif any(argument.startswith(f"{flag}=") for flag in _SENSITIVE_FLAGS):
            flag, _, _ = argument.partition("=")
            redacted[index] = f"{flag}=********"
    return redacted


def format_display_command(program: str, arguments: Sequence[str]) -> str:
    """Format a redacted command using Windows command-line quoting rules."""
    return subprocess.list2cmdline([program, *redact_args(arguments)])
