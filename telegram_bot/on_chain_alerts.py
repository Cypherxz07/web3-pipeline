import asyncio
from config import TELEGRAM_BOT_TOKEN_2, TELEGRAM_CHAT_ID
from telegram import Bot

CHAIN_EXPLORERS = {
    'ethereum': 'etherscan.io',
    'polygon': 'polygonscan.com',
    'arbitrum': 'arbiscan.io'
}

async def send_whale_alert(transfer, threshold, chat_id):
    """Send whale transfer alert to Telegram"""
    bot = Bot(token=TELEGRAM_BOT_TOKEN_2)
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

def load_filters():
    import json, os
    filters_file = os.path.join(os.path.dirname(__file__), '../whale_tracker/user_filters.json')
    if os.path.exists(filters_file):
        with open(filters_file) as f:
            return json.load(f)
    return {}

async def alert(transfer, threshold):
    filters = load_filters()
    if not filters:
        print("Telegram alert skipped: no filter set. Use /set <chain> <min_amount> to enable alerts.")
        return False

    sent_any = False
    for chat_id, user_filter in filters.items():
        if transfer['chain'] != user_filter.get('chain', 'ethereum'):
            continue
        if transfer['amount_usd'] < user_filter.get('min_amount', threshold):
            continue

        await send_whale_alert(transfer, threshold, chat_id)
        sent_any = True

    return sent_any