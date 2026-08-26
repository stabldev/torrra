from pathlib import Path
from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from torrra.__main__ import cli
from torrra._version import __version__
from torrra.core.config import Config


def test_cli_version():
    # tests that the --version flag works
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_search_command_calls_runner(monkeypatch: pytest.MonkeyPatch):
    # tests that the 'search' command calls the correct underlying function
    mock_run_func = MagicMock()
    monkeypatch.setattr("torrra.utils.indexer.run_with_default_indexer", mock_run_func)

    runner = CliRunner()
    result = runner.invoke(cli, ["search", "arch linux iso", "--no-cache"])

    assert result.exit_code == 0
    # assert that the function was called once with the correct arguments
    mock_run_func.assert_called_once_with(no_cache=True, search_query="arch linux iso")


def test_prowlarr_command_calls_runner_with_cache(monkeypatch: pytest.MonkeyPatch):
    # tests that the "prowlarr" command calls the correct underlying function
    mock_run_func = MagicMock()
    monkeypatch.setattr("torrra.utils.indexer.run_with_indexer", mock_run_func)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "prowlarr",
            "--url",
            "http://mock.indexer.url",
            "--api-key",
            "mock_api_key",
            "--no-cache",
        ],
    )

    assert result.exit_code == 0
    mock_run_func.assert_called_once_with(
        name="prowlarr",
        indexer_cls_str="torrra.indexers.prowlarr.ProwlarrIndexer",
        url="http://mock.indexer.url",
        api_key="mock_api_key",
        no_cache=True,
    )


@pytest.mark.usefixtures("mock_config")
def test_config_commands_flow():
    # tests the full get/set/list flow for the config command
    runner = CliRunner()

    # test setting a value
    set_result = runner.invoke(cli, ["config", "set", "test.key", "test_value"])
    assert set_result.exit_code == 0

    # test getting the value back
    get_result = runner.invoke(cli, ["config", "get", "test.key"])
    assert get_result.exit_code == 0
    assert "test_value" in get_result.output

    # test listing all values
    list_result = runner.invoke(cli, ["config", "list"])
    assert list_result.exit_code == 0
    assert "test.key=test_value" in list_result.output


def test_config_edit_opens_editor(monkeypatch: pytest.MonkeyPatch, mock_config: Config):
    from torrra.core import config as config_module

    mock_edit = MagicMock()
    monkeypatch.setattr("click.edit", mock_edit)

    runner = CliRunner()
    result = runner.invoke(cli, ["config", "edit"])

    assert result.exit_code == 0
    mock_edit.assert_called_once_with(
        filename=str(config_module.CONFIG_FILE), editor=None
    )


def test_config_edit_with_custom_editor(
    monkeypatch: pytest.MonkeyPatch, mock_config: Config
):
    from torrra.core import config as config_module

    mock_edit = MagicMock()
    monkeypatch.setattr("click.edit", mock_edit)

    runner = CliRunner()
    result = runner.invoke(cli, ["config", "edit", "--editor", "nano"])

    assert result.exit_code == 0
    mock_edit.assert_called_once_with(
        filename=str(config_module.CONFIG_FILE), editor="nano"
    )

    # test short option -e
    mock_edit.reset_mock()
    result_short = runner.invoke(cli, ["config", "edit", "-e", "vim"])
    assert result_short.exit_code == 0
    mock_edit.assert_called_once_with(
        filename=str(config_module.CONFIG_FILE), editor="vim"
    )


def test_config_edit_updates_cache(
    monkeypatch: pytest.MonkeyPatch, mock_config: Config
):
    from torrra.core.config import get_config

    def mock_edit_write(filename: str, editor: str | None = None):
        with open(filename, "w", encoding="utf-8") as f:
            f.write('[general]\ntheme = "custom-theme"\n')

    monkeypatch.setattr("click.edit", mock_edit_write)

    runner = CliRunner()
    result = runner.invoke(cli, ["config", "edit"])

    assert result.exit_code == 0
    assert get_config().get("general.theme") == "custom-theme"


def test_config_edit_invalid_toml_warning(
    monkeypatch: pytest.MonkeyPatch, mock_config: Config
):
    def mock_edit_invalid(filename: str, editor: str | None = None):
        with open(filename, "w", encoding="utf-8") as f:
            f.write("invalid toml syntax = = =\n")

    monkeypatch.setattr("click.edit", mock_edit_invalid)

    runner = CliRunner()
    result = runner.invoke(cli, ["config", "edit"])

    assert result.exit_code == 0
    assert "Invalid Configuration" in result.output


def test_config_edit_error_handling(
    monkeypatch: pytest.MonkeyPatch, mock_config: Config
):
    import click

    def mock_edit_fail(filename: str, editor: str | None = None):
        raise click.ClickException("Editor not found")

    monkeypatch.setattr("click.edit", mock_edit_fail)

    runner = CliRunner()
    result = runner.invoke(cli, ["config", "edit"])

    assert result.exit_code == 0
    assert "Failed to open editor: Editor not found" in result.output


def test_config_edit_creates_default_file_if_not_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    from torrra.core import config as config_module

    temp_config_dir = tmp_path / "new_torrra"
    temp_config_file = temp_config_dir / "config.toml"
    monkeypatch.setattr(config_module, "CONFIG_DIR", temp_config_dir)
    monkeypatch.setattr(config_module, "CONFIG_FILE", temp_config_file)
    config_module.get_config.cache_clear()

    assert not temp_config_file.exists()

    mock_edit = MagicMock()
    monkeypatch.setattr("click.edit", mock_edit)

    runner = CliRunner()
    result = runner.invoke(cli, ["config", "edit"])

    assert result.exit_code == 0
    assert temp_config_file.exists()
    mock_edit.assert_called_once_with(filename=str(temp_config_file), editor=None)
    config_module.get_config.cache_clear()


def test_download_command_valid_magnet(monkeypatch: pytest.MonkeyPatch):
    mock_run_func = MagicMock()
    monkeypatch.setattr("torrra.utils.indexer.run_without_indexer", mock_run_func)

    runner = CliRunner()
    magnet = "magnet:?xt=urn:btih:0123456789abcdef0123456789abcdef01234567&dn=test"
    result = runner.invoke(cli, ["download", magnet, "--no-cache"])

    assert result.exit_code == 0
    # direct download must not require an indexer
    mock_run_func.assert_called_once_with(
        no_cache=True,
        direct_download=magnet,
        direct_save_path=None,
        direct_sequential=False,
        direct_max_ratio=None,
        direct_max_seeding_time=None,
    )


def test_download_command_passes_save_path(monkeypatch: pytest.MonkeyPatch):
    mock_run_func = MagicMock()
    monkeypatch.setattr("torrra.utils.indexer.run_without_indexer", mock_run_func)

    runner = CliRunner()
    magnet = "magnet:?xt=urn:btih:0123456789abcdef0123456789abcdef01234567"
    result = runner.invoke(
        cli,
        ["download", magnet, "--save-path", "/mnt/media/torrents"],
    )

    assert result.exit_code == 0
    mock_run_func.assert_called_once_with(
        no_cache=False,
        direct_download=magnet,
        direct_save_path="/mnt/media/torrents",
        direct_sequential=False,
        direct_max_ratio=None,
        direct_max_seeding_time=None,
    )


def test_download_command_with_options(monkeypatch: pytest.MonkeyPatch):
    mock_run_func = MagicMock()
    monkeypatch.setattr("torrra.utils.indexer.run_without_indexer", mock_run_func)

    runner = CliRunner()
    magnet = "magnet:?xt=urn:btih:0123456789abcdef0123456789abcdef01234567"
    result = runner.invoke(
        cli,
        [
            "download",
            magnet,
            "--sequential",
            "--seed-ratio",
            "1.5",
            "--seed-time",
            "2h",
        ],
    )

    assert result.exit_code == 0
    mock_run_func.assert_called_once_with(
        no_cache=False,
        direct_download=magnet,
        direct_save_path=None,
        direct_sequential=True,
        direct_max_ratio=1.5,
        direct_max_seeding_time=120,
    )


def test_download_command_invalid_options(monkeypatch: pytest.MonkeyPatch):
    runner = CliRunner()
    magnet = "magnet:?xt=urn:btih:0123456789abcdef0123456789abcdef01234567"
    result = runner.invoke(cli, ["download", magnet, "--seed-ratio", "invalid_ratio"])
    assert result.exit_code == 0
    assert "Invalid --seed-ratio" in result.output

    result2 = runner.invoke(cli, ["download", magnet, "--seed-time", "invalid_time"])
    assert result2.exit_code == 0
    assert "Invalid --seed-time" in result2.output


def test_download_command_invalid_input():
    runner = CliRunner()
    result = runner.invoke(cli, ["download", "not_a_valid_magnet_or_file"])

    assert result.exit_code == 0
    assert "Invalid input" in result.output


def test_downloads_command_calls_runner_without_indexer(
    monkeypatch: pytest.MonkeyPatch,
):
    # the downloads view must launch without an indexer configured
    mock_run_func = MagicMock()
    monkeypatch.setattr("torrra.utils.indexer.run_without_indexer", mock_run_func)

    runner = CliRunner()
    result = runner.invoke(cli, ["downloads", "--no-cache"])

    assert result.exit_code == 0
    mock_run_func.assert_called_once_with(no_cache=True, show_downloads=True)
