// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

// =====================================================
// IMPORTS
// =====================================================
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

/*
 * Interfaces for Aave V2 Flash Loans.
 * Check with the latest Aave docs for any updates.
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

/*
 * Minimal interface for Uniswap V2 (or similar) router.
 */
interface IUniswapV2Router02 {
    function swapExactTokensForTokens(
        uint256 amountIn, 
        uint256 amountOutMin, 
        address[] calldata path, 
        address to, 
        uint256 deadline
    ) external returns (uint256[] memory amounts);
}

// =====================================================
// FLASH LOAN ARBITRAGE CONTRACT WITH RISK MANAGEMENT
// =====================================================
contract FlashLoanArbitrage is IFlashLoanReceiver, ReentrancyGuard {
    // -----------------------------------------------------
    // State Variables
    // -----------------------------------------------------
    IPool public pool;            // Address of the flash loan pool (e.g., Aave V2)
    address public owner;         // Contract owner (for administrative functions)
    bool public emergencyStop;    // Circuit breaker to halt operations in abnormal conditions
    uint256 public minProfit;     // Minimum profit (in token A units) required for arbitrage to proceed

    // -----------------------------------------------------
    // Events (for on-chain logging and off-chain monitoring)
    // -----------------------------------------------------
    event FlashLoanInitiated(address[] assets, uint256[] amounts);
    event ArbitrageExecuted(address indexed initiator, uint256[] premiums, uint256 profit);
    event Withdrawal(address token, uint256 amount);
    event EmergencyStopToggled(bool status);
    event MinProfitUpdated(uint256 newMinProfit);

    // -----------------------------------------------------
    // CONSTRUCTOR
    // -----------------------------------------------------
    constructor(address _pool) {
        require(_pool != address(0), "Pool address cannot be zero");
        pool = IPool(_pool);
        owner = msg.sender;
        emergencyStop = false;
        minProfit = 0; // Default minimum profit is zero; can be updated by owner.
    }

    // =====================================================
    // ADMIN FUNCTIONS
    // =====================================================

    // Toggle emergency stop (circuit breaker).
    function toggleEmergencyStop(bool _status) external {
        require(msg.sender == owner, "Only owner can toggle emergency stop");
        emergencyStop = _status;
        emit EmergencyStopToggled(_status);
    }

    // Update the minimum profit threshold.
    function updateMinProfit(uint256 _minProfit) external {
        require(msg.sender == owner, "Only owner can update minProfit");
        minProfit = _minProfit;
        emit MinProfitUpdated(_minProfit);
    }

    // Withdraw tokens mistakenly sent to this contract.
    function withdrawToken(address _token, uint256 _amount) external {
        require(msg.sender == owner, "Only owner can withdraw");
        IERC20(_token).transfer(owner, _amount);
        emit Withdrawal(_token, _amount);
    }

    // Update the flash loan pool address.
    function updatePool(address _newPool) external {
        require(msg.sender == owner, "Only owner can update pool");
        require(_newPool != address(0), "Invalid pool address");
        pool = IPool(_newPool);
    }

    // =====================================================
    // FUNCTION: executeFlashLoan
    // -----------------------------------------------------
    // Initiates a flash loan by calling the pool's flashLoan function.
    // _assets: Array of token addresses to borrow.
    // _amounts: Array of amounts for each token.
    // _params: ABI-encoded parameters for arbitrage logic.
    // =====================================================
    function executeFlashLoan(
        address[] calldata _assets, 
        uint256[] calldata _amounts, 
        bytes calldata _params
    ) external nonReentrant {
        require(!emergencyStop, "Operations halted due to emergency conditions");
        require(_assets.length > 0, "Must borrow at least one asset");
        require(_assets.length == _amounts.length, "Assets and amounts mismatch");
        
        uint256[] memory modes = new uint256[](_assets.length);
        for (uint i = 0; i < _assets.length; i++) {
            modes[i] = 0;
        }
        
        pool.flashLoan(
            address(this),
            _assets,
            _amounts,
            modes,
            address(this),
            _params,
            0 // referralCode (set to 0 if none)
        );
        
        emit FlashLoanInitiated(_assets, _amounts);
    }

    // =====================================================
    // CALLBACK: executeOperation
    // -----------------------------------------------------
    // This function is called by the pool after funds are sent.
    // Executes arbitrage logic and repays the flash loan (plus fee) within one atomic transaction.
    // =====================================================
    function executeOperation(
        address[] calldata _assets,
        uint256[] calldata _amounts,
        uint256[] calldata _premiums,
        address _initiator,
        bytes calldata _params
    ) external override nonReentrant returns (bool) {
        require(!emergencyStop, "Operations halted due to emergency conditions");
        require(msg.sender == address(pool), "Caller must be the pool");
        require(_initiator == address(this), "Initiator must be this contract");

        // -------------------------------------------------
        // Decode Arbitrage Parameters
        // -------------------------------------------------
        // Expected ABI-encoded _params: 
        // (address routerA, address routerB, uint256 minTokenAOut, uint256 deadline, address[] pathA, address[] pathB)
        (address routerA, address routerB, uint256 minTokenAOut, uint256 deadline, address[] memory pathA, address[] memory pathB) =
            abi.decode(_params, (address, address, uint256, uint256, address[], address[]));

        require(block.timestamp <= deadline, "Transaction deadline passed");

        // -------------------------------------------------
        // Single-asset flash loan assumed (token A)
        // -------------------------------------------------
        address tokenA = _assets[0];
        uint256 amountBorrowed = _amounts[0];

        // -------------------------------------------------
        // Step 1: Swap token A for token B on routerA.
        // -------------------------------------------------
        IERC20(tokenA).approve(routerA, amountBorrowed);
        uint256[] memory amountsOutA = IUniswapV2Router02(routerA).swapExactTokensForTokens(
            amountBorrowed,
            1, // Minimal output; production code should set proper slippage limits.
            pathA,
            address(this),
            deadline
        );
        uint256 amountTokenB = amountsOutA[amountsOutA.length - 1];

        // -------------------------------------------------
        // Step 2: Swap token B back to token A on routerB.
        // -------------------------------------------------
        address tokenB = pathA[pathA.length - 1];
        IERC20(tokenB).approve(routerB, amountTokenB);
        uint256[] memory amountsOutB = IUniswapV2Router02(routerB).swapExactTokensForTokens(
            amountTokenB,
            minTokenAOut, // Enforce minimum acceptable token A received.
            pathB,
            address(this),
            deadline
        );
        uint256 amountReceivedTokenA = amountsOutB[amountsOutB.length - 1];

        // -------------------------------------------------
        // Step 3: Check Profitability & Enforce Risk Limits.
        // -------------------------------------------------
        uint256 amountOwed = amountBorrowed + _premiums[0];
        require(amountReceivedTokenA >= amountOwed, "Arbitrage not profitable");
        uint256 profit = amountReceivedTokenA - amountOwed;
        require(profit >= minProfit, "Profit too low to cover risk and gas fees");

        // -------------------------------------------------
        // Step 4: Approve Repayment and Repay Flash Loan.
        // -------------------------------------------------
        IERC20(tokenA).approve(address(pool), amountOwed);

        emit ArbitrageExecuted(_initiator, _premiums, profit);

        return true;
    }
}
