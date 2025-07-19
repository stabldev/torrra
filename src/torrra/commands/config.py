from typing import Any

from torrra.core.context import config


def handle_config_command(args: Any):
    if args.get:
        get_res = config.get(args.get)
        print(get_res)
    elif args.set:
        config.set(args.set[0], args.set[1])
    elif args.list:
        list_res = config.list()
        print("\n".join(list_res))
