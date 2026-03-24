import time
from web3 import Web3

# Connection setup
rpc_url = "https://eth-mainnet.g.alchemy.com/v2/MSKc1Jbann6Y3MeFZ51Ys"
w3 = Web3(Web3.HTTPProvider(rpc_url))

print("Initializing On-chain Monitor")

# Set the initial state
last_block = w3.eth.block_number
print(f"Monitoring started at Block: {last_block}")

while True:
    try:
        if w3.is_connected():
            current_block = w3.eth.block_number

            # The Conditional Gate: Only act if the data has changed
            if current_block > last_block:
                print(f"🔔 NEW BLOCK DETECTED: {current_block}")

                # Update the state so that we don't alert on the same block twice
                last_block = current_block
            else:
                print("⚠️ Connection lost. Retrying...")

    except Exception as e:
        print(f"❌ Error in the circuit: {e}")

    # Polling interval: Check every 5 seconds to be safe
    time.sleep(5)