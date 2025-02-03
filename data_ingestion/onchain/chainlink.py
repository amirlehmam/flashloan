from web3 import Web3
import asyncio
import logging

# Connect to Ethereum via Infura (update YOUR_INFURA_PROJECT_ID)
infura_url = "https://mainnet.infura.io/v3/58d60a83e2b34cdc854a390914f88304"
web3 = Web3(Web3.HTTPProvider(infura_url))

# Chainlink Aggregator for ETH/USD (example address; update as needed)
aggregator_address = "0x5f4ec3df9cbd43714fe2740f5e3616155c5b8419"
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
        price = round_data[1] / 1e8  # Chainlink scales price by 10^8
        timestamp = round_data[3]
        return {
            "asset": "ETH-USD",
            "price": price,
            "volume": 0,  # Volume not provided by aggregator
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
            logging.info(f"Real Chainlink data: {data}")
            if queue:
                await queue.put(data)
        await asyncio.sleep(5)  # Adjust polling frequency as needed
