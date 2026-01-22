"""
indicators.py - The Technical Analysis Engine
Purpose: Calculate all technical indicators needed by regime and strategy layers.
Ref: Pages 15, 27, 28
"""

import numpy as np
from config import ATR_PERIOD, EMA_FAST, EMA_SLOW, ADX_PERIOD, Z_SCORE_PERIOD, ATR_ZSCORE_PERIOD

def calculate_atr(high, low, close, period=14):
    """
    Ref: Page 28 - ATR Calculation
    Standard ATR using Simple Moving Average of True Range as per doc specs.
    """
    # tr1 = high - low
    tr1 = high[1:] - low[1:]
    # tr2 = abs(high - previous_close)
    tr2 = np.abs(high[1:] - close[:-1])
    # tr3 = abs(low - previous_close)
    tr3 = np.abs(low[1:] - close[:-1])
    
    # Combined True Range
    tr = np.maximum(tr1, np.maximum(tr2, tr3))
    
    # Return SMA of True Range (Page 28 specific logic)
    if len(tr) < period:
        return 0.0
    return float(np.mean(tr[-period:]))

def calculate_ema(data, period):
    """
    Ref: Page 15 - Used for EMA Fast (20) and EMA Slow (50)
    Standard Exponential Moving Average.
    """
    if len(data) < period:
        return 0.0
    
    alpha = 2 / (period + 1)
    ema = data[0]
    for price in data[1:]:
        ema = (price * alpha) + (ema * (1 - alpha))
    return float(ema)

def calculate_adx(high, low, close, period=14):
    """
    Ref: Page 15 - Used for trend strength detection (>25 threshold)
    Simplied version suitable for 1-minute bar logic.
    """
    if len(close) < period * 2:
        return 0.0

    up_move = high[1:] - high[:-1]
    down_move = low[:-1] - low[1:]

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

    # Simplified Smoothing for logic consistency
    tr1 = high[1:] - low[1:]
    tr2 = np.abs(high[1:] - close[:-1])
    tr3 = np.abs(low[1:] - close[:-1])
    tr = np.maximum(tr1, np.maximum(tr2, tr3))

    tr_smooth = np.sum(tr[-period:])
    plus_di = 100 * (np.sum(plus_dm[-period:]) / tr_smooth)
    minus_di = 100 * (np.sum(minus_dm[-period:]) / tr_smooth)

    dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
    return float(dx)

def calculate_zscore(data, period=20):
    """
    Ref: Page 31 - Strategy 2: Mean Reversion
    Calculates the 20-bar price z-score.
    """
    if len(data) < period:
        return 0.0
    
    window = data[-period:]
    mean = np.mean(window)
    std = np.std(window)
    
    if std == 0:
        return 0.0
    
    return float((data[-1] - mean) / std)

def enrich_bar_with_indicators(rates):
    """
    Ref: Page 27 - Critical Design Decision
    Consolidates raw MT5 data into a validated indicator-rich bar dict.
    """
    # Convert MT5 record array to numpy arrays
    high = rates['high']
    low = rates['low']
    close = rates['close']
    
    #parameter = run_optimizer()

    # Latest Indicators (using indices that avoid lookahead bias)
    # Ref: Page 27 - bar = rates[-2] (the last CLOSED bar)
    indicators = {
        "atr": calculate_atr(high, low, close, period=ATR_PERIOD),
        "ema_fast": calculate_ema(close, period=EMA_FAST),
        "ema_slow": calculate_ema(close, period=EMA_SLOW),
        "adx": calculate_adx(high, low, close, period=ADX_PERIOD),
        "zscore": calculate_zscore(close, period=Z_SCORE_PERIOD),
        # ATR Z-score used for Volatility Axis (Ref: Page 15)
        "atr_zscore": calculate_zscore([calculate_atr(high[:i], low[:i], close[:i]) 
                                        for i in range(len(close)-20, len(close))], period=ATR_ZSCORE_PERIOD)
    }
    
    return indicators

def simulate_indicators(rates, atr_lb, ema_fast_lb, ema_slow_lb, adx_lb, zscore_lb, atr_zscore_lb):
    """
    Ref: Page 27 - Critical Design Decision
    Consolidates raw MT5 data into a validated indicator-rich bar dict.
    """
    # Convert MT5 record array to numpy arrays
    high = rates['high']
    low = rates['low']
    close = rates['close']
    
    #parameter = run_optimizer()

    # Latest Indicators (using indices that avoid lookahead bias)
    # Ref: Page 27 - bar = rates[-2] (the last CLOSED bar)
    indicators = {
        "atr": calculate_atr(high, low, close, period= atr_lb),
        "ema_fast": calculate_ema(close, period= ema_fast_lb),
        "ema_slow": calculate_ema(close, period= ema_slow_lb),
        "adx": calculate_adx(high, low, close, period= adx_lb),
        "zscore": calculate_zscore(close, period= zscore_lb),
        # ATR Z-score used for Volatility Axis (Ref: Page 15)
        "atr_zscore": calculate_zscore([calculate_atr(high[:i], low[:i], close[:i]) 
                                        for i in range(len(close)-20, len(close))], period= atr_zscore_lb)
    }
    
    return indicators
