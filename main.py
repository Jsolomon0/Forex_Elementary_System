"""
main.py - The Orchestrator
Purpose: Central command center that coordinates all modules in the decision pipeline.
Ref: Pages 4, 14, 23, 24
"""

import time
import logging
import math
import MetaTrader5 as mt5
from datetime import datetime

# Import Custom Modules
import config
import calibration
import back_test
from state import StateManager
import data, regime, strategy, psychology, costs, risk, execution, monitoring, broker, session

#C:\Users\JOHN ALYN\QFSA0\Forex_System0\config.py

# 1. LOGGING CONFIGURATION (Ref: Page 54)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(config.LOG_FILE_PATH),
        logging.StreamHandler()
    ]
)

def initialize_system():

    """Ref: Page 23 - Initialize MT5 and System State"""
    logging.info("--- INITIALIZING SYSTEM ---")

    #Display MT5 package information
    print("MetaTrader5 package author: ", mt5.__author__)
    print("MetaTrader5 package version: ", mt5.__version__)
    #Initialize a connection to the MetaTrader 5 terminal (demo credentials)
    if not mt5.initialize(login=10008873743, server="MetaQuotes-Demo", password="R!X3PkUy"):
        quit()
        logging.critical(f"MT5 Initialization failed. Error code: {mt5.last_error()}")
        return None
    else:
        print("MT5 initialized successfully")

    state_manager = StateManager(config.STATE_FILE_PATH)
    logging.info("MT5 Connected and State Loaded successfully.")
    return state_manager

def shutdown_sequence(state_manager):
    """Ref: Page 23 - Manage shutdown sequence"""
    logging.info("--- SHUTDOWN SEQUENCE INITIATED ---")
    # Optional: broker.flatten_all() if you want to close trades on exit
    mt5.shutdown()
    logging.info("System Offline.")

def veto_reset():
    time.sleep(60)

def _apply_risk_multiplier(lot_size, multiplier):
    if multiplier >= 1.0:
        return lot_size
    scaled = lot_size * max(multiplier, 0.0)
    scaled = math.floor(scaled / 0.01) * 0.01
    return scaled if scaled >= 0.01 else 0.0

def run_trading_loop(state_manager):
    """Ref: Page 14 - Complete Trade Lifecycle Loop"""
    logging.info("--- STARTING MAIN TRADING LOOP ---")

    while True:
        try:
            # PHASE 1: PRE-FLIGHT CHECKS
            # 1. Reset daily counters at Midnight UTC (Ref: Page 53)
            state_manager.reset_if_new_day()

            # 2. Check Global Kill Switch (Ref: Page 52)
            if state_manager.state.trading_disabled:
                logging.critical("SYSTEM DISABLED: Manual review required.")
                break

            # PHASE 2: THE DECISION PIPELINE (The Hierarchical Veto)
            # Ref: Page 4 - Each stage can VETO (continue to next loop)
            
            # Mock data for testing
            bar = data.get_mock_bar()

            # LAYER 1: DATA INTEGRITY (Ref: Page 5)
            #bar = data.get_processed_bar()
            if bar is None:

                continue # Veto: Data invalid or connection lost
            """
            orgin
            """
            logging.info(f"Bar {bar['bar_index']}: open={bar['open']:.5f}, close={bar['close']:.5f}, atr={bar['atr']:.5f}")

            # LAYER 2: MARKET CONTEXT (Ref: Page 6)
            print("Regime Analysis Starting...")
            context = regime.analyze_regime(bar)
            logging.info(f"Regime: {context['volatility']}/{context['structure']}, allowed={context['trade_allowed']}")

            if not context['trade_allowed']:
                if context["trade_allowed"] == False:
                    print("Regime vetoed: Trading is false.")
                    print(f"Veto Reason: {context['veto_reason']}")
                    veto_reset()
                    print("Activity vetoed. Resetting to main loop.")

                    continue
                print("Regime Error: Status is None.")
                veto_reset()
                print("Activity vetoed. Resetting to main loop.")

                continue # Veto: Unfavorable market conditions

            # LAYER 3: SIGNAL GENERATION (Ref: Page 6)
            print("Strategy Evaluation Starting...")
            signal = strategy.evaluate_strategy(bar, context)

            if signal is None:

                print("Singal Error: Status is None.")
                veto_reset()
                continue # Veto: No high-probability setup found
            print("96")
            logging.info(f"Signal: {signal['direction']} @ {signal['entry_price']}, SL={signal['sl']}, TP={signal['tp']}")

            # LAYER 4: BEHAVIORAL FILTER (Ref: Page 7)
            print("Psychology Check Starting...")
            if not psychology.is_allowed(state_manager.state, bar):
                continue # Veto: Daily limit or cooldown active

            # LAYER 4.5: SESSION FILTER (UTC)
            if not session.is_allowed(bar.get("timestamp")):
                continue

            # LAYER 5: COST MANAGEMENT (Ref: Page 7)
            print("Cost Management Check Starting...")
            if not costs.is_acceptable(bar['spread'], bar.get("timestamp")):
                continue # Veto: Spread/Friction too high

            # LAYER 6: RISK MANAGEMENT (Ref: Page 7)
            print("Risk Management Calculation Starting...")
            lot_size = risk.calculate_size(
                equity=mt5.account_info().equity,
                stop_distance_pips=signal['stop_distance'],
                current_price=bar['close']
            )
            risk_mult = signal.get("risk_multiplier", context.get("risk_multiplier", 1.0))
            if risk_mult <= 0:
                continue
            lot_size = _apply_risk_multiplier(lot_size, risk_mult)
            if lot_size <= 0:
                print("Lot size calculated as zero or negative.")
                continue # Veto: Risk/Leverage violation or size too small

            # LAYER 7: EXECUTION (Ref: Page 8)
            print("Trade Execution Starting...")
            execution_result = execution.execute_trade(signal, lot_size)

            # PHASE 3: POST-TRADE UPDATES (Ref: Page 19)
            if execution_result:
                # Success: Update state and trigger monitoring
                state_manager.state.trades_today += 1
                state_manager.state.last_trade_bar = bar['bar_index']
                state_manager.save()
                
                monitoring.analyze_execution(execution_result, state_manager.state)
                logging.info(f"✅ Trade executed successfully: {lot_size} lots.")
            else:
                # Failure: Track technical health
                print("Execution failed. Logging failure.")
                monitoring.log_execution_failure(state_manager.state)
                state_manager.save()
            # PHASE 4: LOOP CONTINUATION (Ref: Page 19)
            # Wait for the start of the next 1-minute bar
            time.sleep(config.LOOP_DELAY_SECONDS)
        except KeyboardInterrupt:
            logging.info("User initiated stop.")
            break
        except Exception as e:
            logging.exception(f"CRITICAL LOOP ERROR: {e}")
            time.sleep(10) # Pause before retry
            continue

        # PHASE 4: LOOP CONTINUATION (Ref: Page 19)
        # Wait for the start of the next 1-minute bar
        #time.sleep(config.LOOP_DELAY_SECONDS)

if __name__ == "__main__":
    # 0. Pre-flight: calibration + backtest
    try:
        calibration.run_default_calibration()
    except Exception as e:
        logging.exception(f"Calibration failed: {e}")

    try:
        back_test.run_simulation(verbose=False)
    except Exception as e:
        logging.exception(f"Backtest failed: {e}")

    # 1. Live trading
    sm = initialize_system()
    if sm:
        try:
            run_trading_loop(sm)
        finally:
            shutdown_sequence(sm)
