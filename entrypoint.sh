#!/bin/sh
cd /app
export PYTHONPATH=/app:$PYTHONPATH
if [ ! -f /app/config.py ]; then
  cat > /app/config.py <<'EOF'
import os

ETHERSCAN_API_KEY = os.getenv('ETHERSCAN_API_KEY', '')
ALCHEMY_RPC_URL = os.getenv('ALCHEMY_RPC_URL', '')
INFURA_PROJECT_ID = os.getenv('INFURA_PROJECT_ID', '')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_BOT_TOKEN_2 = os.getenv('TELEGRAM_BOT_TOKEN_2', '')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
DUNE_API_KEY = os.getenv('DUNE_API_KEY', '')

WHALE_TRACKER_THRESHOLD_USD = int(os.getenv('WHALE_TRACKER_THRESHOLD_USD', '1'))
WHALE_TRACKER_POLL_INTERVAL = int(os.getenv('WHALE_TRACKER_POLL_INTERVAL', '20'))
WHALE_TRACKER_DB_URL = os.getenv('WHALE_TRACKER_DB_URL', 'sqlite:///whale_tracker.db')
WHALE_TRACKER_TRACKED_TOKENS = {
    '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48': 'USDC',
    '0xC02aaA39b223FE8D0A0e8e4F27ead9083C756Cc2': 'WETH',
    '0xdAC17F958D2ee523a2206206994597C13D831ec7': 'USDT',
    '0x2260fac5e5542a773aa44fbcfedf7c193bc2c599': 'WBTC',
    '0x1f9840a85d5af5bf1d1762f925bdaddc4201f984': 'UNI',
}
EOF
fi
python whale_tracker/whale_api.py
