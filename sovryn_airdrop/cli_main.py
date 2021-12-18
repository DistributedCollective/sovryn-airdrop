from .cli_base import cli
# Make sure the subcommands are imported properly
from . import planning  # noqa


if __name__ == '__main__':
    cli()
