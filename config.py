"""
config.py - The Configuration
Purpose: Single source of truth for all system parameters.
Design Philosophy: "If you might want to change it, it belongs in config.py"
"""

# --- MARKET SETTINGS ---
SYMBOL = "EURUSD"               # Primary currency pair
TIMEFRAME_NAME = "1-Minute"      # For documentation/logging
LOOP_DELAY_SECONDS = 60          # Event loop frequency (60s bar)

# --- RISK PARAMETERS ---
# Ref: Page 24
RISK_PER_TRADE = 0.005           # 0.5% risk per trade of total equity
MAX_EFFECTIVE_LEVERAGE = 5.0     # 5x maximum (Safeguard for small accounts)
MAX_TRADES_PER_DAY = 5           # Hard cap on daily frequency
MAX_DAILY_DRAWDOWN = 0.03        # 3% daily equity stop-loss

# --- COST THRESHOLDS (FRICTION MANAGEMENT) ---
# Ref: Page 24
MEDIAN_SPREAD_PRICE = 0.00010    # 1.0 pip baseline for EURUSD
MAX_SPREAD_MULTIPLIER = 1.5      # Block trades if spread > 1.5 pips
EXPECTED_SLIPPAGE_PIPS = 2.0     # Baseline slippage expectation for cost calc

# --- REGIME DETECTION (MARKET CONTEXT) ---
# Ref: Page 24-25
VOL_Z_COMPRESSION = -1.0
VOL_Z_EXPANSION = 1.0
VOL_Z_EXTREME = 2.0  # new for extreme expansion
ADX_TREND_THRESHOLD = 25         # Level above which market is "trending"

# --- STRATEGY PARAMETERS ---
# Ref: Page 25
RR_MIN = 2.0                     # Minimum 2:1 Reward-to-Risk ratio
ATR_STOP_MULTIPLIER = 1.5        # Stop loss distance = ATR * 1.5
EXTENDED_MULTIPLIER = 1.5     # Ref: strategy.py - Extended candle multiplier

# --- INDICATOR PARAMETERS ---
# Ref: Page 25
ATR_PERIOD = 14                  # ATR period for volatility measurement
EMA_FAST = 20                    # Fast moving average period
EMA_SLOW = 50                    # Slow moving average period
ADX_PERIOD = 14                  # ADX period for trend strength
Z_SCORE_PERIOD = 20              # Period for mean-reversion calculations
ATR_ZSCORE_PERIOD = 20           # Period for ATR Z-score calculation



# --- SYSTEM SETTINGS ---
# Ref: Page 25
MAGIC_NUMBER = 10001             # Unique ID to distinguish bot orders
DEVIATION = 20                   # Maximum price deviation allowed (points)
STATE_FILE_PATH = "C:\\Users\\JOHN ALYN\\QFSA0\\Forex_System0\\state\\trading_state.json"
LOG_FILE_PATH = "C:\\Users\\JOHN ALYN\\QFSA0\\Forex_System0\\logs\\trading.log"

# --- NOTIFICATION SETTINGS (FUTURE FEATURE) ---
TELEGRAM_ENABLED = False
TELEGRAM_TOKEN = "your_token_here"
TELEGRAM_CHAT_ID = "your_chat_id_here"