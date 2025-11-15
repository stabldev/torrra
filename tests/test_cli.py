from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from torrra.__main__ import cli
from torrra._version import __version__


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
