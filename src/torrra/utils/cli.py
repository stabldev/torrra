import argparse


def parse_cli_args():
    parser = argparse.ArgumentParser(prog="torrra")
    parser.add_argument(
        "-j", "--jackett", action="store_true", help="use Jackett configuration"
    )
    return parser.parse_args()
