"""
psychology.py - The Behavioral Control System
Purpose: Enforce discipline that humans struggle with (Discipline is Systematic).
Ref: Pages 7, 12, 16, 32, 33
"""

import logging
from config import MAX_TRADES_PER_DAY

def is_allowed(state_obj, bar):
    """
    Ref: Page 16 - Phase 5: Behavioral Filtering
    Checks four hard rules. A trade must pass ALL to proceed.
    """
    
    # --- CHECK 1: Daily Trade Cap ---
    # Ref: Page 12 - "Prevents overtrading during winning streaks"
    if state_obj.trades_today >= MAX_TRADES_PER_DAY:
        logging.info(f"Psychology Veto: Daily limit of {MAX_TRADES_PER_DAY} reached.")
        return False

    # --- CHECK 2: Cooldown Periods ---
    # Ref: Page 12 - "Prevents clustering of trades in same market condition"
    # Timeline View: If trade at Bar 100, Bar 106 is the first allowed entry.
    current_bar_index = bar['bar_index']
    bars_since_last = current_bar_index - state_obj.last_trade_bar
    
    if bars_since_last < 5:
        logging.info(f"Psychology Veto: Cooldown active. {bars_since_last}/5 bars passed.")
        return False

    # --- CHECK 3: Risk Throttle (System Degradation) ---
    # Ref: Page 13 & 39 - Slippage drift monitoring
    # Triggered by monitoring.py if live slippage exceeds backtest expectations.
    if state_obj.risk_throttle:
        logging.warning("Psychology Veto: Risk throttle active due to slippage drift.")
        return False

    # --- CHECK 4: Global Kill Switch (Manual or Auto) ---
    # Ref: Page 40 & 52 - Nuclear Option / Manual Intervention
    # Triggered by 5 consecutive losses or 3 execution failures.
    if state_obj.trading_disabled:
        logging.critical("Psychology Veto: TRADING DISABLED - Manual review required.")
        return False

    # ALL CHECKS PASSED
    # Ref: Page 17 - "ALL PASS -> CONTINUE"
    return True

def get_behavioral_logic_summary():
    """
    Ref: Page 33 - Key Insight
    Documentation for the user logs.
    """
    return (
        "The psychology module doesn't make you smarter. "
        "It prevents you from being stupid by enforcing hard rules: "
        "Max 5 trades/day, 5-bar cooldown, and auto-shutdown on streaks."
    )