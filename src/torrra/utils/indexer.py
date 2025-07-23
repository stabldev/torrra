import sys

import click

from torrra._types import Indexers, Provider
from torrra.app import TorrraApp
from torrra.core.exceptions import ConfigError


def run_from_indexer(indexer: Indexers, url: str, api_key: str):
    try:
        provider = Provider(indexer, url, api_key)
        app = TorrraApp(provider=provider)
        app.run()
    except (FileNotFoundError, RuntimeError, ConfigError) as e:
        click.secho(f"error: {e}", fg="red", err=True)
        sys.exit(1)
