import token
from dataclasses import dataclass
from typing import Any

import click
from .config import Config
from .utils import EventBatchComplete, get_events, get_web3, get_erc20_contract, is_contract, retryable
from .tokens import Token, load_token
from .core import find_non_contract_token_holders


@dataclass
class TokenHolder:
    address: str
    balance_wei: int


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


@cli.command()
@config_file_option
@click.option('-p', '--plan-file', required=True, metavar='PATH', help='Path to write the plan file to')
def plan(config_file: str, plan_file: str):
    """
    Plan an airdrop, generating a file that can be used to execute the airdrop.
    """
    config = Config.from_file(config_file)
    click.echo(f'Planning airdrop with config {config}')
    web3 = get_web3(config.rpc_url)
    holding_token = load_token(
        web3=web3,
        address=config.holding_token_address
    )
    _echo_token_info(holding_token, "Holding token")

    reward_token = load_token(
        web3=web3,
        address=config.reward_token_address
    )
    _echo_token_info(reward_token, "Reward token")

    # Find token holders
    click.echo('Finding non-contract token holders (this might take a while)')
    num_blocks = config.snapshot_block_number - config.first_scanned_block_number
    with click.progressbar(
        length=num_blocks,
        label='Fetching Transfer events'
    ) as bar:
        transfer_events = get_events(
            event=holding_token.contract.events.Transfer,
            from_block=config.first_scanned_block_number,
            to_block=config.snapshot_block_number,
            batch_size=50,
            on_batch_complete=_event_batch_progress_bar_updater(bar, config.first_scanned_block_number)
        )
    _echo("Found", _hilight(len(transfer_events)), 'transfer events.')
    possible_addresses = set()
    for event in transfer_events:
        possible_addresses.add(event.args['from'])
        possible_addresses.add(event.args['to'])
    _echo("Found", _hilight(len(possible_addresses)), 'possible holder addresses in total (including contracts).')

    # Find token holder balances
    token_holders = []
    with click.progressbar(
        possible_addresses,
        label=f'Fetching snapshot balances and filtering'
    ) as bar:
        for address in bar:
            if not is_contract(
                web3=web3,
                address=address
            ):
                # We don't want to include contract addresses here
                continue

            balance_wei = _fetch_balance_in_block(
                token=holding_token,
                address=address,
                block_number=config.snapshot_block_number
            )
            if balance_wei == 0:
                # The address is not a holder after all
                continue

            token_holder = TokenHolder(
                address=address,
                balance_wei=balance_wei
            )
            token_holders.append(token_holder)

    token_holders.sort(key=lambda t: t.balance_wei, reverse=True)
    total_balance_wei = sum(t.balance_wei for t in token_holders)
    _echo(
        "Address".ljust(42),
        f'{holding_token.symbol} (wei)'.rjust(30),
        f'{holding_token.symbol} (decimal)'.rjust(20),
    )
    for token_holder in token_holders:
        _echo(
            token_holder.address,
            str(token_holder.balance_wei).rjust(30),
            holding_token.str_amount(token_holder.balance_wei, 6).rjust(20)
        )
    _echo(
        "Total balance".ljust(42),
        _hilight(str(total_balance_wei).rjust(30)),
        _hilight(holding_token.str_amount(total_balance_wei, 6).rjust(20))
    )

    # Include LP pool balance in above calculation


@retryable()
def _fetch_balance_in_block(*, token: Token, address, block_number: int) -> int:
    return token.contract.functions.balanceOf(address).call(
        block_identifier=block_number
    )


def _event_batch_progress_bar_updater(bar, from_block: int):
    """Get a callback that can be passed to utils.get_events and that updates a click progress bar"""
    def updater(data: EventBatchComplete):
        bar.update(data.batch_to_block - from_block)
    return updater


def _echo(*texts: Any):
    click.echo(' '.join(str(s) for s in texts))


def _hilight(text: Any):
    return click.style(str(text), fg='green')


def _echo_token_info(token: Token, prefix: str):
    click.echo(f"{prefix}: ", nl=False)
    click.echo(_hilight(f"{token.name} ({token.symbol}) "), nl=False)
    click.echo("at address ", nl=False)
    click.echo(_hilight(f"{token.address} "), nl=False)
    click.echo("with ", nl=False)
    click.echo(_hilight(f"{token.decimals} "), nl=False)
    click.echo("decimals.")


if __name__ == '__main__':
    cli()
