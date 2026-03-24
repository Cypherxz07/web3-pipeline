from web3 import Web3

# Connection setup
rpc_url = "https://eth-mainnet.g.alchemy.com/v2/MSKc1Jbann6Y3MeFZ51Ys"
w3 = Web3(Web3.HTTPProvider(rpc_url))

# Pull the latest block
block = w3.eth.get_block('latest')

# Extract and calculate gas metrics
block_number = block['number']
gas_used = block['gasUsed']
gas_limit = block['gasLimit']
base_fee_wei = block['baseFeePerGas']
base_fee_gwei = base_fee_wei / 1e9
utilization = (gas_used / gas_limit) * 100

# Print a clean report
print(f"Block Number: {block_number}")
print(f"Gas Used: {gas_used:,}")
print(f"Gas Limit: {gas_limit:,}")
print(f"Utilization: {utilization:.2f}%")
print(f"Base Fee: {base_fee_gwei:.6f} Gwei")