from pathlib import Path
from typing import Any, Dict

import tomli_w
from platformdirs import user_config_dir, user_downloads_dir

CONFIG_DIR = Path(user_config_dir("torrra"))
CONFIG_FILE = CONFIG_DIR / "config.toml"


class Config:
    def __init__(self) -> None:
        self.config: Dict[str, Any] = {}
        self.load_config()

    def load_config(self) -> None:
        if not CONFIG_FILE.exists():
            self.create_default_config()
            self.save_config()

    def create_default_config(self) -> None:
        self.config = {
            "general": {
                "download_path": user_downloads_dir(),
                "remember_last_path": True,
                "max_results": 10,
            }
        }

    def save_config(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "wb") as f:
            tomli_w.dump(self.config, f)
