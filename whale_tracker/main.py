import time
import sys
sys.path.append(r'C:\Users\USER\Desktop\web3-pipeline')
from whale_tracker.fetch_transfers import get_transfer_logs, decode_transfer, save_to_db
from web3 import Web3
from config import INFURA_RPC_URL

w3 = Web3(Web3.HTTPProvider(INFURA_RPC_URL))
last_block = None

def run():
    global last_block
    
    latest = w3.eth.block_number
    if last_block is None:
        last_block = latest - 100
    
    print(f"\n[{time.strftime('%H:%M:%S')}] Checking blocks {last_block} to {latest}")
    
    logs = get_transfer_logs(last_block, latest)
    whales = 0
    
    for log in logs:
        transfer = decode_transfer(log)
        if transfer['amount_usd'] > 100000:
            print(f"🐋 {transfer['token_symbol']}: ${transfer['amount_usd']:,.2f}")
            save_to_db(transfer)
            whales += 1
    
    last_block = latest
    print(f"Found {whales} whales")

if __name__ == "__main__":
    while True:
        try:
            run()
        except Exception as e:
            print(f"Error: {e}")
        
        time.sleep(12)  # Poll every 12 seconds