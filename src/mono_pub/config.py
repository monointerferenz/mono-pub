"""Configuration loading for mono-pub."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG_FILENAME = "configuartion.yaml"
CONFIG_ENV_VAR = "MONO_PUB_CONFIG"

PATH_KEYS = ("templates_path",)
PATH_GROUP_KEYS = (
    "drafts_path",
    "releases_path",
    "assets_path",
    "publish_base",
    "publish_path",
    "publish_assets_path",
)


def _resolve_path(path: str, base_dir: Path) -> str:
    resolved = Path(path).expanduser()
    if not resolved.is_absolute():
        resolved = base_dir / resolved
    return str(resolved)


def _resolve_config_paths(config: dict[str, Any], base_dir: Path) -> dict[str, Any]:
    for key in PATH_KEYS:
        if key in config:
            config[key] = _resolve_path(config[key], base_dir)

    for key in PATH_GROUP_KEYS:
        paths = config.get(key, {})
        for path_key, path in paths.items():
            paths[path_key] = _resolve_path(path, base_dir)

    return config

def get_project_root() -> Path:
    return Path(__file__).parent.parent

def load_config(path: str | None = None) -> dict[str, Any]:
    config_path = _resolve_config_path(path)

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as file:
        return _resolve_config_paths(yaml.safe_load(file) or {}, config_path.parent)


def _resolve_config_path(path: str | None) -> Path:
    if path is not None:
        return Path(path).expanduser().resolve()

    env_path = os.environ.get(CONFIG_ENV_VAR)
    if env_path:
        return Path(env_path).expanduser().resolve()

    # Search working-directory-local config
    local = get_project_root().parent / DEFAULT_CONFIG_FILENAME
    if local.exists():
        return local

    # Fall back to user home
    return Path.home() / DEFAULT_CONFIG_FILENAME
