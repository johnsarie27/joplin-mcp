"""JSON config file loading (token, host, port, notebook access)."""

import json
import os
from pathlib import Path

DEFAULT_CONFIG_PATH = "config.json"
VALID_ACCESS_LEVELS = frozenset({"read", "write"})


class ConfigError(Exception):
    """Raised when the config file is missing, unreadable, or malformed."""


def config_path() -> Path:
    return Path(os.environ.get("JOPLIN_CONFIG", DEFAULT_CONFIG_PATH))


def load_config() -> dict:
    path = config_path()
    if not path.is_file():
        raise ConfigError(
            f"Joplin config file not found at '{path}'. Set JOPLIN_CONFIG to its "
            "path, or create config.json in the working directory (copy "
            "config.example.json and fill it in)."
        )
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        raise ConfigError(f"Config file '{path}' is not valid JSON: {e}") from e
    if not isinstance(data, dict):
        raise ConfigError(f"Config file '{path}' must contain a JSON object.")
    return data
