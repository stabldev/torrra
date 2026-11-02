from pathlib import Path
from typing import Any

import httpx
import pytest
import respx

from torrra.core import updater


def _detect(**overrides: Any) -> updater.InstallMethod:
    defaults: dict[str, Any] = {
        "prefix": Path("/venv"),
        "base_prefix": Path("/usr"),
        "executable": Path("/venv/bin/torrra"),
        "module_file": Path(
            "/venv/lib/python3.13/site-packages/torrra/core/updater.py"
        ),
        "frozen": False,
        "platform": "linux",
        "in_docker": False,
    }
    defaults.update(overrides)
    return updater._detect_install_method(**defaults)


def test_detects_uv_tool(tmp_path: Path):
    prefix = tmp_path / "uv" / "tools" / "torrra"
    prefix.mkdir(parents=True)
    (prefix / "uv-receipt.toml").write_text("")

    method = _detect(
        prefix=prefix,
        base_prefix=tmp_path / "python",
        executable=prefix / "Scripts" / "torrra.exe",
        module_file=prefix / "Lib" / "site-packages" / "torrra" / "core" / "updater.py",
    )

    assert method == "uv"


def test_detects_pipx(tmp_path: Path):
    prefix = tmp_path / "pipx" / "venvs" / "torrra"
    prefix.mkdir(parents=True)
    (prefix / "pipx_metadata.json").write_text("{}")

    method = _detect(
        prefix=prefix,
        base_prefix=tmp_path / "python",
        executable=prefix / "bin" / "torrra",
        module_file=prefix / "lib" / "site-packages" / "torrra" / "core" / "updater.py",
    )

    assert method == "pipx"


def test_detects_uv_by_install_path_when_receipt_is_missing():
    assert _detect(prefix=Path("/home/u/.local/share/uv/tools/torrra")) == "uv"


def test_detects_pipx_by_install_path_when_metadata_is_missing():
    assert _detect(prefix=Path("/home/u/.local/pipx/venvs/torrra")) == "pipx"


def test_detects_regular_virtualenv_as_pip():
    assert _detect() == "pip"


def test_detects_system_python_on_linux():
    assert _detect(prefix=Path("/usr"), base_prefix=Path("/usr")) == "system"


def test_detects_system_python_on_windows_as_pip():
    assert (
        _detect(
            prefix=Path("C:/Python313"),
            base_prefix=Path("C:/Python313"),
            platform="win32",
        )
        == "pip"
    )


def test_detects_source_checkout_as_development():
    assert (
        _detect(
            prefix=Path("/repo/.venv"),
            module_file=Path("/repo/src/torrra/core/updater.py"),
        )
        == "development"
    )


def test_detects_docker_before_other_python_installs():
    assert _detect(in_docker=True) == "docker"


def test_detects_nix_store():
    assert _detect(prefix=Path("/nix/store/abc-python")) == "nix"


@pytest.mark.parametrize(
    ("executable", "platform", "expected"),
    [
        (
            (
                "C:/Users/u/AppData/Local/Microsoft/WinGet/Packages/"
                "stabldev.torrra/torrra.exe"
            ),
            "win32",
            "winget",
        ),
        ("/opt/homebrew/Cellar/torrra/2.5.1/bin/torrra", "darwin", "homebrew"),
        ("/home/linuxbrew/.linuxbrew/bin/torrra", "linux", "homebrew"),
        ("/usr/bin/torrra", "linux", "system"),
        ("/usr/local/bin/torrra", "linux", "standalone"),
        ("/home/u/Downloads/torrra", "linux", "standalone"),
    ],
)
def test_detects_frozen_binary_channel(
    executable: str, platform: str, expected: updater.InstallMethod
):
    assert (
        _detect(
            prefix=Path("/unused"),
            executable=Path(executable),
            frozen=True,
            platform=platform,
        )
        == expected
    )


@respx.mock
def test_get_latest_version_uses_pypi(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(updater, "is_frozen", lambda: False)
    route = respx.get(updater.PYPI_URL).mock(
        httpx.Response(200, json={"info": {"version": "9.9.9"}})
    )

    assert updater.get_latest_version() == "9.9.9"
    assert route.called


@respx.mock
def test_get_latest_version_uses_github_when_frozen(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(updater, "is_frozen", lambda: True)
    route = respx.get(updater.GITHUB_LATEST_RELEASE_URL).mock(
        httpx.Response(200, json={"tag_name": "v9.9.9"})
    )

    assert updater.get_latest_version() == "v9.9.9"
    assert route.called


@respx.mock
def test_get_latest_version_returns_none_on_network_error(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(updater, "is_frozen", lambda: False)
    respx.get(updater.PYPI_URL).mock(side_effect=httpx.ConnectError("offline"))

    assert updater.get_latest_version() is None


@respx.mock
def test_get_latest_version_returns_none_on_malformed_payload(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(updater, "is_frozen", lambda: False)
    respx.get(updater.PYPI_URL).mock(httpx.Response(200, json={"info": {}}))

    assert updater.get_latest_version() is None


def test_check_for_update_returns_newer_version(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(updater, "detect_install_method", lambda: "uv")
    monkeypatch.setattr(updater, "get_latest_version", lambda: "2.6.0")

    assert updater.check_for_update("2.5.1") == updater.UpdateInfo(
        version="2.6.0", install_method="uv"
    )


@pytest.mark.parametrize("latest", ["2.5.1", "2.4.9"])
def test_check_for_update_ignores_same_or_older(
    monkeypatch: pytest.MonkeyPatch, latest: str
):
    monkeypatch.setattr(updater, "detect_install_method", lambda: "uv")
    monkeypatch.setattr(updater, "get_latest_version", lambda: latest)

    assert updater.check_for_update("2.5.1") is None


@pytest.mark.parametrize("current", ["dev", "", "not-a-version"])
def test_check_for_update_ignores_invalid_current_version(
    monkeypatch: pytest.MonkeyPatch, current: str
):
    monkeypatch.setattr(updater, "detect_install_method", lambda: "uv")
    monkeypatch.setattr(updater, "get_latest_version", lambda: "9.9.9")

    assert updater.check_for_update(current) is None


def test_check_for_update_ignores_invalid_latest_version(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(updater, "detect_install_method", lambda: "uv")
    monkeypatch.setattr(updater, "get_latest_version", lambda: "nonsense")

    assert updater.check_for_update("2.5.1") is None


def test_check_for_update_skips_development_checkout(
    monkeypatch: pytest.MonkeyPatch,
):
    called = []
    monkeypatch.setattr(updater, "detect_install_method", lambda: "development")
    monkeypatch.setattr(
        updater,
        "get_latest_version",
        lambda: called.append(True) or "9.9.9",
    )

    assert updater.check_for_update("2.5.1") is None
    assert called == []


@pytest.mark.parametrize(
    ("method", "expected"),
    [
        ("uv", "uv tool upgrade torrra"),
        ("pipx", "pipx upgrade torrra"),
        ("pip", "pip install --upgrade torrra"),
        ("system", "package manager"),
        ("winget", "winget upgrade stabldev.torrra"),
        ("homebrew", "brew upgrade torrra"),
        ("nix", "Nix"),
        ("docker", "docker pull stabldev/torrra:latest"),
        ("standalone", "GitHub"),
        ("development", "source checkout"),
    ],
)
def test_format_update_message(method: updater.InstallMethod, expected: str):
    message = updater.format_update_message(
        updater.UpdateInfo(version="9.9.9", install_method=method)
    )

    assert "v9.9.9" in message
    assert expected in message
