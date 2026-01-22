"""
costs.py - The Friction Manager
Purpose: Block trades when transaction costs (spread + slippage) exceed edge.
Ref: Pages 7, 13, 17, 34, 35
"""

import logging
from datetime import datetime, time
from config import MEDIAN_SPREAD_PRICE, MAX_SPREAD_MULTIPLIER, EXPECTED_SLIPPAGE_PIPS

def is_acceptable(current_spread_price):
    """
    Ref: Page 17 - Phase 6: Cost Evaluation
    Evaluates three layers of cost protection.
    """
    
    # --- CHECK 1: Spread Filter ---
    # Ref: Page 34 - "Abnormally wide spreads signal low liquidity or news"
    # Current spread must be < 1.5x the median spread.
    max_allowed_spread = MEDIAN_SPREAD_PRICE * MAX_SPREAD_MULTIPLIER
    
    if current_spread_price > max_allowed_spread:
        logging.info(
            f"Cost Veto: Spread too wide. "
            f"Current: {current_spread_price:.5f}, Max: {max_allowed_spread:.5f}"
        )
        return False

    # --- CHECK 2: Rollover Filter (Time Windows) ---
    # Ref: Page 34 - "Swap charges applied, wide spreads, unpredictable fills"
    # Blocks trading during the 21:59 - 22:05 UTC rollover window.
    if is_in_rollover():
        logging.info("Cost Veto: Inside Rollover Window (21:59 - 22:05 UTC).")
        return False

    # --- CHECK 3: Cost vs. Edge Calculation ---
    # Ref: Page 34 - Actual Edge Calculation
    # Theoretical Edge: +7.5 pips per trade (55% win rate, 30 pip target)
    # Total Cost = Current Spread + Expected Slippage
    
    # Convert spread to pips for comparison (Assuming 5th decimal is 1/10th pip)
    current_spread_pips = current_spread_price * 100000 / 10
    total_cost_pips = current_spread_pips + EXPECTED_SLIPPAGE_PIPS
    
    # Ref Page 14: Cost as % of target should be around 5.7% (1.7 / 30)
    # If costs exceed 10% of the target profit, the trade is mathematically poor.
    if total_cost_pips > 3.0: # Hard limit for EURUSD 1m
        logging.info(f"Cost Veto: Total friction ({total_cost_pips} pips) exceeds edge.")
        return False

    # ALL PASS -> CONTINUE
    return True

def is_in_rollover():
    """
    Checks if current UTC time is within the dangerous rollover window.
    Ref: Page 14 & 34
    """
    now_utc = datetime.utcnow().time()
    start = time(21, 59)
    end = time(22, 5)
    
    # Handle the window crossing midnight (though 22:05 doesn't)
    if start <= now_utc <= end:
        return True
    return False

def get_cost_logic_insight():
    """
    Ref: Page 34 - The Cost Problem
    """
    return (
        "Actual Edge = Expected Profit - Real World Costs. "
        "If spread is 1.5 pips and slippage is 0.5 pips, total cost is 2.0. "
        "At a 7.5 pip theoretical edge, costs consume 27% of your profit."
    )

#______________________________________________

def simulate_acceptable(current_spread_price, med_spread, max_spread_mult, expected_slippage_pips):
    """
    Ref: Page 17 - Phase 6: Cost Evaluation
    Evaluates three layers of cost protection.
    """
    
    # --- CHECK 1: Spread Filter ---
    # Ref: Page 34 - "Abnormally wide spreads signal low liquidity or news"
    # Current spread must be < 1.5x the median spread.
    max_allowed_spread = med_spread * max_spread_mult
    
    if current_spread_price > max_allowed_spread:
        logging.info(
            f"Cost Veto: Spread too wide. "
            f"Current: {current_spread_price:.5f}, Max: {max_allowed_spread:.5f}"
        )
        return False

    # --- CHECK 2: Rollover Filter (Time Windows) ---
    # Ref: Page 34 - "Swap charges applied, wide spreads, unpredictable fills"
    # Blocks trading during the 21:59 - 22:05 UTC rollover window.
    if is_in_rollover():
        logging.info("Cost Veto: Inside Rollover Window (21:59 - 22:05 UTC).")
        return False

    # --- CHECK 3: Cost vs. Edge Calculation ---
    # Ref: Page 34 - Actual Edge Calculation
    # Theoretical Edge: +7.5 pips per trade (55% win rate, 30 pip target)
    # Total Cost = Current Spread + Expected Slippage
    
    # Convert spread to pips for comparison (Assuming 5th decimal is 1/10th pip)
    current_spread_pips = current_spread_price * 100000 / 10
    total_cost_pips = current_spread_pips + expected_slippage_pips
    
    # Ref Page 14: Cost as % of target should be around 5.7% (1.7 / 30)
    # If costs exceed 10% of the target profit, the trade is mathematically poor.
    if total_cost_pips > 3.0: # Hard limit for EURUSD 1m
        logging.info(f"Cost Veto: Total friction ({total_cost_pips} pips) exceeds edge.")
        return False

    # ALL PASS -> CONTINUE
    return True