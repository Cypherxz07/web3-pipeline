import sys
import os
sys.path.append(r'C:\Users\USER\Desktop\web3-pipeline')
import time
import json
import requests
from datetime import datetime, timezone
from web3 import Web3
from config import ALCHEMY_RPC_URL, ETHERSCAN_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

# Connect
w3 = Web3(Web3.HTTPProvider(ALCHEMY_RPC_URL))

# USDC contract
USDC_ADDRESS = w3.to_checksum_address("0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48")
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

with open(r'C:\Users\USER\Desktop\web3-pipeline\usdc_abi.json', 'r') as f:
    usdc_abi = json.load(f)

contract = w3.eth.contract(address=USDC_ADDRESS, abi=usdc_abi)

THRESHOLD_RAW = 1_000_000 * 10**6

KNOWN_ADDRESSES = {
    "0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb": "Morpho",
    "0x37305B1cD40574E4C5Ce33f8e8306Be057fD7341": "Sky PSM",
    "0x38AAEF3782910bdd9eA3566C839788Af6FF9B200": "Whale (Unlabelled)",
    "0x28C6c06298d514Db089934071355E5743bf21d60": "Binance 14",
    "0x98C23E9d8f34FEFb1B7BD6a91B7FF122F4e16F5c": "Aave USDC V3",
    "0x0000000000000000000000000000000000000000": "Burn Address",
}

ADDRESS_CACHE = {}

def load_filters():
    filters_file = os.path.join(os.path.dirname(__file__), '../whale_tracker/user_filters.json')
    if os.path.exists(filters_file):
        with open(filters_file) as f:
            return json.load(f)
    return {}

def get_user_filter():
    return load_filters().get(str(TELEGRAM_CHAT_ID))

# Daily tracking
daily_alert_count = 0
daily_volume = 0.0
last_summary_date = datetime.now(timezone.utc).date()

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

def get_label(address):
    if address in KNOWN_ADDRESSES:
        return KNOWN_ADDRESSES[address]
    if address in ADDRESS_CACHE:
        return ADDRESS_CACHE[address]
    label = get_etherscan_label(address)
    ADDRESS_CACHE[address] = label
    return label

def classify_transfer(sender, receiver):
    if receiver == ZERO_ADDRESS:
        return "🔥 BURN"
    elif sender == ZERO_ADDRESS:
        return "🪙 MINT"
    else:
        return "💸 TRANSFER"

def classify_size(amount_usdc):
    if amount_usdc >= 100_000_000:
        return "🚨 MEGA WHALE"
    elif amount_usdc >= 10_000_000:
        return "🐋 LARGE WHALE"
    elif amount_usdc >= 1_000_000:
        return "🐟 WHALE"
    else:
        return "🔹 TRANSFER"

def get_timestamp(block_number):
    block = w3.eth.get_block(block_number)
    unix_time = block['timestamp']
    dt = datetime.fromtimestamp(unix_time, tz=timezone.utc)
    return dt.strftime('%Y-%m-%d %H:%M:%S UTC')

def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        requests.post(url, data=payload, timeout=5)
    except Exception as e:
        print(f"Telegram error: {e}")

def send_daily_summary(count, volume):
    message = (
        f"📊 <b>Daily USDC Whale Summary</b>\n"
        f"Alerts fired: {count}\n"
        f"Total volume tracked: ${volume:,.2f} USDC\n"
        f"Threshold: 1,000,000 USDC"
    )
    send_telegram(message)

print("Whale Alert Bot started...")
print(f"Threshold: 1,000,000 USDC")
print("Telegram notifications active.")
print("=" * 55)

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
            transfer_type = classify_transfer(sender, receiver)
            size_label = classify_size(amount_usdc)
            label = f"{size_label} — {transfer_type}"
            sender_label = get_label(sender)
            receiver_label = get_label(receiver)
            alerts.append((label, timestamp, block_number,
                          amount_usdc, sender, sender_label,
                          receiver, receiver_label, tx_hash))

    for alert in alerts:
        label, timestamp, block_number, amount_usdc, \
        sender, sender_label, receiver, receiver_label, tx_hash = alert

        user_filter = get_user_filter()
        if not user_filter:
            print("No telegram alert filter set for this chat. Skipping alert until /set_filter is configured.")
            continue

        if user_filter.get('chain', 'ethereum').lower() != 'ethereum':
            print(f"Telegram filter chain is set to {user_filter['chain']}. This bot only monitors Ethereum, skipping alert.")
            continue

        if amount_usdc < user_filter.get('min_amount', THRESHOLD_RAW / 1e6):
            continue

        # Terminal output
        print(f"{label}")
        print(f"  Time:     {timestamp}")
        print(f"  Amount:   {amount_usdc:,.2f} USDC")
        print(f"  From:     {sender} ({sender_label})")
        print(f"  To:       {receiver} ({receiver_label})")
        print(f"  TX:       https://etherscan.io/tx/{tx_hash}")
        print("-" * 55)

        # Telegram message
        message = (
            f"{label}\n"
            f"<b>Time:</b> {timestamp}\n"
            f"<b>Amount:</b> {amount_usdc:,.2f} USDC\n"
            f"<b>From:</b> {sender_label}\n"
            f"<b>To:</b> {receiver_label}\n"
            f"<b>TX:</b> https://etherscan.io/tx/{tx_hash}"
        )
        send_telegram(message)

    # Check if day has changed — send summary at midnight UTC
    current_date = datetime.now(timezone.utc).date()
    if current_date != last_summary_date:
        send_daily_summary(daily_alert_count, daily_volume)
        daily_alert_count = 0
        daily_volume = 0.0
        last_summary_date = current_date

    time.sleep(12)