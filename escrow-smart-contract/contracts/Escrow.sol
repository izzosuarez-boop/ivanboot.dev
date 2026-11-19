// SPDX-License-Identifier: MIT
//
// ─────────────────────────────────────────────────────────────────────────────────────────────
//  TEST BENCH — non-custodial escrow for a digital-goods marketplace (TRON, USDT TRC-20)
// ─────────────────────────────────────────────────────────────────────────────────────────────
//  This is NOT production code yet: it exists to MEASURE, on Tron's testnet (Nile), what each
//  design option actually costs, and to decide with numbers instead of intuition. See README.md.
//
//  INVARIANT (a constraint set by legal counsel): a buyer's money can only end up at the
//  SELLER or back at the BUYER. The fee goes to a FIXED wallet declared at deployment.
//  There is no general withdrawal function of any kind.
//
//  Both design options under comparison are implemented here:
//    · EscrowFactory  (option A) — one address per order, derived with CREATE2.
//    · SingleEscrow   (option B) — a single contract for all orders.
//
//  IMPORTANT (TVM compatibility): compile with evmVersion "istanbul" or "paris". The PUSH0
//  opcode that solc emits from 0.8.20 onwards is NOT supported by Tron's TVM; hence 0.8.19.
// ─────────────────────────────────────────────────────────────────────────────────────────────
pragma solidity 0.8.19;

interface ITRC20 {
    function transfer(address to, uint256 value) external returns (bool);
    function balanceOf(address who) external view returns (uint256);
}

/// A transfer helper that does NOT trust the token's return value — it verifies the EFFECT.
///
/// USDT does not honor the TRC-20/ERC-20 standard in what `transfer` returns. The usual
/// pattern (OpenZeppelin's SafeERC20) is to accept "no return data" or "returns true":
///
///     require(ok && (data.length == 0 || abi.decode(data, (bool))));
///
/// This contract started with that pattern, and it REVERTED — measured on Nile on 2026-09-06:
/// the test USDT moves the money correctly but returns 32 zero bytes, i.e. `false`. Trusting
/// the return value would have made every single order impossible to settle — and in a
/// token-dependent way.
///
/// So instead we check the recipient's balance before and after: whatever the token claims,
/// what matters is that the money arrived. It costs two extra balance reads; in exchange it
/// works with any token, including the ones that lie in their return value.
library SafeTransfer {
    function send(address token, address to, uint256 amount) internal {
        if (amount == 0) return;
        uint256 before = ITRC20(token).balanceOf(to);
        (bool ok, ) = token.call(
            abi.encodeWithSelector(ITRC20.transfer.selector, to, amount)
        );
        require(ok, "token call failed");
        require(ITRC20(token).balanceOf(to) >= before + amount, "token did not deliver");
    }
}

// ═════════════════════════════════════════════════════════════════════════════════════════════
//  OPTION A — one address per order
// ═════════════════════════════════════════════════════════════════════════════════════════════
//
//  How it works:
//    1. The backend computes `addressOf(orderId, buyer, seller)` — nothing exists on-chain
//       yet, so this costs ZERO.
//    2. The buyer sends USDT to that address from anywhere (including an exchange).
//    3. The backend calls `settle(...)`, which deploys an EPHEMERAL contract there: it splits
//       the money inside its own constructor and leaves no persistent code behind.
//
//  WHY THE SALT BINDS BUYER AND SELLER — this is what makes the guarantee real:
//  the address derives from keccak256(orderId, buyer, seller). If the backend tried to settle
//  the order by sending the money elsewhere, it would have to change those inputs — and then
//  CREATE2 would deploy at a DIFFERENT address, where there isn't a cent. The only freedom the
//  backend keeps is the `release` boolean: seller or buyer. Nothing else.
//  Anyone can recompute the address from public data and verify this.
// ═════════════════════════════════════════════════════════════════════════════════════════════

/// Single-use contract. It deploys, splits the funds inside its constructor, and dies leaving
/// no code behind. It takes no constructor arguments ON PURPOSE: that keeps its initcode
/// identical for every order, so the address depends on the salt alone (Uniswap V3's pattern).
contract OrderPayout {
    constructor() {
        (address usdt, address to, address feeWallet, uint16 bps)
            = EscrowFactory(msg.sender).instructions();

        uint256 balance = ITRC20(usdt).balanceOf(address(this));
        if (balance == 0) return;   // diagnostic: with no funds, don't revert — stay observable
        // Split what ACTUALLY arrived, not what was requested: the buyer's exchange may have
        // deducted its withdrawal fee on the way out (it happened: 23 requested, 21.5 received
        // on a real order). Whether that amount is acceptable is the backend's call, BEFORE
        // calling here.
        uint256 fee = (balance * bps) / 10000;
        if (fee > 0) SafeTransfer.send(usdt, feeWallet, fee);
        SafeTransfer.send(usdt, to, balance - fee);
    }
}

contract EscrowFactory {
    address public immutable USDT;
    address public immutable FEE_WALLET;   // immutable: cannot be redirected to another account
    uint16  public immutable FEE_BPS;      // 1000 = 10%
    address public operator;               // the backend's key

    // Instructions the ephemeral clone reads in its constructor. Written right before the
    // CREATE2 and cleared right after (the delete refunds part of the gas).
    struct Instruction { address usdt; address to; address feeWallet; uint16 bps; }
    Instruction private _instr;

    event OrderSettled(bytes32 indexed orderId, address indexed to, bool released, uint256 balance);
    /// DIAGNOSTIC: the actual address CREATE2 deployed at, to compare against addressOf().
    event CloneDeployed(address clone, address computed);

    modifier onlyOperator() { require(msg.sender == operator, "not authorized"); _; }

    constructor(address usdt, address feeWallet, uint16 feeBps) {
        require(feeWallet != address(0) && feeBps <= 10000, "invalid parameters");
        USDT = usdt;
        FEE_WALLET = feeWallet;
        FEE_BPS = feeBps;
        operator = msg.sender;
    }

    function changeOperator(address next) external onlyOperator {
        require(next != address(0), "invalid operator");
        operator = next;   // lets the backend key rotate without touching where the money goes
    }

    /// Read by the clone's constructor. Public because the clone calls it externally.
    function instructions() external view returns (address, address, address, uint16) {
        return (_instr.usdt, _instr.to, _instr.feeWallet, _instr.bps);
    }

    function _salt(bytes32 orderId, address buyer, address seller) internal pure returns (bytes32) {
        return keccak256(abi.encode(orderId, buyer, seller));
    }

    /// The address the buyer must pay to. Computable without deploying anything (zero cost).
    function addressOf(bytes32 orderId, address buyer, address seller)
        public view returns (address)
    {
        bytes32 h = keccak256(abi.encodePacked(
            bytes1(0x41),                       // Tron uses 0x41 where Ethereum uses 0xff
            address(this),
            _salt(orderId, buyer, seller),
            keccak256(type(OrderPayout).creationCode)
        ));
        return address(uint160(uint256(h)));
    }

    /// DIAGNOSTIC: Tron's TVM does not clearly document how it forms CREATE2 addresses.
    /// This computes the candidate variants so they can be compared against the real address
    /// emitted by CloneDeployed, keeping the right one. To be removed once settled.
    function variants(bytes32 orderId, address buyer, address seller)
        external view returns (address v41, address vFF, address v4141, address vNoPrefix)
    {
        bytes32 salt = _salt(orderId, buyer, seller);
        bytes32 ic = keccak256(type(OrderPayout).creationCode);
        v41  = address(uint160(uint256(keccak256(abi.encodePacked(bytes1(0x41), address(this), salt, ic)))));
        vFF  = address(uint160(uint256(keccak256(abi.encodePacked(bytes1(0xff), address(this), salt, ic)))));
        v4141 = address(uint160(uint256(keccak256(abi.encodePacked(bytes1(0x41), bytes1(0x41), address(this), salt, ic)))));
        vNoPrefix = address(uint160(uint256(keccak256(abi.encodePacked(address(this), salt, ic)))));
    }

    /// Deploys the ephemeral contract at the order's address and splits the money.
    /// `release = true`  → fee to the fixed wallet + the rest to the seller.
    /// `release = false` → 100% back to the buyer (no fee charged).
    function settle(bytes32 orderId, address buyer, address seller, bool release)
        external onlyOperator
    {
        address to = release ? seller : buyer;
        _instr = Instruction({
            usdt: USDT,
            to: to,
            feeWallet: FEE_WALLET,
            bps: release ? FEE_BPS : 0      // a refund carries NO fee
        });

        bytes32 salt = _salt(orderId, buyer, seller);
        address clone = address(new OrderPayout{salt: salt}());

        delete _instr;   // clean up and refund part of the gas
        emit CloneDeployed(clone, addressOf(orderId, buyer, seller));
        emit OrderSettled(orderId, to, release, ITRC20(USDT).balanceOf(clone));
    }
}

// ═════════════════════════════════════════════════════════════════════════════════════════════
//  OPTION B — a single contract for all orders
// ═════════════════════════════════════════════════════════════════════════════════════════════
//  Every buyer pays to THE SAME address, so the contract cannot know whose deposit is whose
//  (a contract cannot read chain logs). The backend — which does see the chain from outside,
//  via TronGrid — has to tell it.
//
//  What the contract DOES guarantee: no more money can be registered than it actually holds
//  (the `totalCommitted <= balance` invariant), and the destinations remain only seller,
//  buyer, or the fixed fee wallet.
//  What it does NOT guarantee: that the split BETWEEN orders is correct. That's on the backend.
// ═════════════════════════════════════════════════════════════════════════════════════════════
contract SingleEscrow {
    address public immutable USDT;
    address public immutable FEE_WALLET;
    uint16  public immutable FEE_BPS;
    address public operator;

    struct Order { address buyer; address seller; uint256 amount; uint8 state; }  // 0=none,1=registered,2=released,3=refunded
    mapping(bytes32 => Order) public orders;
    uint256 public totalCommitted;

    modifier onlyOperator() { require(msg.sender == operator, "not authorized"); _; }

    constructor(address usdt, address feeWallet, uint16 feeBps) {
        require(feeWallet != address(0) && feeBps <= 10000, "invalid parameters");
        USDT = usdt; FEE_WALLET = feeWallet; FEE_BPS = feeBps;
        operator = msg.sender;
    }

    function registerDeposit(bytes32 orderId, address buyer, address seller, uint256 amount)
        public onlyOperator
    {
        require(orders[orderId].state == 0, "already registered");
        // PREVENTS invented deposits: you cannot commit money the contract does not hold.
        require(totalCommitted + amount <= ITRC20(USDT).balanceOf(address(this)), "insufficient balance");
        orders[orderId] = Order(buyer, seller, amount, 1);
        totalCommitted += amount;
    }

    function release(bytes32 orderId) public onlyOperator {
        Order storage o = orders[orderId];
        require(o.state == 1, "invalid state");
        o.state = 2;
        totalCommitted -= o.amount;
        uint256 fee = (o.amount * FEE_BPS) / 10000;
        if (fee > 0) SafeTransfer.send(USDT, FEE_WALLET, fee);
        SafeTransfer.send(USDT, o.seller, o.amount - fee);
    }

    function refund(bytes32 orderId) public onlyOperator {
        Order storage o = orders[orderId];
        require(o.state == 1, "invalid state");
        o.state = 3;
        totalCommitted -= o.amount;
        SafeTransfer.send(USDT, o.buyer, o.amount);
    }

    /// The real advantage of this option: settle N orders in ONE transaction.
    function releaseMany(bytes32[] calldata ids) external onlyOperator {
        for (uint256 i = 0; i < ids.length; i++) release(ids[i]);
    }
}

// ═════════════════════════════════════════════════════════════════════════════════════════════
//  Test token (testnet ONLY). Mimics USDT, including its no-return-value `transfer`.
// ═════════════════════════════════════════════════════════════════════════════════════════════
contract FakeUSDT {
    string public name = "Test USDT";
    uint8  public decimals = 18;          // like BSC's USDT (TRON/Ethereum's uses 6)
    mapping(address => uint256) public balanceOf;

    /// ESSENTIAL: without this event, on-chain verification (eth_getLogs) sees NOTHING.
    /// The first version of this mock didn't emit it, and the BSC test reported 'no_payment'
    /// with the payment already on-chain. Same class of error as trusting a lab token's return
    /// value: if the lab token doesn't behave like the real one, the test validates something
    /// that doesn't exist.
    event Transfer(address indexed from, address indexed to, uint256 value);

    constructor(uint256 supply) {
        balanceOf[msg.sender] = supply;
        emit Transfer(address(0), msg.sender, supply);
    }

    /// No return value, just like real USDT: proves SafeTransfer works with the real token's
    /// behavior and not only with a well-behaved lab token.
    function transfer(address to, uint256 value) external {
        require(balanceOf[msg.sender] >= value, "insufficient balance");
        balanceOf[msg.sender] -= value;
        balanceOf[to] += value;
        emit Transfer(msg.sender, to, value);
    }
}
