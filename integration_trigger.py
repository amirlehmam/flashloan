import os
import sys
import time
import json
from web3 import Web3
from web3.exceptions import TransactionNotFound

# ================================================
# Configuration
# ================================================
# Replace with your Infura (or other provider) URL
INFURA_URL = "https://mainnet.infura.io/v3/YOUR_INFURA_PROJECT_ID"

# Replace with your deployed FlashLoanArbitrage contract address
FLASHLOAN_CONTRACT_ADDRESS = "0xYourFlashLoanContractAddress"

# Path to the ABI JSON file for the flash loan contract
ABI_FILE = "FlashLoanArbitrageABI.json"

# Set your account address and private key (DO NOT hardcode in production!)
DEFAULT_ACCOUNT = "0xYourWalletAddress"
PRIVATE_KEY = os.environ.get("PRIVATE_KEY")
if PRIVATE_KEY is None:
    print("Please set the PRIVATE_KEY environment variable.")
    sys.exit(1)

# ================================================
# Initialize Web3
# ================================================
web3 = Web3(Web3.HTTPProvider(INFURA_URL))
if not web3.isConnected():
    print("Web3 is not connected. Please check your provider URL.")
    sys.exit(1)

# Ensure the default account is set (checksum format)
web3.eth.defaultAccount = Web3.toChecksumAddress(DEFAULT_ACCOUNT)

# ================================================
# Load Contract ABI
# ================================================
try:
    with open(ABI_FILE, "r") as f:
        flashloan_abi = json.load(f)
except Exception as e:
    print(f"Failed to load ABI file: {e}")
    sys.exit(1)

# Create contract instance
flashloan_address = Web3.toChecksumAddress(FLASHLOAN_CONTRACT_ADDRESS)
flashloan_contract = web3.eth.contract(address=flashloan_address, abi=flashloan_abi)

# ================================================
# Function: trigger_flashloan
# ================================================
def trigger_flashloan(
    routerA, routerB, minTokenAOut, deadline,
    pathA, pathB, assets, amounts
):
    """
    Serialize arbitrage parameters, send a transaction to execute flash loan,
    and monitor the transaction status.
    
    Parameters:
      - routerA: Address of first DEX router (e.g., Uniswap V2).
      - routerB: Address of second DEX router (e.g., SushiSwap).
      - minTokenAOut: The minimum acceptable output of token A from the second swap (for slippage protection).
      - deadline: Unix timestamp by which swaps must complete.
      - pathA: List of addresses representing the swap path on routerA (token A -> token B).
      - pathB: List of addresses representing the swap path on routerB (token B -> token A).
      - assets: Array of token addresses to borrow (flash loan assets). For our example, single asset.
      - amounts: Array of amounts for each token to borrow.
    
    Returns:
      - Transaction receipt.
    """
    # Encode arbitrage parameters into bytes.
    # The contract expects the _params to be ABI-encoded as:
    # (address routerA, address routerB, uint256 minTokenAOut, uint256 deadline, address[] pathA, address[] pathB)
    params = web3.eth.abi.encode_abi(
        ["address", "address", "uint256", "uint256", "address[]", "address[]"],
        [routerA, routerB, minTokenAOut, deadline, pathA, pathB]
    )

    # Build the transaction to call executeFlashLoan(assets, amounts, params)
    nonce = web3.eth.getTransactionCount(web3.eth.defaultAccount)
    tx = flashloan_contract.functions.executeFlashLoan(assets, amounts, params).buildTransaction({
        'chainId': web3.eth.chainId,
        'gas': 800000,  # Adjust gas limit as needed.
        'gasPrice': web3.eth.gas_price,
        'nonce': nonce,
    })

    # Optionally: simulate the transaction (gas estimation)
    try:
        estimated_gas = web3.eth.estimateGas(tx)
        print(f"Estimated Gas: {estimated_gas}")
    except Exception as e:
        print(f"Gas estimation failed: {e}")
        sys.exit(1)

    # Sign and send the transaction
    signed_tx = web3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    try:
        tx_hash = web3.eth.sendRawTransaction(signed_tx.rawTransaction)
    except Exception as e:
        print(f"Transaction submission failed: {e}")
        sys.exit(1)
    print("Transaction sent, tx hash:", tx_hash.hex())

    # Monitor transaction status until mined
    print("Waiting for transaction receipt...")
    try:
        receipt = web3.eth.waitForTransactionReceipt(tx_hash, timeout=300)  # 5-minute timeout
    except Exception as e:
        print(f"Error waiting for transaction receipt: {e}")
        sys.exit(1)

    if receipt.status == 1:
        print("Transaction successful!")
    else:
        print("Transaction failed!")
    return receipt

# ================================================
# Main Execution: Example Trigger
# ================================================
if __name__ == "__main__":
    # Example parameter values.
    # Replace these with real addresses and values for your use case.
    routerA = Web3.toChecksumAddress("0xRouterAAddress")  # e.g., Uniswap V2 router
    routerB = Web3.toChecksumAddress("0xRouterBAddress")  # e.g., SushiSwap router

    # For slippage protection, set minimum token A received (in wei).
    minTokenAOut = 1 * (10 ** 18)  # e.g., 1 token A

    # Set deadline to 5 minutes from now.
    deadline = int(time.time()) + 300

    # Set swap paths.
    # Example: token A -> token B on routerA; token B -> token A on routerB.
    tokenA = Web3.toChecksumAddress("0xTokenAAddress")
    tokenB = Web3.toChecksumAddress("0xTokenBAddress")
    pathA = [tokenA, tokenB]
    pathB = [tokenB, tokenA]

    # Flash loan asset and amount. For a single asset flash loan.
    assets = [tokenA]
    amounts = [1 * (10 ** 18)]  # Borrow 1 token A (in wei)

    # Trigger the flash loan arbitrage transaction.
    receipt = trigger_flashloan(routerA, routerB, minTokenAOut, deadline, pathA, pathB, assets, amounts)
    print("Transaction Receipt:", receipt)
