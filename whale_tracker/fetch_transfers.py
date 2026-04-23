import os
import sys
from web3 import Web3
import sqlite3
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import INFURA_PROJECT_ID, WHALE_TRACKER_TRACKED_TOKENS

TRACKED_TOKENS = {Web3.to_checksum_address(addr): symbol for addr, symbol in WHALE_TRACKER_TRACKED_TOKENS.items()}

DECIMALS = {
    '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48': 6,
    '0xC02aaA39b223FE8D0A0e8e4F27ead9083C756Cc2': 18,
}

PRICES = {
    '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48': 1.0,
    '0xC02aaA39b223FE8D0A0e8e4F27ead9083C756Cc2': 2500,
}

def get_transfer_logs(w3, from_block, to_block, chain='ethereum'):
    transfer_sig = Web3.keccak(text="Transfer(address,address,uint256)")
    all_logs = []
    
    for token_addr in list(TRACKED_TOKENS.keys())[:2]:
        try:
            logs = w3.eth.get_logs({
                'fromBlock': from_block,
                'toBlock': min(to_block, from_block + 100),
                'topics': [transfer_sig],
                'address': [token_addr]
            })
            all_logs.extend(logs)
        except Exception as e:
            print(f"Error on {chain}: {e}")
    
    return all_logs

def decode_transfer(log):
    from_addr = '0x' + log['topics'][1].hex()[-40:]
    to_addr = '0x' + log['topics'][2].hex()[-40:]
    amount = int(log['data'].hex(), 16)
    token = log['address']
    
    decimals = DECIMALS.get(token, 18)
    readable_amount = amount / (10 ** decimals)
    price = PRICES.get(token, 0)
    amount_usd = readable_amount * price
    
    return {
        'tx_hash': log['transactionHash'].hex(),
        'block': log['blockNumber'],
        'from': from_addr,
        'to': to_addr,
        'token': token,
        'token_symbol': TRACKED_TOKENS.get(token, 'UNKNOWN'),
        'amount': readable_amount,
        'amount_usd': amount_usd
    }

def save_to_db(transfer):
    db_path = r'C:\Users\USER\Desktop\web3-pipeline\whale_tracker\whale_tracker.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()  # ADD THIS LINE
    
    try:
        cursor.execute("""
        INSERT OR IGNORE INTO transfers 
        (tx_hash, block_number, from_address, to_address, token_address, token_symbol, amount, amount_usd)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            transfer['tx_hash'],
            transfer['block'],
            transfer['from'],
            transfer['to'],
            transfer['token'],
            transfer['token_symbol'],
            transfer['amount'],
            transfer['amount_usd']
        ))
        conn.commit()
    except Exception as e:
        print(f"DB error: {e}")
    finally:
        conn.close()