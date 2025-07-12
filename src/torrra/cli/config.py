from typing import Any

from torrra.core.config import Config
from torrra.exceptions import ConfigError


def handle_config_command(args: Any):
    config = Config()

    if args.get:
        try:
            get_res = config.get(args.get)
            print(get_res)
        except ConfigError as e:
            print(e)

    elif args.list:
        list_res = config.list()
        print("\n".join(list_res))
