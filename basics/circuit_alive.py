from web3 import Web3

# 1. Establish the connection
# Replace 'YOUR_ALCHEMY_URL' with the link you copied
rpc_url = "https://eth-mainnet.g.alchemy.com/v2/MSKc1Jbann6Y3MeFZ51Ys"
w3 = Web3(Web3.HTTPProvider(rpc_url))

# 2. Define the Target (The Wallet Address)
# This is a Vitalin Buterin's address for testing
target_address = w3.to_checksum_address("0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045")

if w3.is_connected():
    # 3. Fetch Raw Data (Wei)
    balance_wei = w3.eth.get_balance(target_address)
    number_of_transactions = w3.eth.get_transaction_count(target_address)
    block_number = w3.eth.get_block_number()

    # 4. Convert to Human-Readable (Ether)
    balance_eth = w3.from_wei(balance_wei, 'ether')

    print(f"✅ Connection Stable")
    print(f"Block number: {block_number}")
    print(f"Wallet: {target_address}")
    print(f"Number of transactions: {number_of_transactions}")
    print(f"Balance: {balance_eth} ETH")
else:
    print("❌ Connection Failed")