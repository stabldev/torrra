import click

from torrra._version import __version__
from torrra.core.exceptions import ConfigError


@click.group(invoke_without_command=True)
@click.version_option(version=__version__, prog_name="torrra")
@click.pass_context
def cli(ctx: click.Context):
    if not ctx.invoked_subcommand:
        # run app
        pass


# ==================== INDEXERS ====================


@cli.command(help="Use Jackett as the indexer.")
@click.option("--url", required=True, help="Jackett server URL.")
@click.option("--api-key", required=True, help="Jackett API key.")
def jackett(url: str, api_key: str):
    from torrra.utils.indexer import run_with_indexer

    run_with_indexer("jackett", url, api_key)


@cli.command(help="Use Prowlarr as the indexer.")
@click.option("--url", required=True, help="Prowlarr server URL.")
@click.option("--api-key", required=True, help="Prowlarr API key.")
def prowlarr(url: str, api_key: str):
    from torrra.utils.indexer import run_with_indexer

    run_with_indexer("prowlarr", url, api_key)


# ==================== CONFIG ====================


@cli.group()
def config():
    pass


@config.command(name="get", help="Get a config value.")
@click.argument("key")
def config_get(key: str):
    from torrra.core.config import Config

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

    config = Config()
    try:
        config.set(key, value)
    except ConfigError as e:
        click.secho(e, fg="red", err=True)


@config.command(name="list", help="List all configurations.")
def config_list():
    from torrra.core.config import Config

    config = Config()
    try:
        click.echo("\n".join(config.list()))
    except ConfigError as e:
        click.secho(e, fg="red", err=True)


if __name__ == "__main__":
    cli()
