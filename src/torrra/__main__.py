import click

from torrra._version import __version__


@click.group(invoke_without_command=True)
@click.version_option(version=__version__, prog_name="torrra")
@click.pass_context
def cli(ctx: click.Context) -> None:
    if not ctx.invoked_subcommand:
        # run app
        pass


# ========== INDEXERS ==========


@cli.command(help="Use Jackett as the indexer.")
@click.option("--url", required=True, help="Jackett server URL.")
@click.option("--api-key", required=True, help="Jackett API key.")
def jackett(url: str, api_key: str) -> None:
    click.secho(f"connecting to jackett server at: {url}", fg="cyan")

    import asyncio

    from torrra.core.exceptions import JackettConnectionError
    from torrra.indexers.jackett import JackettIndexer
    from torrra.utils.indexer import run_with_indexer

    async def validate_indexer() -> bool:
        try:
            return await JackettIndexer(url, api_key).validate()
        except JackettConnectionError as e:
            click.secho(e, fg="red", err=True)
            return False

    valid = asyncio.run(validate_indexer())
    if valid:
        run_with_indexer("jackett", url, api_key)


@cli.command(help="Use Prowlarr as the indexer.")
@click.option("--url", required=True, help="Prowlarr server URL.")
@click.option("--api-key", required=True, help="Prowlarr API key.")
def prowlarr(url: str, api_key: str):
    click.secho(f"connecting to prowlarr server at: {url}", fg="cyan")

    import asyncio

    from torrra.core.exceptions import ProwlarrConnectionError
    from torrra.indexers.prowlarr import ProwlarrIndexer
    from torrra.utils.indexer import run_with_indexer

    async def validate_indexer() -> bool:
        try:
            return await ProwlarrIndexer(url, api_key).validate()
        except ProwlarrConnectionError as e:
            click.secho(e, fg="red", err=True)
            return False

    valid = asyncio.run(validate_indexer())
    if valid:
        run_with_indexer("prowlarr", url, api_key)


# ========== CONFIG ==========


@cli.group(help="Manage configuration.")
def config():
    pass


@config.command(name="get", help="Get a config value.")
@click.argument("key")
def config_get(key: str):
    from torrra.core.config import Config
    from torrra.core.exceptions import ConfigError

    config = Config()
    try:
        click.echo(config.get(key))
    except ConfigError as e:
        click.secho(e, fg="red", err=True)


@config.command(name="set", help="Set a config value to path.")
@click.argument("key")
@click.argument("value")
def config_set(key: str, value: str):
    from torrra.core.config import Config
    from torrra.core.exceptions import ConfigError

    config = Config()
    try:
        config.set(key, value)
    except ConfigError as e:
        click.secho(e, fg="red", err=True)


@config.command(name="list", help="List all configurations.")
def config_list():
    from torrra.core.config import Config
    from torrra.core.exceptions import ConfigError

    config = Config()
    try:
        click.echo("\n".join(config.list()))
    except ConfigError as e:
        click.secho(e, fg="red", err=True)


if __name__ == "__main__":
    cli()
