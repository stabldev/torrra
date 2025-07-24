import sys

import click

from torrra._types import Indexer, IndexerName
from torrra.core.exceptions import ConfigError


def run_with_indexer(indexer: IndexerName, url: str, api_key: str, use_cache: bool):
    from torrra.app import TorrraApp

    try:
        provider = Indexer(indexer, url, api_key)
        app = TorrraApp(provider, use_cache)
        app.run()
    except (FileNotFoundError, RuntimeError, ConfigError) as e:
        click.secho(f"error: {e}", fg="red", err=True)
        sys.exit(1)
