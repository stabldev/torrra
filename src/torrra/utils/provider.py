import json
from pathlib import Path
from typing import Dict, Literal

from platformdirs import user_config_dir

from torrra._types import Provider


def load_provider(provider: Literal["jackett"]) -> Provider:
    if provider == "jackett":
        return load_jackett_config()


def load_jackett_config() -> Provider:
    config_path = Path(user_config_dir("Jackett")) / "ServerConfig.json"
    config = _load_json_config(config_path)

    port = config.get("Port", 9117)
    host = config.get("LocalBindAddress", "127.0.0.1")
    url = f"http://{host}:{port}"

    return Provider(name="Jackett", url=url, api_key=config["APIKey"])


def _load_json_config(path: Path) -> Dict:
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception as e:
        raise RuntimeError(f"error: loading {path} config: {e}")
