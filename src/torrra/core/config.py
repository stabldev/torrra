import ast
import os
from contextlib import suppress
from functools import lru_cache
from pathlib import Path
from typing import Any, cast

import tomli_w
from platformdirs import user_config_dir, user_downloads_dir

from torrra.core.constants import (
    DEFAULT_CACHE_TTL,
    DEFAULT_MAX_RETRIES,
    DEFAULT_MIN_SEEDERS,
    DEFAULT_SORT,
    DEFAULT_SORT_ORDER,
    DEFAULT_TIMEOUT,
)
from torrra.core.exceptions import ConfigError
from torrra.utils.helpers import get_tomllib

CONFIG_DIR = Path(user_config_dir("torrra"))
CONFIG_FILE = CONFIG_DIR / "config.toml"

# sentinel value used for robust
# config.get(..., default=...) value check
_sentinel = object()

_PATH_KEYS = {"general.download_path"}


def _resolve_path(value: str) -> str:
    expanded = os.path.expandvars(value)
    resolved = os.path.expanduser(expanded)
    # an unresolved variable is only harmful because it leaves the path
    # relative, which anchors it to the cwd; a literal '$' in an absolute
    # path is a valid filename character and must be left alone
    if not (os.path.isabs(resolved) or resolved.startswith(("/", "\\"))) and "$" in expanded:
        raise ConfigError(f"unresolved environment variable in path: {value}")
    return os.path.abspath(resolved)


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

            if key_path in _PATH_KEYS and isinstance(current, str):
                return _resolve_path(current)

            return current

        except (KeyError, TypeError):
            if default is not _sentinel:
                if key_path in _PATH_KEYS and isinstance(default, str):
                    return _resolve_path(default)
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
            raise ConfigError(f"failed to set '{key_path}': {e!s}")

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

        tomllib = get_tomllib()
        try:
            with open(CONFIG_FILE, "rb") as f:
                self.config = tomllib.load(f)
        except (OSError, tomllib.TOMLDecodeError) as e:
            print(f"loading config failed: {e}")

    def _create_default_config(self) -> None:
        self.config = {
            "general": {
                "download_path": user_downloads_dir(),
                "download_in_external_client": False,
                "theme": "textual-dark",
                "timeout": DEFAULT_TIMEOUT,
                "max_retries": DEFAULT_MAX_RETRIES,
                "use_cache": True,
                "cache_ttl": DEFAULT_CACHE_TTL,
                "default_sort": DEFAULT_SORT,
                "default_sort_order": DEFAULT_SORT_ORDER,
                "min_seeders": DEFAULT_MIN_SEEDERS,
            }
        }

    def _save_config(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "wb") as f:
            tomli_w.dump(self.config, f)
