import csv
from dataclasses import dataclass
from typing import Iterable, List, Optional

from eth_typing import ChecksumAddress

from .tokens import Token


class Airdrop:
    transactions: List['AirdropTransaction']
    reward_token: Token
    rewarder_address: ChecksumAddress

    def __init__(
        self,
        *,
        reward_token: Token,
        rewarder_address: ChecksumAddress,
    ):
        self.transactions = []
        self.reward_token = reward_token
        self.rewarder_address = rewarder_address

    def __repr__(self):
        return f"<Airdrop with {len(self.transactions)} transactions>"

    @classmethod
    def from_file(
        cls,
        file_path: str,
        rewarder_token: Token,
        rewarder_address: ChecksumAddress,
    ) -> 'Airdrop':
        airdrop = cls(
            reward_token=rewarder_token,
            rewarder_address=rewarder_address,
        )
        with open(file_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                airdrop.add_transaction(
                    to_address=row['to_address'],
                    amount_wei=int(row['amount_wei']),
                    transaction_nonce=int(row['transaction_nonce']),
                    transaction_hash=row['transaction_hash'] or None,
                )
        return airdrop

    def to_file(self, file_path: str):
        with open(file_path, 'w') as f:
            writer = csv.DictWriter(
                f,
                fieldnames=['to_address', 'amount_wei', 'transaction_nonce', 'transaction_hash']
            )
            writer.writeheader()
            for transaction in self.transactions:
                writer.writerow({
                    'to_address': transaction.to_address,
                    'amount_wei': str(transaction.amount_wei),
                    'transaction_nonce': str(transaction.transaction_nonce),
                    'transaction_hash': str(transaction.transaction_hash or ''),
                })

    def add_transaction(
        self,
        *,
        to_address: ChecksumAddress,
        amount_wei: int,
        transaction_nonce: int,
        transaction_hash: Optional[str] = None,
    ):
        transaction = AirdropTransaction(
            airdrop=self,
            to_address=to_address,
            amount_wei=amount_wei,
            transaction_nonce=transaction_nonce,
            transaction_hash=transaction_hash
        )
        self.transactions.append(transaction)

    @property
    def total_amount_wei(self):
        return sum(t.amount_wei for t in self.transactions)

    def as_table(self):
        rows = [
            airdrop_row_repr(
                'To address',
                f'Reward in {self.reward_token.symbol}',
                'TX Nonce',
                'TX Hash'
            ),
        ]
        rows.extend(t.as_row() for t in self.transactions)
        return '\n'.join(rows)

    @property
    def unsent_transactions(self) -> Iterable['AirdropTransaction']:
        return [t for t in self.transactions if t.transaction_hash is None]

    @property
    def sent_transactions(self) -> Iterable['AirdropTransaction']:
        return [t for t in self.transactions if t.transaction_hash is not None]


@dataclass
class AirdropTransaction:
    airdrop: 'Airdrop'
    to_address: ChecksumAddress
    amount_wei: int
    transaction_nonce: int
    transaction_hash: Optional[str]

    def as_row(self):
        return airdrop_row_repr(
            self.to_address,
            self.airdrop.reward_token.str_amount(self.amount_wei),
            self.transaction_nonce,
            self.transaction_hash
        )


def airdrop_row_repr(to_address, amount_wei, transaction_nonce, transaction_hash) -> str:
    cols = [
        to_address.ljust(42),
        str(amount_wei).rjust(30),
        str(transaction_nonce).rjust(12),
        str(transaction_hash) if transaction_hash else '',
    ]
    return ' '.join(cols)