Sovryn Airdrop script
=====================

A simple script to plan and execute airdrops. Created initially for the MYNT tokens airdrop,
but can be adapted for other uses

Installation
------------

Python3.8 is required (though this could be dockerized with ease).

```shell
python3.8 -m venv venv
./venv/bin/pip install -e .
```

Planning an airdrop
-------------------

Create a JSON config file that looks like this:

```json
{
  "rpcUrl": "http://my-rsk-rpc-url.invalid",
  "holdingTokenAddress": "0x2e6B1d146064613E8f521Eb3c6e65070af964EbB",
  "holdingTokenLiquidityPoolAddress": "0x3a18e61d9c9f1546dea013478dd653c793098f17",
  "liquidityMiningAddress": "0xf730af26e87D9F55E46A6C447ED2235C385E55e0",
  "rewardTokenAddress": "0x2e6B1d146064613E8f521Eb3c6e65070af964EbB",
  "rewarderAccountAddress": "0xf00f00f00f00f00f00f00f00f00f00f00f001337",
  "totalRewardAmountWei": "1111112053928883000000000",
  "minRewardWei": "10000000000000000000",
  "snapshotBlockNumber": 3976082,
  "firstScannedBlockNumber": 3831000
}
```

Then run (with the assumption that the config file is in `my-config.json`):

```shell
./venv/bin/python -m sovryn_airdrop.cli_main plan -c my-config.json -p plan.csv
```

This will fetch the holding token (`0x2e6B1d146064613E8f521Eb3c6e65070af964EbB`) balances
of all users on block `3976082`. It will get the token holders by scanning transfer events
between that block and the configured starting block `3831000`.

It will also determine the balances of LP tokens from the configured liquidity pool,
also accounting for balances on the configured liquidity mining contract, and calculate
the amount of the holding token they represent.

It will then allocate the configured reward amount (`1111112.053928883000000000`) to be
distributed proportionally between the token holders, and save a csv file to `plan.csv`
with the token transfers and transaction nonces.

Executing an airdrop
--------------------

To execute the airdrop, run:

```shell
./venv/bin/python -m sovryn_airdrop.cli_main send -c my-config.json -p plan.csv
```

The script will double-confirm everything and then ask for a private key of the rewarder account.
After that, it will send and verify the transactions in batches of 4, constantly updating the plan
file with the transaction hashes.