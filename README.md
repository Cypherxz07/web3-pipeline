# Web3 Pipeline

On-chain analytics scripts built during a 90-day Web3 learning journey.

## Contents

- **basics/** — First connection to Ethereum, block numbers, wallet balances
- **fee_monitor/** — Live Ethereum base fee and gas utilization monitor
- **whale_transfer_monitor/** — Real-time USDC whale transfer monitor with Etherscan labels
- **ABI_and_contract_interactions/** — USDC contract reader and whale balance tracker
- **lending_and_others/** — Aave USDC market health monitor

## Stack

- Python + web3.py
- Alchemy RPC node
- Etherscan API V2
- Dune Analytics (SQL dashboards)

## Dashboard

**Whale Tracker** (Real-time Ethereum transfers):
https://web3-pipeline-1.onrender.com/

Live USDC Market Intelligence dashboard:
https://dune.com/0xkairo/usdc-market-intelligence

## Setup

1. Clone the repo
2. Install dependencies: pip install web3 requests
3. Create a config.py file with your own API keys:
ALCHEMY_RPC_URL = "your_alchemy_url"
ETHERSCAN_API_KEY = "your_etherscan_key"
