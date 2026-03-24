import json
from web3 import Web3

# Connect to Ethereum
RPC_URL = "https://eth-mainnet.g.alchemy.com/v2/MSKc1Jbann6Y3MeFZ51Ys"
w3 = Web3(Web3.HTTPProvider(RPC_URL))

# Target contract and wallet
TOKEN_ADDRESS = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
WALLET_ADDRESS = "0x28C6c06298d514Db089934071355E5743bf21d60"

# Load ABI
with open('usdc_abi.json', 'r') as f:
    token_abi = json.load(f)

# Create contract object
contract = w3.eth.contract(address=TOKEN_ADDRESS, abi=token_abi)

# Pull all view functions
name = contract.functions.name().call()
symbol = contract.functions.symbol().call()
decimals = contract.functions.decimals().call()
total_supply_raw = contract.functions.totalSupply().call()
balance_raw = contract.functions.balanceOf(WALLET_ADDRESS).call()
is_paused = contract.functions.paused().call()
is_blacklisted = contract.functions.isBlacklisted(WALLET_ADDRESS).call()

# Convert raw values
total_supply = total_supply_raw / 10 ** decimals
balance = balance_raw / 10 ** decimals

# Print full report
print("=" * 45)
print(f"  TOKEN REPORT: {name} ({symbol})")
print("=" * 45)
print(f"  Total Supply:    {total_supply:>20,.2f} {symbol}")
print(f"  Decimals:        {decimals}")
print(f"  Contract Paused: {is_paused}")
print()
print(f"  Wallet: {WALLET_ADDRESS}")
print(f"  Balance:         {balance:>20,.2f} {symbol}")
print(f"  Blacklisted:     {is_blacklisted}")
print("=" * 45)