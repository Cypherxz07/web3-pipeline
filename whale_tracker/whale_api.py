from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import os
import sqlite3
import threading
import json
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from whale_tracker.main import start_worker
from config import TELEGRAM_BOT_TOKEN_2, TELEGRAM_CHAT_ID

db_path = os.path.join(os.path.dirname(__file__), 'whale_tracker.db')
filters_file = os.path.join(os.path.dirname(__file__), 'user_filters.json')

app = Flask(__name__)
CORS(app)

worker_thread = threading.Thread(target=start_worker, daemon=True)
worker_thread.start()

def load_filters():
    if os.path.exists(filters_file):
        with open(filters_file) as f:
            return json.load(f)
    return {}

def save_filters(filters):
    with open(filters_file, 'w') as f:
        json.dump(filters, f)

async def set_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Usage: /set_filter ethereum 500000"""
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /set_filter <chain> <min_amount>\nExample: /set_filter ethereum 500000")
        return
    
    chain = context.args[0]
    min_amount = float(context.args[1])
    
    filters = load_filters()
    filters[str(TELEGRAM_CHAT_ID)] = {'chain': chain, 'min_amount': min_amount}
    save_filters(filters)
    
    await update.message.reply_text(f"✅ Alerts: {chain.upper()} > ${min_amount:,.0f}")

async def start_tg_bot():
    app_tg = Application.builder().token(TELEGRAM_BOT_TOKEN_2).build()
    app_tg.add_handler(CommandHandler("set_filter", set_filter))
    await app_tg.run_polling()

tg_thread = threading.Thread(target=lambda: __import__('asyncio').run(start_tg_bot()), daemon=True)
tg_thread.start()

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

@app.route('/api/cron', methods=['GET'])
def cron_trigger():
    import subprocess
    os.chdir('/app/whale_tracker')
    subprocess.Popen(['python', 'main.py'])
    return {'status': 'cron triggered'}, 200

if __name__ == "__main__":
    port = int(os.getenv('PORT', '5000'))
    app.run(debug=True, host='0.0.0.0', port=port, use_reloader=False)