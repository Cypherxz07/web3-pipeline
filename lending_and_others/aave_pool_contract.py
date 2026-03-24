import time
import sys
from web3 import Web3
sys.path.append(r'C:\Users\USER\Documents\Web3\python_pipeline')
from config import ALCHEMY_RPC_URL

w3 = Web3(Web3.HTTPProvider(ALCHEMY_RPC_URL))

# aToken = total supplied, vdToken = total borrowed
ATOKEN_ADDRESS = w3.to_checksum_address("0x98C23E9d8f34FEFb1B7BD6a91B7FF122F4e16F5c")
VDTOKEN_ADDRESS = w3.to_checksum_address("0x72E95b8931767C79bA4EeE721354d6E99a61D004")

ERC20_ABI = [
    {
        "name": "totalSupply",
        "type": "function",
        "inputs": [],
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view"
    }
]

atoken = w3.eth.contract(address=ATOKEN_ADDRESS, abi=ERC20_ABI)
vdtoken = w3.eth.contract(address=VDTOKEN_ADDRESS, abi=ERC20_ABI)

UTILIZATION_ALERT = 80

print("Aave USDC Health Monitor started...")
print(f"Alert threshold: {UTILIZATION_ALERT}% utilization")
print("=" * 55)

while True:
    total_supplied = atoken.functions.totalSupply().call() / 1e6
    total_borrowed = vdtoken.functions.totalSupply().call() / 1e6
    utilization = (total_borrowed / total_supplied) * 100

    print(f"Total Supplied:  ${total_supplied:>20,.2f} USDC")
    print(f"Total Borrowed:  ${total_borrowed:>20,.2f} USDC")
    print(f"Utilization:     {utilization:.2f}%")

    if utilization > UTILIZATION_ALERT:
        print(f"*** ALERT: Utilization {utilization:.2f}% above {UTILIZATION_ALERT}% ***")

    print("-" * 55)
    time.sleep(60)