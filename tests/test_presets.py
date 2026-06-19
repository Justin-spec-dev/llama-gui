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


def test_preset_corrupt_file_recovers_with_backup(tmp_path: Path):
    path = tmp_path / "presets.json"
    backup = tmp_path / "presets.json.bak"
    backup.write_text("stale backup", encoding="utf-8")
    path.write_text("not valid json{", encoding="utf-8")
    store = PresetStore(path=path)

    assert store.list() == []
    assert store.recovery_notice is not None
    assert str(backup) in store.recovery_notice
    assert "Original error:" in store.recovery_notice
    assert backup.read_text(encoding="utf-8") == "not valid json{"
    assert json.loads(path.read_text(encoding="utf-8")) == {
        "version": 1,
        "presets": [],
    }


@pytest.mark.parametrize(
    "payload",
    [
        {"version": 1},
        {"version": 1, "presets": {}},
        {"version": 1, "presets": [{"name": "missing-fields"}]},
        {
            "version": 1,
            "presets": [
                {
                    "name": "bad-config",
                    "config": {"unknown_option": True},
                    "updated_at": "2026-01-01T00:00:00Z",
                }
            ],
        },
        {
            "version": 1,
            "presets": [
                {
                    "name": "bad-config-type",
                    "config": [],
                    "updated_at": "2026-01-01T00:00:00Z",
                }
            ],
        },
    ],
)
def test_preset_malformed_structure_recovers(tmp_path: Path, payload: object):
    path = tmp_path / "presets.json"
    original = json.dumps(payload)
    path.write_text(original, encoding="utf-8")

    store = PresetStore(path=path)

    assert store.list() == []
    assert store.recovery_notice is not None
    assert str(tmp_path / "presets.json.bak") in store.recovery_notice
    assert "Original error:" in store.recovery_notice
    assert (tmp_path / "presets.json.bak").read_text(encoding="utf-8") == original
    assert json.loads(path.read_text(encoding="utf-8"))["presets"] == []


def test_preset_save_omits_secrets_from_memory_and_disk(tmp_path: Path):
    path = tmp_path / "presets.json"
    store = PresetStore(path=path)
    config = _make_config("secret")
    config.api_key = "api-secret"
    config.hf_token = "hf-secret"

    store.save(
        Preset(
            name="secret",
            config=config,
            updated_at="2026-01-01T00:00:00Z",
        )
    )

    assert config.api_key == "api-secret"
    assert config.hf_token == "hf-secret"
    stored = store.get("secret")
    assert stored.config.api_key is None
    assert stored.config.hf_token is None
    serialized_config = json.loads(path.read_text(encoding="utf-8"))["presets"][0]["config"]
    assert serialized_config["api_key"] is None
    assert serialized_config["hf_token"] is None
    assert "api-secret" not in path.read_text(encoding="utf-8")
    assert "hf-secret" not in path.read_text(encoding="utf-8")


@pytest.mark.parametrize("create_file", [False, True])
def test_preset_valid_or_new_file_has_no_recovery_notice(
    tmp_path: Path, create_file: bool
):
    path = tmp_path / "presets.json"
    if create_file:
        path.write_text('{"version": 1, "presets": []}', encoding="utf-8")

    store = PresetStore(path=path)

    assert store.recovery_notice is None


def test_existing_secret_fields_are_readable_and_removed_on_save(tmp_path: Path):
    path = tmp_path / "presets.json"
    config = _make_config("legacy")
    config.api_key = "legacy-api-secret"
    config.hf_token = "legacy-hf-secret"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "presets": [
                    {
                        "name": "legacy",
                        "config": config.__dict__,
                        "updated_at": "2026-01-01T00:00:00Z",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    store = PresetStore(path=path)
    loaded = store.get("legacy")
    assert loaded.config.api_key == "legacy-api-secret"
    assert loaded.config.hf_token == "legacy-hf-secret"

    store.save(loaded)

    assert store.get("legacy").config.api_key is None
    assert store.get("legacy").config.hf_token is None
    serialized = path.read_text(encoding="utf-8")
    assert "legacy-api-secret" not in serialized
    assert "legacy-hf-secret" not in serialized


def test_preset_save_creates_parent_dirs(tmp_path: Path):
    path = tmp_path / "subdir" / "presets.json"
    store = PresetStore(path=path)
    store.save(Preset(name="x", config=_make_config("x"), updated_at="2026-01-01T00:00:00Z"))
    assert path.exists()
