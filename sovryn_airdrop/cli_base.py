# Base for CLI
from typing import Any

import click

from sovryn_airdrop.tokens import Token

config_file_option = click.option(
    '-c',
    '--config-file',
    required=True,
    metavar='PATH',
    help='Path to JSON config file'
)


@click.group('sovryn_airdrop')
def cli():
    pass


def echo(*texts: Any):
    click.echo(' '.join(str(s) for s in texts))


def bold(text: Any):
    return click.style(str(text), bold=True)


def hilight(text: Any):
    return click.style(str(text), fg='green')


def echo_token_info(token: Token, prefix: str):
    click.echo(f"{prefix}: ", nl=False)
    click.echo(hilight(f"{token.name} ({token.symbol}) "), nl=False)
    click.echo("at address ", nl=False)
    click.echo(hilight(f"{token.address} "), nl=False)
    click.echo("with ", nl=False)
    click.echo(hilight(f"{token.decimals} "), nl=False)
    click.echo("decimals.")
