import asyncio
import json
import logging
import websockets
from utils.normalization import normalize_data

COINBASE_WS_URL = "wss://ws-feed.pro.coinbase.com"

async def subscribe(ws):
    subscribe_message = {
        "type": "subscribe",
        "channels": [{"name": "ticker", "product_ids": ["BTC-USD", "ETH-USD"]}]
    }
    await ws.send(json.dumps(subscribe_message))
    logging.info("Subscribed to Coinbase ticker feed")

async def process_message(message: str, queue=None):
    try:
        data = json.loads(message)
        normalized = normalize_data('coinbase', data)
        logging.info(f"Coinbase data: {normalized}")
        if queue:
            await queue.put(normalized)
    except Exception as e:
        logging.error(f"Error processing Coinbase message: {e}")

async def start_stream(queue=None):
    try:
        async with websockets.connect(COINBASE_WS_URL) as websocket:
            logging.info("Connected to Coinbase WebSocket")
            await subscribe(websocket)
            async for message in websocket:
                asyncio.create_task(process_message(message, queue))
    except Exception as e:
        logging.error(f"Coinbase stream error: {e}")
