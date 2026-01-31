"""
monte_carlo.py - Monte Carlo resampling of trade returns.
"""

import random
import numpy as np
from backtest_config import BT_INITIAL_BALANCE
import back_test

def _max_drawdown(equity_curve):
    peak = equity_curve[0]
    mdd = 0.0
    for val in equity_curve:
        if val > peak:
            peak = val
        dd = (val - peak) / peak
        if dd < mdd:
            mdd = dd
    return mdd * 100.0

def run_monte_carlo(iterations=10000, seed=42):
    report, trades = back_test.run_simulation_with_trades(verbose=False)
    if not trades:
        print("No trades available for Monte Carlo.")
        return

    returns = [t["return_pct"] for t in trades if "return_pct" in t]
    if not returns:
        print("No returns available for Monte Carlo.")
        return

    random.seed(seed)
    final_balances = []
    mdds = []
    for _ in range(iterations):
        eq = BT_INITIAL_BALANCE
        curve = [eq]
        for _ in range(len(returns)):
            r = random.choice(returns)
            eq = eq * (1.0 + r)
            curve.append(eq)
        final_balances.append(eq)
        mdds.append(_max_drawdown(curve))

    print("Monte Carlo iterations:", iterations)
    print("Final balance percentiles (5/50/95):",
          np.percentile(final_balances, [5, 50, 95]).tolist())
    print("Max drawdown percentiles (5/50/95):",
          np.percentile(mdds, [5, 50, 95]).tolist())

if __name__ == "__main__":
    run_monte_carlo()
