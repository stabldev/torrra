from pathlib import Path
import pytest

from torrra.core import config as config_module
from torrra.core.config import Config
from torrra.core.exceptions import ConfigError


@pytest.fixture
def config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # fixture to create a Config instance that uses a temp dir
    temp_config_dir = tmp_path / "torrra"
    temp_config_file = temp_config_dir / "config.toml"

    # monkeypatch constants in the config module
    monkeypatch.setattr(config_module, "CONFIG_DIR", temp_config_dir)
    monkeypatch.setattr(config_module, "CONFIG_FILE", temp_config_file)

    # the lru_cache on get_config needs to be cleared so that it doesn't
    # return a cached instance that was created before our patch was applied.
    config_module.get_config.cache_clear()

    # this will now create a Config instance using the tmp_path
    return Config()


def test_config_initialization_creates_default_file(config: Config):
    # test that a default config file is created
    config_path = config_module.CONFIG_FILE
    assert config_path.exists()
    # check for a known default value
    assert config.get("general.theme") == "textual-dark"


def test_config_get_existing_value(config: Config):
    # test getting a pre-existing value
    assert config.get("general.use_cache") is True


def test_config_get_nonexistent_with_default(config: Config):
    # test that a default value is returned for a non-existent key
    assert config.get("general.non_existent_key", "default") == "default"


def test_config_get_nonexistent_raises_error(config: Config):
    # test that getting a non-existent key w/o a default raises ConfigError
    with pytest.raises(ConfigError, match="key does not contain a section"):
        config.get("general.non_existent_key")


def test_config_get_section_raises_error(config: Config):
    # test that trying to get a value from a section key raises ConfigError
    with pytest.raises(ConfigError, match="key does not contain a value"):
        config.get("general")


def test_config_set_and_get_new_value(config: Config):
    # test setting a new value and then getting it back
    config.set("new.section.key", "new_value")
    assert config.get("new.section.key") == "new_value"


def test_config_set_type_conversion(config: Config):
    # test that string values are correctly converted to other types
    config.set("types.bool_true", "true")
    config.set("types.bool_false", "False")
    config.set("types.integer", "123")
    config.set("types.float", "45.6")

    assert config.get("types.bool_true") is True
    assert config.get("types.bool_false") is False
    assert config.get("types.integer") == 123
    assert config.get("types.float") == 45.6


def test_config_list_flattens_correctly(config: Config):
    # test that list method correctly flattens
    config.set("general.theme", "new-theme")
    config.set("new.section.key", "value")
    config.set("new.section.bool", "true")

    config_list = config.list()
    # the order can vary, so we check for presence instead of exact list match
    assert "general.theme=new-theme" in config_list
    assert "new.section.key=value" in config_list
    assert "new.section.bool=true" in config_list
    # check a default value is also present
    assert "general.remember_last_path=true" in config_list
