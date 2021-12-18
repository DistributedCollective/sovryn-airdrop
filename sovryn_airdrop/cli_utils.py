from typing import Any

import click


def echo(*texts: Any):
    click.echo(' '.join(str(s) for s in texts))


def bold(text: Any):
    return click.style(str(text), bold=True)


def hilight(text: Any):
    return click.style(str(text), fg='green')


