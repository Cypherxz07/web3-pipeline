import asyncio
from config import TELEGRAM_BOT_TOKEN_2, TELEGRAM_CHAT_ID
from telegram import Bot

CHAIN_EXPLORERS = {
    'ethereum': 'etherscan.io',
    'polygon': 'polygonscan.com',
    'arbitrum': 'arbiscan.io'
}

async def send_whale_alert(transfer, threshold):
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
    
    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode='Markdown')

def load_filters():
    import json, os
    filters_file = os.path.join(os.path.dirname(__file__), '../whale_tracker/user_filters.json')
    if os.path.exists(filters_file):
        with open(filters_file) as f:
            return json.load(f)
    return {}

async def alert(transfer, threshold):
    filters = load_filters()
    user_filter = filters.get(str(TELEGRAM_CHAT_ID), {})
    
    if user_filter:
        if transfer['chain'] != user_filter.get('chain', 'ethereum'):
            return
        if transfer['amount_usd'] < user_filter.get('min_amount', threshold):
            return
    
    if transfer['amount_usd'] > threshold:
        await send_whale_alert(transfer, threshold)