import tomllib
from pathlib import Path
from typing import Any, Dict, List

import tomli_w
from platformdirs import user_config_dir, user_downloads_dir

from torrra.exceptions import ConfigError

CONFIG_DIR = Path(user_config_dir("torrra"))
CONFIG_FILE = CONFIG_DIR / "config.toml"


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

    def list(self) -> List[str]:
        results = []
        for section in self.config:
            for key, value in self.config[section].items():
                if isinstance(value, bool):
                    value = str(value).lower()
                results.append(f"{section}.{key}={value}")

        return results

    def _load_config(self) -> None:
        if not CONFIG_FILE.exists():
            self._create_default_config()
            self._save_config()

        try:
            with open(CONFIG_FILE, "rb") as f:
                self.config = tomllib.load(f)
        except Exception as e:
            print(f"error: loading config: {e}")

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
