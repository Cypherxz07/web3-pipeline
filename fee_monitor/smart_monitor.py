import time
from web3 import Web3

# Connect to Ethereum
RPC_URL = "https://eth-mainnet.g.alchemy.com/v2/MSKc1Jbann6Y3MeFZ51Ys"
w3 = Web3(Web3.HTTPProvider(RPC_URL))

# Settings
THRESHOLD_GWEI = 0.1
CHANGE_FILTER_PCT = 10

# State variables
last_printed_fee = None
above_threshold = False

print("Smart monitor started...")

while True:
    block = w3.eth.get_block('latest')
    
    block_number = block['number']
    gas_used = block['gasUsed']
    gas_limit = block['gasLimit']
    base_fee_gwei = block['baseFeePerGas'] / 1e9
    utilization = (gas_used / gas_limit) * 100

    # First run — no previous value to compare against yet
    if last_printed_fee is None:
        print(f"Block {block_number} | Utilization: {utilization:.2f}% | Base Fee: {base_fee_gwei:.6f} Gwei")
        last_printed_fee = base_fee_gwei

    else:
        # Calculate how much the fee has moved since last print
        change_pct = abs(base_fee_gwei - last_printed_fee) / last_printed_fee * 100

        # Only print if the move is significant
        if change_pct >= CHANGE_FILTER_PCT:
            print(f"Block {block_number} | Utilization: {utilization:.2f}% | Base Fee: {base_fee_gwei:.6f} Gwei | Change: {change_pct:.2f}%")
            last_printed_fee = base_fee_gwei

    # Threshold crossing alerts
    if base_fee_gwei > THRESHOLD_GWEI and not above_threshold:
        print(f"*** ALERT: Base fee crossed ABOVE threshold at block {block_number} — {base_fee_gwei:.6f} Gwei ***")
        above_threshold = True

    if base_fee_gwei <= THRESHOLD_GWEI and above_threshold:
        print(f"*** ALERT: Base fee dropped BELOW threshold at block {block_number} — {base_fee_gwei:.6f} Gwei ***")
        above_threshold = False

    time.sleep(12)