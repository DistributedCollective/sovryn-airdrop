# Base for CLI
from typing import Any

import click


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


