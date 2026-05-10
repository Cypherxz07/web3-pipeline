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

# Telegram bot integration
from telegram import Update
from telegram.ext import Application
from telegram_bot.bot import add_handlers_to_app

db_path = os.path.join(os.path.dirname(__file__), 'whale_tracker.db')

app = Flask(__name__)
CORS(app)

# Initialize Telegram app if token is available
telegram_app = None
if os.getenv('TELEGRAM_BOT_TOKEN_2'):
    telegram_app = Application.builder().token(os.getenv('TELEGRAM_BOT_TOKEN_2')).build()
    add_handlers_to_app(telegram_app)
    print("🐋 Telegram bot initialized in Flask app")


worker_thread = threading.Thread(target=start_worker, daemon=True)
worker_thread.start()

@app.route('/telegram', methods=['POST'])
def telegram_webhook():
    if telegram_app and request.method == 'POST':
        update = Update.de_json(request.get_json(force=True), telegram_app.bot)
        telegram_app.process_update(update)
        return 'ok'
    return 'no telegram app', 400


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
    root_filters = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'user_filters.json'))
    filters_file = root_filters
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
    
    root_filters = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'user_filters.json'))
    filters_file = root_filters
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

@app.route('/api/debug/filter-status', methods=['GET'])
def debug_filter_status():
    root_filters = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'user_filters.json'))
    exists = os.path.exists(root_filters)
    filters = {}
    if exists:
        with open(root_filters) as f:
            filters = json.load(f)
    return jsonify({
        'filters_file': root_filters,
        'exists': exists,
        'filters': filters
    })

@app.route('/api/cron', methods=['GET'])
def cron_trigger():
    import subprocess
    os.chdir('/app/whale_tracker')
    subprocess.Popen(['python', 'main.py'])
    return {'status': 'cron triggered'}, 200

if __name__ == "__main__":
    # Set up Telegram webhook if available
    if telegram_app:
        webhook_url = os.getenv('RENDER_EXTERNAL_URL', os.getenv('WEBHOOK_URL', ''))
        if webhook_url:
            full_webhook_url = webhook_url.rstrip('/') + '/telegram'
            try:
                import asyncio
                asyncio.run(telegram_app.bot.set_webhook(full_webhook_url))
                print(f"🐋 Telegram webhook set to {full_webhook_url}")
            except Exception as e:
                print(f"Failed to set Telegram webhook: {e}")
        else:
            print("No WEBHOOK_URL or RENDER_EXTERNAL_URL set, Telegram bot will not receive updates")

    port = int(os.getenv('PORT', '5000'))
    # Use threaded=True to allow concurrent requests
    app.run(debug=False, host='0.0.0.0', port=port, use_reloader=False, threaded=True)