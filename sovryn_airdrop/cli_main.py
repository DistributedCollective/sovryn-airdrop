from .cli_base import cli
# Make sure the subcommands are imported properly
from . import planning  # noqa
from . import sending  # noqa


if __name__ == '__main__':
    cli()
