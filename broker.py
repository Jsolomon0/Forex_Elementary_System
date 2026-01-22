"""
broker.py - The Emergency Stop
Purpose: Nuclear option for immediate position closure.
Ref: Pages 22, 41, 42, 43
"""

import MetaTrader5 as mt5
import logging
from config import SYMBOL, MAGIC_NUMBER

def flatten_all():
    """
    Ref: Page 41 - Core Function
    Close ALL open positions immediately - No questions asked.
    Ignores all rules and filters to prioritize account safety.
    """
    logging.critical("🚨 EMERGENCY: Flattening all positions immediately.")
    
    # 1. Get all open positions
    # We fetch positions for our SYMBOL to ensure we don't accidentally
    # close the user's unrelated manual trades on other pairs.
    positions = mt5.positions_get(symbol=SYMBOL)
    
    if positions is None:
        logging.error("Emergency Error: Could not retrieve positions.")
        return False

    if len(positions) == 0:
        logging.info("Emergency: No open positions to close.")
        return True

    success_count = 0
    
    for position in positions:
        ticket = position.ticket
        volume = position.volume
        pos_type = position.type
        
        # 2. Determine opposite order type (Ref: Page 41)
        if pos_type == mt5.POSITION_TYPE_BUY:
            close_type = mt5.ORDER_TYPE_SELL
            price = mt5.symbol_info_tick(SYMBOL).bid
        else:
            close_type = mt5.ORDER_TYPE_BUY
            price = mt5.symbol_info_tick(SYMBOL).ask

        # 3. Build close request
        # Ref: Page 42 - "comment: EMERGENCY_FLAT"
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": SYMBOL,
            "volume": float(volume),
            "type": close_type,
            "position": ticket,
            "price": float(price),
            "deviation": 20,
            "magic": MAGIC_NUMBER,
            "comment": "EMERGENCY_FLAT",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        # 4. Execute immediately (No retry logic - Ref: Page 42)
        result = mt5.order_send(request)
        
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            success_count += 1
            logging.info(f"Successfully closed position #{ticket}")
        else:
            logging.error(f"Failed to close position #{ticket}: {result.comment}")

    logging.info(f"Emergency Summary: {success_count}/{len(positions)} positions closed.")
    return success_count == len(positions)

def set_global_kill_switch(state_manager, status=True):
    """
    Ref: Page 52 - Manual Kill Switch (Level 2)
    Updates the state file to disable the bot from taking new trades.
    """
    state_manager.state.trading_disabled = status
    state_manager.save()
    action = "DISABLED" if status else "ENABLED"
    logging.critical(f"USER INTERVENTION: System has been {action}.")

def get_emergency_use_cases():
    """
    Ref: Page 42 - Use Cases
    """
    return {
        "SCENARIO 1": "System Detects Critical Error (Monitoring Layer)",
        "SCENARIO 2": "VPS Maintenance Required (Operator Shutdown)",
        "SCENARIO 3": "Major News Event (NFP / FOMC / Central Bank)",
    }