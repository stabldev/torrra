import asyncio
import json
from pathlib import Path
from typing import Dict, Literal

from platformdirs import site_config_dir, user_config_dir

from torrra._types import Provider
from torrra.providers.jackett import JackettClient


def load_provider(provider: Literal["jackett"]) -> Provider:
    if provider == "jackett":
        return load_jackett_config()


def load_provider_from_args(
    name: Literal["jackett"], url: str, api_key: str
) -> Provider:
    if name == "jackett":
        jc = JackettClient(url=url, api_key=api_key)
        if asyncio.run(jc.validate()):
            return Provider(name="Jackett", url=url, api_key=api_key)
        else:
            raise SystemExit(1)


def load_jackett_config() -> Provider:
    config_path = _find_jackett_config_path()
    config = _load_json_config(config_path)

    port = config.get("Port", 9117)
    host = config.get("LocalBindAddress", "127.0.0.1")
    url = f"http://{host}:{port}"

    try:
        api_key = config["APIKey"]
    except KeyError:
        raise RuntimeError(f"[error] 'APIKey' not found in config: {config_path}")

    jc = JackettClient(url=url, api_key=api_key)
    if asyncio.run(jc.validate()):
        return Provider(name="Jackett", url=url, api_key=api_key)
    else:
        raise SystemExit(1)


def _find_jackett_config_path() -> Path:
    possible_paths = [
        Path(user_config_dir(None)) / "Jackett" / "ServerConfig.json",
        Path(site_config_dir(None)) / "Jackett" / "ServerConfig.json",
    ]

    for path in possible_paths:
        if path.exists():
            return path

    raise FileNotFoundError(
        "[error] jackett config file not found in known locations.\n"
        "checked:\n "
        + "\n ".join(str(p) for p in possible_paths)
        + "\nplease ensure jackett is installed and has run at least once."
    )


def _load_json_config(path: Path) -> Dict:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"[error] invalid json in config file: {path}\n{e}")
    except Exception as e:
        raise RuntimeError(f"[error] failed to load config file: {path}\n{e}")
