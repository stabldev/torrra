import pytest

from torrra.core import config as config_module
from torrra.core.config import Config
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
    assert "download.client=internal" in config_list
