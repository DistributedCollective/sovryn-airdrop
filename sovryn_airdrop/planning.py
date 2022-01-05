import os
from collections import Counter, defaultdict
from dataclasses import dataclass
from decimal import Decimal
from typing import Set

import click
from eth_typing import ChecksumAddress
from web3 import Web3

from .airdrop import Airdrop
from .cli_base import cli, bold, echo, echo_token_info, hilight, config_file_option
from .config import Config
from .tokens import Token, load_token
from .web3_utils import EventBatchComplete, get_erc20_contract, get_events, is_contract, load_abi, retryable


@dataclass
class TokenHolder:
    address: ChecksumAddress
    holding_token_balance_on_account_wei: int
    lp_token_balance_on_account_wei: int
    holding_token_balance_on_lp_wei: int

    @property
    def total_holding_token_balance_wei(self) -> int:
        return self.holding_token_balance_on_account_wei + self.holding_token_balance_on_lp_wei


@cli.command()
@config_file_option
@click.option('-p', '--plan-file', required=True, metavar='PATH', help='Path to write the plan file to')
def plan(config_file: str, plan_file: str):
    """
    Plan an airdrop, generating a file that can be used to execute the airdrop.
    """
    config = Config.from_file(config_file)
    click.echo(f'Planning airdrop with config {config}')

    if os.path.exists(plan_file):
        click.confirm(f'A plan file already exists at {plan_file!r}, overwrite?', abort=True)

    web3 = config.web3
    holding_token = config.holding_token
    echo_token_info(holding_token, "Holding token")

    reward_token = config.reward_token
    echo_token_info(reward_token, "Reward token")

    lp_token, holding_token_reserve_balance, lp_token_total_supply = fetch_liquidity_pool_data(
        config=config,
        holding_token=holding_token,
        web3=web3
    )

    # Find token holders
    click.echo('Finding non-contract token holder addresses and balances (this might take a while)')
    possible_addresses = set()
    possible_addresses |= fetch_possible_token_holders(config, holding_token)
    possible_addresses |= fetch_possible_token_holders(config, lp_token)
    echo(
        "Found a total of",
        hilight(len(possible_addresses)),
        'possible token holder addresses (including contracts)',
        f'from {holding_token.symbol} and/or {lp_token.symbol} transfers.'
    )

    # Find token holder balances
    token_holders = []
    excluded_because = Counter()
    with click.progressbar(
        possible_addresses,
        label=f'Fetching snapshot balances and filtering out contracts'
    ) as bar:
        for address in bar:
            if is_contract(
                web3=web3,
                address=address
            ):
                # We don't want to include contract addresses here
                #print('\nis_contract', address)
                excluded_because['is_contract'] += 1
                continue

            holding_token_balance_wei = fetch_balance_in_block(
                token=holding_token,
                address=address,
                block_number=config.snapshot_block_number
            )
            lp_token_balance_wei = fetch_balance_in_block(
                token=lp_token,
                address=address,
                block_number=config.snapshot_block_number
            )
            if lp_token_balance_wei == holding_token_balance_wei == 0:
                # The address is not a holder after all
                #print('zero_balance', address, holding_token_balance_wei, lp_token_balance_wei)
                excluded_because['zero_balance'] += 1
                continue

            # Calculate holding token balance on liquidity pool by multiplying LP token balance in user wallet with the
            # fraction of the holding token one LP token represents.
            holding_token_balance_on_lp_wei = (
                lp_token_balance_wei * holding_token_reserve_balance // lp_token_total_supply
            )
            token_holder = TokenHolder(
                address=address,
                holding_token_balance_on_account_wei=holding_token_balance_wei,
                lp_token_balance_on_account_wei=lp_token_balance_wei,
                holding_token_balance_on_lp_wei=holding_token_balance_on_lp_wei,
            )
            token_holders.append(token_holder)

    echo("Found", hilight(len(token_holders)), f'actual token holders (excluding contracts and zero balances)')
    echo('Reasons excluded:', excluded_because)

    token_holders.sort(key=lambda t: t.total_holding_token_balance_wei, reverse=True)
    echo_balance_table(
        holding_token=holding_token,
        lp_token=lp_token,
        token_holders=token_holders
    )

    total_holding_token_balance_wei = sum(t.total_holding_token_balance_wei for t in token_holders)
    airdrop = Airdrop(
        config=config
    )
    current_nonce = web3.eth.get_transaction_count(config.rewarder_account_address)
    for token_holder in token_holders:
        # Calculate proportional reward amount
        balance_wei = token_holder.total_holding_token_balance_wei
        reward_amount_wei = config.total_reward_amount_wei * balance_wei // total_holding_token_balance_wei
        if reward_amount_wei < config.min_reward_wei:
            continue
        airdrop.add_transaction(
            to_address=token_holder.address,
            reward_amount_wei=reward_amount_wei,
            transaction_nonce=current_nonce
        )
        current_nonce += 1

    click.echo("")
    click.echo("Airdrop plan is as follows:")
    click.echo(airdrop.as_table())
    click.echo(f"Saving airdrop plan to {plan_file!r}")
    airdrop.to_file(plan_file)


def fetch_liquidity_pool_data(*, config: Config, holding_token: Token, web3: Web3):
    liquidity_pool = web3.eth.contract(
        address=config.holding_token_liquidity_pool_address,
        abi=load_abi('LiquidityPoolV1Converter'),
    )
    echo('Holding token liquidity pool (converter) at address:', hilight(config.holding_token_liquidity_pool_address))
    converter_type = liquidity_pool.functions.converterType().call()
    if converter_type != 1:
        raise ValueError(
            f"Invalid converter type: {converter_type}. Only V1 converters are supported for now."
        )
    lp_token = load_token(
        web3=web3,
        address=liquidity_pool.functions.anchor().call(),
    )
    echo_token_info(lp_token, 'Holding LP token')
    lp_token_total_supply = lp_token.contract.functions.totalSupply().call(
        block_identifier=config.snapshot_block_number
    )
    echo(
        'Total LP token supply:',
        hilight(lp_token.formatted_amount(lp_token_total_supply)),
    )

    # The pool only supports 2 reserve tokens -- the holding token is one of these
    reserve_token_addresses = [
        liquidity_pool.functions.reserveTokens(0).call(block_identifier=config.snapshot_block_number),
        liquidity_pool.functions.reserveTokens(1).call(block_identifier=config.snapshot_block_number),
    ]
    reserve_tokens = [
        load_token(
            address=token_address,
            web3=config.web3
        )
        for token_address in reserve_token_addresses
    ]
    reserve_balances = [
        liquidity_pool.functions.reserveBalance(token_address).call(block_identifier=config.snapshot_block_number)
        for token_address in reserve_token_addresses
    ]
    holding_token_reserve_index = reserve_token_addresses.index(holding_token.address)
    holding_token_reserve_balance = reserve_balances[holding_token_reserve_index]
    echo("Liquidity pool reserves:")
    for token, balance in zip(reserve_tokens, reserve_balances):
        echo(
            token.address,
            token.str_amount(balance).rjust(30),
            token.symbol,
            '(holding token)' if token.address == holding_token.address else ''
        )

    #echo(
    #    'Holding token',
    #    hilight(holding_token.symbol),
    #    'represents',
    #    hilight(f'{holding_token_reserve_balance / total_reserve_balance * 100} %'),
    #    'of the liquidity pool reserve balances.'
    #)

    ## Print this info here because it's a pretty interesting sanity check
    #try:
    #    other_symbol = lp_token.symbol.replace(holding_token.symbol, '').replace('/', '')
    #    echo(
    #        '(So, according to reserve balances,',
    #        hilight('1'),
    #        other_symbol,
    #        '=',
    #        hilight(holding_token_reserve_balance / (total_reserve_balance - holding_token_reserve_balance)),
    #        lp_token.symbol.replace(other_symbol, '').replace('/', ''),
    #        ')'
    #    )
    #except Exception:  # noqa
    #    pass

    echo(
        '1 LP token represents',
        hilight(
            holding_token.formatted_amount(
                lp_token.wei_amount(1) * holding_token_reserve_balance // lp_token_total_supply
            ),
        ),
    )

    return lp_token, holding_token_reserve_balance, lp_token_total_supply


def fetch_possible_token_holders(config, token: Token) -> Set[str]:
    possible_addresses = set()
    num_blocks = config.snapshot_block_number - config.first_scanned_block_number
    with click.progressbar(
        length=num_blocks,
        label=f'Fetching {token.symbol} Transfer events'
    ) as bar:
        transfer_events = get_events(
            event=token.contract.events.Transfer,
            from_block=config.first_scanned_block_number,
            to_block=config.snapshot_block_number,
            batch_size=500,
            on_batch_complete=event_batch_progress_bar_updater(bar, config.first_scanned_block_number)
        )
    echo("Found", hilight(len(transfer_events)), f'{token.symbol} Transfer events.')
    for event in transfer_events:
        possible_addresses.add(event.args['from'])
        possible_addresses.add(event.args['to'])
    echo(
        "Found",
        hilight(len(possible_addresses)),
        f'possible {token.symbol} holder addresses in total (including contracts).'
    )
    return possible_addresses


@retryable()
def fetch_balance_in_block(*, token: Token, address, block_number: int) -> int:
    return token.contract.functions.balanceOf(address).call(
        block_identifier=block_number
    )


def event_batch_progress_bar_updater(bar, from_block: int):
    """Get a callback that can be passed to utils.get_events and that updates a click progress bar"""
    def updater(data: EventBatchComplete):
        # Update takes the number of items to advance the bar.
        # Blocks are inclusive, hence + 1
        bar.update(data.batch_to_block - data.batch_from_block + 1)
    return updater


def echo_balance_table(holding_token, lp_token, token_holders):
    total_balance_wei = sum(t.total_holding_token_balance_wei for t in token_holders)
    echo(
        bold("Address".ljust(42)),
        bold(f'{holding_token.symbol}'.rjust(30)),
        bold(f'{lp_token.symbol}'.rjust(30)),
        bold(f'{holding_token.symbol} on LP'.rjust(30)),
        bold(f'{holding_token.symbol} total'.rjust(30)),
    )
    str_amount = holding_token.str_amount
    for token_holder in token_holders:
        echo(
            token_holder.address,
            str_amount(token_holder.holding_token_balance_on_account_wei).rjust(30),
            str_amount(token_holder.lp_token_balance_on_account_wei).rjust(30),
            str_amount(token_holder.holding_token_balance_on_lp_wei).rjust(30),
            bold(str_amount(token_holder.total_holding_token_balance_wei).rjust(30))
        )
    echo(
        bold("Total balances".ljust(42)),
        bold(str_amount(sum(t.holding_token_balance_on_account_wei for t in token_holders)).rjust(30)),
        bold(str_amount(sum(t.lp_token_balance_on_account_wei for t in token_holders)).rjust(30)),
        bold(str_amount(sum(t.holding_token_balance_on_lp_wei for t in token_holders)).rjust(30)),
        bold(str_amount(total_balance_wei).rjust(30)),
    )
