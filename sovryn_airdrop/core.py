import web3.contract
from web3 import Web3
import click
from .tokens import Token
from .utils import get_events, EventBatchComplete


def _event_batch_progress_bar_updater(bar, from_block: int):
    def updater(data: EventBatchComplete):
        bar.update(data.batch_to_block - from_block)
    return updater


def find_non_contract_token_holders(
    *,
    web3: Web3,
    token_contract: web3.contract.Contract,
    from_block: int,
    to_block: int
):
    """
    Find addresses that are possible token holders and are not contracts
    """
    with click.progressbar(length=to_block - from_block, label='Fetching Transfer events') as bar:
        events = get_events(
            event=token_contract.events.Transfer,
            from_block=from_block,
            to_block=to_block,
            batch_size=50,
            on_batch_complete=_event_batch_progress_bar_updater(bar, from_block)
        )

