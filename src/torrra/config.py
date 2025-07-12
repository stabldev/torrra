import tomllib
from pathlib import Path
from typing import Any, Dict

import tomli_w
from platformdirs import user_config_dir, user_downloads_dir

CONFIG_DIR = Path(user_config_dir("torrra"))
CONFIG_FILE = CONFIG_DIR / "config.toml"


class ConfigError(Exception):
    """Custom error for config key issues."""

    pass


class Config:
    def __init__(self) -> None:
        self.config: Dict[str, Any] = {}
        self._load_config()

    def get(self, key_path: str) -> Any:
        keys = key_path.split(".")
        current = self.config

        try:
            for key in keys:
                current = current[key]
        except (KeyError, TypeError):
            if len(keys) > 1:
                raise ConfigError(f"error: key does not contain a section: {key_path}")
            else:
                raise ConfigError(f"error: key not found: {key_path}")

        if isinstance(current, dict):
            raise ConfigError(
                f"error: key does not contain a value (it's a section): {key_path}"
            )

        return current

    def _load_config(self) -> None:
        if not CONFIG_FILE.exists():
            self._create_default_config()
            self._save_config()

        try:
            with open(CONFIG_FILE, "rb") as f:
                self.config = tomllib.load(f)
        except Exception as e:
            print(f"Error loading config: {e}, using defaults...")

    def _create_default_config(self) -> None:
        self.config = {
            "general": {
                "download_path": user_downloads_dir(),
                "remember_last_path": True,
                "max_results": 10,
            }
        }

    def _save_config(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "wb") as f:
            tomli_w.dump(self.config, f)
