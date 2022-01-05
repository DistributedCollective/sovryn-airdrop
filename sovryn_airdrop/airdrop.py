import csv
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence

from eth_account.signers.local import LocalAccount
from eth_typing import ChecksumAddress
from eth_utils import to_hex

from .config import Config
from .tokens import Token


class Airdrop:
    transactions: List['AirdropTransaction']
    config: Config
    reward_token: Token
    rewarder_account: Optional[LocalAccount] = None

    def __init__(self, config: Config):
        self.transactions = []
        self.config = config
        self.reward_token = config.reward_token

    def __repr__(self):
        return f"<Airdrop with {len(self.transactions)} transactions>"

    @classmethod
    def from_file(
        cls,
        file_path: str,
        config: Config,
    ) -> 'Airdrop':
        airdrop = cls(config=config)
        with open(file_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                airdrop.add_transaction(
                    to_address=row['to_address'],
                    reward_amount_wei=int(row['reward_amount_wei']),
                    transaction_nonce=int(row['transaction_nonce']),
                    transaction_hash=row['transaction_hash'] or None,
                )
        return airdrop

    def to_file(self, file_path: str):
        with open(file_path, 'w') as f:
            writer = csv.DictWriter(
                f,
                fieldnames=['to_address', 'reward_amount_wei', 'transaction_nonce', 'transaction_hash']
            )
            writer.writeheader()
            for transaction in self.transactions:
                writer.writerow({
                    'to_address': transaction.to_address,
                    'reward_amount_wei': str(transaction.reward_amount_wei),
                    'transaction_nonce': str(transaction.transaction_nonce),
                    'transaction_hash': str(transaction.transaction_hash or ''),
                })

    def add_transaction(
        self,
        *,
        to_address: ChecksumAddress,
        reward_amount_wei: int,
        transaction_nonce: int,
        transaction_hash: Optional[str] = None,
    ):
        transaction = AirdropTransaction(
            airdrop=self,
            to_address=to_address,
            reward_amount_wei=reward_amount_wei,
            transaction_nonce=transaction_nonce,
            transaction_hash=transaction_hash
        )
        self.transactions.append(transaction)

    @property
    def total_reward_amount_wei(self):
        return sum(t.reward_amount_wei for t in self.transactions)

    def as_table(self):
        rows = [
            airdrop_row_repr(
                'To address',
                f'Reward in {self.reward_token.symbol}',
                'TX Nonce',
                'TX Hash',
            ),
        ]
        rows.extend(t.as_row() for t in self.transactions)
        rows.append(
            airdrop_row_repr(
                'Total',
                self.reward_token.str_amount(self.total_reward_amount_wei),
                '',
                '',
            )
        )
        return '\n'.join(rows)

    @property
    def unsent_transactions(self) -> Sequence['AirdropTransaction']:
        return [t for t in self.transactions if t.transaction_hash is None]

    @property
    def sent_transactions(self) -> Sequence['AirdropTransaction']:
        return [t for t in self.transactions if t.transaction_hash is not None]


@dataclass
class AirdropTransaction:
    airdrop: 'Airdrop'
    to_address: ChecksumAddress
    reward_amount_wei: int
    transaction_nonce: int
    transaction_hash: Optional[str]

    def as_row(self):
        return airdrop_row_repr(
            self.to_address,
            self.airdrop.reward_token.str_amount(self.reward_amount_wei),
            self.transaction_nonce,
            self.transaction_hash
        )

    def send(self):
        if self.transaction_hash:
            raise ValueError("Already sent")
        config = self.airdrop.config
        reward_token_contract = config.reward_token.contract
        # TODO: ????
        tx_hash = reward_token_contract.functions.transfer(
            self.to_address,
            self.reward_amount_wei,
        #).transact({'from': config.rewarder_account_address})
        ).transact()
        self.transaction_hash = to_hex(tx_hash)

    def verify(self):
        receipt = self.airdrop.config.web3.eth.wait_for_transaction_receipt(self.transaction_hash, timeout=600)
        if not receipt.status:
            raise ValueError(f'Transaction failed: {self.as_row()}')
        return receipt


def airdrop_row_repr(to_address, reward_amount_wei, transaction_nonce, transaction_hash) -> str:
    cols = [
        to_address.ljust(42),
        str(reward_amount_wei).rjust(30),
        str(transaction_nonce).rjust(12),
        str(transaction_hash) if transaction_hash else '',
    ]
    return ' '.join(cols)