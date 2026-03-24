import json
from web3 import Web3

# Connect to Ethereum
RPC_URL = "https://eth-mainnet.g.alchemy.com/v2/MSKc1Jbann6Y3MeFZ51Ys"
w3 = Web3(Web3.HTTPProvider(RPC_URL))

# USDC contract address — always use the proxy address
USDC_ADDRESS = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"

# VARIABLE
wallet = "0x28C6c06298d514Db089934071355E5743bf21d60"

# Load the ABI from your saved file
with open('usdc_abi.json', 'r') as f:
    usdc_abi = json.load(f)

# Create the contract object
usdc_contract = w3.eth.contract(
    address=USDC_ADDRESS,
    abi=usdc_abi
)

# Call view functions
name = usdc_contract.functions.name().call()
symbol = usdc_contract.functions.symbol().call()
decimals = usdc_contract.functions.decimals().call()
total_supply_raw = usdc_contract.functions.totalSupply().call()
balance_raw = usdc_contract.functions.balanceOf(wallet).call()
blacklisted = usdc_contract.functions.isBlacklisted(wallet).call()

# USDC uses 6 decimal places — divide by 10^6
total_supply = total_supply_raw / 10 ** decimals
balance = balance_raw / 10 ** decimals

print(f"Token Name:    {name}")
print(f"Symbol:        {symbol}")
print(f"Decimals:      {decimals}")
print(f"Total Supply:  {total_supply:,.2f} USDC")

print(f"User's address: {wallet}")
print(f"USDC Balance: {balance:,.2f} USDC")
print(f"Is Blacklisted: {blacklisted}")