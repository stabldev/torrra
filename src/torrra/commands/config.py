from typing import Any

from torrra.core.config import Config
from torrra.core.exceptions import ConfigError


def handle_config_command(args: Any):
    config = Config()

    if args.get:
        try:
            get_res = config.get(args.get)
            print(get_res)
        except ConfigError as e:
            print(e)
    elif args.set:
        try:
            config.set(args.set[0], args.set[1])
        except ConfigError as e:
            print(e)
    elif args.list:
        list_res = config.list()
        print("\n".join(list_res))
