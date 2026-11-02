from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import httpx
from packaging.version import InvalidVersion, Version

from torrra._version import __version__
from torrra.core.constants import UPDATE_CHECK_TIMEOUT

PYPI_URL = "https://pypi.org/pypi/torrra/json"
GITHUB_LATEST_RELEASE_URL = (
    "https://api.github.com/repos/stabldev/torrra/releases/latest"
)
USER_AGENT = f"torrra/{__version__}"

InstallMethod = Literal[
    "uv",
    "pipx",
    "pip",
    "system",
    "winget",
    "homebrew",
    "nix",
    "docker",
    "standalone",
    "development",
]

_UPDATE_HINTS: dict[InstallMethod, str] = {
    "uv": "run `uv tool upgrade torrra`",
    "pipx": "run `pipx upgrade torrra`",
    "pip": "run `pip install --upgrade torrra`",
    "system": "update via your package manager",
    "winget": "run `winget upgrade stabldev.torrra`",
    "homebrew": "run `brew upgrade torrra`",
    "nix": "update via Nix",
    "docker": "pull the latest image with `docker pull stabldev/torrra:latest`",
    "standalone": "download the latest release from GitHub",
    "development": "update your source checkout",
}


@dataclass(frozen=True)
class UpdateInfo:
    version: str
    install_method: InstallMethod


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def _running_in_docker() -> bool:
    if not sys.platform.startswith("linux"):
        return False
    if Path("/.dockerenv").exists():
        return True
    return os.environ.get("container", "").lower() in {"docker", "podman"}


def _normalize_path(path: Path) -> str:
    return str(path).replace("\\", "/").lower()


def _detect_install_method(
    *,
    prefix: Path,
    base_prefix: Path,
    executable: Path,
    module_file: Path,
    frozen: bool,
    platform: str,
    in_docker: bool,
) -> InstallMethod:
    normalized_prefix = _normalize_path(prefix)
    normalized_executable = _normalize_path(executable)
    normalized_module = _normalize_path(module_file)

    if in_docker:
        return "docker"

    if (
        normalized_prefix.startswith("/nix/store")
        or "/nix/store/" in normalized_module
        or "/nix/store/" in normalized_executable
    ):
        return "nix"

    if frozen:
        if "winget" in normalized_executable:
            return "winget"
        if (
            "cellar" in normalized_executable
            or "homebrew" in normalized_executable
            or "linuxbrew" in normalized_executable
        ):
            return "homebrew"
        if platform.startswith("linux") and normalized_executable.startswith(
            "/usr/bin/"
        ):
            return "system"
        return "standalone"

    if prefix == base_prefix:
        # AUR/distro packages and pip-installed system Pythons are both here;
        # Linux is overwhelmingly package-managed, Windows/macOS usually pip.
        return "system" if platform.startswith("linux") else "pip"

    if (prefix / "uv-receipt.toml").is_file():
        return "uv"
    if (prefix / "pipx_metadata.json").is_file():
        return "pipx"
    if "/uv/tools/" in normalized_prefix:
        return "uv"
    if "/pipx/venvs/" in normalized_prefix:
        return "pipx"

    if "/site-packages/" in normalized_module or "/dist-packages/" in normalized_module:
        return "pip"

    # editable/source checkout (`uv run torrra`, `pip install -e .`)
    return "development"


def detect_install_method() -> InstallMethod:
    return _detect_install_method(
        prefix=Path(sys.prefix),
        base_prefix=Path(sys.base_prefix),
        executable=Path(sys.executable),
        module_file=Path(__file__),
        frozen=is_frozen(),
        platform=sys.platform,
        in_docker=_running_in_docker(),
    )


def _request_json(url: str) -> dict[str, Any] | None:
    try:
        response = httpx.get(
            url,
            timeout=UPDATE_CHECK_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        )
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, dict) else None
    except (httpx.HTTPError, ValueError, TypeError):
        return None


def _fetch_pypi_version() -> str | None:
    payload = _request_json(PYPI_URL)
    if payload is None:
        return None
    info = payload.get("info")
    if not isinstance(info, dict):
        return None
    version = info.get("version")
    return str(version) if version else None


def _fetch_github_version() -> str | None:
    payload = _request_json(GITHUB_LATEST_RELEASE_URL)
    if payload is None:
        return None
    tag = payload.get("tag_name")
    return str(tag) if tag else None


def get_latest_version() -> str | None:
    if is_frozen():
        return _fetch_github_version()
    return _fetch_pypi_version()


def _parse_version(value: str) -> Version | None:
    try:
        return Version(value.strip().lstrip("vV"))
    except InvalidVersion:
        return None


def check_for_update(current_version: str | None = None) -> UpdateInfo | None:
    method = detect_install_method()
    if method == "development":
        return None

    current = _parse_version(
        __version__ if current_version is None else current_version
    )
    if current is None:
        return None

    latest_raw = get_latest_version()
    latest = _parse_version(latest_raw or "")
    if latest is None or latest <= current:
        return None

    return UpdateInfo(version=str(latest), install_method=method)


def format_update_message(info: UpdateInfo) -> str:
    hint = _UPDATE_HINTS[info.install_method]
    return f"Update available: v{info.version} — {hint}"
