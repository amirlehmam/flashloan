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

async def process_message(message: str):
    try:
        data = json.loads(message)
        # Kraken sends heartbeat and event messages as dicts; ticker updates as lists.
        if isinstance(data, list):
            normalized = normalize_data('kraken', data)
            logging.info(f"Kraken data: {normalized}")
        else:
            logging.debug(f"Kraken event message: {data}")
    except Exception as e:
        logging.error(f"Error processing Kraken message: {e}")

async def start_stream():
    try:
        async with websockets.connect(KRAKEN_WS_URL) as websocket:
            logging.info("Connected to Kraken WebSocket")
            await subscribe(websocket)
            async for message in websocket:
                asyncio.create_task(process_message(message))
    except Exception as e:
        logging.error(f"Kraken stream error: {e}")
