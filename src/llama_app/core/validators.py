"""Validation helpers for paths and ports."""
from __future__ import annotations

import socket
from pathlib import Path


def validate_executable(path: str) -> Path:
    """Verify that ``path`` points to a Windows .exe file. Return resolved Path."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"llama-server.exe not found: {path}")
    if p.suffix.lower() != ".exe":
        raise ValueError(f"Server binary must end in .exe: {path}")
    return p.resolve()


def validate_model_file(path: str) -> Path:
    """Verify that ``path`` points to an existing model file. Return resolved Path."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Model file not found: {path}")
    return p.resolve()


def validate_mmproj_file(path: str) -> Path:
    """Verify that ``path`` points to an existing mmproj file. Return resolved Path."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"mmproj file not found: {path}")
    return p.resolve()


def validate_port_available(host: str, port: int) -> bool:
    """Return True if ``(host, port)`` can be bound (i.e. port appears free).

    Note: this is a best-effort check. A free port may become occupied between
    the check and the actual llama-server start. llama-server itself will
    report a clearer error in that case.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind((host, port))
        except OSError:
            return False
    return True