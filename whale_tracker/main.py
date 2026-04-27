import importlib.util
import os
import sys
import time
import asyncio
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
config_path = os.path.join(ROOT_DIR, 'config.py')
spec = importlib.util.spec_from_file_location('config', config_path)
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)
from whale_tracker.fetch_transfers import get_transfer_logs, decode_transfer, save_to_db
from telegram_bot.on_chain_alerts import alert
from web3 import Web3
INFURA_PROJECT_ID = config.INFURA_PROJECT_ID
WHALE_TRACKER_THRESHOLD_USD = config.WHALE_TRACKER_THRESHOLD_USD

CHAINS = {
    'ethereum': f'https://mainnet.infura.io/v3/{INFURA_PROJECT_ID}',
    'polygon': f'https://polygon-mainnet.infura.io/v3/{INFURA_PROJECT_ID}',
    'arbitrum': f'https://arbitrum-mainnet.infura.io/v3/{INFURA_PROJECT_ID}'
}

last_blocks = {'ethereum': None, 'polygon': None, 'arbitrum': None}

async def run():
    for chain_name, rpc_url in CHAINS.items():
        try:
            w3 = Web3(Web3.HTTPProvider(rpc_url))
            latest = w3.eth.block_number
            
            if last_blocks[chain_name] is None:
                last_blocks[chain_name] = latest - 100
            
            print(f"\n[{time.strftime('%H:%M:%S')}] {chain_name.upper()} blocks {last_blocks[chain_name]} to {latest}")

            try:
                logs = get_transfer_logs(w3, last_blocks[chain_name], min(latest, last_blocks[chain_name] + 10), chain=chain_name)
            except Exception as e:
                print(f"Error fetching logs on {chain_name}: {e}")
                continue
            
            whales = 0
            for log in logs:
                transfer = decode_transfer(log)
                transfer['chain'] = chain_name
                
                if transfer['amount_usd'] > WHALE_TRACKER_THRESHOLD_USD:
                    print(f"🐋 [{chain_name}] {transfer['token_symbol']}: ${transfer['amount_usd']:,.2f}")
                    save_to_db(transfer)
                    try:
                        await alert(transfer, WHALE_TRACKER_THRESHOLD_USD)
                    except Exception as e:
                        print(f"Alert error: {e}")
                    whales += 1
            
            last_blocks[chain_name] = latest
            print(f"Found {whales} whales")
        
        except Exception as e:
            print(f"Error on {chain_name}: {e}")

def start_worker():
    while True:
        asyncio.run(run())
        time.sleep(12)

if __name__ == "__main__":
    start_worker()