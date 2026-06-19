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
    """Return True if ``(host, port)`` appears free for llama-server to bind.

    We attempt a connect() with a short timeout. If the connect succeeds,
    something is already listening on that port — so it is *not* available.
    If the connect is refused or times out, the port is treated as free.

    Why not bind()? Binding with ``SO_REUSEADDR`` is unreliable on Windows: it
    can succeed for ports that are actively in use by another socket (e.g.
    TIME_WAIT, or another process that already bound first). A connect probe
    better reflects "will llama-server actually be able to listen here?".

    Note: this is still a best-effort TOCTOU check — the port may be claimed
    between this call and llama-server's actual bind. llama-server itself
    will report a clearer error in that case.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        try:
            s.connect((host, port))
        except (ConnectionRefusedError, socket.timeout, OSError):
            # Refused / timed out / network unreachable => treat as free.
            return True
        except Exception:
            return True
        # connect() succeeded — something is already listening.
        return False