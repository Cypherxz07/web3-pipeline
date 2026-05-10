#!/usr/bin/env python3
"""
Standalone Telegram Bot for Whale Tracker
"""
import os
import sys
import time
import asyncio
import json
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
        await query.edit_message_text(
            "Enter custom amount with command:\n/set <chain> <amount>\n\nExample: /set ethereum 250000"
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
            cooldown_text = f"{cooldown//60}min" if cooldown >= 60 else f"{cooldown}s"
            status_text = "✅ Active" if enabled else "🛑 Stopped"
            keyboard = [
                [InlineKeyboardButton("Change Filter", callback_data="set_filter")],
                [InlineKeyboardButton("Test Alert", callback_data="test_alert")],
                [InlineKeyboardButton("Stop Alerts" if enabled else "Resume Alerts", callback_data="toggle_alerts")],
                [InlineKeyboardButton(f"Rate Limit: {cooldown_text}", callback_data="set_cooldown")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                f"Status: {status_text}\nChain: {user_filter['chain'].upper()}\nMinimum amount: ${user_filter['min_amount']:,.0f}\nRate limit: {cooldown_text} between alerts",
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

    elif data == "set_cooldown":
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

    keyboard = [
        [InlineKeyboardButton("Change Filter", callback_data="set_filter")],
        [InlineKeyboardButton("Test Alert", callback_data="test_alert")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"✅ Current filter:\nChain: {user_filter['chain'].upper()}\nMinimum amount: ${user_filter['min_amount']:,.0f}",
        reply_markup=reply_markup
    )

async def start_command(update: Update, context):
    keyboard = [
        [InlineKeyboardButton("Set Alert Filter", callback_data="set_filter")],
        [InlineKeyboardButton("Check Status", callback_data="status")],
        [InlineKeyboardButton("Test Alert", callback_data="test_alert")],
        [InlineKeyboardButton("Stop Alerts", callback_data="stop_alerts")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🐋 Welcome to Multi-Chain Whale Tracker!\n\n"
        "Get notified when large cryptocurrency transfers happen on Ethereum, Polygon, and Arbitrum.\n\n"
        "Commands: /set, /status, /stop, /resume",
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

def add_handlers_to_app(app):
    app.add_handler(CommandHandler(["set", "set_filter"], set_filter))
    app.add_handler(CommandHandler("status", get_filter_status))
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("stop", stop_command))
    app.add_handler(CommandHandler("resume", resume_command))
    app.add_handler(CallbackQueryHandler(button_callback))

def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN_2).build()
    add_handlers_to_app(app)

    print("🐋 Telegram Whale Tracker Bot started!")
    print("Available commands: /start, /set, /status")
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