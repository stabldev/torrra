import asyncio
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Literal

from platformdirs import site_config_dir, user_config_dir

from torrra._types import Provider
from torrra.providers.jackett import JackettClient


def load_provider(provider: Literal["jackett", "prowlarr"]) -> Provider:
    if provider == "jackett":
        return load_jackett_config()
    elif provider == "prowlarr":
        return load_prowlarr_config()


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
    config_path = _find_config_path("Jackett", "ServerConfig.json")
    config = _load_json_config(config_path)

    port = config.get("Port", 9117)
    host = config.get("LocalBindAddress", "127.0.0.1")
    api_key = config["APIKey"]
    url = f"http://{host}:{port}"

    jc = JackettClient(url=url, api_key=api_key)
    if asyncio.run(jc.validate()):
        return Provider(name="Jackett", url=url, api_key=api_key)
    else:
        raise SystemExit(1)


def load_prowlarr_config() -> Provider:
    config_path = _find_config_path("Prowlarr", "config.xml")
    config = _load_xml_config(config_path)

    port = config.get("Port", 9696)
    bind_address = config.get("BindAddress")
    host = "127.0.0.1" if bind_address in ["*", "0.0.0.0"] else bind_address
    api_key = config["ApiKey"]
    url = f"http://{host}:{port}"

    return Provider(name="Prowlarr", url=url, api_key=api_key)


def _find_config_path(appname: str, config_file: str) -> Path:
    possible_paths = [
        Path(user_config_dir(appname)) / config_file,
        Path(site_config_dir(appname)) / config_file,
    ]

    for path in possible_paths:
        if path.exists():
            return path

    raise FileNotFoundError(
        f"[error] {appname.lower()} config file not found in known locations.\n"
        "checked:\n "
        + "\n ".join(str(p) for p in possible_paths)
        + f"\nplease ensure {appname.lower()} is installed and has run at least once."
    )


def _load_json_config(path: Path) -> Dict:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"[error] invalid json in config file: {path}\n{e}")
    except Exception as e:
        raise RuntimeError(f"[error] failed to load config file: {path}\n{e}")


def _load_xml_config(path: Path) -> Dict:
    try:
        tree = ET.parse(path)
        root = tree.getroot()

        config = {}
        for child in root:
            config[child.tag] = child.text

        return config
    except Exception as e:
        raise RuntimeError(f"[error] failed to load config file: {path}\n{e}")
