"""Tests for the Config dataclass and ConfigBuilder."""
from __future__ import annotations

import pytest

from llama_app.core.config import Config, ConfigBuilder


def test_config_minimal_required_fields():
    """Config requires only nonblank server_path and model_path values."""
    cfg = Config(server_path="C:/llama/llama-server.exe", model_path="C:/models/qwen.gguf")
    assert cfg.server_path == "C:/llama/llama-server.exe"
    assert cfg.model_path == "C:/models/qwen.gguf"
    assert cfg.mmproj_path is None
    assert cfg.n_gpu_layers is None


def test_config_default_booleans():
    cfg = Config(server_path="x", model_path="y")
    assert cfg.mlock is False
    assert cfg.no_mmap is False
    assert cfg.enable_ui is None
    assert cfg.metrics is False
    assert cfg.verbose is False


def test_config_to_args_minimum():
    """Empty config still produces a valid -m flag, plus nothing else."""
    cfg = Config(server_path="llama-server.exe", model_path="model.gguf")
    args = ConfigBuilder.to_args(cfg)
    assert args == ["-m", "model.gguf"]


def test_config_to_args_uses_long_form_for_known_aliases():
    cfg = Config(
        server_path="llama-server.exe",
        model_path="m.gguf",
        n_gpu_layers=99,
    )
    args = ConfigBuilder.to_args(cfg)
    assert "--n-gpu-layers" in args
    assert "99" in args
    assert "-m" in args
    assert "m.gguf" in args


def test_config_to_args_skips_none():
    cfg = Config(server_path="s", model_path="m", n_gpu_layers=None, port=None)
    args = ConfigBuilder.to_args(cfg)
    assert "--n-gpu-layers" not in args
    assert "--port" not in args


def test_config_to_args_emits_boolean_true_flag():
    cfg = Config(server_path="s", model_path="m", mlock=True)
    args = ConfigBuilder.to_args(cfg)
    assert "--mlock" in args


def test_config_to_args_emits_no_form_for_negation():
    cfg = Config(server_path="s", model_path="m", no_mmap=True)
    args = ConfigBuilder.to_args(cfg)
    assert "--no-mmap" in args
    assert "--mmap" not in args


def test_config_to_args_string_enum():
    cfg = Config(
        server_path="s",
        model_path="m",
        flash_attn="on",
    )
    args = ConfigBuilder.to_args(cfg)
    assert "--flash-attn" in args
    assert "on" in args


@pytest.mark.parametrize("field", ["server_path", "model_path"])
def test_config_validate_rejects_blank_required_paths(field):
    values = {"server_path": "server.exe", "model_path": "model.gguf"}
    values[field] = "   "
    cfg = Config(**values)

    with pytest.raises(ValueError, match=field):
        cfg.validate()


def test_config_validate_rejects_ubatch_larger_than_batch():
    cfg = Config(
        server_path="server.exe",
        model_path="model.gguf",
        batch_size=128,
        ubatch_size=256,
    )

    with pytest.raises(ValueError, match="ubatch_size"):
        cfg.validate()
