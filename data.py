"""
data.py - The Data Ingestion Layer
Purpose: Fetch, validate, and enrich market data.
Ref: Pages 5, 26, 27, 49
"""

import MetaTrader5 as mt5
import logging
from datetime import datetime
import indicators
from config import SYMBOL
import mock_data #mock testing module


def get_mock_bar():
    """
    MOCK VERSION of the Data Ingestion Layer.
    Generates synthetic data that bypasses 'Compression' and 'Whipsaw' vetos.
    Maintains exact same dictionary schema as get_processed_bar().
    """
    try:
        # 1. GENERATE NEW BAR IN SIMULATOR
        # Every time this is called, it moves the simulated clock forward 1 minute
        mock_data.sim.generate_next_bar()
        
        # 2. FETCH HISTORICAL RATES (100 bars for indicator calculation)
        rates = mock_data.sim.get_rates(100)
        
        # 3. SEPARATE CLOSED BAR (Ref: Page 27 - Use rates[-2] for no lookahead bias)
        closed_bar = rates[-2]
        
        # 4. ENRICH WITH INDICATORS (Ref: Page 28)
        # We use the real indicator logic on mock data to ensure calculations work
        metrics = indicators.enrich_bar_with_indicators(rates)
        
        # 5. OVERRIDE VETO TRIGGERS FOR TESTING
        # We manually nudge these values to ensure "Normal + Trend" regime
        metrics['atr_zscore'] = 0.1  # Force into "Normal" volatility
        metrics['adx'] = 30.0        # Force into "Trending" structure
        
        # 6. CONSTRUCT OUTPUT DICT (Exact copy of live schema)
        bar_dict = {
            "bar_index": int(closed_bar['time']),
            "timestamp": datetime.fromtimestamp(closed_bar['time']),
            "open": float(closed_bar['open']),
            "high": float(closed_bar['high']),
            "low": float(closed_bar['low']),
            "close": float(closed_bar['close']),
            "volume": int(closed_bar['tick_volume']),
            "spread": 0.00012, # Healthy 1.2 pip spread for testing
            "range": float(closed_bar['high'] - closed_bar['low']),
            **metrics # ATR, EMA_FAST, EMA_SLOW, ADX, ZSCORE, ATR_ZSCORE
        }

        return bar_dict

    except Exception as e:
        print(f"Mock Data Error: {e}")
        return None
    

def get_processed_bar():
    """
    Ref: Page 26 - "Provide ONE clean, validated, indicator-rich bar per call"
    Ref: Page 27 - Critical Design Decision: AVOID LOOKAHEAD BIAS
    """
    try:
        # 1. FETCH RAW DATA
        # We fetch 100 bars to ensure we have enough history for 50-period EMA
        # Ref: Page 27 - Always use rates[-2] (the last CLOSED bar)
        rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M1, 0, 100)
        
        if rates is None or len(rates) < 2:
            logging.error("Data Layer Error: Could not fetch rates from MT5")
            return None # LAYER 3: Fail closed (Page 48)

        # 2. SEPARATE CLOSED BAR FROM CURRENT TICK
        # rates[-1] is the bar currently forming (DO NOT USE - Page 27)
        # rates[-2] is the most recent completed 1-minute bar
        closed_bar = rates[-2]
        
        # 3. DATA VALIDATION (Ref: Page 15, 49)
        if not validate_bar_integrity(closed_bar):
            return None # Fail closed

        # 4. FETCH CURRENT TICK FOR SPREAD (Ref: Page 49)
        tick = mt5.symbol_info_tick(SYMBOL)
        if tick is None:
            logging.error("Data Layer Error: Could not fetch current tick")
            return None
        
        spread = tick.ask - tick.bid
        if spread <= 0:
            logging.warning(f"Data Layer Warning: Invalid spread detected ({spread})")
            return None

        # 5. ENRICH WITH INDICATORS (Ref: Page 28)
        # We pass the full rates array to indicators.py to calculate metrics
        metrics = indicators.enrich_bar_with_indicators(rates)
        
        # 6. CONSTRUCT OUTPUT DICT (Ref: Page 27)
        bar_dict = {
            "bar_index": int(closed_bar['time']), # Use timestamp as monotonic index
            "timestamp": datetime.fromtimestamp(closed_bar['time']),
            "open": float(closed_bar['open']),
            "high": float(closed_bar['high']),
            "low": float(closed_bar['low']),
            "close": float(closed_bar['close']),
            "volume": int(closed_bar['tick_volume']),
            "spread": float(spread),
            "range": float(closed_bar['high'] - closed_bar['low']),
            **metrics # Merge in ATR, EMA, ADX, Z-Score
        }

        return bar_dict

    except Exception as e:
        logging.exception(f"Unexpected error in Data Layer: {e}")
        return None # Ref: Page 44 - Unknown state = safe state (no trade)

def validate_bar_integrity(bar):
    """
    Ref: Page 49 - LAYER 1: Input Validation
    """
    # Check OHLC Logic
    if not (bar['high'] >= bar['low']):
        logging.error("Validation Error: High is lower than Low")
        return False
    
    if not (bar['high'] >= bar['open'] and bar['high'] >= bar['close']):
        logging.error("Validation Error: High is not the highest point")
        return False
        
    if not (bar['low'] <= bar['open'] and bar['low'] <= bar['close']):
        logging.error("Validation Error: Low is not the lowest point")
        return False

    return True