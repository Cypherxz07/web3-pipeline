import sys
import json
import time
import requests
from web3 import Web3

sys.path.append(r'C:\Users\USER\Desktop\web3-pipeline')
from config import ALCHEMY_RPC_URL, ETHERSCAN_API_KEY, DUNE_API_KEY

# Validate input
if len(sys.argv) < 2:
    print("Usage: python token_analytics.py <token_address>")
    sys.exit(1)

# Connect
w3 = Web3(Web3.HTTPProvider(ALCHEMY_RPC_URL))

# Token address from command line
try:
    TOKEN_ADDRESS = w3.to_checksum_address(sys.argv[1])
except Exception:
    print("Invalid address. Please provide a valid Ethereum address.")
    sys.exit(1)

# Minimal ERC20 ABI
ERC20_ABI = [
    {"name": "name", "type": "function", "inputs": [], "outputs": [{"name": "", "type": "string"}], "stateMutability": "view"},
    {"name": "symbol", "type": "function", "inputs": [], "outputs": [{"name": "", "type": "string"}], "stateMutability": "view"},
    {"name": "decimals", "type": "function", "inputs": [], "outputs": [{"name": "", "type": "uint8"}], "stateMutability": "view"},
    {"name": "totalSupply", "type": "function", "inputs": [], "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view"},
    {"name": "balanceOf", "type": "function", "inputs": [{"name": "account", "type": "address"}], "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view"},
]

token = w3.eth.contract(address=TOKEN_ADDRESS, abi=ERC20_ABI)

# Pull basic token data
print("\nFetching token data...")
name = token.functions.name().call()
symbol = token.functions.symbol().call()
decimals = token.functions.decimals().call()
total_supply_raw = token.functions.totalSupply().call()
total_supply = total_supply_raw / 10 ** decimals

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

contract_name = get_etherscan_label(TOKEN_ADDRESS)

# Print token report
print("=" * 60)
print(f"  TOKEN ANALYTICS — {name} ({symbol})")
print("=" * 60)
print(f"  Contract:      {TOKEN_ADDRESS}")
print(f"  Verified As:   {contract_name}")
print(f"  Decimals:      {decimals}")
print(f"  Total Supply:  {total_supply:>20,.2f} {symbol}")
print("=" * 60)

# Known large holders — checked directly on-chain
KNOWN_HOLDERS = {
    "0x37305B1cD40574E4C5Ce33f8e8306Be057fD7341": "Sky PSM",
    "0x38AAEF3782910bdd9eA3566C839788Af6FF9B200": "Whale (Unlabelled)",
    "0xe1940f578743367F38D3f25c2D2d32D6636929B6": "Binance 91",
    "0xaD354CfBAa4A8572DD6Df021514a3931A8329Ef5": "Binance 90",
    "0x98C23E9d8f34FEFb1B7BD6a91B7FF122F4e16F5c": "Aave USDC V3",
    "0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb": "Morpho",
    "0x28C6c06298d514Db089934071355E5743bf21d60": "Binance 14",
}

print("\n  KNOWN HOLDER BALANCES")
print("-" * 60)

holder_balances = []
for address, label in KNOWN_HOLDERS.items():
    try:
        checksummed = w3.to_checksum_address(address)
        balance_raw = token.functions.balanceOf(checksummed).call()
        balance = balance_raw / 10 ** decimals
        holder_balances.append((label, balance, address))
    except Exception:
        pass

# Sort by balance largest first
holder_balances = sorted(holder_balances, key=lambda x: x[1], reverse=True)

for label, balance, address in holder_balances:
    pct = (balance / total_supply * 100) if total_supply > 0 else 0
    print(f"  {label:<25} {balance:>15,.2f} {symbol} ({pct:.2f}%)")

print("=" * 60)

# DEX trading data via Dune API
print("\nFetching DEX trading data...")

def run_dune_query(query_id):
    try:
        # Execute query
        url = f"https://api.dune.com/api/v1/query/{query_id}/execute"
        headers = {"X-Dune-API-Key": DUNE_API_KEY}
        response = requests.post(url, headers=headers, timeout=10)
        execution_id = response.json()['execution_id']

        # Poll for results
        for _ in range(30):
            time.sleep(3)
            result_url = f"https://api.dune.com/api/v1/execution/{execution_id}/results"
            result = requests.get(result_url, headers=headers, timeout=10)
            data = result.json()
            if data.get('state') == 'QUERY_STATE_COMPLETED':
                return data['result']['rows']
            elif data.get('state') == 'QUERY_STATE_FAILED':
                return []
        return []
    except Exception as e:
        print(f"Dune API error: {e}")
        return []

def get_dex_volume(query_id):
    try:
        headers = {"X-Dune-API-Key": DUNE_API_KEY}
        
        # Execute saved query
        url = f"https://api.dune.com/api/v1/query/{query_id}/execute"
        response = requests.post(url, headers=headers, timeout=10)
        data = response.json()
        
        execution_id = data.get('execution_id')
        if not execution_id:
            print(f"  Execution failed: {data}")
            return None

        # Poll for results
        for _ in range(20):
            time.sleep(3)
            result_url = f"https://api.dune.com/api/v1/execution/{execution_id}/results"
            result = requests.get(result_url, headers=headers, timeout=10)
            result_data = result.json()
            state = result_data.get('state')
            if state == 'QUERY_STATE_COMPLETED':
                rows = result_data['result']['rows']
                return rows
            elif state == 'QUERY_STATE_FAILED':
                print("  Query failed on Dune side.")
                return None
        return None
    except Exception as e:
        print(f"DEX data error: {e}")
        return None

dex_data = get_dex_volume(6796089)

if dex_data:
    print("=" * 60)
    print(f"  TOP USDC MOVERS — Last 24 Hours")
    print("=" * 60)
    for i, row in enumerate(dex_data[:5], 1):
        address = row.get('address', '')
        direction = row.get('direction', '')
        volume = float(row.get('total_volume_usdc', 0))
        count = int(row.get('transfer_count', 0))
        print(f"  #{i} {direction:<4} ${volume:>20,.2f} USDC ({count} transfers)")
        print(f"       {address}")
    print("=" * 60)
else:
    print("  Transfer data unavailable.")
    print("=" * 60)

print(f"\n  Analysis complete for {symbol}\n")