import argparse

from torrra._version import __version__


def parse_cli_args():
    parser = argparse.ArgumentParser(prog="torrra")
    subparsers = parser.add_subparsers(dest="command")

    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s v{__version__}",
        help="show torrra version and exit",
    )
    parser.add_argument(
        "-j",
        "--jackett",
        nargs="*",
        metavar=("URL", "API_KEY"),
        help="use Jackett provider and/or provide URL and API key",
    )

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

    return parser.parse_args()
