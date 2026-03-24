import json
from web3 import Web3

# Connect to Ethereum
RPC_URL = "https://eth-mainnet.g.alchemy.com/v2/MSKc1Jbann6Y3MeFZ51Ys"
w3 = Web3(Web3.HTTPProvider(RPC_URL))

# USDC contract
TOKEN_ADDRESS = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"

with open('usdc_abi.json', 'r') as f:
    token_abi = json.load(f)

contract = w3.eth.contract(address=TOKEN_ADDRESS, abi=token_abi)
decimals = contract.functions.decimals().call()

# Whale wallets to track
wallets = {
    "Sky PSM":  w3.to_checksum_address("0x37305B1cD40574E4C5Ce33f8e8306Be057fD7341"),
    "Unlabelled":  w3.to_checksum_address("0x38AAEF3782910bdd9eA3566C839788Af6FF9B200"),
    "Binance 91":    w3.to_checksum_address("0xe1940f578743367F38D3f25c2D2d32D6636929B6"),
    "Binance 90":  w3.to_checksum_address("0xaD354CfBAa4A8572DD6Df021514a3931A8329Ef5"),
    "Aave USDC V3":  w3.to_checksum_address("0x98C23E9d8f34FEFb1B7BD6a91B7FF122F4e16F5c"),
}

# Collect results
results = []

for label, address in wallets.items():
    balance_raw = contract.functions.balanceOf(address).call()
    balance = balance_raw / 10 ** decimals
    results.append((label, balance, address))

# Sort by balance — largest first
results = sorted(results, key=lambda x: x[1], reverse=True)

# Print leaderboard
print("=" * 65)
print("  USDC WHALE TRACKER — LIVE BALANCES")
print("=" * 65)

for rank, (label, balance, address) in enumerate(results, start=1):
    print(f"  #{rank} {label:<15} {balance:>20,.2f} USDC")
    print(f"     {address}")
    print()

print("=" * 65)