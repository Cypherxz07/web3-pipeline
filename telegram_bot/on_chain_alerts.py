import asyncio
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_BOT_TOKEN_2, TELEGRAM_CHAT_ID
from telegram import Bot

# Default cooldown (seconds) between alerts per chat when not set by user
DEFAULT_ALERT_COOLDOWN = 60

BOT_TOKEN = TELEGRAM_BOT_TOKEN_2 or TELEGRAM_BOT_TOKEN

CHAIN_EXPLORERS = {
    'ethereum': 'etherscan.io',
    'polygon': 'polygonscan.com',
    'arbitrum': 'arbiscan.io'
}

async def send_whale_alert(transfer, threshold, chat_id):
    """Send whale transfer alert to Telegram"""
    bot = Bot(token=BOT_TOKEN)
    chain = transfer.get('chain', 'ethereum')
    explorer = CHAIN_EXPLORERS.get(chain, 'etherscan.io')
    
    message = f"""
🐋 **WHALE ALERT** [{chain.upper()}]

Token: {transfer['token_symbol']}
Amount: ${transfer['amount_usd']:,.2f}
From: `{transfer['from'][:6]}...{transfer['from'][-4:]}`
To: `{transfer['to'][:6]}...{transfer['to'][-4:]}`
Tx: https://{explorer}/tx/{transfer['tx_hash']}
Block: {transfer['block']}
"""
    
    await bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')

FILTER_WARNING_LOGGED = False

# Rate limiting: last alert time per chat_id
last_alert_times = {}

def load_filters():
    import json, os
    root_filters = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'user_filters.json'))
    telegram_filters = os.path.normpath(os.path.join(os.path.dirname(__file__), 'user_filters.json'))
    legacy_filters = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'whale_tracker', 'user_filters.json'))

    for path in (root_filters, telegram_filters, legacy_filters):
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)

    global FILTER_WARNING_LOGGED
    if not FILTER_WARNING_LOGGED:
        print(f"No filter file found. Checked: {root_filters}, {telegram_filters}, and {legacy_filters}")
        FILTER_WARNING_LOGGED = True
    return {}

async def alert(transfer, threshold):
    filters = load_filters()
    if not filters:
        return False

    import time
    current_time = time.time()

    sent_any = False
    for chat_id, user_filter in filters.items():
        if transfer['chain'] != user_filter.get('chain', 'ethereum'):
            continue
        if transfer['amount_usd'] < user_filter.get('min_amount', threshold):
            continue
        if not user_filter.get('enabled', True):
            continue

        # Rate limiting - configurable per user
        cooldown_seconds = user_filter.get('cooldown', DEFAULT_ALERT_COOLDOWN)
        last_time = last_alert_times.get(chat_id, 0)
        if current_time - last_time < cooldown_seconds:
            continue  # Skip if too recent

        await send_whale_alert(transfer, threshold, chat_id)
        last_alert_times[chat_id] = current_time
        sent_any = True

    return sent_any