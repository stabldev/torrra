import os
from pathlib import Path

import pytest

from torrra.core import config as config_module
from torrra.core.config import Config
from torrra.core.constants import (
    DEFAULT_SPEED_LIMIT_DOWNLOAD,
    DEFAULT_SPEED_LIMIT_UPLOAD,
)
from torrra.core.exceptions import ConfigError


def test_config_initialization_creates_default_file(mock_config: Config):
    # test that a default config file is created
    config_path = config_module.CONFIG_FILE
    assert config_path.exists()
    # check for a known default value
    assert mock_config.get("general.theme") == "textual-dark"


def test_config_get_existing_value(mock_config: Config):
    # test getting a pre-existing value
    assert mock_config.get("general.use_cache") is True


def test_config_get_nonexistent_with_default(mock_config: Config):
    # test that a default value is returned for a non-existent key
    assert mock_config.get("general.non_existent_key", "default") == "default"


def test_config_get_nonexistent_raises_error(mock_config: Config):
    # test that getting a non-existent key w/o a default raises ConfigError
    with pytest.raises(ConfigError, match="key does not contain a section"):
        mock_config.get("general.non_existent_key")


def test_config_get_section_raises_error(mock_config: Config):
    # test that trying to get a value from a section key raises ConfigError
    with pytest.raises(ConfigError, match="key does not contain a value"):
        mock_config.get("general")


def test_config_set_and_get_new_value(mock_config: Config):
    # test setting a new value and then getting it back
    mock_config.set("new.section.key", "new_value")
    assert mock_config.get("new.section.key") == "new_value"


def test_config_set_type_conversion(mock_config: Config):
    # test that string values are correctly converted to other types
    mock_config.set("types.bool_true", "true")
    mock_config.set("types.bool_false", "False")
    mock_config.set("types.integer", "123")
    mock_config.set("types.float", "45.6")

    assert mock_config.get("types.bool_true") is True
    assert mock_config.get("types.bool_false") is False
    assert mock_config.get("types.integer") == 123
    assert mock_config.get("types.float") == 45.6


def test_default_speed_limits_are_turtle_values(mock_config: Config):
    # fresh config ships with qBittorrent-style 10 KB/s turtle limits
    assert DEFAULT_SPEED_LIMIT_UPLOAD == 10 * 1024
    assert DEFAULT_SPEED_LIMIT_DOWNLOAD == 10 * 1024
    assert mock_config.get("speed_limit.upload_limit") == DEFAULT_SPEED_LIMIT_UPLOAD
    assert mock_config.get("speed_limit.download_limit") == DEFAULT_SPEED_LIMIT_DOWNLOAD


def test_config_set_speed_limit_parses_human_units(mock_config: Config):
    # speed limit keys accept human-readable units and store bytes/sec
    mock_config.set("speed_limit.download_limit", "2M")
    mock_config.set("speed_limit.upload_limit", "500K")
    mock_config.set("speed_limit.download_limit", "1.5 GB/s")

    # last write wins
    assert mock_config.get("speed_limit.download_limit") == int(1.5 * 1024**3)
    assert mock_config.get("speed_limit.upload_limit") == 500 * 1024


def test_config_set_speed_limit_unlimited_and_invalid(mock_config: Config):
    # "unlimited"/"0" normalize to 0 bytes/sec
    mock_config.set("speed_limit.upload_limit", "unlimited")
    assert mock_config.get("speed_limit.upload_limit") == 0

    with pytest.raises(ConfigError, match="invalid value"):
        mock_config.set("speed_limit.download_limit", "abc")


def test_config_list_flattens_correctly(mock_config: Config):
    # test that list method correctly flattens
    mock_config.set("general.theme", "new-theme")
    mock_config.set("new.section.key", "value")
    mock_config.set("new.section.bool", "true")

    config_list = mock_config.list()
    # the order can vary, so we check for presence instead of exact list match
    assert "general.theme=new-theme" in config_list
    assert "new.section.key=value" in config_list
    assert "new.section.bool=true" in config_list
    # check a default value is also present
    assert "general.download_in_external_client=false" in config_list


def test_config_get_download_path_expands_tilde(mock_config: Config):
    import os

    mock_config.set("general.download_path", "~/my_downloads")
    expected = os.path.abspath(os.path.expanduser("~/my_downloads"))
    assert mock_config.get("general.download_path") == expected


def test_config_get_download_path_expands_env_vars(
    mock_config: Config, monkeypatch: pytest.MonkeyPatch
):
    import os

    monkeypatch.setenv("TEST_DOWNLOAD_DIR", "custom_downloads")
    mock_config.set("general.download_path", "~/$TEST_DOWNLOAD_DIR")
    expected = os.path.abspath(
        os.path.expanduser(os.path.expandvars("~/$TEST_DOWNLOAD_DIR"))
    )
    assert mock_config.get("general.download_path") == expected


def test_config_get_download_path_relative_to_absolute(mock_config: Config):
    import os

    mock_config.set("general.download_path", "some_relative_path")
    expected = os.path.abspath("some_relative_path")
    assert mock_config.get("general.download_path") == expected


def test_config_get_download_path_default_expansion(mock_config: Config):
    import os

    del mock_config.config["general"]["download_path"]
    result = mock_config.get("general.download_path", "~/fallback_downloads")
    expected = os.path.abspath(os.path.expanduser("~/fallback_downloads"))
    assert result == expected


def test_config_get_download_path_allows_literal_dollar_in_absolute_path(
    mock_config: Config,
):
    # '$' is a legal filename character; an absolute path containing one is
    # valid and must not be mistaken for an unresolved environment variable
    test_path = "/Volumes/My$Drive/Downloads"
    mock_config.set("general.download_path", test_path)
    assert mock_config.get("general.download_path") == os.path.abspath(test_path)


def test_config_get_download_path_allows_literal_dollar_after_tilde(
    mock_config: Config, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    mock_config.set("general.download_path", "~/Music/AC$DC")
    expected = os.path.join(str(tmp_path), "Music", "AC$DC")
    assert mock_config.get("general.download_path") == expected


def test_config_get_download_path_relative_with_dollar_raises_error(
    mock_config: Config, monkeypatch: pytest.MonkeyPatch
):
    # a '$' that leaves the path relative is what anchors it to the cwd,
    # which is the failure mode this validation exists to catch
    monkeypatch.delenv("UNDEFINED_VAR_TEST", raising=False)
    mock_config.set("general.download_path", "$UNDEFINED_VAR_TEST/downloads")
    with pytest.raises(ConfigError, match="unresolved environment variable"):
        mock_config.get("general.download_path")


def test_config_get_non_path_key_not_expanded(mock_config: Config):
    mock_config.set("general.theme", "~/not-a-path")
    assert mock_config.get("general.theme") == "~/not-a-path"


def test_deep_merge_adds_missing_keys_and_preserves_custom_keys():
    default_config = {
        "schema_version": 1,
        "general": {
            "theme": "textual-dark",
            "timeout": 10,
            "nested": {"a": 1, "b": 2},
        },
        "speed_limit": {"enabled": False},
    }
    user_config = {
        "general": {
            "theme": "gruvbox",
            "nested": {"b": 99},
        },
        "indexers": {
            "jackett": {"url": "http://localhost:9117"},
        },
    }

    merged, had_missing = config_module.deep_merge(default_config, user_config)

    assert had_missing is True
    # Overridden values preserved
    assert merged["general"]["theme"] == "gruvbox"
    assert merged["general"]["nested"]["b"] == 99
    # Missing defaults populated
    assert merged["general"]["timeout"] == 10
    assert merged["general"]["nested"]["a"] == 1
    assert merged["speed_limit"]["enabled"] is False
    assert merged["schema_version"] == 1
    # Custom sections preserved
    assert merged["indexers"]["jackett"]["url"] == "http://localhost:9117"


def test_deep_merge_handles_corrupted_section_types():
    default_config = {
        "general": {"theme": "textual-dark", "timeout": 10},
    }
    user_config = {
        "general": "corrupted_non_dict_value",
    }

    merged, had_missing = config_module.deep_merge(default_config, user_config)

    assert had_missing is True
    assert isinstance(merged["general"], dict)
    assert merged["general"]["theme"] == "textual-dark"
    assert merged["general"]["timeout"] == 10


def test_deep_merge_no_missing_keys():
    default_config = {
        "schema_version": 1,
        "general": {"theme": "textual-dark"},
    }
    user_config = {
        "schema_version": 1,
        "general": {"theme": "gruvbox"},
    }

    merged, had_missing = config_module.deep_merge(default_config, user_config)
    assert had_missing is False
    assert merged["general"]["theme"] == "gruvbox"


def test_apply_migrations_sequential():
    # Setup test migration functions
    def migrate_v1_to_v2(data: dict) -> dict:
        data["general"]["v2_field"] = "migrated_v2"
        return data

    def migrate_v2_to_v3(data: dict) -> dict:
        data["general"]["v3_field"] = data["general"]["v2_field"] + "_v3"
        return data

    original_migrations = config_module.MIGRATIONS.copy()
    try:
        config_module.MIGRATIONS[2] = migrate_v1_to_v2
        config_module.MIGRATIONS[3] = migrate_v2_to_v3

        raw_config = {
            "schema_version": 1,
            "general": {"theme": "textual-dark"},
        }

        migrated, was_migrated = config_module.apply_migrations(
            raw_config, target_version=3
        )

        assert was_migrated is True
        assert migrated["schema_version"] == 3
        assert migrated["general"]["v2_field"] == "migrated_v2"
        assert migrated["general"]["v3_field"] == "migrated_v2_v3"
    finally:
        config_module.MIGRATIONS.clear()
        config_module.MIGRATIONS.update(original_migrations)


def test_apply_migrations_already_up_to_date():
    raw_config = {"schema_version": 2, "general": {"theme": "textual-dark"}}
    migrated, was_migrated = config_module.apply_migrations(
        raw_config, target_version=2
    )
    assert was_migrated is False
    assert migrated == raw_config


def test_apply_migrations_from_unversioned_legacy_config():
    raw_config = {"general": {"theme": "textual-dark"}}
    migrated, was_migrated = config_module.apply_migrations(
        raw_config, target_version=1
    )
    assert was_migrated is True
    assert migrated["schema_version"] == 1


def test_existing_user_missing_keys_auto_merged_and_persisted_to_disk(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    # Simulate an existing user whose config.toml only had a few keys from an older version
    temp_config_dir = tmp_path / "legacy_user_torrra"
    temp_config_file = temp_config_dir / "config.toml"
    temp_config_dir.mkdir(parents=True, exist_ok=True)

    # Write a minimal legacy config file
    with open(temp_config_file, "w", encoding="utf-8") as f:
        f.write('[general]\ntheme = "catppuccin-mocha"\n')

    monkeypatch.setattr(config_module, "CONFIG_DIR", temp_config_dir)
    monkeypatch.setattr(config_module, "CONFIG_FILE", temp_config_file)
    config_module.get_config.cache_clear()

    # Load config instance
    cfg = config_module.Config()

    # Verify custom user preference is retained
    assert cfg.get("general.theme") == "catppuccin-mocha"

    # Verify missing fields are available in-memory with defaults
    assert cfg.get("general.min_seeders") == 0
    assert cfg.get("speed_limit.upload_limit") == DEFAULT_SPEED_LIMIT_UPLOAD
    assert cfg.get("speed_limit.enabled") is False

    # Verify config file on disk was automatically synced with missing keys
    tomllib = config_module.get_tomllib()
    with open(temp_config_file, "rb") as f:
        disk_data = tomllib.load(f)

    assert disk_data["general"]["theme"] == "catppuccin-mocha"
    assert disk_data["general"]["min_seeders"] == 0
    assert disk_data["speed_limit"]["upload_limit"] == DEFAULT_SPEED_LIMIT_UPLOAD
    assert disk_data["schema_version"] == config_module.CURRENT_SCHEMA_VERSION

    config_module.get_config.cache_clear()


def test_existing_user_custom_indexer_sections_preserved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    temp_config_dir = tmp_path / "custom_indexer_torrra"
    temp_config_file = temp_config_dir / "config.toml"
    temp_config_dir.mkdir(parents=True, exist_ok=True)

    # Legacy config with custom indexers
    with open(temp_config_file, "w", encoding="utf-8") as f:
        f.write(
            '[indexers.jackett]\nurl = "http://my-custom-jackett:9117"\napi_key = "secret_123"\n'
        )

    monkeypatch.setattr(config_module, "CONFIG_DIR", temp_config_dir)
    monkeypatch.setattr(config_module, "CONFIG_FILE", temp_config_file)
    config_module.get_config.cache_clear()

    cfg = config_module.Config()

    # Custom indexer settings are intact
    assert cfg.get("indexers.jackett.url") == "http://my-custom-jackett:9117"
    assert cfg.get("indexers.jackett.api_key") == "secret_123"
    # General defaults are also filled
    assert cfg.get("general.theme") == "textual-dark"

    config_module.get_config.cache_clear()


def test_corrupted_toml_syntax_falls_back_to_defaults(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    temp_config_dir = tmp_path / "broken_torrra"
    temp_config_file = temp_config_dir / "config.toml"
    temp_config_dir.mkdir(parents=True, exist_ok=True)

    with open(temp_config_file, "w", encoding="utf-8") as f:
        f.write("this is not valid [[ toml syntax = = =\n")

    monkeypatch.setattr(config_module, "CONFIG_DIR", temp_config_dir)
    monkeypatch.setattr(config_module, "CONFIG_FILE", temp_config_file)
    config_module.get_config.cache_clear()

    # Should not raise an exception, but fall back gracefully to defaults
    cfg = config_module.Config()
    assert cfg.get("general.theme") == "textual-dark"
    assert cfg.get("speed_limit.enabled") is False

    config_module.get_config.cache_clear()


def test_up_to_date_config_does_not_trigger_disk_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    temp_config_dir = tmp_path / "uptodate_torrra"
    temp_config_file = temp_config_dir / "config.toml"
    monkeypatch.setattr(config_module, "CONFIG_DIR", temp_config_dir)
    monkeypatch.setattr(config_module, "CONFIG_FILE", temp_config_file)
    config_module.get_config.cache_clear()

    # Initial creation
    cfg = config_module.Config()
    assert temp_config_file.exists()

    # Track save calls
    save_called = False
    original_save = cfg._save_config

    def spy_save():
        nonlocal save_called
        save_called = True
        original_save()

    monkeypatch.setattr(cfg, "_save_config", spy_save)

    # Re-loading up-to-date config should not trigger _save_config
    cfg._load_config()
    assert save_called is False

    config_module.get_config.cache_clear()


def test_non_dict_loaded_data_resets_to_defaults(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    temp_config_dir = tmp_path / "nondict_torrra"
    temp_config_file = temp_config_dir / "config.toml"
    monkeypatch.setattr(config_module, "CONFIG_DIR", temp_config_dir)
    monkeypatch.setattr(config_module, "CONFIG_FILE", temp_config_file)
    config_module.get_config.cache_clear()

    # Mock tomllib.load to return a non-dict (e.g. integer or list)
    tomllib_mock = config_module.get_tomllib()
    monkeypatch.setattr(tomllib_mock, "load", lambda f: [1, 2, 3])

    temp_config_dir.mkdir(parents=True, exist_ok=True)
    temp_config_file.touch()

    cfg = config_module.Config()
    assert cfg.get("general.theme") == "textual-dark"
    assert cfg.get("schema_version") == config_module.CURRENT_SCHEMA_VERSION

    config_module.get_config.cache_clear()


def test_apply_migrations_handles_invalid_version_type():
    # If schema_version is negative or non-integer, treat as version 0
    raw_config = {"schema_version": "invalid_str", "general": {"theme": "gruvbox"}}
    migrated, was_migrated = config_module.apply_migrations(
        raw_config, target_version=1
    )
    assert was_migrated is True
    assert migrated["schema_version"] == 1
    assert migrated["general"]["theme"] == "gruvbox"
