import time
import json
from datetime import datetime, timezone
from web3 import Web3

# Connect
RPC_URL = "https://eth-mainnet.g.alchemy.com/v2/MSKc1Jbann6Y3MeFZ51Ys"
w3 = Web3(Web3.HTTPProvider(RPC_URL))

# USDC contract
USDC_ADDRESS = w3.to_checksum_address("0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48")
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

with open('usdc_abi.json', 'r') as f:
    usdc_abi = json.load(f)

contract = w3.eth.contract(address=USDC_ADDRESS, abi=usdc_abi)

THRESHOLD_RAW = 1_000_000 * 10**6

def classify_transfer(sender, receiver):
    if receiver == ZERO_ADDRESS:
        return "🔥 BURN"
    elif sender == ZERO_ADDRESS:
        return "🪙 MINT"
    else:
        return "🐋 TRANSFER"

def get_timestamp(block_number):
    block = w3.eth.get_block(block_number)
    unix_time = block['timestamp']
    dt = datetime.fromtimestamp(unix_time, tz=timezone.utc)
    return dt.strftime('%Y-%m-%d %H:%M:%S UTC')

print("Transfer monitor started. Watching for large USDC moves...")
print(f"Threshold: 1,000,000 USDC")
print("=" * 65)

transfer_filter = contract.events.Transfer.create_filter(from_block='latest')

while True:
    new_events = transfer_filter.get_new_entries()

    for event in new_events:
        sender = event['args']['from']
        receiver = event['args']['to']
        value_raw = event['args']['value']
        amount_usdc = value_raw / 1e6

        if value_raw >= THRESHOLD_RAW:
            tx_hash = event['transactionHash'].hex()
            block_number = event['blockNumber']
            timestamp = get_timestamp(block_number)
            label = classify_transfer(sender, receiver)

            print(f"{label}")
            print(f"  Time:     {timestamp}")
            print(f"  Block:    {block_number}")
            print(f"  Amount:   {amount_usdc:,.2f} USDC")
            print(f"  From:     {sender}")
            print(f"  To:       {receiver}")
            print(f"  TX:       https://etherscan.io/tx/{tx_hash}")
            print("-" * 65)

    time.sleep(12)