import asyncio
import logging
import os

from data_ingestion.exchanges import binance, coinbase, kraken
from data_ingestion.onchain import chainlink
from arbitrage_detection.detection import ArbitrageDetector

# Option to use Redis for production-grade messaging
USE_REDIS = os.getenv("USE_REDIS", "false").lower() == "true"

if USE_REDIS:
    import aioredis
    import json

    async def redis_publisher(queue: asyncio.Queue, redis_url="redis://localhost"):
        redis = await aioredis.create_redis_pool(redis_url)
        while True:
            data = await queue.get()
            await redis.publish("market_data", json.dumps(data))
            queue.task_done()

    async def redis_subscriber(detector, redis_url="redis://localhost"):
        redis = await aioredis.create_redis_pool(redis_url)
        res = await redis.subscribe("market_data")
        channel = res[0]
        async for message in channel.iter(encoding="utf-8"):
            data = json.loads(message)
            await detector.update_data(data)
else:
    async def data_consumer(queue: asyncio.Queue, detector: ArbitrageDetector):
        while True:
            normalized_data = await queue.get()
            await detector.update_data(normalized_data)
            queue.task_done()

async def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # Shared queue for normalized market data
    data_queue = asyncio.Queue()

    # Initialize the arbitrage detector with our enhanced settings
    detector = ArbitrageDetector(
        spread_threshold=0.5,
        update_interval=2,
        min_volume=100,
        volatility_factor=1.5,
        history_window=10,
        latency_threshold=6.0
    )

    tasks = [
        asyncio.create_task(binance.start_stream(queue=data_queue)),
        asyncio.create_task(coinbase.start_stream(queue=data_queue)),
        asyncio.create_task(kraken.start_stream(queue=data_queue)),
        asyncio.create_task(chainlink.fetch_real_chainlink_feed(queue=data_queue))
    ]

    if USE_REDIS:
        tasks.append(asyncio.create_task(redis_publisher(data_queue)))
        tasks.append(asyncio.create_task(redis_subscriber(detector)))
    else:
        tasks.append(asyncio.create_task(data_consumer(data_queue, detector)))

    tasks.append(asyncio.create_task(detector.run_detection()))

    await asyncio.gather(*tasks)

if __name__ == '__main__':
    asyncio.run(main())
