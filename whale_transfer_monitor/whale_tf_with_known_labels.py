import sys
sys.path.append(r'C:\Users\USER\Documents\Web3\python_pipeline')
import time
import json
import requests
from datetime import datetime, timezone
from web3 import Web3
from config import ETHERSCAN_API_KEY, ALCHEMY_RPC_URL

# Connect
w3 = Web3(Web3.HTTPProvider(ALCHEMY_RPC_URL))

# USDC contract
USDC_ADDRESS = w3.to_checksum_address("0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48")
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

with open('usdc_abi.json', 'r') as f:
    usdc_abi = json.load(f)

contract = w3.eth.contract(address=USDC_ADDRESS, abi=usdc_abi)

THRESHOLD_RAW = 1_000_000 * 10**6

# Known addresses — your personal label database
KNOWN_ADDRESSES = {
    "0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb": "Morpho",
    "0x37305B1cD40574E4C5Ce33f8e8306Be057fD7341": "Sky PSM",
    "0x38AAEF3782910bdd9eA3566C839788Af6FF9B200": "Whale (Unlabelled)",
    "0x28C6c06298d514Db089934071355E5743bf21d60": "Binance 14",
    "0x98C23E9d8f34FEFb1B7BD6a91B7FF122F4e16F5c": "Aave USDC V3",
    "0x0000000000000000000000000000000000000000": "🔥 Burn Address",
}

# Cache — fills automatically as new addresses are discovered
ADDRESS_CACHE = {}

def get_etherscan_label(address):
    try:
        url = "https://api.etherscan.io/v2/api"
        params = {
            "chainid": "1",
            "module": "contract",
            "action": "getsourcecode",
            "address": address,
            "apikey": ETHERSCAN_API_KEY
        }
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        if data['status'] == '1':
            name = data['result'][0].get('ContractName', '')
            return name if name else "EOA Wallet"
        return "Unknown"
    except Exception:
        return "Unknown"

# Test Etherscan API
test_address = "0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb"
result = get_etherscan_label(test_address)
print(f"API Test — Morpho address returned: '{result}'")

def get_label(address):
    # Layer 1 — check known addresses
    if address in KNOWN_ADDRESSES:
        return KNOWN_ADDRESSES[address]
    # Layer 2 — check cache
    if address in ADDRESS_CACHE:
        return ADDRESS_CACHE[address]
    # Layer 3 — call Etherscan API
    label = get_etherscan_label(address)
    ADDRESS_CACHE[address] = label
    return label

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
print("Threshold: 1,000,000 USDC")
print("=" * 65)

transfer_filter = contract.events.Transfer.create_filter(from_block='latest')

while True:
    new_events = transfer_filter.get_new_entries()

    alerts = []
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
            sender_label = get_label(sender)
            receiver_label = get_label(receiver)
            alerts.append((label, timestamp, block_number,
                          amount_usdc, sender, sender_label,
                          receiver, receiver_label, tx_hash))

    for alert in alerts:
        label, timestamp, block_number, amount_usdc, \
        sender, sender_label, receiver, receiver_label, tx_hash = alert

        print(f"{label}")
        print(f"  Time:     {timestamp}")
        print(f"  Block:    {block_number}")
        print(f"  Amount:   {amount_usdc:,.2f} USDC")
        print(f"  From:     {sender} ({sender_label})")
        print(f"  To:       {receiver} ({receiver_label})")
        print(f"  TX:       https://etherscan.io/tx/{tx_hash}")
        print("-" * 65)

    time.sleep(12)