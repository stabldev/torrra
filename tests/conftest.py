from pathlib import Path

import pytest

from torrra._types import Indexer
from torrra.app import TorrraApp
from torrra.core import config as config_module
from torrra.core.config import Config


@pytest.fixture
def app_factory():
    def _create_app(search_query: str | None = None):
        return TorrraApp(
            indexer=Indexer(
                name="jackett", url="http://mock.indexer.url", api_key="mock_api_key"
            ),
            use_cache=False,
            search_query=search_query,
        )

    return _create_app


@pytest.fixture
def mock_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
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
