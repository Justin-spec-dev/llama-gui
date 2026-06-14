"""Shared pytest fixtures for llama-gui tests."""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure src/ is on the import path so tests can import llama_app
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
