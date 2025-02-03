from web3 import Web3
import asyncio
import logging
import time
from eth_utils import to_checksum_address

# Connect to Ethereum via Infura (update your project ID)
infura_url = "https://mainnet.infura.io/v3/58d60a83e2b34cdc854a390914f88304"
web3 = Web3(Web3.HTTPProvider(infura_url))

aggregator_address_raw = "0x5f4ec3df9cbd43714fe2740f5e3616155c5b8419"
aggregator_address = to_checksum_address(aggregator_address_raw)

abi = [
    {
        "inputs": [],
        "name": "latestRoundData",
        "outputs": [
            {"internalType": "uint80", "name": "roundId", "type": "uint80"},
            {"internalType": "int256", "name": "answer", "type": "int256"},
            {"internalType": "uint256", "name": "startedAt", "type": "uint256"},
            {"internalType": "uint256", "name": "updatedAt", "type": "uint256"},
            {"internalType": "uint80", "name": "answeredInRound", "type": "uint80"}
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

aggregator = web3.eth.contract(address=aggregator_address, abi=abi)

def get_chainlink_price():
    try:
        round_data = aggregator.functions.latestRoundData().call()
        price = round_data[1] / 1e8
        timestamp = round_data[3]
        # If the timestamp is too old (e.g. > 10 seconds), use the current time.
        if abs(time.time() - timestamp) > 10:
            logging.info("Chainlink timestamp is too old; using current time instead.")
            timestamp = time.time()
        return {
            "asset": "ETH-USD",
            "price": price,
            "volume": 0,
            "timestamp": timestamp,
            "exchange": "chainlink"
        }
    except Exception as e:
        logging.error(f"Error fetching Chainlink data: {e}")
        return None

async def fetch_real_chainlink_feed(queue=None):
    while True:
        data = get_chainlink_price()
        if data:
            logging.debug(f"Real Chainlink data: {data}")
            if queue:
                await queue.put(data)
        await asyncio.sleep(5)
