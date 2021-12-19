import json
from dataclasses import dataclass
from typing import Optional

from eth_typing import ChecksumAddress

from .web3_utils import to_address


@dataclass
class JSONConfig:
    rpcUrl: str
    holdingTokenAddress: str
    holdingTokenLiquidityPoolAddress: str
    rewardTokenAddress: str
    rewarderAccountAddress: str
    snapshotBlockNumber: int
    firstScannedBlockNumber: int
    totalRewardAmountWei: Optional[str] = None
    totalRewardAmountDecimal: Optional[str] = None

    @classmethod
    def from_file(cls, file_path: str) -> 'JSONConfig':
        with open(file_path) as f:
            raw = json.load(f)
            return cls(**raw)

@dataclass
class Config:
    rpc_url: str
    holding_token_address: ChecksumAddress
    holding_token_liquidity_pool_address: ChecksumAddress  # Let's make it non-optional for now
    reward_token_address: ChecksumAddress
    rewarder_account_address: ChecksumAddress
    total_reward_amount_wei: int
    snapshot_block_number: int
    first_scanned_block_number: int

    @classmethod
    def from_file(cls, file_path: str) -> 'Config':
        raw = JSONConfig.from_file(file_path)

        return cls(
            rpc_url=raw.rpcUrl,
            holding_token_address=to_address(raw.holdingTokenAddress),
            holding_token_liquidity_pool_address=to_address(raw.holdingTokenLiquidityPoolAddress),
            reward_token_address=to_address(raw.rewardTokenAddress),
            rewarder_account_address=to_address(raw.rewarderAccountAddress),
            total_reward_amount_wei=int(raw.totalRewardAmountWei),
            snapshot_block_number=int(raw.snapshotBlockNumber),
            first_scanned_block_number=int(raw.firstScannedBlockNumber),
        )
