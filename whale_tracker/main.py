import importlib.util
import os
import sys
import time
import asyncio
import requests
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

# Verify config at startup
if not INFURA_PROJECT_ID:
    print("[ERROR] INFURA_PROJECT_ID is not set! Worker will fail.")
else:
    print(f"[CONFIG] INFURA_PROJECT_ID loaded: {INFURA_PROJECT_ID[:10]}...")
    print(f"[CONFIG] WHALE_TRACKER_THRESHOLD_USD: ${WHALE_TRACKER_THRESHOLD_USD}")

last_blocks = {'ethereum': None, 'polygon': None, 'arbitrum': None}

async def run():
    for chain_name, rpc_url in CHAINS.items():
        try:
            print(f"[{chain_name.upper()}] Connecting to RPC...")
            print(f"[{chain_name.upper()}] RPC URL: {rpc_url[:50]}...")
            from requests.adapters import HTTPAdapter
            from urllib3.util.retry import Retry
            session = requests.Session()
            retries = Retry(total=3, backoff_factor=0.5)
            adapter = HTTPAdapter(max_retries=retries)
            session.mount('http://', adapter)
            session.mount('https://', adapter)
            w3 = Web3(Web3.HTTPProvider(rpc_url, session=session, request_kwargs={'timeout': 10}))
            print(f"[{chain_name.upper()}] Checking RPC connection...")
            latest = w3.eth.block_number
            print(f"[{chain_name.upper()}] Connected. Latest block: {latest}")
            
            if last_blocks[chain_name] is None:
                last_blocks[chain_name] = latest - 100
                print(f"[{chain_name.upper()}] Starting from block {last_blocks[chain_name]}")
            
            print(f"\n[{time.strftime('%H:%M:%S')}] {chain_name.upper()} blocks {last_blocks[chain_name]} to {latest}")

            try:
                logs = get_transfer_logs(w3, last_blocks[chain_name], min(latest, last_blocks[chain_name] + 10), chain=chain_name)
                print(f"[{chain_name.upper()}] Found {len(logs)} logs")
            except Exception as e:
                print(f"[{chain_name.upper()}] Error fetching logs: {e}")
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
    print("[WORKER] Starting whale tracker worker...")
    attempt = 0
    while True:
        attempt += 1
        try:
            print(f"[WORKER] Poll cycle #{attempt} starting...")
            asyncio.run(run())
        except Exception as e:
            print(f"[WORKER] ERROR in poll cycle #{attempt}: {e}")
            import traceback
            traceback.print_exc()
        time.sleep(12)

if __name__ == "__main__":
    start_worker()