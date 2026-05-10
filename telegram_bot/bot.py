#!/usr/bin/env python3
"""
Standalone Telegram Bot for Whale Tracker
"""
import os
import sys
import asyncio
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

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
            keyboard = [
                [InlineKeyboardButton("Change Filter", callback_data="set_filter")],
                [InlineKeyboardButton("Test Alert", callback_data="test_alert")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                f"✅ Current filter:\nChain: {user_filter['chain'].upper()}\nMinimum amount: ${user_filter['min_amount']:,.0f}",
                reply_markup=reply_markup
            )

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
        [InlineKeyboardButton("Test Alert", callback_data="test_alert")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🐋 Welcome to Multi-Chain Whale Tracker!\n\n"
        "Get notified when large cryptocurrency transfers happen on Ethereum, Polygon, and Arbitrum.",
        reply_markup=reply_markup
    )

async def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN_2).build()
    app.add_handler(CommandHandler(["set", "set_filter"], set_filter))
    app.add_handler(CommandHandler("status", get_filter_status))
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CallbackQueryHandler(button_callback))

    print("🐋 Telegram Whale Tracker Bot started!")
    print("Available commands: /start, /set, /status")
    print("Filter file:", USER_FILTERS_FILE)

    await app.run_polling(stop_signals=())

def run_bot():
    """Run bot in separate thread with its own event loop"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    except Exception as e:
        print(f"❌ Bot error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        loop.close()

if __name__ == "__main__":
    import signal
    import threading
    
    # Run bot in background thread
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Keep main thread alive
    try:
        while True:
            signal.pause()
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")