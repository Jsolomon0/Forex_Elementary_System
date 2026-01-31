"""
calibration.py - Derive spread/slippage/commission defaults from MT5 history.
"""

from datetime import datetime, timedelta
import numpy as np
import MetaTrader5 as mt5
from backtest_config import BT_SYMBOL

PIP_SIZE = 0.0001

def _spread_pips_from_rates(rates):
    # MT5 rates spread is in points; for 5-digit pairs 1 point = 0.00001
    spread_price = rates['spread'] * 0.00001
    return spread_price / PIP_SIZE

def _slippage_proxy_pips_from_rates(rates):
    # Proxy slippage from 90th percentile of absolute mid changes.
    mid = (rates['high'] + rates['low']) / 2.0
    abs_change = np.abs(np.diff(mid)) / PIP_SIZE
    if abs_change.size == 0:
        return 0.0
    return float(np.percentile(abs_change, 90) * 0.5)

def calibrate_from_rates(symbol, start_date, end_date, timeframe=mt5.TIMEFRAME_M1):
    if not mt5.initialize():
        raise RuntimeError("MT5 initialization failed")
    rates = mt5.copy_rates_range(symbol, timeframe, start_date, end_date)
    mt5.shutdown()

    if rates is None or len(rates) == 0:
        raise RuntimeError("No rates data returned")

    spread_pips = _spread_pips_from_rates(rates)
    stats = {
        "spread_pips_median": float(np.median(spread_pips)),
        "spread_pips_mean": float(np.mean(spread_pips)),
        "spread_pips_p90": float(np.percentile(spread_pips, 90)),
        "slippage_pips_proxy": _slippage_proxy_pips_from_rates(rates),
        "bars": int(len(rates)),
    }
    return stats

def run_default_calibration(lookback_days=90):
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=lookback_days)
    stats = calibrate_from_rates(BT_SYMBOL, start_date, end_date)
    print("Calibration window:", start_date.isoformat(), "->", end_date.isoformat())
    for k, v in stats.items():
        print(f"{k}: {v}")

if __name__ == "__main__":
    run_default_calibration()
