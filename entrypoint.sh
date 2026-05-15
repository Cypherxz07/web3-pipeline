#!/bin/sh
set -e
cd /app
export PYTHONPATH=/app:$PYTHONPATH

PYTHON_BIN="$(command -v python || true)"
if [ -z "$PYTHON_BIN" ]; then
  PYTHON_BIN="/opt/venv/bin/python"
fi

echo "🐋 Starting web3-pipeline..."
echo "🐋 Python binary: $PYTHON_BIN"
echo "🐋 Python version: $($PYTHON_BIN --version)"
echo "🐋 Python path: $($PYTHON_BIN -c 'import sys; print(sys.executable)')"
echo "🐋 Current directory: $(pwd)"
echo "🐋 Files in directory: $(ls -la)"

# Test basic Python import
echo "🐋 Testing basic Python..."
"$PYTHON_BIN" -c "import sys; print('Python works'); print('Python path:', sys.path[:3])"

# Test Flask import
echo "🐋 Testing Flask import..."
"$PYTHON_BIN" -c "import flask; print('Flask version:', flask.__version__)" || echo "Flask import failed"

# Always generate config.py from environment variables to ensure Cloud Run env vars are used
cat > /app/config.py <<'EOF'
import os

ETHERSCAN_API_KEY = os.getenv('ETHERSCAN_API_KEY', '')
ALCHEMY_RPC_URL = os.getenv('ALCHEMY_RPC_URL', '')
INFURA_PROJECT_ID = os.getenv('INFURA_PROJECT_ID', '')
ETHEREUM_RPC_URL = os.getenv('ETHEREUM_RPC_URL', '')
POLYGON_RPC_URL = os.getenv('POLYGON_RPC_URL', '')
ARBITRUM_RPC_URL = os.getenv('ARBITRUM_RPC_URL', '')
TELEGRAM_BOT_TOKEN_2 = os.getenv('TELEGRAM_BOT_TOKEN_2', '')
TELEGRAM_BOT_TOKEN = TELEGRAM_BOT_TOKEN_2
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
DUNE_API_KEY = os.getenv('DUNE_API_KEY', '')

WHALE_TRACKER_THRESHOLD_USD = int(os.getenv('WHALE_TRACKER_THRESHOLD_USD', '1000000'))
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

echo "🐋 Config generated from environment variables"
echo "🐋 PORT=${PORT:-5000}"
echo "🐋 Starting Flask app..."

# Start the Flask app with explicit error handling
exec "$PYTHON_BIN" -u whale_tracker/whale_api.py 2>&1
