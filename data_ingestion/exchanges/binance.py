import asyncio
import json
import logging
import websockets
from utils.normalization import normalize_data

BINANCE_WS_URL = "wss://stream.binance.com:9443/ws/!ticker@arr"

async def process_message(message: str, queue=None):
    try:
        data = json.loads(message)
        normalized = normalize_data('binance', data)
        logging.info(f"Binance data: {normalized}")
        if queue:
            await queue.put(normalized)
    except Exception as e:
        logging.error(f"Error processing Binance message: {e}")

async def start_stream(queue=None):
    try:
        async with websockets.connect(BINANCE_WS_URL) as websocket:
            logging.info("Connected to Binance WebSocket")
            async for message in websocket:
                asyncio.create_task(process_message(message, queue))
    except Exception as e:
        logging.error(f"Binance stream error: {e}")
