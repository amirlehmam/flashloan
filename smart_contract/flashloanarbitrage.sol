// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

// =====================================================
// IMPORTS
// =====================================================
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

/*
 * Interfaces for Aave V2 Flash Loans.
 * Ensure you check with the latest Aave documentation for any interface changes.
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
// FLASH LOAN ARBITRAGE CONTRACT
// =====================================================
contract FlashLoanArbitrage is IFlashLoanReceiver, ReentrancyGuard {
    // -----------------------------------------------------
    // State Variables
    // -----------------------------------------------------
    IPool public pool;          // Address of the flash loan pool (e.g., Aave V2)
    address public owner;       // Contract owner (for administrative functions)

    // -----------------------------------------------------
    // Events (for on-chain logging & off-chain monitoring)
    // -----------------------------------------------------
    event FlashLoanInitiated(address[] assets, uint256[] amounts);
    event ArbitrageExecuted(address indexed initiator, uint256[] premiums, uint256 profit);
    event Withdrawal(address token, uint256 amount);

    // -----------------------------------------------------
    // CONSTRUCTOR
    // -----------------------------------------------------
    constructor(address _pool) {
        require(_pool != address(0), "Pool address cannot be zero");
        pool = IPool(_pool);
        owner = msg.sender;
    }

    // =====================================================
    // FUNCTION: executeFlashLoan
    // -----------------------------------------------------
    // Initiates a flash loan by calling the pool's flashLoan function.
    // _assets: Array of token addresses to borrow.
    // _amounts: Array of amounts to borrow for each token.
    // _params: ABI-encoded parameters for arbitrage logic.
    // =====================================================
    function executeFlashLoan(
        address[] calldata _assets, 
        uint256[] calldata _amounts, 
        bytes calldata _params
    ) external nonReentrant {
        require(_assets.length > 0, "Must borrow at least one asset");
        require(_assets.length == _amounts.length, "Assets and amounts mismatch");
        
        // Set all modes to 0 for flash loan (no debt)
        uint256[] memory modes = new uint256[](_assets.length);
        for (uint i = 0; i < _assets.length; i++) {
            modes[i] = 0;
        }
        
        // Initiate flash loan.
        pool.flashLoan(
            address(this),
            _assets,
            _amounts,
            modes,
            address(this),
            _params,
            0  // referralCode (if none, set to 0)
        );
        
        emit FlashLoanInitiated(_assets, _amounts);
    }

    // =====================================================
    // CALLBACK: executeOperation
    // -----------------------------------------------------
    // Called by the pool after funds are sent.
    // Executes arbitrage logic and repays the flash loan (plus fee) within one atomic transaction.
    // =====================================================
    function executeOperation(
        address[] calldata _assets,
        uint256[] calldata _amounts,
        uint256[] calldata _premiums,
        address _initiator,
        bytes calldata _params
    ) external override nonReentrant returns (bool) {
        // Security: Only the pool may call this function.
        require(msg.sender == address(pool), "Caller must be the pool");
        // The initiator must be this contract.
        require(_initiator == address(this), "Initiator must be this contract");

        // -------------------------------------------------
        // Decode Arbitrage Parameters
        // -------------------------------------------------
        // _params is expected to be ABI-encoded as:
        // (address routerA, address routerB, uint256 minTokenAOut, uint256 deadline, address[] pathA, address[] pathB)
        //   - routerA: DEX router for first swap (token A -> token B).
        //   - routerB: DEX router for second swap (token B -> token A).
        //   - minTokenAOut: Minimum acceptable output of token A from the second swap (slippage protection).
        //   - deadline: Unix timestamp by which the swaps must complete.
        //   - pathA: Swap path for routerA (token A -> token B).
        //   - pathB: Swap path for routerB (token B -> token A).
        (address routerA, address routerB, uint256 minTokenAOut, uint256 deadline, address[] memory pathA, address[] memory pathB) =
            abi.decode(_params, (address, address, uint256, uint256, address[], address[]));

        require(block.timestamp <= deadline, "Transaction deadline passed");

        // -------------------------------------------------
        // Assume a single-asset flash loan for token A.
        // -------------------------------------------------
        address tokenA = _assets[0];
        uint256 amountBorrowed = _amounts[0];

        // -------------------------------------------------
        // Step 1: Swap token A for token B on routerA.
        // -------------------------------------------------
        // Approve routerA to spend token A.
        IERC20(tokenA).approve(routerA, amountBorrowed);
        uint256[] memory amountsOutA = IUniswapV2Router02(routerA).swapExactTokensForTokens(
            amountBorrowed,
            1,  // Minimal output; production code should enforce proper slippage limits.
            pathA,
            address(this),
            deadline
        );
        uint256 amountTokenB = amountsOutA[amountsOutA.length - 1];

        // -------------------------------------------------
        // Step 2: Swap token B back to token A on routerB.
        // -------------------------------------------------
        // The last element in pathA is token B.
        address tokenB = pathA[pathA.length - 1];
        IERC20(tokenB).approve(routerB, amountTokenB);
        uint256[] memory amountsOutB = IUniswapV2Router02(routerB).swapExactTokensForTokens(
            amountTokenB,
            minTokenAOut,  // Enforce minimum acceptable token A received.
            pathB,
            address(this),
            deadline
        );
        uint256 amountReceivedTokenA = amountsOutB[amountsOutB.length - 1];

        // -------------------------------------------------
        // Step 3: Check Profitability and Enforce Slippage/Profit Threshold.
        // -------------------------------------------------
        uint256 amountOwed = amountBorrowed + _premiums[0];
        require(amountReceivedTokenA >= amountOwed, "Arbitrage not profitable");
        uint256 profit = amountReceivedTokenA - amountOwed;
        // Optional: enforce a minimum profit threshold.
        // For example: require(profit >= SOME_MIN_PROFIT, "Profit too low");

        // -------------------------------------------------
        // Step 4: Approve Repayment and Repay Flash Loan.
        // -------------------------------------------------
        IERC20(tokenA).approve(address(pool), amountOwed);

        // Emit event with arbitrage result.
        emit ArbitrageExecuted(_initiator, _premiums, profit);

        return true;
    }

    // =====================================================
    // ADMIN FUNCTION: withdrawToken
    // -----------------------------------------------------
    // Allows the owner to withdraw any ERC20 tokens inadvertently sent to this contract.
    // =====================================================
    function withdrawToken(address _token, uint256 _amount) external {
        require(msg.sender == owner, "Only owner can withdraw");
        IERC20(_token).transfer(owner, _amount);
        emit Withdrawal(_token, _amount);
    }

    // =====================================================
    // ADMIN FUNCTION: updatePool
    // -----------------------------------------------------
    // Allows the owner to update the liquidity pool address.
    // =====================================================
    function updatePool(address _newPool) external {
        require(msg.sender == owner, "Only owner can update pool");
        require(_newPool != address(0), "Invalid pool address");
        pool = IPool(_newPool);
    }
}
