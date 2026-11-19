# -*- coding: utf-8 -*-
"""
Compiles Escrow.sol for Tron's TVM and reports each contract's SIZE.

Size matters: deployment cost on Tron is largely proportional to the bytes of code left
on-chain. This makes the difference between the factory (deployed ONCE) and the ephemeral
per-order contract visible at a glance.

    python scripts/compile.py
"""
import json
import os
import sys

import solcx

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(DIR, "..", "contracts", "Escrow.sol")
OUTPUT = os.path.join(DIR, "build.json")

VERSION = "0.8.19"       # do NOT bump to 0.8.20+: it emits PUSH0, unsupported by the TVM
EVM = "istanbul"         # Tron's TVM is compatible up to here


def compile_contracts() -> dict:
    if VERSION not in [str(v) for v in solcx.get_installed_solc_versions()]:
        print(f"Installing solc {VERSION}...")
        solcx.install_solc(VERSION)

    out = solcx.compile_standard(
        {
            "language": "Solidity",
            "sources": {"Escrow.sol": {"content": open(SOURCE, encoding="utf-8").read()}},
            "settings": {
                "optimizer": {"enabled": True, "runs": 200},
                "evmVersion": EVM,
                "outputSelection": {"*": {"*": ["abi", "evm.bytecode", "evm.deployedBytecode"]}},
            },
        },
        solc_version=VERSION,
        allow_paths=os.path.dirname(SOURCE),
    )
    return out["contracts"]["Escrow.sol"]


def main() -> int:
    try:
        contracts = compile_contracts()
    except Exception as e:
        print(f"Compilation FAILED: {e}")
        return 1

    print(f"Compiled with solc {VERSION} (evmVersion={EVM}, optimizer 200 runs)\n")
    print(f"{'contract':<18} {'on-chain code':>15} {'initcode':>12}")
    print("-" * 49)
    data = {}
    for name, c in contracts.items():
        runtime = len(c["evm"]["deployedBytecode"]["object"]) // 2   # hex -> bytes
        initcode = len(c["evm"]["bytecode"]["object"]) // 2
        data[name] = {
            "abi": c["abi"],
            "bytecode": c["evm"]["bytecode"]["object"],
            "bytes_runtime": runtime,
            "bytes_initcode": initcode,
        }
        print(f"{name:<18} {runtime:>12} B {initcode:>9} B")

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)
    print(f"\nABI + bytecode -> {os.path.basename(OUTPUT)}")

    payout = data.get("OrderPayout", {}).get("bytes_runtime", 0)
    factory = data.get("EscrowFactory", {}).get("bytes_runtime", 0)
    if payout and factory:
        print(f"\nEACH ORDER's contract leaves {payout} B on-chain; the factory (one-time) "
              f"leaves {factory} B — {factory / payout:.0f}x more.")
        print("That is why per-order cost does NOT resemble the cost of deploying the factory.")
    print("\nThis is size only. REAL energy cost is measured by measure_costs.py against Nile.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
