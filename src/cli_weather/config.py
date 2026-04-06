from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict


APP_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "cli-weather"
CONFIG_PATH = APP_DIR / "config.json"

DEFAULT_CONFIG: Dict[str, Any] = {
    "provider": "metno",
    "location": "",
    "recipient": "",
    "sender": "",
    "smtp_host": "",
    "smtp_port": 587,
    "smtp_username": "",
    "smtp_password": "",
    "smtp_starttls": True,
    "smtp_ssl": False,
    "visualcrossing_api_key": "",
}

ENV_VAR_MAP = {
    "provider": "CLI_WEATHER_PROVIDER",
    "location": "CLI_WEATHER_LOCATION",
    "recipient": "CLI_WEATHER_RECIPIENT",
    "sender": "CLI_WEATHER_SENDER",
    "smtp_host": "CLI_WEATHER_SMTP_HOST",
    "smtp_port": "CLI_WEATHER_SMTP_PORT",
    "smtp_username": "CLI_WEATHER_SMTP_USERNAME",
    "smtp_password": "CLI_WEATHER_SMTP_PASSWORD",
    "smtp_starttls": "CLI_WEATHER_SMTP_STARTTLS",
    "smtp_ssl": "CLI_WEATHER_SMTP_SSL",
    "visualcrossing_api_key": "CLI_WEATHER_VISUALCROSSING_API_KEY",
}


def load_config(path: Path = CONFIG_PATH) -> Dict[str, Any]:
    config = DEFAULT_CONFIG.copy()
    if path.exists():
        with path.open("r", encoding="utf-8") as handle:
            stored = json.load(handle)
        config.update(stored)
    config.update(_load_environment_overrides())
    return config


def save_config(values: Dict[str, Any], path: Path = CONFIG_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    config = DEFAULT_CONFIG.copy()
    config.update(values)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(config, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return path


def set_config_values(updates: Dict[str, Any], path: Path = CONFIG_PATH) -> Dict[str, Any]:
    config = load_config(path)
    config.update({key: value for key, value in updates.items() if value is not None})
    save_config(config, path)
    return config


def _load_environment_overrides() -> Dict[str, Any]:
    overrides: Dict[str, Any] = {}
    for key, env_var in ENV_VAR_MAP.items():
        raw_value = os.environ.get(env_var)
        if raw_value is None or raw_value == "":
            continue
        overrides[key] = _coerce_env_value(key, raw_value)
    return overrides


def _coerce_env_value(key: str, value: str) -> Any:
    if key == "smtp_port":
        return int(value)
    if key in {"smtp_starttls", "smtp_ssl"}:
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
        raise ValueError(
            f"Environment variable {ENV_VAR_MAP[key]} must be true/false, yes/no, on/off, or 1/0."
        )
    return value
