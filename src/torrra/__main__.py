import click

from torrra._version import __version__


@click.group(invoke_without_command=True)
@click.version_option(version=__version__, prog_name="torrra")
@click.pass_context
def cli(ctx: click.Context):
    if not ctx.invoked_subcommand:
        # run app
        pass


@cli.group(help="Manage configuration.")
def config():
    pass


@config.command(help="Get a config value.")
@click.argument("path")
def config_get(path: str):
    click.echo(f"getting config value at: {path}")


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


if __name__ == "__main__":
    cli()
