# arbitrage_detection/main.py

import asyncio
import random
import time
from arbitrage_detection.detection import ArbitrageDetector

async def fake_data_producer(queue: asyncio.Queue):
    """
    Simulates incoming normalized data from various exchanges.
    In production, the Data Ingestion module would push real data into this queue.
    """
    exchanges = ['binance', 'coinbase', 'kraken']
    assets = ['BTC-USD', 'ETH-USD']  # Ensure asset symbols are consistent across sources.
    
    while True:
        for asset in assets:
            for exchange in exchanges:
                # Simulate a base price and add a random fluctuation.
                base_price = 50000 if asset == 'BTC-USD' else 3000
                price = base_price * (1 + random.uniform(-0.005, 0.005))  # +/- 0.5% fluctuation
                volume = random.uniform(100, 1000)
                normalized_data = {
                    'exchange': exchange,
                    'asset': asset,
                    'price': price,
                    'volume': volume,
                    'timestamp': time.time()
                }
                await queue.put(normalized_data)
        # Pause briefly before pushing the next round of simulated data.
        await asyncio.sleep(1)

async def data_consumer(queue: asyncio.Queue, detector: ArbitrageDetector):
    """
    Consumes normalized data from the queue and passes it to the arbitrage detector.
    """
    while True:
        normalized_data = await queue.get()
        await detector.update_data(normalized_data)
        queue.task_done()

async def main():
    # Create a shared queue for normalized data.
    data_queue = asyncio.Queue()
    
    # Initialize the arbitrage detector with a spread threshold of 0.5%
    # (Adjust threshold based on your strategy and market conditions.)
    detector = ArbitrageDetector(spread_threshold=0.5, update_interval=2)
    
    # Create tasks for producing data, consuming data, and running detection.
    producer_task = asyncio.create_task(fake_data_producer(data_queue))
    consumer_task = asyncio.create_task(data_consumer(data_queue, detector))
    detection_task = asyncio.create_task(detector.run_detection())
    
    # Run all tasks concurrently.
    await asyncio.gather(producer_task, consumer_task, detection_task)

if __name__ == '__main__':
    asyncio.run(main())