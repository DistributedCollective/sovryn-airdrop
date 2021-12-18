import json
from dataclasses import dataclass
from eth_typing import HexAddress

from .utils import to_address


@dataclass
class Config:
    rpc_url: str
    holding_token_address: HexAddress
    reward_token_address: HexAddress
    reward_amount: int

    @classmethod
    def from_file(cls, file_path: str):
        with open(file_path) as f:
            raw = json.load(f)
        return cls(
            rpc_url=raw['rpcUrl'],
            holding_token_address=to_address(raw['holdingTokenAddress']),
            reward_token_address=to_address(raw['rewardTokenAddress']),
            reward_amount=int(raw['rewardAmount']),
        )