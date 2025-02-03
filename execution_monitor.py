import os
import sys
import time
import json
import logging
from web3 import Web3
from web3.middleware import geth_poa_middleware
from web3.exceptions import TransactionNotFound

# Configure logging for detailed audit trails.
logging.basicConfig(
    filename="execution_logs.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger()

# Configuration: replace these with your settings.
INFURA_URL = "https://mainnet.infura.io/v3/YOUR_INFURA_PROJECT_ID"
FLASHLOAN_CONTRACT_ADDRESS = "0xYourFlashLoanContractAddress"
ABI_FILE = "FlashLoanArbitrageABI.json"
DEFAULT_ACCOUNT = "0xYourWalletAddress"
PRIVATE_KEY = os.environ.get("PRIVATE_KEY")
if PRIVATE_KEY is None:
    logger.error("PRIVATE_KEY environment variable not set.")
    sys.exit(1)

# Initialize Web3
web3 = Web3(Web3.HTTPProvider(INFURA_URL))
# Use middleware if you are on a POA network:
# web3.middleware_onion.inject(geth_poa_middleware, layer=0)
if not web3.isConnected():
    logger.error("Web3 not connected.")
    sys.exit(1)
web3.eth.defaultAccount = Web3.toChecksumAddress(DEFAULT_ACCOUNT)

# Load contract ABI
try:
    with open(ABI_FILE, "r") as f:
        flashloan_abi = json.load(f)
except Exception as e:
    logger.error(f"Failed to load ABI: {e}")
    sys.exit(1)
flashloan_contract = web3.eth.contract(
    address=Web3.toChecksumAddress(FLASHLOAN_CONTRACT_ADDRESS),
    abi=flashloan_abi
)

def send_flashloan_transaction(assets, amounts, params):
    """Builds, signs, sends, and monitors a flash loan transaction."""
    nonce = web3.eth.getTransactionCount(web3.eth.defaultAccount)
    tx = flashloan_contract.functions.executeFlashLoan(assets, amounts, params).buildTransaction({
        'chainId': web3.eth.chainId,
        'gas': 800000,
        'gasPrice': web3.eth.gas_price,
        'nonce': nonce,
    })
    try:
        estimated_gas = web3.eth.estimateGas(tx)
        logger.debug(f"Estimated Gas: {estimated_gas}")
    except Exception as e:
        logger.error(f"Gas estimation failed: {e}")
        sys.exit(1)
    signed_tx = web3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    try:
        tx_hash = web3.eth.sendRawTransaction(signed_tx.rawTransaction)
        logger.info(f"Transaction sent: {tx_hash.hex()}")
    except Exception as e:
        logger.error(f"Transaction submission failed: {e}")
        sys.exit(1)

    start_time = time.time()
    receipt = None
    while True:
        try:
            receipt = web3.eth.getTransactionReceipt(tx_hash)
            if receipt is not None:
                break
        except TransactionNotFound:
            pass
        time.sleep(5)
    end_time = time.time()
    logger.info(f"Transaction mined in {end_time - start_time:.2f} seconds, receipt: {receipt}")
    return receipt

def monitor_events():
    """Listens to on-chain events emitted by the flash loan contract."""
    event_filter = flashloan_contract.events.ArbitrageExecuted.createFilter(fromBlock='latest')
    logger.info("Monitoring flash loan contract events...")
    while True:
        for event in event_filter.get_new_entries():
            logger.info(f"Event detected: {event}")
        time.sleep(10)

if __name__ == "__main__":
    # Example: Serialize arbitrage parameters.
    # (These should be produced by your arbitrage detection logic.)
    routerA = Web3.toChecksumAddress("0xRouterAAddress")
    routerB = Web3.toChecksumAddress("0xRouterBAddress")
    minTokenAOut = 1 * 10**18  # Example: 1 token A (in wei)
    deadline = int(time.time()) + 300  # 5 minutes from now.
    tokenA = Web3.toChecksumAddress("0xTokenAAddress")
    tokenB = Web3.toChecksumAddress("0xTokenBAddress")
    pathA = [tokenA, tokenB]
    pathB = [tokenB, tokenA]
    params = web3.eth.abi.encode_abi(
        ["address", "address", "uint256", "uint256", "address[]", "address[]"],
        [routerA, routerB, minTokenAOut, deadline, pathA, pathB]
    )
    assets = [tokenA]
    amounts = [1 * 10**18]

    # Trigger the flash loan transaction.
    receipt = send_flashloan_transaction(assets, amounts, params)
    print("Transaction Receipt:", receipt)

    # Optionally, run event monitoring in a separate thread/process.
    # monitor_events()
