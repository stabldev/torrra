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
