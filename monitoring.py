"""
monitoring.py - The Watchdog
Purpose: Detect when live performance diverges from expectations and apply kill switches.
Ref: Pages 9, 39, 40, 41
"""

import logging
import numpy as np
from config import EXPECTED_SLIPPAGE_PIPS

def analyze_execution(result, state_obj):
    """
    Ref: Page 19 - Phase 10: Monitoring
    Called after every successful order fill to track slippage drift.
    """
    # 1. CALCULATE SLIPPAGE
    # Ref: Page 19 - slippage = |filled_price - requested_price|
    requested_price = result.request.price
    filled_price = result.price
    
    slippage_price = abs(filled_price - requested_price)
    # Convert price units to pips (assuming EURUSD 5th decimal)
    slippage_pips = (slippage_price * 100000) / 10
    
    # 2. UPDATE ROLLING WINDOW
    # Ref: Page 39 - "Track last 20 trades"
    if not hasattr(state_obj, 'slippage_window'):
        state_obj.slippage_window = []
        
    state_obj.slippage_window.append(slippage_pips)
    if len(state_obj.slippage_window) > 20:
        state_obj.slippage_window.pop(0)

    # 3. CHECK FOR SLIPPAGE DRIFT
    # Ref: Page 39 - "median_slippage > expected + 3 pips"
    if len(state_obj.slippage_window) >= 5: # Need a small sample first
        median_slippage = np.median(state_obj.slippage_window)
        
        # Threshold: 2.0 (expected) + 3.0 (max drift) = 5.0 pips
        drift_threshold = EXPECTED_SLIPPAGE_PIPS + 3.0
        
        if median_slippage > drift_threshold or median_slippage > 5.5:
            state_obj.risk_throttle = True
            logging.critical(f"⚠️ ALERT: Slippage drift detected ({median_slippage:.1f} pips). Throttling risk.")
        else:
            state_obj.risk_throttle = False

def update_statistics(trade_won, state_obj):
    """
    Ref: Page 40 - Loss Streak Monitoring
    Called after a trade is closed to monitor for streaks.
    """
    if trade_won:
        state_obj.consecutive_losses = 0
    else:
        state_obj.consecutive_losses += 1
        
    # 4. CHECK LOSS STREAK
    # Ref: Page 40 - "5 consecutive losses -> trading_disabled = True"
    # Math: At 55% win rate, 5 losses in a row is only a 1.8% probability.
    if state_obj.consecutive_losses >= 5:
        state_obj.trading_disabled = True
        logging.critical("🚨 ALERT: Max loss streak (5) reached. TRADING DISABLED.")

def log_execution_failure(state_obj):
    """
    Ref: Page 41 - Execution Failure Monitoring
    Called when execution.py returns None or an error.
    """
    state_obj.execution_failures += 1
    
    # 5. CHECK FAILURE COUNT
    # Ref: Page 41 - "3 execution failures -> trading_disabled = True"
    if state_obj.execution_failures >= 3:
        state_obj.trading_disabled = True
        logging.critical("🚨 ALERT: Multiple execution failures (3). TRADING DISABLED.")

def get_watchdog_insight():
    """Ref: Page 39 - Core Responsibility"""
    return (
        "Compare what IS happening vs. what SHOULD happen. "
        "Apply kill switches before damage compounds."
    )