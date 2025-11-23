import ast
from contextlib import suppress
from functools import lru_cache
from pathlib import Path
from typing import Any, cast

import tomli_w
import tomllib
from platformdirs import user_config_dir, user_downloads_dir

from torrra.core.constants import DEFAULT_CACHE_TTL
from torrra.core.exceptions import ConfigError

CONFIG_DIR = Path(user_config_dir("torrra"))
CONFIG_FILE = CONFIG_DIR / "config.toml"

# sentinel value used for robust
# config.get(..., default=...) value check
_sentinel = object()


@lru_cache
def get_config() -> "Config":
    return Config()


class Config:
    def __init__(self) -> None:
        self.config: dict[str, Any] = {}
        self._load_config()

    def get(self, key_path: str, default: Any | None = _sentinel) -> Any:
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
            if default is not _sentinel:
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

        def _flatten_config(data: dict[str, Any], prefix: str = "") -> None:
            # recursively iterate through config
            for key, value in data.items():
                # construct new prefix
                new_prefix = f"{prefix}.{key}" if prefix else key
                if isinstance(value, dict):
                    # if dict, recurse deeper
                    _flatten_config(cast(dict[str, Any], value), new_prefix)
                else:
                    if isinstance(value, bool):
                        # if bool, convert to lowercase string
                        value = str(value).lower()
                    # append flattened key-value pair
                    results.append(f"{new_prefix}={value}")

        _flatten_config(self.config)
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
                "cache_ttl": DEFAULT_CACHE_TTL,
            }
        }

    def _save_config(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "wb") as f:
            tomli_w.dump(self.config, f)
