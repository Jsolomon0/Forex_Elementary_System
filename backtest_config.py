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

# --- STRATEGY CONTROL (BACKTEST ONLY) ---
BT_MEAN_REVERSION_ONLY = True     # Disable trend-following for testing

# --- BREAKEVEN SETTINGS (BACKTEST ONLY) ---
# Move SL to breakeven after price moves BE_TRIGGER_R_MULT * stop_distance.
# Optional small buffer (in pips) to cover costs.
BE_TRIGGER_R_MULT = 1.0
BE_OFFSET_PIPS = 0.0

# --- MICROSTRUCTURE (BACKTEST ONLY) ---
MS_ENABLE = True
MS_SESSION_MULT_ASIA = 1.1
MS_SESSION_MULT_LONDON = 1.0
MS_SESSION_MULT_NY = 1.1
MS_SESSION_MULT_OFF = 1.3

MS_VOL_MULT_COMPRESSION = 0.8
MS_VOL_MULT_NORMAL = 1.0
MS_VOL_MULT_EXPANSION = 1.3
MS_VOL_MULT_EXTREME = 1.6

# --- SWAP (BACKTEST ONLY) ---
# Per-lot per-rollover swap cost. Use negative for a cost, positive for credit.
SWAP_LONG_PER_LOT = 0.0
SWAP_SHORT_PER_LOT = 0.0

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

# --- SESSION / TIME-OF-DAY FILTER ---
# All times assumed to be server time (UTC in backtests)
SESSION_FILTER_ENABLED = True      # Set to False to disable session gating
SESSION_START_HOUR_UTC = 7         # e.g. 07:00 UTC (London open region)
SESSION_END_HOUR_UTC = 17          # e.g. 17:00 UTC (end of main NY session)
SESSION_SKIP_WEEKENDS = True       # Skip Saturday/Sunday bars entirely

# --- BACKTEST EXECUTION / SWAP SETTINGS ---
BACKTEST_SLIPPAGE_PIPS = FIXED_SLIPPAGE_PIPS  # or a separate value
TICK_SIZE = 0.00001
SWAP_LONG_POINTS = 0.0
SWAP_SHORT_POINTS = 0.0

# --- TRADE LIFETIME / TIME STOP SETTINGS ---
# Maximum number of bars a trade is allowed to stay open.
# For M2 bars, 60 bars = 120 minutes.
MAX_BARS_IN_TRADE = 60 # Needs to be tuned based on strategy specifics.


