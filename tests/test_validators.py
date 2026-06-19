"""Tests for path and port validation."""
from __future__ import annotations

import socket
from pathlib import Path

import pytest

from llama_app.core.validators import (
    validate_executable,
    validate_model_file,
    validate_port_available,
)


def test_validate_executable_accepts_existing(tmp_path: Path):
    exe = tmp_path / "llama-server.exe"
    exe.write_bytes(b"MZ")
    assert validate_executable(str(exe)) == exe.resolve()


def test_validate_executable_rejects_missing(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="llama-server.exe not found"):
        validate_executable(str(tmp_path / "missing.exe"))


def test_validate_executable_rejects_non_windows_extension(tmp_path: Path):
    bad = tmp_path / "llama-server"
    bad.write_bytes(b"MZ")
    with pytest.raises(ValueError, match="must end in .exe"):
        validate_executable(str(bad))


def test_validate_model_file_accepts_gguf(tmp_path: Path):
    model = tmp_path / "qwen.gguf"
    model.write_bytes(b"GGUF")
    assert validate_model_file(str(model)) == model.resolve()


def test_validate_model_file_accepts_no_extension(tmp_path: Path):
    """Some llama.cpp builds use no extension for the model."""
    model = tmp_path / "model"
    model.write_bytes(b"GGUF")
    assert validate_model_file(str(model)) == model.resolve()


def test_validate_model_file_rejects_missing(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        validate_model_file(str(tmp_path / "missing.gguf"))


def test_validate_port_available_detects_listening_server():
    """When something is listening, validate_port_available must return False."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]
        assert validate_port_available("127.0.0.1", port) is False


def test_validate_port_available_finds_free_port():
    """When nothing is listening, validate_port_available must return True."""
    # Find a port, close it, then ask the validator. Refusal means free.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    # Port is now closed; the connect probe should be refused.
    assert validate_port_available("127.0.0.1", port) is True