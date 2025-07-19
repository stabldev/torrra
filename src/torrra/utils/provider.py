import json
from pathlib import Path
from typing import Dict, Literal

from platformdirs import user_config_dir

from torrra._types import Provider


def load_provider(provider: Literal["jackett"]) -> Provider:
    if provider == "jackett":
        return load_jackett_config()


def find_jackett_config() -> Path:
    # Default per-user config location
    default_path = Path(user_config_dir("Jackett")) / "ServerConfig.json"
    if default_path.exists():
        return default_path

    # Common system-wide config location (e.g., Windows service install)
    alt_path = Path("C:/ProgramData/Jackett/ServerConfig.json")
    if alt_path.exists():
        return alt_path

    # Could add more fallback paths here if needed

    # If nothing found, raise helpful error
    raise RuntimeError(
        "[ERROR] Jackett config file not found in known locations.\n"
        "Checked:\n"
        f"  {default_path}\n"
        f"  {alt_path}\n"
        "Please ensure Jackett is installed and has run at least once."
    )


def load_jackett_config() -> Provider:
    config_path = find_jackett_config()
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
