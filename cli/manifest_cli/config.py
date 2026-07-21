"""Persistent CLI configuration (server URL + acting user).

Resolution order for every value: explicit CLI flag > environment variable >
config file (~/.manifest/config.json) > built-in default.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("MANIFEST_CONFIG_DIR", Path.home() / ".manifest"))
CONFIG_FILE = CONFIG_DIR / "config.json"
DEFAULT_URL = "http://localhost:8080"


def load() -> dict:
    try:
        return json.loads(CONFIG_FILE.read_text())
    except (OSError, ValueError):
        return {}


def save(data: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(data, indent=2))


def resolve_url(flag: str | None) -> str:
    return flag or os.environ.get("MANIFEST_URL") or load().get("url") or DEFAULT_URL


def resolve_user(flag: str | None) -> str | None:
    return flag or os.environ.get("MANIFEST_USER") or load().get("user")
