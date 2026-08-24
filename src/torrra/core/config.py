import ast
import copy
import os
from collections.abc import Callable
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
    DEFAULT_SPEED_LIMIT_DOWNLOAD,
    DEFAULT_SPEED_LIMIT_UPLOAD,
    DEFAULT_TIMEOUT,
)
from torrra.core.exceptions import ConfigError
from torrra.utils.helpers import get_tomllib, parse_speed_limit

CONFIG_DIR = Path(user_config_dir("torrra"))
CONFIG_FILE = CONFIG_DIR / "config.toml"

CURRENT_SCHEMA_VERSION = 1

# Registry of migration functions for sequential schema upgrades.
# Key is target schema version (e.g. 1, 2, 3...)
# Migration function signature: (config_data: dict[str, Any]) -> dict[str, Any]
MIGRATIONS: dict[int, Callable[[dict[str, Any]], dict[str, Any]]] = {}

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
    if (
        not (os.path.isabs(resolved) or resolved.startswith(("/", "\\")))
        and "$" in expanded
    ):
        raise ConfigError(f"unresolved environment variable in path: {value}")
    return os.path.abspath(resolved)


def get_default_config() -> dict[str, Any]:
    """Returns the baseline default configuration dictionary."""
    return {
        "schema_version": CURRENT_SCHEMA_VERSION,
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
        },
        "speed_limit": {
            "upload_limit": DEFAULT_SPEED_LIMIT_UPLOAD,
            "download_limit": DEFAULT_SPEED_LIMIT_DOWNLOAD,
            "enabled": False,
        },
    }


def apply_migrations(
    raw_config: dict[str, Any], target_version: int = CURRENT_SCHEMA_VERSION
) -> tuple[dict[str, Any], bool]:
    """
    Applies sequential migrations to raw_config up to target_version.
    Returns (migrated_config, was_migrated).
    """
    current_version = raw_config.get("schema_version", 0)
    if not isinstance(current_version, int) or current_version < 0:
        current_version = 0

    if current_version >= target_version:
        return raw_config, False

    migrated = copy.deepcopy(raw_config)
    for ver in range(current_version + 1, target_version + 1):
        migration_fn = MIGRATIONS.get(ver)
        if migration_fn is not None:
            migrated = migration_fn(migrated)
        migrated["schema_version"] = ver

    return migrated, True


def deep_merge(
    default: dict[str, Any], user: dict[str, Any]
) -> tuple[dict[str, Any], bool]:
    """
    Recursively merges user dict into default dict.
    - Default keys missing in user are added with default values (had_missing=True).
    - User values override default values.
    - Additional user-defined keys/sections (e.g. custom indexers) are preserved.
    Returns (merged_dict, had_missing_keys).
    """
    merged: dict[str, Any] = {}
    had_missing = False

    # 1. Fill from default, overriding with user when present
    for key, def_val in default.items():
        if key not in user:
            merged[key] = copy.deepcopy(def_val)
            had_missing = True
        else:
            user_val = user[key]
            if isinstance(def_val, dict):
                if isinstance(user_val, dict):
                    merged_sub, sub_missing = deep_merge(def_val, user_val)
                    merged[key] = merged_sub
                    if sub_missing:
                        had_missing = True
                else:
                    # User provided a non-dict where a section dict is required.
                    # Fallback to default dict to repair structure.
                    merged[key] = copy.deepcopy(def_val)
                    had_missing = True
            else:
                merged[key] = user_val

    # 2. Preserve any user keys that are not part of default (e.g. custom sections / indexers)
    for key, user_val in user.items():
        if key not in default:
            merged[key] = copy.deepcopy(user_val)

    return merged, had_missing


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
            # speed limit keys accept human-readable units ("500K", "2M",
            # "1.5 GB/s", "10 KB/s", "unlimited"); validate with parse_speed_limit
            # and store the string representation
            if key_path in (
                "speed_limit.upload_limit",
                "speed_limit.download_limit",
            ):
                try:
                    parse_speed_limit(value)
                    new_value = str(value).strip()
                except ValueError as e:
                    raise ConfigError(
                        f"invalid value for '{key_path}': {value!r} ({e}). "
                        + "use e.g. 500K, 2M, 10 KB/s, or unlimited"
                    ) from e
            # handle case-insensitive "true"/"false" for booleans
            elif value.lower() == "true":
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
        defaults = get_default_config()

        if not CONFIG_FILE.exists():
            self.config = defaults
            self._save_config()
            return

        tomllib = get_tomllib()
        try:
            with open(CONFIG_FILE, "rb") as f:
                user_data = tomllib.load(f)
        except (OSError, tomllib.TOMLDecodeError) as e:
            print(f"loading config failed: {e}")
            self.config = defaults
            return

        if not isinstance(user_data, dict):
            self.config = defaults
            self._save_config()
            return

        # 1. Apply sequential migrations
        migrated_data, was_migrated = apply_migrations(
            user_data, CURRENT_SCHEMA_VERSION
        )

        # 2. Deep merge with defaults to populate missing keys and sections
        merged_config, had_missing = deep_merge(defaults, migrated_data)
        self.config = merged_config

        # 3. Auto-sync: Save to disk if new keys were added or migrations were run
        if was_migrated or had_missing:
            self._save_config()

    def _create_default_config(self) -> None:
        self.config = get_default_config()

    def _save_config(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "wb") as f:
            tomli_w.dump(self.config, f)
