// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

// ================================================
// IMPORTS
// ================================================
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

/*
 * Interfaces for Aave V2 Flash Loans.
 * In production, please verify the interface with the latest Aave documentation.
 */
interface IPool {
    function flashLoan(
        address receiverAddress,
        address[] calldata assets,
        uint256[] calldata amounts,
        uint256[] calldata modes,  // 0: no debt (flash loan), 1: stable, 2: variable
        address onBehalfOf,
        bytes calldata params,
        uint16 referralCode
    ) external;
}

interface IFlashLoanReceiver {
    function executeOperation(
        address[] calldata assets, 
        uint256[] calldata amounts,
        uint256[] calldata premiums, 
        address initiator, 
        bytes calldata params
    ) external returns (bool);
}

// ================================================
// FLASH LOAN ARBITRAGE CONTRACT
// ================================================
contract FlashLoanArbitrage is IFlashLoanReceiver, ReentrancyGuard {
    // Address of the liquidity pool (e.g. Aave V2 Pool)
    IPool public pool;
    // Owner of the contract (for administrative tasks)
    address public owner;

    // ================================================
    // EVENTS (optional, for easier off-chain monitoring)
    // ================================================
    event FlashLoanInitiated(address[] assets, uint256[] amounts);
    event ArbitrageExecuted(address initiator, uint256[] premiums);
    event Withdrawal(address token, uint256 amount);

    // ================================================
    // CONSTRUCTOR
    // ================================================
    constructor(address _pool) {
        pool = IPool(_pool);
        owner = msg.sender;
    }

    // ================================================
    // FUNCTION: Execute Flash Loan
    // -----------------------------------------------
    // Initiates a flash loan by calling the pool's flashLoan function.
    // _assets: Array of token addresses to borrow.
    // _amounts: Array of amounts for each token.
    // _params: Encoded parameters that can be used in the arbitrage logic.
    // ================================================
    function executeFlashLoan(
        address[] calldata _assets, 
        uint256[] calldata _amounts, 
        bytes calldata _params
    ) external nonReentrant {
        // For a flash loan, all modes should be 0 (no debt).
        uint256[] memory modes = new uint256[](_assets.length);
        for (uint i = 0; i < _assets.length; i++) {
            modes[i] = 0;
        }
        
        // Initiate the flash loan.
        pool.flashLoan(
            address(this),
            _assets,
            _amounts,
            modes,
            address(this),
            _params,
            0  // referralCode (set to 0 if none)
        );
        
        emit FlashLoanInitiated(_assets, _amounts);
    }

    // ================================================
    // CALLBACK: executeOperation
    // -----------------------------------------------
    // This function is called by the pool after the funds are sent.
    // The function must perform the arbitrage/trading logic and ensure repayment.
    // ================================================
    function executeOperation(
        address[] calldata _assets,
        uint256[] calldata _amounts,
        uint256[] calldata _premiums,
        address _initiator,
        bytes calldata _params
    ) external override returns (bool) {
        // Ensure that only the pool can call this function and that the initiator is this contract.
        require(msg.sender == address(pool), "Caller must be the pool");
        require(_initiator == address(this), "Not initiated by this contract");

        // ===================================================
        // PLACE YOUR ARBITRAGE/TRADE LOGIC HERE:
        // ===================================================
        // Example:
        // 1. Swap borrowed tokens across different exchanges.
        // 2. Capture the price difference (spread).
        // 3. Ensure that after the trade, the contract has enough funds to repay _amounts + _premiums.
        //
        // IMPORTANT: If any step fails (insufficient profit, slippage, execution error), 
        // the transaction must revert. This ensures atomicity (only gas fees are lost).
        //
        // For this example, we assume the trade is successful.
        // ---------------------------------------------------
        
        // Example (pseudo-code):
        // require(executeArbitrage(_assets, _amounts, _params), "Arbitrage failed");

        // ===================================================
        // Repay the flash loan: Approve the pool to pull the owed amount.
        // ===================================================
        for (uint i = 0; i < _assets.length; i++) {
            uint256 amountOwed = _amounts[i] + _premiums[i];
            IERC20(_assets[i]).approve(address(pool), amountOwed);
        }
        
        emit ArbitrageExecuted(_initiator, _premiums);
        return true;
    }

    // ================================================
    // ADMIN FUNCTION: Withdraw tokens
    // -----------------------------------------------
    // In case tokens are mistakenly sent to this contract, allow the owner to withdraw them.
    // ================================================
    function withdrawToken(address _token, uint256 _amount) external {
        require(msg.sender == owner, "Only owner can withdraw");
        IERC20(_token).transfer(owner, _amount);
        emit Withdrawal(_token, _amount);
    }

    // ================================================
    // ADMIN FUNCTION: Update the pool address
    // -----------------------------------------------
    // Allows the owner to update the pool address if needed.
    // ================================================
    function updatePool(address _newPool) external {
        require(msg.sender == owner, "Only owner");
        pool = IPool(_newPool);
    }
}
