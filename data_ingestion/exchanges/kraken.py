import asyncio
import json
import logging
import websockets
from utils.normalization import normalize_data

KRAKEN_WS_URL = "wss://ws.kraken.com"

async def subscribe(ws):
    subscribe_message = {
        "event": "subscribe",
        "pair": ["XBT/USD", "ETH/USD"],
        "subscription": {"name": "ticker"}
    }
    await ws.send(json.dumps(subscribe_message))
    logging.info("Subscribed to Kraken ticker feed")

async def process_message(message: str, queue=None):
    try:
        logging.debug("Kraken raw message: " + message)
        data = json.loads(message)
        if isinstance(data, list):
            normalized = normalize_data('kraken', data)
            logging.debug(f"Kraken normalized data: {normalized}")
            if queue:
                await queue.put(normalized)
        else:
            logging.debug(f"Kraken event message: {data}")
    except Exception as e:
        logging.error(f"Error processing Kraken message: {e}")

async def start_stream(queue=None):
    try:
        async with websockets.connect(KRAKEN_WS_URL) as websocket:
            logging.info("Connected to Kraken WebSocket")
            await subscribe(websocket)
            async for message in websocket:
                asyncio.create_task(process_message(message, queue))
    except Exception as e:
        logging.error(f"Kraken stream error: {e}")
