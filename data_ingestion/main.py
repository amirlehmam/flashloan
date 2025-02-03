import asyncio
import logging

# Import stream functions from exchange modules and on-chain module
from data_ingestion.exchanges import binance, coinbase, kraken
from data_ingestion.onchain import chainlink

async def main():
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Create tasks for each data source
    tasks = [
        asyncio.create_task(binance.start_stream()),
        asyncio.create_task(coinbase.start_stream()),
        asyncio.create_task(kraken.start_stream()),
        asyncio.create_task(chainlink.fetch_price_feed())
    ]
    
    # Run all tasks concurrently
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    asyncio.run(main())
