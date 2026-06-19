"""Persistence layer for user-defined presets.

A preset is a named ``Config`` snapshot. The store is a single JSON file with
atomic writes. Corruption is detected on load and a ``.bak`` is created.
"""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from pathlib import Path

from .config import Config


PRESETS_VERSION = 1


@dataclass
class Preset:
    name: str
    config: Config
    updated_at: str  # ISO 8601

    @staticmethod
    def now(name: str, config: Config) -> "Preset":
        return Preset(
            name=name,
            config=config,
            updated_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        )


def default_path() -> Path:
    """Return the default presets.json location: %APPDATA%/llama-gui/presets.json."""
    if os.name == "nt":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(base) / "llama-gui" / "presets.json"
    # Sensible fallback for development on non-Windows
    return Path.home() / ".config" / "llama-gui" / "presets.json"


class PresetStore:
    """JSON-backed preset store with atomic writes."""

    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path is not None else default_path()
        self.recovery_notice: str | None = None
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._presets: dict[str, Preset] = {}
            self._save_atomic()  # create empty file
            return
        try:
            raw = self.path.read_text(encoding="utf-8")
            data = json.loads(raw)
            if not isinstance(data, dict):
                raise ValueError("presets file root must be an object")
            entries = data["presets"]
            if not isinstance(entries, list):
                raise ValueError("presets must be a list")
            self._presets = {
                entry["name"]: Preset(
                    name=entry["name"],
                    config=Config(**entry["config"]),
                    updated_at=entry["updated_at"],
                )
                for entry in entries
            }
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            self._recover(e)

    def _recover(self, error: Exception) -> None:
        backup = self.path.with_suffix(self.path.suffix + ".bak")
        self.path.replace(backup)
        self.recovery_notice = (
            f"Presets file was recovered. Backed up to {backup}. "
            f"Original error: {error}"
        )
        self._presets = {}
        self._save_atomic()

    def list(self) -> list[Preset]:
        return sorted(self._presets.values(), key=lambda p: p.name.lower())

    def get(self, name: str) -> Preset:
        if name not in self._presets:
            raise KeyError(f"Preset '{name}' not found")
        return self._presets[name]

    def save(self, preset: Preset) -> None:
        sanitized = replace(
            preset,
            config=replace(preset.config, api_key=None, hf_token=None),
        )
        self._presets[sanitized.name] = sanitized
        self._save_atomic()

    def delete(self, name: str) -> None:
        if name not in self._presets:
            raise KeyError(f"Preset '{name}' not found")
        del self._presets[name]
        self._save_atomic()

    def rename(self, old: str, new: str) -> None:
        if old not in self._presets:
            raise KeyError(f"Preset '{old}' not found")
        if new in self._presets:
            raise ValueError(f"Preset '{new}' already exists")
        p = self._presets.pop(old)
        p.name = new
        self._presets[new] = p
        self._save_atomic()

    def _save_atomic(self) -> None:
        payload = {
            "version": PRESETS_VERSION,
            "presets": [
                {
                    "name": p.name,
                    "config": asdict(p.config),
                    "updated_at": p.updated_at,
                }
                for p in self._presets.values()
            ],
        }
        # Atomic write: write to temp file in same dir, then rename.
        fd, tmp_name = tempfile.mkstemp(
            dir=self.path.parent, prefix=".presets-", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
            os.replace(tmp_name, self.path)
        except Exception:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)
            raise
