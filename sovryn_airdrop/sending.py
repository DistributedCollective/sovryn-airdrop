import click

from .airdrop import Airdrop
from .cli_base import cli, config_file_option, echo, echo_token_info
from .config import Config
from .tokens import load_token
from .web3_utils import get_web3


@cli.command()
@config_file_option
@click.option('-p', '--plan-file', required=True, metavar='PATH', help='Path to read the plan file from')
def send(config_file: str, plan_file: str):
    config = Config.from_file(config_file)
    web3 = get_web3(config.rpc_url)
    reward_token = load_token(
        web3=web3,
        address=config.reward_token_address
    )
    echo_token_info(reward_token, "Reward token")
    airdrop = Airdrop.from_file(
        file_path=plan_file,
        rewarder_address=config.rewarder_account_address,
        rewarder_token=reward_token
    )
    echo("Preparing to send Airdrop")
    echo(airdrop.as_table())
