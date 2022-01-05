import click

from eth_account import Account
from eth_account.signers.local import LocalAccount

from .airdrop import Airdrop
from .cli_base import cli, config_file_option, echo, echo_token_info, hilight
from .config import Config
from .tokens import load_token
from .web3_utils import get_web3, set_web3_account


@cli.command()
@config_file_option
@click.option('-p', '--plan-file', required=True, metavar='PATH', help='Path to read the plan file from')
def send(config_file: str, plan_file: str):
    config = Config.from_file(config_file)
    echo('Config:', config)
    airdrop = Airdrop.from_file(
        file_path=plan_file,
        config=config
    )
    echo("Rewarder account", config.rewarder_account_address)
    echo("Reward token balance:", config.reward_token.formatted_amount(
        config.reward_token.contract.functions.balanceOf(config.rewarder_account_address).call()
    ))
    echo("Next nonce:", config.web3.eth.get_transaction_count(config.rewarder_account_address))
    echo("\nPreparing to send Airdrop:")
    echo(airdrop.as_table())
    click.confirm('Execute airdrop?', abort=True)
    private_key = click.prompt(
        f'Enter private key for rewarder address {config.rewarder_account_address} (input hidden)',
        hide_input=True
    )
    rewarder_account: LocalAccount = Account.from_key(private_key)
    if rewarder_account.address != config.rewarder_account_address:
        raise click.Abort(
            f"Address from private key {rewarder_account.address} does not match configured address "
            f"{config.rewarder_account_address}."
        )

    web3 = config.web3
    set_web3_account(web3=web3, account=rewarder_account)

    backup_file_path = plan_file + '.bak'
    echo(f'Backing up airdrop plan file to {backup_file_path}')
    airdrop.to_file(backup_file_path)

    if airdrop.sent_transactions:
        echo(
            hilight(len(airdrop.sent_transactions)),
            'transactions have already been sent, verifying.'
        )
        for transaction in airdrop.sent_transactions:
            echo('Verifying', transaction.as_row())
            echo(transaction.verify())

    #num_total = len(airdrop.unsent_transactions)
    #max_pending = 4
    #pending = []
    for transaction in airdrop.unsent_transactions:
        echo('Sending:', transaction.as_row())
        transaction.send()
        echo('Sent', transaction.transaction_hash)
        airdrop.to_file(plan_file)
        echo('Verifying...')
        transaction.verify()
        echo('Ok')

    click.echo("Airdrop sent")