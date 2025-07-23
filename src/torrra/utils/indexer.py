import sys

import click

from torrra._types import Indexers, Provider
from torrra.core.exceptions import ConfigError


def run_with_indexer(indexer: Indexers, url: str, api_key: str):
    from torrra.app import TorrraApp

    try:
        provider = Provider(indexer, url, api_key)
        app = TorrraApp(provider=provider)
        app.run()
    except (FileNotFoundError, RuntimeError, ConfigError) as e:
        click.secho(f"error: {e}", fg="red", err=True)
        sys.exit(1)
