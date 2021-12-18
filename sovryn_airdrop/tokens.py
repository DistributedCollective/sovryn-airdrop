from dataclasses import dataclass
from dataclasses import dataclass
from decimal import Decimal
from typing import Union

from eth_typing import AnyAddress
from web3 import Web3
from web3.eth import Contract

from .web3_utils import get_erc20_contract


@dataclass
class Token:
    contract: Contract
    address: str
    chain_id: int
    name: str
    symbol: str
    decimals: int

    def decimal_amount(self, amount_wei: int) -> Decimal:
        return amount_wei / (Decimal(10) ** self.decimals)

    def str_amount(self, amount_wei: int, decimal_places=None) -> str:
        if decimal_places is None:
            return str(self.decimal_amount(amount_wei))
        else:
            return str(round(self.decimal_amount(amount_wei), decimal_places))

    def formatted_amount(self, amount_wei: int, decimal_places=6):
        return f'{self.decimal_amount(amount_wei):{decimal_places + 9}.{decimal_places}f} {self.symbol}'


def load_token(*, address: Union[str, AnyAddress], web3: Web3) -> Token:
    contract = get_erc20_contract(
        token_address=address,
        web3=web3,
    )
    return Token(
        address=contract.address,
        chain_id=web3.eth.chain_id,
        name=contract.functions.name().call(),
        symbol=contract.functions.symbol().call(),
        decimals=contract.functions.decimals().call(),
        contract=contract,
    )
