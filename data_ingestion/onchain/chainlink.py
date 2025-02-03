import asyncio
import logging
import random
import time
from utils.normalization import normalize_data

async def fetch_price_feed():
    """
    Simulate fetching on-chain data (e.g., from a Chainlink price feed).
    In a production setting, this would involve interacting with a blockchain node via Web3.py.
    """
    while True:
        # Simulated data; replace with real on-chain queries as needed.
        simulated_data = {
            "asset": "BTC-USD",
            "price": 50000 + random.uniform(-100, 100),
            "volume": random.uniform(100, 1000),
            "timestamp": int(time.time())
        }
        normalized = normalize_data('chainlink', simulated_data)
        logging.info(f"Chainlink data: {normalized}")
        await asyncio.sleep(5)  # simulate a 5-second interval between fetches
