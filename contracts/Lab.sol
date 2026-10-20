// SPDX-License-Identifier: MIT
pragma solidity 0.8.19;

/// @notice Educational token: only the deployer may mint. Never use for real value.
contract LabToken {
    string public name;
    string public symbol;
    uint8 public constant decimals = 18;
    uint256 public totalSupply;
    address public immutable owner = msg.sender;
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;
    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);
    constructor(string memory s) { name = string.concat("Lab ", s); symbol = s; }
    function mint(address to, uint256 value) external {
        require(msg.sender == owner && to != address(0), "mint denied");
        totalSupply += value; balanceOf[to] += value; emit Transfer(address(0), to, value);
    }
    function approve(address spender, uint256 value) external returns (bool) {
        allowance[msg.sender][spender] = value; emit Approval(msg.sender, spender, value); return true;
    }
    function transfer(address to, uint256 value) external returns (bool) { _transfer(msg.sender, to, value); return true; }
    function transferFrom(address from, address to, uint256 value) external returns (bool) {
        uint256 allowed = allowance[from][msg.sender];
        if (allowed != type(uint256).max) { allowance[from][msg.sender] = allowed - value; }
        _transfer(from, to, value); return true;
    }
    function _transfer(address from, address to, uint256 value) internal {
        require(to != address(0), "zero recipient");
        balanceOf[from] -= value; balanceOf[to] += value; emit Transfer(from, to, value);
    }
}

interface IERC20Lab {
    function balanceOf(address) external view returns(uint256);
    function approve(address,uint256) external returns(bool);
    function transfer(address,uint256) external returns(bool);
}
interface IPoolLab {
    function flashLoanSimple(address,address,uint256,bytes calldata,uint16) external;
}
interface IRouterLab {
    function swapExactTokensForTokens(uint256,uint256,address[] calldata,address,uint256) external returns(uint256[] memory);
}

/// @notice Fixed-price oracle for the isolated educational Aave market only.
contract LabOracle {
    function getAssetPrice(address) external pure returns(uint256) { return 1e8; }
    function getAssetsPrices(address[] calldata assets) external pure returns(uint256[] memory prices) {
        prices = new uint256[](assets.length);
        for(uint256 i; i < assets.length; i++) prices[i] = 1e8;
    }
    function BASE_CURRENCY() external pure returns(address) { return address(0); }
    function BASE_CURRENCY_UNIT() external pure returns(uint256) { return 1e8; }
}

/// @notice Borrow A, swap A->B on router 1, B->A on router 2, repay principal+fee atomically.
contract FlashArbitrage {
    address public immutable owner = msg.sender;
    address public immutable pool;
    address public immutable router1;
    address public immutable router2;
    bool private active;
    uint256 private initialBalance;
    event Executed(address indexed asset, uint256 amount, uint256 premium, uint256 profit);
    constructor(address p, address r1, address r2) { pool=p; router1=r1; router2=r2; }
    function run(address asset, address intermediate, uint256 amount, uint256 minB, uint256 minA, uint256 minProfit, uint256 deadline) external {
        require(msg.sender == owner && !active, "owner/active");
        require(asset != intermediate && amount > 0, "invalid trade");
        active = true;
        initialBalance = IERC20Lab(asset).balanceOf(address(this));
        IPoolLab(pool).flashLoanSimple(address(this), asset, amount, abi.encode(intermediate,minB,minA,minProfit,deadline), 0);
        active = false;
    }
    function executeOperation(address asset,uint256 amount,uint256 premium,address initiator,bytes calldata params) external returns(bool) {
        require(msg.sender == pool && initiator == address(this) && active, "unauthorized callback");
        (address mid,uint256 minB,uint256 minA,uint256 minProfit,uint256 deadline) = abi.decode(params,(address,uint256,uint256,uint256,uint256));
        address[] memory path = new address[](2); path[0]=asset; path[1]=mid;
        require(IERC20Lab(asset).approve(router1, amount), "approve 1");
        uint256[] memory first = IRouterLab(router1).swapExactTokensForTokens(amount,minB,path,address(this),deadline);
        path[0]=mid; path[1]=asset;
        require(IERC20Lab(mid).approve(router2, first[1]), "approve 2");
        IRouterLab(router2).swapExactTokensForTokens(first[1],minA,path,address(this),deadline);
        uint256 end = IERC20Lab(asset).balanceOf(address(this));
        require(end >= initialBalance + amount + premium + minProfit, "unprofitable");
        uint256 profit = end - initialBalance - amount - premium;
        require(IERC20Lab(asset).approve(pool,amount+premium), "approve repayment");
        emit Executed(asset,amount,premium,profit);
        return true;
    }
    function withdraw(address asset) external {
        require(msg.sender == owner && !active, "owner/active");
        require(IERC20Lab(asset).transfer(owner,IERC20Lab(asset).balanceOf(address(this))), "transfer");
    }
}
