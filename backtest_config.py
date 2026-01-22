"""
backtest_config.py - Simulation Environment Settings
Purpose: Centralized parameters for the historical simulator and performance analysis.
Ref: Pages 40, 59, 61
"""
from datetime import datetime

# --- SIMULATION WINDOW ---
# Ref: Page 59
BT_START_DATE = datetime(2025, 12, 1)
BT_END_DATE = datetime(2026, 1, 1)
BT_INITIAL_BALANCE = 1000.00      # Ref: Page 60 (More Comfortable Capital)

# --- VIRTUAL BROKER SETTINGS (FRICTION) ---
# Ref: Page 40 (Backtest Assumptions)
# Using 'worst-case' values to ensure a conservative, realistic backtest.
FIXED_SPREAD_PIPS = 1.5           # Average spread for EURUSD
FIXED_SLIPPAGE_PIPS = 2.0         # Ref: Page 40 - Average live degradation
COMMISSION_PER_LOT = 0.00         # Adjust if your broker charges a fee

# --- SIMULATION PARAMETERS ---
BT_SYMBOL = "EURUSD"
BT_TIMEFRAME = "M1"               # Hardcoded to 1-minute as per PDF
WARMUP_PERIOD = 100               # Number of bars to pre-load for indicators

# --- RISK PARAMETERS (FROM LIVE CONFIG) ---
# We keep these here so you can test 'What If' scenarios
BT_RISK_PER_TRADE = 0.005         # 0.5%
BT_RR_MIN = 2.0                   # 2:1 Reward to Risk
BT_MAX_LEVERAGE = 5.0             # Ref: Page 11

# --- PERFORMANCE BENCHMARKS ---
# Ref: Page 61 (Success Metrics)
# These are used to color-code or flag the results in the final report.
TARGETS = {
    "WIN_RATE": 55.0,             # Percent
    "PROFIT_FACTOR": 2.0,         # Ratio
    "MAX_DRAWDOWN": -10.0,        # Percent
    "SHARPE_RATIO": 1.5           # Annualized ratio
}

# --- ANALYTICS SETTINGS ---
RISK_FREE_RATE = 0.0              # Typically 0 for retail FX backtesting

ANNUALIZATION_FACTOR = 252        # Standard trading days per year
