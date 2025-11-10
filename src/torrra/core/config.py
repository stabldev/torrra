import ast
import tomllib
from contextlib import suppress
from functools import lru_cache
from pathlib import Path
from typing import Any

import tomli_w
from platformdirs import user_config_dir, user_downloads_dir

from torrra.core.exceptions import ConfigError

CONFIG_DIR = Path(user_config_dir("torrra"))
CONFIG_FILE = CONFIG_DIR / "config.toml"


class Config:
    def __init__(self) -> None:
        self.config: dict[str, Any] = {}
        self._load_config()

    def get(self, key_path: str, default: Any | None = None) -> Any:
        keys = key_path.split(".")
        current = self.config

        try:
            for key in keys:
                current = current[key]

            if isinstance(current, dict):
                raise ConfigError(
                    f"key does not contain a value (it's a section): {key_path}"
                )
            return current

        except (KeyError, TypeError):
            if default is not None:
                return default

            if len(keys) > 1:
                raise ConfigError(f"key does not contain a section: {key_path}")
            raise ConfigError(f"key not found: {key_path}")

    def set(self, key_path: str, value: str) -> None:
        current = self.config
        keys = key_path.split(".")

        try:
            for key in keys[:-1]:
                if key not in current:
                    current[key] = {}
                elif not isinstance(current[key], dict):
                    raise ConfigError(
                        f"cannot set '{key_path}': '{key}' is not a section"
                    )
                current = current[key]

            new_value: Any = value
            # handle case-insensitive "true"/"false" for booleans
            if value.lower() == "true":
                new_value = True
            elif value.lower() == "false":
                new_value = False
            # handle other literals (int, float, etc.)
            else:  # convert data type silently
                with suppress(ValueError, SyntaxError):
                    new_value = ast.literal_eval(value)

            current[keys[-1]] = new_value
            self._save_config()

        except (KeyError, TypeError) as e:
            raise ConfigError(f"failed to set '{key_path}': {str(e)}")

    def list(self) -> list[str]:
        results: list[str] = []
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
            print(f"loading config failed: {e}")

    def _create_default_config(self) -> None:
        self.config = {
            "general": {
                "download_path": user_downloads_dir(),
                "remember_last_path": True,
                "download_in_external_client": False,
                "theme": "textual-dark",
                "use_cache": True,
                "seed_ratio": None,
            }
        }

    def _save_config(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "wb") as f:
            tomli_w.dump(self.config, f)


@lru_cache
def get_config() -> Config:
    return Config()


# cached Config() instance
config = get_config()
