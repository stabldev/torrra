import click

from torrra._version import __version__


@click.group(invoke_without_command=True)
@click.version_option(version=__version__, prog_name="torrra")
@click.option("--no-cache", is_flag=True, help="Disable caching mechanism.")
@click.pass_context
def cli(ctx: click.Context, no_cache: bool) -> None:
    if ctx.invoked_subcommand is None:
        from torrra.utils.indexer import run_with_default_indexer

        # detect indexer from config and execute
        run_with_default_indexer(no_cache=no_cache)


# --------------------------------------------------
# SEARCH
# --------------------------------------------------
@cli.command(help="Search for a torrent.")
@click.argument("search_query")
@click.option("--no-cache", is_flag=True, help="Disable caching mechanism.")
def search(search_query: str, no_cache: bool) -> None:
    from torrra.utils.indexer import run_with_default_indexer

    # detect indexer from config and execute with given search query
    run_with_default_indexer(no_cache=no_cache, search_query=search_query)


# --------------------------------------------------
# INDEXERS
# --------------------------------------------------
@cli.command(help="Use Jackett as the indexer.")
@click.option("--url", required=False, help="Jackett server URL.")
@click.option("--api-key", required=False, help="Jackett API key.")
@click.option("--no-cache", is_flag=True, help="Disable caching mechanism.")
def jackett(url: str | None, api_key: str | None, no_cache: bool) -> None:
    from torrra.utils.indexer import run_with_indexer

    # run app with jackett indexer
    run_with_indexer(
        name="jackett",
        indexer_cls_str="torrra.indexers.jackett.JackettIndexer",
        url=url,
        api_key=api_key,
        no_cache=no_cache,
    )


@cli.command(help="Use Prowlarr as the indexer.")
@click.option("--url", required=False, help="Prowlarr server URL.")
@click.option("--api-key", required=False, help="Prowlarr API key.")
@click.option("--no-cache", is_flag=True, help="Disable caching mechanism.")
def prowlarr(url: str | None, api_key: str | None, no_cache: bool):
    from torrra.utils.indexer import run_with_indexer

    # run app with prowlarr indexer
    run_with_indexer(
        name="prowlarr",
        indexer_cls_str="torrra.indexers.prowlarr.ProwlarrIndexer",
        url=url,
        api_key=api_key,
        no_cache=no_cache,
    )


# --------------------------------------------------
# CONFIG
# --------------------------------------------------
@cli.group(help="Manage configuration.")
def config():
    pass


@config.command(name="get", help="Get a config value.")
@click.argument("key")
def config_get(key: str):
    from torrra.core.config import config
    from torrra.core.exceptions import ConfigError

    try:
        click.echo(config.get(key))
    except ConfigError as e:
        click.secho(e, fg="red", err=True)


@config.command(name="set", help="Set a config value to path.")
@click.argument("key")
@click.argument("value")
def config_set(key: str, value: str):
    from torrra.core.config import config
    from torrra.core.exceptions import ConfigError

    try:
        config.set(key, value)
    except ConfigError as e:
        click.secho(e, fg="red", err=True)


@config.command(name="list", help="List all configurations.")
def config_list():
    from torrra.core.config import config
    from torrra.core.exceptions import ConfigError

    try:
        click.echo("\n".join(config.list()))
    except ConfigError as e:
        click.secho(e, fg="red", err=True)


if __name__ == "__main__":
    cli()
