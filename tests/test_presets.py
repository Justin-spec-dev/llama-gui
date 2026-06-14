"""Tests for PresetStore persistence."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from llama_app.core.config import Config
from llama_app.core.presets import Preset, PresetStore


def _make_config(name: str) -> Config:
    return Config(
        server_path="C:/llama/llama-server.exe",
        model_path=f"C:/models/{name}.gguf",
        n_gpu_layers=99,
        ctx_size=8192,
    )


def test_preset_round_trip(tmp_path: Path):
    path = tmp_path / "presets.json"
    store = PresetStore(path=path)
    cfg = _make_config("qwen")
    preset = Preset(name="qwen-32b-8k", config=cfg, updated_at="2026-06-14T10:00:00Z")
    store.save(preset)

    store2 = PresetStore(path=path)
    loaded = store2.get("qwen-32b-8k")
    assert loaded.name == "qwen-32b-8k"
    assert loaded.config.model_path == "C:/models/qwen.gguf"
    assert loaded.config.n_gpu_layers == 99
    assert loaded.config.ctx_size == 8192


def test_preset_list_returns_sorted(tmp_path: Path):
    store = PresetStore(path=tmp_path / "presets.json")
    for name in ["charlie", "alpha", "bravo"]:
        store.save(Preset(name=name, config=_make_config(name), updated_at="2026-01-01T00:00:00Z"))
    names = [p.name for p in store.list()]
    assert names == ["alpha", "bravo", "charlie"]


def test_preset_delete(tmp_path: Path):
    store = PresetStore(path=tmp_path / "presets.json")
    store.save(Preset(name="x", config=_make_config("x"), updated_at="2026-01-01T00:00:00Z"))
    store.delete("x")
    with pytest.raises(KeyError):
        store.get("x")


def test_preset_rename(tmp_path: Path):
    store = PresetStore(path=tmp_path / "presets.json")
    store.save(Preset(name="old", config=_make_config("old"), updated_at="2026-01-01T00:00:00Z"))
    store.rename("old", "new")
    assert store.get("new").name == "new"
    with pytest.raises(KeyError):
        store.get("old")


def test_preset_get_missing_raises(tmp_path: Path):
    store = PresetStore(path=tmp_path / "presets.json")
    with pytest.raises(KeyError, match="not found"):
        store.get("nope")


def test_preset_corrupt_file_raises_with_backup(tmp_path: Path):
    path = tmp_path / "presets.json"
    path.write_text("not valid json{", encoding="utf-8")
    with pytest.raises(ValueError, match="corrupt"):
        PresetStore(path=path)
    assert (tmp_path / "presets.json.bak").exists()


def test_preset_save_creates_parent_dirs(tmp_path: Path):
    path = tmp_path / "subdir" / "presets.json"
    store = PresetStore(path=path)
    store.save(Preset(name="x", config=_make_config("x"), updated_at="2026-01-01T00:00:00Z"))
    assert path.exists()
