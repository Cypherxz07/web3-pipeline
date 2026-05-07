from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import os
import sys
import sqlite3
import threading
import json

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from whale_tracker.main import start_worker

db_path = os.path.join(os.path.dirname(__file__), 'whale_tracker.db')

app = Flask(__name__)
CORS(app)

worker_thread = threading.Thread(target=start_worker, daemon=True)
worker_thread.start()

@app.route('/', methods=['GET'])
def index():
    return send_from_directory(os.path.dirname(__file__), 'dashboard.html')

@app.route('/api/whales', methods=['GET'])
def get_whales():
    chain = request.args.get('chain', 'ethereum')
    min_amount = float(request.args.get('min_amount', 1))
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
    SELECT tx_hash, block_number, from_address, to_address, token_symbol, amount_usd, chain
    FROM transfers
    WHERE amount_usd >= ? AND chain = ?
    ORDER BY block_number DESC
    LIMIT 100
    """, (min_amount, chain))
    
    rows = cursor.fetchall()
    conn.close()
    
    return jsonify([dict(row) for row in rows])

@app.route('/api/debug/test-alert', methods=['GET'])
def test_alert():
    """Debug endpoint to test alert functionality"""
    from config import TELEGRAM_CHAT_ID
    chat_id = request.args.get('chat_id', TELEGRAM_CHAT_ID)
    chain = request.args.get('chain', 'ethereum')
    amount = float(request.args.get('amount', '100000'))
    
    # Create a test transfer
    test_transfer = {
        'tx_hash': '0x1234567890abcdef',
        'block': 12345678,
        'from': '0x742d35Cc6634C0532925a3b844Bc454e4438f44e',
        'to': '0x8ba1f109551bD432803012645261768374161',
        'token_symbol': 'USDC',
        'amount_usd': amount,
        'chain': chain
    }
    
    # Test filter loading
    filters_file = os.path.join(os.path.dirname(__file__), 'user_filters.json')
    if os.path.exists(filters_file):
        with open(filters_file) as f:
            filters = json.load(f)
    else:
        filters = {}
    
    # Test alert logic
    import asyncio
    from telegram_bot.on_chain_alerts import alert
    
    async def test():
        result = await alert(test_transfer, 50000)
        return result
    
    try:
        result = asyncio.run(test())
        return jsonify({
            'status': 'success',
            'alert_sent': result,
            'filters_loaded': filters,
            'test_transfer': test_transfer,
            'chat_id': chat_id
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'filters_loaded': filters,
            'test_transfer': test_transfer
        })

@app.route('/api/debug/set-filter', methods=['GET'])
def debug_set_filter():
    """Debug endpoint to set a test filter"""
    from config import TELEGRAM_CHAT_ID
    chat_id = request.args.get('chat_id', TELEGRAM_CHAT_ID)
    chain = request.args.get('chain', 'ethereum')
    amount = float(request.args.get('amount', '100000'))
    
    filters_file = os.path.join(os.path.dirname(__file__), 'user_filters.json')
    if os.path.exists(filters_file):
        with open(filters_file) as f:
            filters = json.load(f)
    else:
        filters = {}
    
    filters[str(chat_id)] = {'chain': chain, 'min_amount': amount}
    
    with open(filters_file, 'w') as f:
        json.dump(filters, f)
    
    return jsonify({
        'status': 'success',
        'message': f'Filter set for chat {chat_id}: {chain.upper()} >= ${amount:,.0f}',
        'filters': filters
    })

@app.route('/api/cron', methods=['GET'])
def cron_trigger():
    import subprocess
    os.chdir('/app/whale_tracker')
    subprocess.Popen(['python', 'main.py'])
    return {'status': 'cron triggered'}, 200

if __name__ == "__main__":
    port = int(os.getenv('PORT', '5000'))
    # Use threaded=True to allow concurrent requests
    app.run(debug=False, host='0.0.0.0', port=port, use_reloader=False, threaded=True)