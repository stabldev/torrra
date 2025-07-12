from typing import Any

from torrra.core.config import Config
from torrra.exceptions import ConfigError


def handle_config_command(args: Any):
    config = Config()

    if args.get:
        try:
            print(config.get(args.get))
        except ConfigError as e:
            print(e)
