# Flashloan Arbitrage Data Ingestion & Preprocessing

This repository contains the Data Ingestion & Preprocessing module for our flash loan arbitrage project. It collects real‑time market data from multiple exchanges (Binance, Coinbase, Kraken) via WebSocket connections and simulates on‑chain price feeds (e.g., Chainlink). Incoming data is normalized into a standard format for further processing by the arbitrage detection engine.

## Features

- **Exchange APIs:** Connects to Binance, Coinbase, and Kraken WebSocket feeds.
- **On‑Chain Data Simulation:** Simulates periodic price feed retrieval (e.g., Chainlink).
- **Data Normalization:** Standardizes data from different sources to a common schema.
- **Asynchronous Processing:** Uses `asyncio` for non‑blocking data ingestion.
- **Logging:** Provides real‑time logs of the ingested and normalized data.

## Prerequisites

- Python 3.8+
- Dependencies listed in `requirements.txt`

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/flashloan-arbitrage.git
   cd flashloan-arbitrage

## Repository Structure

```plaintext
flashloan-arbitrage/
├── docs/
├── models/
├── data_ingestion/
│   ├── __init__.py
│   ├── main.py
│   ├── exchanges/
│   │   ├── __init__.py
│   │   ├── binance.py
│   │   ├── coinbase.py
│   │   └── kraken.py
│   └── onchain/
│       ├── __init__.py
│       └── chainlink.py
├── arbitrage_detection/
│   ├── __init__.py
│   └── engine.py
├── smart_contract/
│   ├── contracts/
│   │   └── FlashLoanArbitrage.sol
│   ├── migrations/
│   │   └── deploy_contracts.js
│   ├── tests/
│   │   └── test_flashloan.js
│   └── truffle-config.js
├── integration/
│   ├── __init__.py
│   └── trigger.py
├── monitoring/
│   ├── __init__.py
│   └── dashboard.py
├── backtesting/
│   ├── __init__.py
│   └── backtest.py
├── risk_management/
│   ├── __init__.py
│   └── risk.py
├── utils/
│   ├── __init__.py
│   └── normalization.py
├── requirements.txt
├── integration.py
├── integration_trigger.py
├── execution_monitor.py
├── dashboard.py
├── docker-compose.yml
└── README.md

```

## Final Integration & Usage

1. **Deploy and Run:**
- Deploy your smart contract and note its address.
- Run your off‑chain monitoring module (execution_monitor.py) to capture and log transaction details and on‑chain events.
- Start the dashboard with:
streamlit run dashboard.py

2. **Monitoring & Logging:**
- The execution_logs.log file will contain a detailed audit trail of your transaction execution.
- On‑chain events from your flash loan contract (such as ArbitrageExecuted) can be monitored by your off‑chain module and stored as needed.
