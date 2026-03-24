import time
from web3 import Web3

# Connection setup
rpc_url = "https://eth-mainnet.g.alchemy.com/v2/MSKc1Jbann6Y3MeFZ51Ys"
w3 = Web3(Web3.HTTPProvider(rpc_url))

# Set your alert threshold in Gwei
THRESHOLD_GWEI = 0.1

print("Monitor started. Watching base fee...")

while True:
    # Pull the latest block
    block = w3.eth.get_block('latest')

    # Extract and calculate gas metrics
    block_number = block['number']
    gas_used = block['gasUsed']
    gas_limit = block['gasLimit']
    base_fee_gwei = block['baseFeePerGas'] / 1e9
    utilization = (gas_used / gas_limit) * 100

    # Print current status
    print(f"Block {block_number} | Utilization: {utilization:.2f}% | Base Fee: {base_fee_gwei:.6f} Gwei")

    # Fire alert if threshold is crossed
    if base_fee_gwei > THRESHOLD_GWEI:
        print(f"*** ALERT: Base fee {base_fee_gwei:.6f} Gwei has crossed your threshold of {THRESHOLD_GWEI} Gwei ***")

    #Wait one block time before checking again
    time.sleep(12)