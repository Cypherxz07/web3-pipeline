#!/usr/bin/env python3
"""
Standalone Telegram Bot for Whale Tracker
"""
import os
import sys
import time
import asyncio
import json
import re
import sqlite3
from datetime import datetime, timezone, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from telegram.error import Conflict

# Add parent directory to path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from config import TELEGRAM_BOT_TOKEN_2

# Shared filter file path at repository root
USER_FILTERS_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'user_filters.json'))
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'whale_tracker', 'whale_tracker.db'))

def load_filters():
    if os.path.exists(USER_FILTERS_FILE):
        with open(USER_FILTERS_FILE) as f:
            return json.load(f)
    return {}

def save_filters(filters):
    with open(USER_FILTERS_FILE, 'w') as f:
        json.dump(filters, f)

async def set_filter(update: Update, context):
    """Usage: /set <chain> <min_amount>"""
    if len(context.args) < 2:
        # Show menu instead of text usage
        keyboard = [
            [InlineKeyboardButton("Ethereum", callback_data="chain_ethereum"),
             InlineKeyboardButton("Polygon", callback_data="chain_polygon"),
             InlineKeyboardButton("Arbitrum", callback_data="chain_arbitrum")],
            [InlineKeyboardButton("$100K", callback_data="amount_100000"),
             InlineKeyboardButton("$500K", callback_data="amount_500000"),
             InlineKeyboardButton("$1M", callback_data="amount_1000000")],
            [InlineKeyboardButton("Custom Amount", callback_data="custom_amount")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🐋 Select chain and minimum amount for whale alerts:",
            reply_markup=reply_markup
        )
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

async def button_callback(update: Update, context):
    query = update.callback_query
    await query.answer()

    chat_id = str(query.message.chat.id)
    data = query.data

    if data.startswith("chain_"):
        chain = data.split("_")[1]
        context.user_data['selected_chain'] = chain
        await query.edit_message_text(
            f"Selected chain: {chain.upper()}\nNow select minimum amount:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("$100K", callback_data="amount_100000"),
                 InlineKeyboardButton("$500K", callback_data="amount_500000"),
                 InlineKeyboardButton("$1M", callback_data="amount_1000000")],
                [InlineKeyboardButton("Custom Amount", callback_data="custom_amount")]
            ])
        )

    elif data.startswith("amount_"):
        amount = int(data.split("_")[1])
        chain = context.user_data.get('selected_chain', 'ethereum')

        filters = load_filters()
        filters[chat_id] = {'chain': chain, 'min_amount': amount}
        save_filters(filters)

        await query.edit_message_text(
            f"✅ Alerts set for {chain.upper()} transactions above ${amount:,.0f}\n\n"
            f"Use /status to check your filter or /set to change it."
        )

    elif data == "custom_amount":
        context.user_data['waiting_for_custom_amount'] = True
        await query.edit_message_text(
            f"Selected chain: {context.user_data.get('selected_chain', 'ethereum').upper()}\n\n"
            "Send me the custom minimum amount (e.g., 250000 for $250K):"
        )

    elif data == "set_filter":
        keyboard = [
            [InlineKeyboardButton("Ethereum", callback_data="chain_ethereum"),
             InlineKeyboardButton("Polygon", callback_data="chain_polygon"),
             InlineKeyboardButton("Arbitrum", callback_data="chain_arbitrum")],
            [InlineKeyboardButton("$100K", callback_data="amount_100000"),
             InlineKeyboardButton("$500K", callback_data="amount_500000"),
             InlineKeyboardButton("$1M", callback_data="amount_1000000")],
            [InlineKeyboardButton("Custom Amount", callback_data="custom_amount")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🐋 Select chain and minimum amount for whale alerts:",
            reply_markup=reply_markup
        )

    elif data == "status":
        filters = load_filters()
        user_filter = filters.get(chat_id)
        if not user_filter:
            keyboard = [[InlineKeyboardButton("Set Filter", callback_data="set_filter")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "No filter set. Set up alerts to get notified of whale transactions:",
                reply_markup=reply_markup
            )
        else:
            enabled = user_filter.get('enabled', True)
            cooldown = user_filter.get('cooldown', 60)
            status_text = "✅ Active" if enabled else "🛑 Stopped"
            keyboard = [
                [InlineKeyboardButton("Change Filter", callback_data="set_filter")],
                [InlineKeyboardButton("Test Alert", callback_data="test_alert")],
                [InlineKeyboardButton("Stop Alerts" if enabled else "Resume Alerts", callback_data="toggle_alerts")],
                [InlineKeyboardButton(f"Rate Limit: {format_duration(cooldown)}", callback_data="set_cooldown")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                f"Status: {status_text}\nChain: {user_filter['chain'].upper()}\nMinimum amount: ${user_filter['min_amount']:,.0f}\nRate limit: {format_duration(cooldown)} between alerts\n\nUse /cooldown to change the limit or /history to view recent transfers.",
                reply_markup=reply_markup
            )

    elif data == "toggle_alerts":
        filters = load_filters()
        user_filter = filters.get(chat_id, {})
        enabled = user_filter.get('enabled', True)
        user_filter['enabled'] = not enabled
        filters[chat_id] = user_filter
        save_filters(filters)

        new_status = "resumed" if user_filter['enabled'] else "stopped"
        keyboard = [[InlineKeyboardButton("Back to Status", callback_data="status")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"✅ Alerts {new_status}!",
            reply_markup=reply_markup
        )

    elif data == "set_cooldown" or data == "set_cooldown_from_menu":
        keyboard = [
            [InlineKeyboardButton("No limit", callback_data="cooldown_0")],
            [InlineKeyboardButton("30 seconds", callback_data="cooldown_30")],
            [InlineKeyboardButton("1 minute", callback_data="cooldown_60")],
            [InlineKeyboardButton("5 minutes", callback_data="cooldown_300")],
            [InlineKeyboardButton("Back to Status", callback_data="status")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🐋 Choose rate limit between alerts:\n\n• No limit: Get all matching alerts\n• 30s/1min/5min: Space out alerts to reduce spam",
            reply_markup=reply_markup
        )

    elif data.startswith("cooldown_"):
        cooldown_value = int(data.split("_")[1])
        filters = load_filters()
        user_filter = filters.get(chat_id, {})
        user_filter['cooldown'] = cooldown_value
        filters[chat_id] = user_filter
        save_filters(filters)

        cooldown_text = "No limit" if cooldown_value == 0 else f"{cooldown_value//60}min" if cooldown_value >= 60 else f"{cooldown_value}s"
        keyboard = [[InlineKeyboardButton("Back to Status", callback_data="status")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"✅ Rate limit set to: {cooldown_text}",
            reply_markup=reply_markup
        )

    elif data == "stop_alerts":
        filters = load_filters()
        user_filter = filters.get(chat_id, {})
        user_filter['enabled'] = False
        filters[chat_id] = user_filter
        save_filters(filters)

        keyboard = [[InlineKeyboardButton("Resume Alerts", callback_data="resume")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🛑 Alerts stopped.\n\nYou won't receive whale transfer notifications until you resume.",
            reply_markup=reply_markup
        )

    elif data == "resume":
        filters = load_filters()
        user_filter = filters.get(chat_id, {})
        user_filter['enabled'] = True
        filters[chat_id] = user_filter
        save_filters(filters)

        await query.edit_message_text("✅ Alerts resumed! You'll now receive whale transfer notifications again.")

    elif data == "history_menu":
        keyboard = [
            [InlineKeyboardButton("Last 24h", callback_data="history_period_24h")],
            [InlineKeyboardButton("Last 7 days", callback_data="history_period_7d")],
            [InlineKeyboardButton("Last 30 days", callback_data="history_period_30d")],
            [InlineKeyboardButton("Back to Menu", callback_data="status")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "📜 Select a time period to view transfer history:",
            reply_markup=reply_markup
        )

    elif data.startswith("history_period_"):
        period_map = {"24h": "24h", "7d": "7d", "30d": "30d"}
        period = data.split("_")[-1]
        period_key = period_map.get(period, "24h")
        
        filters = load_filters()
        user_filter = filters.get(chat_id, {})
        chain = user_filter.get('chain')
        min_amount = user_filter.get('min_amount')
        
        now = datetime.now(timezone.utc)
        if period_key == "24h":
            start_ts = int((now - timedelta(hours=24)).timestamp())
        elif period_key == "7d":
            start_ts = int((now - timedelta(days=7)).timestamp())
        else:
            start_ts = int((now - timedelta(days=30)).timestamp())
        end_ts = int(now.timestamp())
        
        rows = query_history_rows(chain, start_ts, end_ts, min_amount=min_amount)
        chat_chain = f" on {chain.upper()}" if chain else ""
        min_text = f" (min ${min_amount:,.0f})" if min_amount else ""
        title = f"📜 Transfer history{chat_chain}{min_text} (last {period_key}):"
        await send_history_messages(query.message, rows, title)

    elif data == "test_alert":
        # Send a test alert
        from telegram import Bot
        bot = Bot(token=TELEGRAM_BOT_TOKEN_2)

        test_message = """
🐋 **TEST ALERT** [ETHEREUM]

Token: USDC
Amount: $123,456.78
From: `0x742d...44e`
To: `0x8ba1...161`
Tx: https://etherscan.io/tx/0x1234567890abcdef
Block: 12345678
"""
        await bot.send_message(chat_id=chat_id, text=test_message, parse_mode='Markdown')
        await query.edit_message_text("✅ Test alert sent! Check your messages.")

def format_duration(seconds: int) -> str:
    if seconds == 0:
        return "No limit"
    if seconds >= 60 and seconds % 60 == 0:
        return f"{seconds // 60}min"
    return f"{seconds}s"


def parse_cooldown_arg(token: str) -> int | None:
    token = token.strip().lower()
    if token.isdigit():
        return int(token)
    m = re.match(r'^(\d+)([smhd])$', token)
    if not m:
        return None
    value, unit = int(m.group(1)), m.group(2)
    if unit == 's':
        return value
    if unit == 'm':
        return value * 60
    if unit == 'h':
        return value * 3600
    if unit == 'd':
        return value * 86400
    return None


def parse_date_token(token: str) -> datetime | None:
    try:
        return datetime.strptime(token, '%Y-%m-%d').replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def query_history_rows(chain: str | None, start_ts: int, end_ts: int, min_amount: float | None = None, limit: int = 10):
    if not os.path.exists(DB_PATH):
        return []
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    params = []
    where_clauses = ['created_at BETWEEN datetime(?, "unixepoch") AND datetime(?, "unixepoch")']
    params.extend([start_ts, end_ts])

    if chain:
        where_clauses.insert(0, 'chain = ?')
        params.insert(0, chain)

    if min_amount is not None:
        where_clauses.append('amount_usd >= ?')
        params.append(min_amount)

    where_sql = ' AND '.join(where_clauses)
    sql = (
        'SELECT tx_hash, block_number, created_at, token_symbol, amount_usd, chain FROM transfers '
        f'WHERE {where_sql} '
        'ORDER BY created_at DESC LIMIT ?'
    )
    params.append(limit)
    cursor.execute(sql, tuple(params))
    rows = cursor.fetchall()
    conn.close()
    return rows


async def get_filter_status(update: Update, context):
    chat_id = str(update.effective_chat.id)
    filters = load_filters()
    user_filter = filters.get(chat_id)
    if not user_filter:
        keyboard = [[InlineKeyboardButton("Set Filter", callback_data="set_filter")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "No filter set. Set up alerts to get notified of whale transactions:",
            reply_markup=reply_markup
        )
        return

    cooldown = user_filter.get('cooldown', 60)
    keyboard = [
        [InlineKeyboardButton("Change Filter", callback_data="set_filter")],
        [InlineKeyboardButton("Test Alert", callback_data="test_alert")],
        [InlineKeyboardButton("Stop Alerts", callback_data="toggle_alerts")],
        [InlineKeyboardButton(f"Rate Limit: {format_duration(cooldown)}", callback_data="set_cooldown")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"✅ Current filter:\nChain: {user_filter['chain'].upper()}\n"  \
        f"Minimum amount: ${user_filter['min_amount']:,.0f}\n"  \
        f"Rate limit: {format_duration(cooldown)}\n"  \
        f"Use /cooldown to change rate limit or /history to view recent transfers.",
        reply_markup=reply_markup
    )


def format_history_link(chain: str, tx_hash: str) -> str:
    explorers = {
        'ethereum': 'https://etherscan.io',
        'polygon': 'https://polygonscan.com',
        'arbitrum': 'https://arbiscan.io',
    }
    base = explorers.get(chain.lower(), 'https://etherscan.io')
    return f"{base}/tx/{tx_hash}"


def format_history_message(rows):
    if not rows:
        return "No transfers were found for that range."
    text = []
    for row in rows:
        ts = row['created_at'] if row['created_at'] else 'N/A'
        amount_usd = row['amount_usd'] or 0
        text.append(
            f"💰 {row['chain'].upper()} {row['token_symbol']} ${amount_usd:,.2f}\n"
            f"📦 Block {row['block_number']} | {ts}\n"
            f"🔗 {format_history_link(row['chain'], row['tx_hash'])}"
        )
    return "\n\n".join(text)


async def send_history_messages(update: Update, rows, title: str):
    """Split history into readable chunks to avoid Telegram message limits."""
    if not rows:
        await update.callback_query.edit_message_text(f"{title}\n\nNo transfers found.")
        return
    
    messages = []
    current_msg = ""
    
    for row in rows:
        ts = row['created_at'] if row['created_at'] else 'N/A'
        amount_usd = row['amount_usd'] or 0
        entry = (
            f"💰 {row['chain'].upper()} {row['token_symbol']} ${amount_usd:,.2f}\n"
            f"📦 Block {row['block_number']} | {ts}\n"
            f"🔗 {format_history_link(row['chain'], row['tx_hash'])}"
        )
        
        if len(current_msg) + len(entry) + 4 > 3500:
            if current_msg:
                messages.append(current_msg)
            current_msg = entry
        else:
            current_msg += ("\n\n" if current_msg else "") + entry
    
    if current_msg:
        messages.append(current_msg)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(title)
    else:
        await update.message.reply_text(title)
    
    for msg in messages:
        if update.callback_query:
            await update.callback_query.message.reply_text(msg)
        else:
            await update.message.reply_text(msg)


async def cooldown_command(update: Update, context):
    chat_id = str(update.effective_chat.id)
    filters = load_filters()
    user_filter = filters.get(chat_id, {})
    if not context.args:
        current = user_filter.get('cooldown', 60)
        await update.message.reply_text(
            f"Current cooldown is {format_duration(current)}.\n"
            "Use /cooldown <seconds|30s|1m|5m|0> to change it."
        )
        return

    cooldown_value = parse_cooldown_arg(context.args[0])
    if cooldown_value is None or cooldown_value < 0:
        await update.message.reply_text(
            "Invalid cooldown. Use /cooldown <seconds|30s|1m|5m|0>. Example: /cooldown 60"
        )
        return

    user_filter['cooldown'] = cooldown_value
    filters[chat_id] = user_filter
    save_filters(filters)

    await update.message.reply_text(
        f"✅ Rate limit set to {format_duration(cooldown_value)}."
    )


async def history_command(update: Update, context):
    chat_id = str(update.effective_chat.id)
    filters = load_filters()
    user_filter = filters.get(chat_id, {})
    chain = user_filter.get('chain')

    if len(context.args) == 0:
        await update.message.reply_text(
            "Usage: /history <period> OR /history <from> <to>\n"
            "Examples:\n"
            " /history 24h\n"
            " /history 7d\n"
            " /history 2026-05-01 2026-05-07\n"
            " /history 18000000 18001000\n"
            "If you have a filter active, history will default to that chain."
        )
        return

    now = datetime.now(timezone.utc)
    start_ts = None
    end_ts = int(now.timestamp())
    if len(context.args) == 1:
        period = context.args[0].lower()
        m = re.match(r'^(\d+)([smhd])$', period)
        if m:
            value = int(m.group(1))
            unit = m.group(2)
            if unit == 's':
                delta = timedelta(seconds=value)
            elif unit == 'm':
                delta = timedelta(minutes=value)
            elif unit == 'h':
                delta = timedelta(hours=value)
            else:
                delta = timedelta(days=value)
            start_ts = int((now - delta).timestamp())
        else:
            await update.message.reply_text(
                "Invalid history period. Use 24h, 7d, or provide two dates or blocks."
            )
            return
    elif len(context.args) == 2:
        left, right = context.args
        left_date = parse_date_token(left)
        right_date = parse_date_token(right)
        if left_date and right_date:
            start_ts = int(left_date.timestamp())
            end_ts = int((right_date + timedelta(days=1)).timestamp())
        elif left.isdigit() and right.isdigit():
            start_block = int(left)
            end_block = int(right)
            if start_block > end_block:
                start_block, end_block = end_block, start_block
            rows = []
            if os.path.exists(DB_PATH):
                conn = sqlite3.connect(DB_PATH)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                params = [start_block, end_block]
                where = ['block_number BETWEEN ? AND ?']
                if chain:
                    where.insert(0, 'chain = ?')
                    params.insert(0, chain)
                min_amt = user_filter.get('min_amount')
                if min_amt is not None:
                    where.append('amount_usd >= ?')
                    params.append(min_amt)
                where_sql = ' AND '.join(where)
                sql = (
                    'SELECT tx_hash, block_number, timestamp, token_symbol, amount_usd, chain FROM transfers '
                    f'WHERE {where_sql} '
                    'ORDER BY block_number DESC LIMIT ?'
                )
                params.append(10)
                cursor.execute(sql, tuple(params))
                rows = cursor.fetchall()
                conn.close()
            await update.message.reply_text(
                f"📜 Transfer history for blocks {start_block} to {end_block}:\n\n" + format_history_message(rows)
            )
            return
        else:
            await update.message.reply_text(
                "Invalid history arguments. Use two dates (YYYY-MM-DD) or two block numbers."
            )
            return
    else:
        await update.message.reply_text(
            "Too many arguments. Use /history <period> or /history <from> <to>."
        )
        return

    min_amount = user_filter.get('min_amount')
    rows = query_history_rows(chain, start_ts, end_ts, min_amount=min_amount)
    chat_chain = f" on {chain.upper()}" if chain else ""
    min_text = f" (min ${min_amount:,.0f})" if min_amount else ""
    await update.message.reply_text(
        f"📜 Transfer history{chat_chain}{min_text} from {datetime.fromtimestamp(start_ts, tz=timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} "
        f"to {datetime.fromtimestamp(end_ts, tz=timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}:\n\n"
        + format_history_message(rows)
    )


async def start_command(update: Update, context):
    keyboard = [
        [InlineKeyboardButton("Set Alert Filter", callback_data="set_filter")],
        [InlineKeyboardButton("Check Status", callback_data="status")],
        [InlineKeyboardButton("View History", callback_data="history_menu")],
        [InlineKeyboardButton("Rate Limit", callback_data="set_cooldown")],
        [InlineKeyboardButton("Test Alert", callback_data="test_alert")],
        [InlineKeyboardButton("Stop Alerts", callback_data="stop_alerts")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🐋 Welcome to Multi-Chain Whale Tracker!\n\n"
        "Get notified when large cryptocurrency transfers happen on Ethereum, Polygon, and Arbitrum.\n\n"
        "Use the buttons below or type: /set, /status, /cooldown, /history, /stop, /resume",
        reply_markup=reply_markup
    )

async def stop_command(update: Update, context):
    chat_id = str(update.effective_chat.id)
    filters = load_filters()
    user_filter = filters.get(chat_id, {})
    user_filter['enabled'] = False
    filters[chat_id] = user_filter
    save_filters(filters)

    keyboard = [[InlineKeyboardButton("Resume Alerts", callback_data="resume")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🛑 Alerts stopped.\n\nYou won't receive whale transfer notifications until you resume.",
        reply_markup=reply_markup
    )

async def resume_command(update: Update, context):
    chat_id = str(update.effective_chat.id)
    filters = load_filters()
    user_filter = filters.get(chat_id, {})
    user_filter['enabled'] = True
    filters[chat_id] = user_filter
    save_filters(filters)

    await update.message.reply_text("✅ Alerts resumed! You'll now receive whale transfer notifications again.")

async def handle_custom_amount(update: Update, context):
    """Handle text input for custom amount."""
    if not context.user_data.get('waiting_for_custom_amount'):
        return
    
    try:
        amount = float(update.message.text)
        if amount <= 0:
            await update.message.reply_text("Please enter a positive number.")
            return
        
        chat_id = str(update.effective_chat.id)
        chain = context.user_data.get('selected_chain', 'ethereum')
        
        filters = load_filters()
        filters[chat_id] = {'chain': chain, 'min_amount': amount}
        save_filters(filters)
        
        context.user_data['waiting_for_custom_amount'] = False
        await update.message.reply_text(
            f"✅ Alerts set for {chain.upper()} transactions above ${amount:,.0f}\n\n"
            f"Use /status to check your filter or /set to change it."
        )
    except ValueError:
        await update.message.reply_text("Please enter a valid number (e.g., 250000).")


def add_handlers_to_app(app):
    from telegram.ext import MessageHandler, filters
    
    app.add_handler(CommandHandler(["set", "set_filter"], set_filter))
    app.add_handler(CommandHandler("status", get_filter_status))
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("stop", stop_command))
    app.add_handler(CommandHandler("resume", resume_command))
    app.add_handler(CommandHandler("cooldown", cooldown_command))
    app.add_handler(CommandHandler("history", history_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_custom_amount))
    app.add_handler(CallbackQueryHandler(button_callback))

def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN_2).build()
    add_handlers_to_app(app)

    print("🐋 Telegram Whale Tracker Bot started!")
    print("Available commands: /start, /set, /status, /cooldown, /history, /stop, /resume")
    print("Filter file:", USER_FILTERS_FILE)

    try:
        print("Clearing any existing webhook/pending updates before polling...")
        app.bot.delete_webhook(drop_pending_updates=True)
    except Exception as e:
        print(f"Warning: could not clear webhook before polling: {e}")

    while True:
        try:
            app.run_polling(stop_signals=())
            break
        except Conflict as e:
            print(f"Telegram polling conflict: {e}. Retrying in 15s...")
            time.sleep(15)
        except Exception as e:
            print(f"Telegram bot error: {e}. Retrying in 15s...")
            time.sleep(15)

if __name__ == "__main__":
    main()