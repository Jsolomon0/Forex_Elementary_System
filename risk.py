"""
risk.py - The Supreme Authority
Purpose: Calculate safe position size that satisfies ALL risk constraints.
Ref: Pages 8, 11, 35, 36, 37
"""

import math
import logging
from config import RISK_PER_TRADE, MAX_EFFECTIVE_LEVERAGE

PIP_SIZE = 0.0001

def simulate_size(equity, stop_distance_pips, current_price, risk_trade, max_leverage):
    """
    Ref: Page 35 - The Risk Algorithm
    Translates equity and volatility into a specific lot size.
    """
    try:
        # STEP 1: Determine Risk Amount ($)
        # Ref: Page 35 - "risk_dollars = equity * 0.005"
        risk_dollars = equity * risk_trade
        
        if risk_dollars <= 0:
            print("Risk Calculation Error: Non-positive risk dollars.")
            return 0.0

        # STEP 2: Determine Pip Value
        # Ref: Page 35 - Standard Lot = 100,000 units. 1 pip = 0.0001
        # Pip value per lot = 100,000 * 0.0001 = $10
        pip_value_per_lot = 10.0 

        # STEP 3: Calculate Raw Position Size
        # Ref: Page 36 - "lots = risk_dollars / (stop_pips * pip_value)"
        if stop_distance_pips <= 0:
            print("Risk Calculation Error: Non-positive stop distance.")
            return 0.0
        stop_distance_pips = stop_distance_pips / PIP_SIZE
        raw_lots = risk_dollars / (stop_distance_pips * pip_value_per_lot)

        # STEP 4: Apply Leverage Cap (Safety Layer)
        # Ref: Page 36 - Max 5x effective leverage
        # Notional Value = Lots * 100,000 * Price
        notional_value = raw_lots * 100000 * current_price
        current_leverage = notional_value / equity

        if current_leverage > max_leverage:
            # Scale down to meet the 5x limit
            raw_lots = (equity * max_leverage) / (100000 * current_price)
            logging.warning(f"Risk Warning: Leverage capped at {max_leverage}x. Size reduced.")

        # STEP 5: Quantize to Broker Step (Ref: Page 37)
        # CRITICAL SAFETY: NEVER ROUND UP (Risk Violation)
        final_lots = _quantize_lot_size(raw_lots)

        # STEP 6: Validate Minimum Size
        # Ref: Page 36 - "If quantized < min_lot_size -> RETURN 0"
        if final_lots < 0.01:
            logging.info(f"Risk Veto: Calculated size {raw_lots:.4f} below broker minimum.")
            return 0.0

        return float(final_lots)

    except Exception as e:
        logging.error(f"Error in Risk Layer: {e}")
        return 0.0 # Fail-Closed: Unknown state = no trade


def calculate_size(equity, stop_distance_pips, current_price):
    """
    Ref: Page 35 - The Risk Algorithm
    Translates equity and volatility into a specific lot size.
    """
    try:
        # STEP 1: Determine Risk Amount ($)
        # Ref: Page 35 - "risk_dollars = equity * 0.005"
        risk_dollars = equity * RISK_PER_TRADE
        
        if risk_dollars <= 0:
            print("Risk Calculation Error: Non-positive risk dollars.")
            return 0.0

        # STEP 2: Determine Pip Value
        # Ref: Page 35 - Standard Lot = 100,000 units. 1 pip = 0.0001
        # Pip value per lot = 100,000 * 0.0001 = $10
        pip_value_per_lot = 10.0 

        # STEP 3: Calculate Raw Position Size
        # Ref: Page 36 - "lots = risk_dollars / (stop_pips * pip_value)"
        if stop_distance_pips <= 0:
            print("Risk Calculation Error: Non-positive stop distance.")
            return 0.0
        stop_distance_pips = stop_distance_pips / PIP_SIZE
        raw_lots = risk_dollars / (stop_distance_pips * pip_value_per_lot)

        # STEP 4: Apply Leverage Cap (Safety Layer)
        # Ref: Page 36 - Max 5x effective leverage
        # Notional Value = Lots * 100,000 * Price
        notional_value = raw_lots * 100000 * current_price
        current_leverage = notional_value / equity

        if current_leverage > MAX_EFFECTIVE_LEVERAGE:
            # Scale down to meet the 5x limit
            raw_lots = (equity * MAX_EFFECTIVE_LEVERAGE) / (100000 * current_price)
            logging.warning(f"Risk Warning: Leverage capped at {MAX_EFFECTIVE_LEVERAGE}x. Size reduced.")

        # STEP 5: Quantize to Broker Step (Ref: Page 37)
        # CRITICAL SAFETY: NEVER ROUND UP (Risk Violation)
        final_lots = _quantize_lot_size(raw_lots)

        # STEP 6: Validate Minimum Size
        # Ref: Page 36 - "If quantized < min_lot_size -> RETURN 0"
        if final_lots < 0.01:
            logging.info(f"Risk Veto: Calculated size {raw_lots:.4f} below broker minimum.")
            return 0.0

        return float(final_lots)

    except Exception as e:
        logging.error(f"Error in Risk Layer: {e}")
        return 0.0 # Fail-Closed: Unknown state = no trade

def _quantize_lot_size(lots):
    """
    Critical Safety Feature: Floor division to ensure we never round up.
    Ref: Page 37 - "RIGHT: quantized = floor(lots / step) * step"
    """
    step = 0.01
    # Use floor to ensure we stay UNDER the 0.5% risk limit
    quantized = math.floor(lots / step) * step
    return round(quantized, 2)

def get_sophisticated_insight():
    """
    Ref: Page 36 - Why This is Complex
    """
    return (
        "Result: CONSTANT RISK, ADAPTIVE SIZE. "
        "When volatility is high (wide stops), size is small. "
        "When volatility is low (tight stops), size is large. "
        "In both cases, you lose exactly 0.5% if stopped out."
    )
