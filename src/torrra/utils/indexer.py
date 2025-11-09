import asyncio
from typing import cast

import click

from torrra._types import Indexer, IndexerName
from torrra.core.config import config
from torrra.core.exceptions import ConfigError
from torrra.indexers.base import BaseIndexer
from torrra.utils.helpers import lazy_import


def handle_indexer_command(
    name: IndexerName,
    indexer_cls_str: str,
    connection_error_cls_str: str,
    url: str | None,
    api_key: str | None,
    no_cache: bool,
) -> None:
    # validate command args
    if (url is None) != (api_key is None):
        click.secho(
            "both --url and --api-key must be provided together, or neither to use config.",
            fg="red",
            err=True,
        )
        return

    # url, api_key config fallback
    if url is None and api_key is None:
        try:
            url = config.get(f"indexers.{name}.url")
            api_key = config.get(f"indexers.{name}.api_key")
        except ConfigError as e:
            click.secho(f"{e}\ncheck your configuration file.", fg="red", err=True)
            return

    click.secho(f"connecting to {name} server at {url}", fg="cyan")

    # import indexers only when needed
    indexer_cls = lazy_import(indexer_cls_str)
    connection_error_cls = lazy_import(connection_error_cls_str)

    # type narrowing for pyright
    assert url is not None and api_key is not None

    # async indexer validation
    async def healthcheck_indexer():
        try:
            assert issubclass(indexer_cls, BaseIndexer)
            return await indexer_cls(url, api_key).healthcheck()
        except connection_error_cls as e:
            click.secho(str(e), fg="red", err=True)
            return False

    if not asyncio.run(healthcheck_indexer()):
        return

    # update/store indexers configuration
    config.set(f"indexers.{name}.url", url)
    config.set(f"indexers.{name}.api_key", api_key)

    # load app only when needed (heavy stuff)
    from torrra.app import TorrraApp

    try:
        # determine cache settings with CLI override
        use_cache = config.get("general.use_cache", True)
        if no_cache:  # --no-cache flag overrides config
            use_cache = False

        indexer = Indexer(name, url, api_key)
        app = TorrraApp(indexer, use_cache=use_cache)
        app.run()
    except RuntimeError as e:
        click.secho(str(e), fg="red", err=True)


def auto_detect_indexer_and_run(no_cache: bool) -> None:
    try:
        default_indexer = config.get("indexers.default")
        if not default_indexer:
            raise ConfigError("no default indexer specified under [indexers.default].")

        url = config.get(f"indexers.{default_indexer}.url")
        api_key = config.get(f"indexers.{default_indexer}.api_key")

        handle_indexer_command(
            name=cast(IndexerName, default_indexer),
            indexer_cls_str=f"torrra.indexers.{default_indexer}.{default_indexer.title()}Indexer",
            connection_error_cls_str=f"torrra.core.exceptions.{default_indexer.title()}ConnectionError",
            url=url,
            api_key=api_key,
            no_cache=no_cache,
        )
    except ConfigError as e:
        click.secho(f"{e}\ncheck your configuration file.", fg="red", err=True)
