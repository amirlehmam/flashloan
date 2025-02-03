import asyncio
import json
import logging
import websockets
from utils.normalization import normalize_data

# Binance WebSocket URL for all market tickers
BINANCE_WS_URL = "wss://stream.binance.com:9443/ws/!ticker@arr"

async def process_message(message: str):
    try:
        data = json.loads(message)
        # Normalize the data using our utility function
        normalized = normalize_data('binance', data)
        logging.info(f"Binance data: {normalized}")
    except Exception as e:
        logging.error(f"Error processing Binance message: {e}")

async def start_stream():
    try:
        async with websockets.connect(BINANCE_WS_URL) as websocket:
            logging.info("Connected to Binance WebSocket")
            async for message in websocket:
                # Process each incoming message asynchronously
                asyncio.create_task(process_message(message))
    except Exception as e:
        logging.error(f"Binance stream error: {e}")
