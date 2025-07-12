from typing import Any

from torrra.config import Config, ConfigError


def handle_config_command(args: Any):
    config = Config()

    if args.get:
        try:
            print(config.get(args.get))
        except ConfigError as e:
            print(e)
