from typing import cast

import click

from torrra._types import Indexer, IndexerName


def handle_indexer_command(
    name: IndexerName,
    indexer_cls_str: str,
    connection_error_cls_str: str,
    url: str | None,
    api_key: str | None,
    no_cache: bool,
):
    if url is None and api_key is None:
        from torrra.core.context import config
        from torrra.core.exceptions import ConfigError

        try:
            url = config.get(f"indexers.{name}.url")
            api_key = config.get(f"indexers.{name}.api_key")
        except ConfigError as e:
            click.secho(f"{e}\ncheck your configuration file.", fg="red", err=True)
            return
    elif url is None or api_key is None:
        click.secho(
            "both --url and --api-key must be provided together, or neither to use config.",
            fg="red",
            err=True,
        )
        return

    click.secho(f"connecting to {name} server at {url}", fg="cyan")
    import asyncio

    from torrra.utils.helpers import lazy_import

    indexer_cls = lazy_import(indexer_cls_str)
    connection_error_cls = lazy_import(connection_error_cls_str)

    async def validate_indexer() -> bool:
        try:
            return await indexer_cls(url, api_key).validate()
        except connection_error_cls as e:
            click.secho(str(e), fg="red", err=True)
            return False

    if asyncio.run(validate_indexer()):
        from torrra.app import TorrraApp
        from torrra.core.context import config

        # update/store indexers configuration
        config.set(f"indexers.{name}.url", url)
        config.set(f"indexers.{name}.api_key", api_key)

        provider = Indexer(name, url, api_key)
        app = TorrraApp(provider, use_cache=not no_cache)
        app.run()


def auto_detect_indexer_and_run():
    from torrra.core.context import config
    from torrra.core.exceptions import ConfigError

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
            no_cache=False,
        )
    except ConfigError as e:
        click.secho(f"{e}\ncheck your configuration file.", fg="red", err=True)
        return
