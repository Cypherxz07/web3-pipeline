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
    """Usage: /set <chain> <min_amount>"""
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /set <chain> <min_amount>\nExample: /set ethereum 500000")
        return

    chain = context.args[0].lower()
    try:
        min_amount = float(context.args[1])
    except ValueError:
        await update.message.reply_text("Please provide a numeric minimum amount. Example: /set ethereum 500000")
        return

    if chain not in {"ethereum", "polygon", "arbitrum"}:
        await update.message.reply_text("Supported chains: ethereum, polygon, arbitrum. Example: /set ethereum 500000")
        return

    chat_id = str(update.effective_chat.id)
    filters = load_filters()
    filters[chat_id] = {'chain': chain, 'min_amount': min_amount}
    save_filters(filters)

    await update.message.reply_text(f"✅ Alerts set for {chain.upper()} transactions above ${min_amount:,.0f}")
    print(f"Telegram filter saved for chat {chat_id}: {filters[chat_id]}")

async def get_filter_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    filters = load_filters()
    user_filter = filters.get(chat_id)
    if not user_filter:
        await update.message.reply_text("No filter set. Use /set <chain> <min_amount> to enable alerts.")
        return

    await update.message.reply_text(
        f"✅ Current filter:\nChain: {user_filter['chain'].upper()}\nMinimum amount: ${user_filter['min_amount']:,.0f}"
    )

async def start_tg_bot():
    app_tg = Application.builder().token(TELEGRAM_BOT_TOKEN_2).build()
    app_tg.add_handler(CommandHandler(["set", "set_filter"], set_filter))
    app_tg.add_handler(CommandHandler("status", get_filter_status))
    print("Telegram polling bot started.")
    await app_tg.run_polling(stop_signals=())

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