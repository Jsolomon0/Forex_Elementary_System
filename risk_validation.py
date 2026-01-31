"""
risk_validation.py - Validate realized risk per trade vs configuration.
"""

import numpy as np
from backtest_config import BT_RISK_PER_TRADE
import back_test

def run_risk_validation():
    report, trades = back_test.run_simulation_with_trades(verbose=False)
    if not trades:
        print("No trades available for validation.")
        return

    realized_r = []
    for t in trades:
        pnl = t.get("pnl")
        balance = t.get("balance")
        if pnl is None or balance is None:
            continue
        entry_balance = balance - pnl
        if entry_balance <= 0:
            continue
        target_risk = entry_balance * BT_RISK_PER_TRADE
        if target_risk <= 0:
            continue
        realized_r.append(pnl / target_risk)

    if not realized_r:
        print("No valid realized R values.")
        return

    realized_r = np.array(realized_r)
    print("Realized R stats:")
    print("count:", realized_r.size)
    print("mean:", float(np.mean(realized_r)))
    print("median:", float(np.median(realized_r)))
    print("p10/p90:", np.percentile(realized_r, [10, 90]).tolist())
    print("min/max:", float(np.min(realized_r)), float(np.max(realized_r)))

if __name__ == "__main__":
    run_risk_validation()
