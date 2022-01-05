import json
from dataclasses import dataclass
from typing import Optional

from eth_typing import ChecksumAddress
from web3 import Web3

from .web3_utils import get_web3, to_address
from .tokens import Token, load_token


@dataclass
class JSONConfig:
    """
    Raw config, as it exists as JSON on disk
    """
    rpcUrl: str
    holdingTokenAddress: str
    holdingTokenLiquidityPoolAddress: str
    rewardTokenAddress: str
    rewarderAccountAddress: str
    snapshotBlockNumber: int
    firstScannedBlockNumber: int
    totalRewardAmountWei: Optional[str] = None
    totalRewardAmountDecimal: Optional[str] = None
    minRewardWei: Optional[str] = None

    @classmethod
    def from_file(cls, file_path: str) -> 'JSONConfig':
        with open(file_path) as f:
            raw = json.load(f)
            raw = {k: v for (k, v) in raw.items() if not k.startswith('#')}
            return cls(**raw)


@dataclass
class Config:
    """
    Config that contains data in a nice form, possibly pre-loaded from web3
    """
    web3: Web3
    rpc_url: str  # we could get rid of this
    holding_token: Token
    holding_token_liquidity_pool_address: ChecksumAddress  # Let's make it non-optional for now
    reward_token: Token
    rewarder_account_address: ChecksumAddress
    total_reward_amount_wei: int
    min_reward_wei: int
    snapshot_block_number: int
    first_scanned_block_number: int

    @property
    def holding_token_address(self) -> ChecksumAddress:
        return to_address(self.holding_token.address)

    @property
    def reward_token_address(self) -> ChecksumAddress:
        return to_address(self.reward_token.address)

    @classmethod
    def from_file(cls, file_path: str) -> 'Config':
        raw = JSONConfig.from_file(file_path)

        web3 = get_web3(raw.rpcUrl)
        holding_token = load_token(
            address=to_address(raw.holdingTokenAddress),
            web3=web3
        )
        reward_token = load_token(
            address=to_address(raw.rewardTokenAddress),
            web3=web3
        )

        return cls(
            web3=web3,
            rpc_url=raw.rpcUrl,
            holding_token=holding_token,
            holding_token_liquidity_pool_address=to_address(raw.holdingTokenLiquidityPoolAddress),
            reward_token=reward_token,
            rewarder_account_address=to_address(raw.rewarderAccountAddress),
            total_reward_amount_wei=int(raw.totalRewardAmountWei),
            min_reward_wei=int(raw.minRewardWei) if raw.minRewardWei is not None else 1,
            snapshot_block_number=int(raw.snapshotBlockNumber),
            first_scanned_block_number=int(raw.firstScannedBlockNumber),
        )
