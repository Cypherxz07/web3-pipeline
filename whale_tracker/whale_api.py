from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import os
import sys
import sqlite3
import threading
import json
import requests
import asyncio

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
    
    # Set up Telegram bot in a single async operation
    async def setup_telegram():
        await telegram_app.initialize()
        print("🐋 Telegram bot initialized in Flask app")
        
        # Set bot commands for menu
        from telegram import BotCommand
        commands = [
            BotCommand("start", "Show welcome message and options"),
            BotCommand("set", "Set alert filter (chain and amount)"),
            BotCommand("status", "Check current filter and status"),
            BotCommand("stop", "Stop receiving alerts"),
            BotCommand("resume", "Resume receiving alerts")
        ]
        await telegram_app.bot.set_my_commands(commands)
        print("🐋 Telegram bot commands set")
        
        # Set webhook synchronously to avoid event loop issues
        base_url = os.getenv('RENDER_EXTERNAL_URL', 'https://web3-pipeline-1.onrender.com')
        webhook_url = f"{base_url}/telegram"
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN_2')
        set_webhook_url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
        data = {"url": webhook_url}
        response = requests.post(set_webhook_url, data=data)
        if response.status_code == 200:
            print("🐋 Telegram webhook set successfully")
            # Verify webhook was set
            info_response = requests.get(f"https://api.telegram.org/bot{bot_token}/getWebhookInfo")
            if info_response.status_code == 200:
                info = info_response.json()
                print(f"🐋 Webhook info: {info}")
            else:
                print(f"🐋 Failed to get webhook info: {info_response.text}")
        else:
            print(f"🐋 Failed to set Telegram webhook: {response.text}")
    
    # Run all async setup in one call
    asyncio.run(setup_telegram())
    
    # Test bot token
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN_2')
    if bot_token:
        test_response = requests.get(f"https://api.telegram.org/bot{bot_token}/getMe")
        if test_response.status_code == 200:
            bot_info = test_response.json()
            print(f"🐋 Bot info: {bot_info}")
        else:
            print(f"🐋 Bot token test failed: {test_response.text}")


def maintain_webhook():
    """Periodically check and reset webhook if needed"""
    import time
    while True:
        try:
            bot_token = os.getenv('TELEGRAM_BOT_TOKEN_2')
            if bot_token:
                # Check current webhook
                info_response = requests.get(f"https://api.telegram.org/bot{bot_token}/getWebhookInfo", timeout=10)
                if info_response.status_code == 200:
                    info = info_response.json()
                    current_url = info.get('result', {}).get('url', '')
                    expected_url = f"{os.getenv('RENDER_EXTERNAL_URL', 'https://web3-pipeline-1.onrender.com')}/telegram"
                    
                    if current_url != expected_url:
                        print(f"🐋 Webhook URL mismatch. Current: {current_url}, Expected: {expected_url}. Resetting...")
                        # Reset webhook
                        set_response = requests.post(f"https://api.telegram.org/bot{bot_token}/setWebhook", 
                                                   data={"url": expected_url}, timeout=10)
                        if set_response.status_code == 200:
                            print("🐋 Webhook reset successfully")
                        else:
                            print(f"🐋 Failed to reset webhook: {set_response.text}")
                    else:
                        print("🐋 Webhook check passed")
                else:
                    print(f"🐋 Failed to get webhook info: {info_response.text}")
        except Exception as e:
            print(f"🐋 Webhook maintenance error: {e}")
        
        # Check every 5 minutes
        time.sleep(300)

# Start webhook maintenance thread
webhook_thread = threading.Thread(target=maintain_webhook, daemon=True)
webhook_thread.start()

@app.route('/telegram', methods=['POST'])
def telegram_webhook():
    print(f"🐋 Webhook received: method={request.method}, content-type={request.content_type}")
    if telegram_app and request.method == 'POST':
        try:
            payload = request.get_json(force=True)
            print('🐋 Telegram webhook payload received:', payload)
            update = Update.de_json(payload, telegram_app.bot)
            print('🐋 Created update object')
            import asyncio
            result = asyncio.run(telegram_app.process_update(update))
            print('🐋 Telegram webhook processed update result:', result)
            return 'ok'
        except Exception as e:
            print(f"🐋 Error processing webhook: {e}")
            import traceback
            traceback.print_exc()
            return 'error', 500
    print('🐋 Telegram webhook received request but telegram_app is not initialized')
    return 'no telegram app', 400

@app.route('/api/debug/telegram-webhook-info', methods=['GET'])
def debug_telegram_webhook_info():
    if not telegram_app:
        return jsonify({'status': 'error', 'error': 'telegram_app not initialized'})

    import asyncio
    try:
        webhook_info = asyncio.run(telegram_app.bot.get_webhook_info())
        return jsonify({'status': 'success', 'webhook_info': webhook_info.to_dict()})
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)})

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
    port = int(os.getenv('PORT', '5000'))
    app.run(debug=False, host='0.0.0.0', port=port, use_reloader=False, threaded=True)

