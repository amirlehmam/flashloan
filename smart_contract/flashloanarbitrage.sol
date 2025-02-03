// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

// ================================================
// IMPORTS
// ================================================
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

/*
 * Interfaces for Aave V2 Flash Loans.
 * (Double-check these with the latest Aave documentation.)
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
 * Minimal interface for Uniswap V2 Router (and similar DEXs).
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

// ================================================
// FLASH LOAN ARBITRAGE CONTRACT
// ================================================
contract FlashLoanArbitrage is IFlashLoanReceiver, ReentrancyGuard {
    // --------------------------------------------
    // State Variables
    // --------------------------------------------
    IPool public pool;          // Address of the flash loan pool (e.g., Aave V2 Pool)
    address public owner;       // Owner (for administrative functions)

    // --------------------------------------------
    // Events (for off-chain monitoring)
    // --------------------------------------------
    event FlashLoanInitiated(address[] assets, uint256[] amounts);
    event ArbitrageExecuted(address initiator, uint256[] premiums);
    event Withdrawal(address token, uint256 amount);

    // --------------------------------------------
    // Constructor
    // --------------------------------------------
    constructor(address _pool) {
        pool = IPool(_pool);
        owner = msg.sender;
    }

    // ================================================
    // FUNCTION: executeFlashLoan
    // -----------------------------------------------
    // Initiates a flash loan.
    // _assets: Array of token addresses to borrow.
    // _amounts: Array of amounts for each token.
    // _params: Encoded parameters for arbitrage logic.
    // ================================================
    function executeFlashLoan(
        address[] calldata _assets, 
        uint256[] calldata _amounts, 
        bytes calldata _params
    ) external nonReentrant {
        // For a flash loan, set modes to 0 (no debt).
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
    // Called by the pool after the funds are sent.
    // Executes arbitrage logic and repays the loan.
    // ================================================
    function executeOperation(
        address[] calldata _assets,
        uint256[] calldata _amounts,
        uint256[] calldata _premiums,
        address _initiator,
        bytes calldata _params
    ) external override returns (bool) {
        // Ensure only the pool can call this function and that the initiator is this contract.
        require(msg.sender == address(pool), "Caller must be the pool");
        require(_initiator == address(this), "Initiator must be this contract");

        // ===================================================
        // Decode Arbitrage Parameters
        // ===================================================
        // Expect _params to be ABI encoded as:
        // (address routerA, address routerB, uint256 amountOutMin, address[] pathA, address[] pathB)
        // - routerA: DEX to swap token A for token B.
        // - routerB: DEX to swap token B back to token A.
        // - amountOutMin: Minimum acceptable output of token A from the second swap.
        // - pathA: Swap path for routerA (token A -> token B).
        // - pathB: Swap path for routerB (token B -> token A).
        (address routerA, address routerB, uint256 amountOutMin, address[] memory pathA, address[] memory pathB) =
            abi.decode(_params, (address, address, uint256, address[], address[]));

        // ===================================================
        // Assume the flash loan is for a single asset.
        // _assets[0] is token A.
        // ===================================================
        address tokenA = _assets[0];
        uint256 amountBorrowed = _amounts[0];

        // ===================================================
        // Step 1: Execute the first swap on routerA: token A -> token B.
        // ===================================================
        // Approve routerA to spend token A.
        IERC20(tokenA).approve(routerA, amountBorrowed);

        uint256 deadline = block.timestamp + 300; // 5-minute deadline.
        uint256[] memory amountsOutA = IUniswapV2Router02(routerA).swapExactTokensForTokens(
            amountBorrowed,
            1, // Set minimum output to 1 for demonstration. In production, use proper slippage protection.
            pathA,
            address(this),
            deadline
        );

        // Determine the amount of token B received.
        uint256 amountTokenB = amountsOutA[amountsOutA.length - 1];

        // ===================================================
        // Step 2: Execute the second swap on routerB: token B -> token A.
        // ===================================================
        // The last element of pathA is token B.
        address tokenB = pathA[pathA.length - 1];

        // Approve routerB to spend token B.
        IERC20(tokenB).approve(routerB, amountTokenB);

        uint256[] memory amountsOutB = IUniswapV2Router02(routerB).swapExactTokensForTokens(
            amountTokenB,
            amountOutMin, // Minimum amount of token A expected.
            pathB,
            address(this),
            deadline
        );

        // Determine the amount of token A received after the second swap.
        uint256 amountReceivedTokenA = amountsOutB[amountsOutB.length - 1];

        // ===================================================
        // Step 3: Check Profitability
        // ===================================================
        // Calculate the total amount owed (borrowed amount + premium).
        uint256 amountOwed = amountBorrowed + _premiums[0];

        // Require that the received token A is enough to repay the flash loan.
        require(amountReceivedTokenA >= amountOwed, "Arbitrage not profitable");

        // ===================================================
        // Step 4: Repay the Flash Loan
        // ===================================================
        // Approve the pool to withdraw the owed amount.
        IERC20(tokenA).approve(address(pool), amountOwed);

        // Emit an event indicating successful arbitrage.
        emit ArbitrageExecuted(_initiator, _premiums);

        return true;
    }

    // ================================================
    // ADMIN FUNCTION: Withdraw tokens
    // -----------------------------------------------
    // Allows the owner to withdraw tokens sent accidentally to this contract.
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
