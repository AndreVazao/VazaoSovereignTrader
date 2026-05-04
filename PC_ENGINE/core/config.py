from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"
LOG_DIR = DATA_DIR / "logs"
CONFIG_LOCAL = CONFIG_DIR / "config.local.json"
CONFIG_EXAMPLE = CONFIG_DIR / "config.example.json"


def ensure_runtime_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> Dict[str, Any]:
    ensure_runtime_dirs()
    path = CONFIG_LOCAL if CONFIG_LOCAL.exists() else CONFIG_EXAMPLE
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def env_value(name: str, default: str = "") -> str:
    return os.getenv(name, default)
