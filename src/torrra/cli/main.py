import argparse

from torrra.cli.config import handle_config_command
from torrra.cli.torrent import run_torrent_flow


def main() -> None:
    parser = argparse.ArgumentParser(prog="torrra")
    subparsers = parser.add_subparsers(dest="command")

    # "config" sub-command
    config_parser = subparsers.add_parser("config", help="configure torrra")
    config_parser.add_argument("-g", "--get", metavar="KEY", help="get a config value")
    config_parser.add_argument(
        "-s",
        "--set",
        nargs=2,
        metavar=("KEY", "VALUE"),
        help="set a config key-value pair",
    )
    config_parser.add_argument(
        "-l", "--list", action="store_true", help="list all configs"
    )

    args = parser.parse_args()

    if args.command == "config":
        handle_config_command(args)
    else:
        run_torrent_flow()
