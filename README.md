# Web3 Pipeline 🔍

Real-time on-chain analytics scripts built during a 90-day Web3 learning challenge.

## Live Demos
- 🐋 **Whale Tracker Dashboard** → `WEBHOOK_BASE_URL` should be set in production for your deployment URL
- 📊 **USDC Market Intelligence** (Dune) → [dune.com/0xkairo/usdc-market-intelligence](https://dune.com/0xkairo/usdc-market-intelligence)

---

## What This Does

Monitors multiple blockchains in real-time for large on-chain transfers. When a transfer exceeds a custom threshold, it fires a Telegram alert and logs the event to a local SQLite database.

- ⛓️ Multi-chain: Ethereum, Polygon, Arbitrum
- 🚨 Custom alert threshold (configurable per chain)
- 📲 Telegram notifications with tx details
- 🗄️ SQLite logging for historical analysis
- ⏱️ Polls every 12 seconds

---

## Modules

| Folder | Description |
|---|---|
| `basics/` | Ethereum connection, block numbers, wallet balances |
| `fee_monitor/` | Live base fee + gas utilization monitor |
| `whale_transfer_monitor/` | Real-time USDC whale transfer monitor with Etherscan labels |
| `ABI_and_contract_interactions/` | USDC contract reader + whale balance tracker |
| `lending_and_others/` | Aave USDC market health monitor |

---

## Stack

- Python 3.14 + web3.py
- Alchemy & Infura RPC nodes
- Etherscan API V2
- Dune Analytics (SQL dashboards)
- Telegram Bot API
- SQLite

---

## Setup

```bash
git clone https://github.com/Cypherxz07/web3-pipeline.git
cd web3-pipeline
pip install web3 requests
```

Create a `config.py` in the root:

```python
ALCHEMY_RPC_URL = "your_alchemy_url"
ETHERSCAN_API_KEY = "your_etherscan_key"
TELEGRAM_BOT_TOKEN = "your_bot_token"
TELEGRAM_CHAT_ID = "your_chat_id"
ALERT_THRESHOLD_ETH = 100_000  # USD value to trigger alert
```

Run the whale tracker:

```bash
python whale_transfer_monitor/tracker.py
```

---

## Google Cloud Run deployment

This project is ready for Google Cloud Run using the existing `Dockerfile`.

1. Authenticate and select your project:

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

2. Deploy with Cloud Build:

```bash
gcloud builds submit --config cloudbuild.yaml --substitutions _REGION=us-central1,_WEBHOOK_BASE_URL=https://your-cloud-run-url.run.app
```

3. Set production environment variables in Cloud Run for your service:

- `TELEGRAM_BOT_TOKEN_2`
- `TELEGRAM_CHAT_ID`
- `INFURA_PROJECT_ID`
- `ALCHEMY_RPC_URL`
- `ETHERSCAN_API_KEY`
- `WEBHOOK_BASE_URL`

If you want to use Cloud Run without Cloud Build, deploy directly with `gcloud run deploy`.

---

## Screenshots

<img width="400" alt="Telegram alert" src="https://github.com/user-attachments/assets/f825f104-5501-412b-a254-e7bb0e9b7b6c" />
<img width="700" alt="Dashboard" src="https://github.com/user-attachments/assets/90506cde-0fbe-4258-8ba6-dec74f2cd3a8" />


---

Built by [@Isahbless79](https://twitter.com/Isahbless79) · Part of a 90-day Web3 challenge
