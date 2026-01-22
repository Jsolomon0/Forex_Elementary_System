"""
execution.py - The Order Handler
Purpose: Convert trading intent into confirmed filled orders.
Ref: Pages 8, 18, 37, 38, 39
"""

import MetaTrader5 as mt5
import time
import logging
from config import SYMBOL, MAGIC_NUMBER, DEVIATION

def execute_trade(signal, volume):
    """
    Ref: Page 37 - Execution Flow
    Main entry point for placing an order with the broker.
    """
    
    # STEP 1: Validate Preconditions
    # Ref: Page 52 - "ONE POSITION AT A TIME"
    if _already_have_position():
        logging.info("Execution Abort: Position already exists (One-at-a-time limit).")
        return None

    if volume <= 0:
        logging.error(f"Execution Abort: Invalid volume calculated ({volume})")
        return None

    # STEP 2: Execute with Retry Logic
    # Ref: Page 38 - "FOR attempt IN [1, 2]"
    for attempt in range(1, 3):
        logging.info(f"Execution Attempt {attempt} for {signal['direction']} {volume} lots")
        
        # Build fresh order request with latest price
        request = _build_request(signal, volume)
        if not request:
            continue

        # Send the order to MT5
        result = mt5.order_send(request)

        # STEP 3: Handle Result
        # Ref: Page 38 - Error Categorization
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            logging.info(f"✅ Trade Executed Successfully: {signal['direction']} {volume} lots")
            return result # SUCCESS

        # Handle Retriable Errors
        if result.retcode in [mt5.TRADE_RETCODE_REQUOTE, mt5.TRADE_RETCODE_PRICE_CHANGED]:
            logging.warning(f"Execution: Price moved (Requote). Retrying...")
            time.sleep(0.1) # Small pause before retry
            continue # Try attempt 2

        if result.retcode == mt5.TRADE_RETCODE_OFF_QUOTES:
            logging.warning("Execution: Broker Off-quotes. Waiting 300ms...")
            time.sleep(0.3) # Ref: Page 8
            continue # Try attempt 2

        # Handle Fatal Errors
        # Ref: Page 39 - "These are signs you SHOULDN'T be trading"
        logging.error(f"Execution Fatal Error: {result.comment} (Code: {result.retcode})")
        break # Do not retry fatal errors

    logging.error("Execution: Max retries exceeded or fatal error encountered.")
    return None

def _already_have_position():
    """Ref: Page 52 - Ensure only one open trade for the SYMBOL."""
    positions = mt5.positions_get(symbol=SYMBOL)
    return len(positions) > 0

def _build_request(signal, volume):
    """Ref: Page 38 - Build MT5 order request structure."""
    tick = mt5.symbol_info_tick(SYMBOL)
    if not tick:
        return None

    # Determine direction and price
    if signal['direction'] == "BUY":
        order_type = mt5.ORDER_TYPE_BUY
        price = tick.ask
    else:
        order_type = mt5.ORDER_TYPE_SELL
        price = tick.bid

    return {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": SYMBOL,
        "volume": float(volume),
        "type": order_type,
        "price": float(price),
        "sl": float(signal['sl']),
        "tp": float(signal['tp']),
        "magic": MAGIC_NUMBER,
        "deviation": DEVIATION,
        "comment": "Professional FX Bot",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC, # Immediate or Cancel
    }

def get_reality_check():
    """Ref: Page 39 - Why Max 2 Attempts"""
    return (
        "If you can't fill after 2 attempts, the market is moving too fast "
        "or liquidity is poor. Better to skip this opportunity than chase "
        "bad conditions."
    )