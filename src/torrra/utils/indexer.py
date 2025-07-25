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

    indexer_cls = _lazy_import(indexer_cls_str)
    connection_error_cls = _lazy_import(connection_error_cls_str)

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


def _lazy_import(dotted_path: str):
    import importlib

    try:
        module_path, obj_name = dotted_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        return getattr(module, obj_name)
    except (ModuleNotFoundError, AttributeError) as e:
        click.secho(f"failed to load: {dotted_path}\n{e}", fg="red", err=True)
        raise
