"""
backtest.py - The Deterministic Simulator
Purpose: Iterates through historical data using the production decision pipeline.
Ref: Pages 5, 27, 40, 61
"""

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from contextlib import contextmanager, redirect_stdout
import os
import math
from backtest_config import MAX_BARS_IN_TRADE  # already imported via * but explicit is fine


# Import production modules
import data, indicators, regime, strategy, psychology, costs, risk, session, microstructure
# Import simulation settings
from backtest_config import *
from backtest_config import (
    BT_MEAN_REVERSION_ONLY,
    BE_TRIGGER_R_MULT,
    BE_OFFSET_PIPS,
    MS_ENABLE,
    SWAP_LONG_PER_LOT,
    SWAP_SHORT_PER_LOT
)
from config import EXTENDED_MULTIPLIER
from config import EXTENDED_MULTIPLIER
from performance import PerformanceAnalyzer

PIP_SIZE = 0.0001

@contextmanager
def _suppress_stdout(enabled):
    if enabled:
        yield
        return
    with open(os.devnull, "w") as devnull, redirect_stdout(devnull):
        yield

def _apply_risk_multiplier(lot_size, multiplier):
    if multiplier >= 1.0:
        return lot_size
    scaled = lot_size * max(multiplier, 0.0)
    # Floor to broker step (0.01) without rounding up
    scaled = math.floor(scaled / 0.01) * 0.01
    return scaled if scaled >= 0.01 else 0.0

def _apply_microstructure(spread_price, slippage_pips, atr_zscore, timestamp_utc):
    if not MS_ENABLE:
        return spread_price, slippage_pips
    return microstructure.adjust_spread_slippage(spread_price, slippage_pips, atr_zscore, timestamp_utc)

def _count_rollovers(entry_time, exit_time):
    if exit_time <= entry_time:
        return 0
    rollover = entry_time.replace(hour=22, minute=0, second=0, microsecond=0)
    if entry_time >= rollover:
        rollover += timedelta(days=1)
    count = 0
    while rollover <= exit_time:
        count += 1
        rollover += timedelta(days=1)
    return count

def _calc_swap(trade, exit_time):
    rollovers = _count_rollovers(trade['time'], exit_time)
    if rollovers <= 0:
        return 0.0
    rate = SWAP_LONG_PER_LOT if trade['type'] == "BUY" else SWAP_SHORT_PER_LOT
    return rate * trade['size'] * rollovers

def _select_signal_by_bias(bar_dict, market_context):
    bias = market_context.get("strategy_bias")
    if BT_MEAN_REVERSION_ONLY:
        if bias != "mean_reversion":
            return None
        bias = "mean_reversion"
    if bias == "trend":
        signal = strategy.get_trend_following_signal(bar_dict, market_context)
    elif bias == "mean_reversion":
        signal = strategy.get_mean_reversion_signal(bar_dict)
    else:
        return None

    if signal and bar_dict['range'] > (bar_dict['atr'] * EXTENDED_MULTIPLIER):
        return None
    return signal

def _select_sim_signal_by_bias(bar_dict, market_context, rr_min, atr_multiplier, ext_mult):
    bias = market_context.get("strategy_bias")
    if BT_MEAN_REVERSION_ONLY:
        if bias != "mean_reversion":
            return None
        bias = "mean_reversion"
    if bias == "trend":
        signal = strategy.sim_get_trend_following_signal(bar_dict, rr_min, atr_multiplier)
    elif bias == "mean_reversion":
        signal = strategy.sim_get_mean_reversion_signal(bar_dict, rr_min, atr_multiplier)
    else:
        return None

    if signal and bar_dict['range'] > (bar_dict['atr'] * ext_mult):
        return None
    return signal

def _maybe_move_breakeven(trade, current_bar):
    if trade is None or trade.get("be_moved"):
        return
    stop_distance = trade.get("stop_distance")
    if not stop_distance:
        stop_distance = abs(trade.get("entry_price", 0.0) - trade.get("sl", 0.0))
    if stop_distance <= 0:
        return

    trigger_move = stop_distance * BE_TRIGGER_R_MULT
    entry_exec = trade.get("entry_price", 0.0)
    be_offset = BE_OFFSET_PIPS * PIP_SIZE
    mid_low = current_bar['low']
    mid_high = current_bar['high']

    if trade['type'] == "BUY":
        if mid_high >= entry_exec + trigger_move:
            trade['sl'] = max(trade['sl'], entry_exec + be_offset)
            trade['be_moved'] = True
    else:
        if mid_low <= entry_exec - trigger_move:
            trade['sl'] = min(trade['sl'], entry_exec - be_offset)
            trade['be_moved'] = True

def opt_ind_test(atr_period,
            ema_fast_period, 
            ema_slow_period, 
            adx_period, 
            zscore_period, 
            atr_zscore_period,
            verbose=True):
    """
    The function Optuna will try to maximize.
    We define the 'Search Space' here.
    """

    # 1. Initialize and Fetch Data
    if not mt5.initialize():
        print("MT5 initialization failed")
        return

    print(f"Fetching {BT_SYMBOL} data for simulation...")
    rates = mt5.copy_rates_range(
        BT_SYMBOL, 
        mt5.TIMEFRAME_M2, 
        BT_START_DATE, 
        BT_END_DATE
    )
    mt5.shutdown()
    print(len(rates), "bars retrieved.")
    
    if rates is None or len(rates) < WARMUP_PERIOD:
        print("Insufficient historical data.")
        return

    # 2. Setup Virtual Environment
    equity = BT_INITIAL_BALANCE
    trade_history = []
    active_trade = None
    
    # Virtual State (Ref: Page 25)
    from state import TradingState
    bt_state = TradingState(trading_day=BT_START_DATE.strftime("%Y-%m-%d"))

    print(f"Simulation started: {len(rates)} bars.")

    # 3. Main Simulation Loop
    with _suppress_stdout(verbose):
        for i in range(WARMUP_PERIOD, len(rates)):
            # Ref Page 27: Extract window. window[-1] is the bar we are 'at'
            # window[-2] is the last completed bar we use for signals
            window = rates[i - WARMUP_PERIOD : i]
            current_bar_data = window[-1] 
            
            # --- TRADE MANAGEMENT (Check Exits) ---
            if active_trade:
                # Check High/Low of current bar to see if SL or TP hit
                _maybe_move_breakeven(active_trade, current_bar_data)
                exit_data = check_exit_conditions(active_trade, current_bar_data)
                if exit_data:
                    gross_pnl = exit_data['raw_pnl']
                    commission_cost = active_trade.get('commission_per_lot', 0.0) * active_trade['size'] * 2.0
                    net_pnl = gross_pnl - commission_cost
                    swap_cost = _calc_swap(active_trade, datetime.fromtimestamp(current_bar_data['time']))
                    net_pnl -= swap_cost

                    equity += net_pnl

                    # Record Trade for PerformanceAnalyzer
                    trade_history.append({
                        'entry_time': active_trade['time'],
                        'exit_time': datetime.fromtimestamp(current_bar_data['time']),
                        'result': exit_data['result'],
                        'pnl': net_pnl,
                        'balance': equity,
                        'return_pct': net_pnl / (equity - net_pnl),
                        'type': active_trade['type'],
                        'structure': active_trade.get('structure'),
                        'strategy': active_trade.get('strategy'),
                        'entry_hour': active_trade.get('entry_hour'),
                        'zscore': active_trade.get('zscore'),
                        'atr_zscore': active_trade.get('atr_zscore'),
                        'spread': active_trade.get('spread'),
                        'stop_distance': active_trade.get('stop_distance'),
                        'target_distance': active_trade.get('target_distance')
                    })

                    # Update State for Psychology Layer (Cooldown)
                    bt_state.last_trade_bar = i
                    active_trade = None
                continue

            # --- THE HIERARCHICAL VETO PIPELINE ---
            
            # Layer 1 & Indicators (Data)
            bar_dict = opt_data_adapter(window, atr_period, ema_fast_period, ema_slow_period, adx_period, zscore_period, atr_zscore_period)

            
            # Layer 2: Regime (Context)
            market_context = regime.analyze_regime(bar_dict)
            if not market_context['trade_allowed']: continue
            
            # Layer 3: Strategy (Signal)
            #signal = strategy.evaluate_signal(bar_dict, market_context)
            signal = _select_signal_by_bias(bar_dict, market_context)
            if signal is None: continue
            
            # Layer 4: Psychology (Discipline)
            # Note: We pass the loop index 'i' as the bar index
            #if not psychology.backtest_check(bt_state, i): continue
            if not psychology.is_allowed(bt_state, bar_dict): continue
            if not session.is_allowed(bar_dict.get('timestamp')): continue
            
            # Layer 5: Costs (Friction)
            # We use fixed spread from config for the backtest

            current_spread_price = bar_dict['spread']

            costs_ok = costs.is_acceptable(current_spread_price, bar_dict.get('timestamp'))
            if not costs_ok: continue
            
            # Layer 6: Risk (Position Sizing)
            #lot_size = risk.calculate_position_size(equity, bar_dict['atr'])
            lot_size = risk.calculate_size(
                equity,
                signal['stop_distance'],
                bar_dict['close']
                
                )
            lot_size = _apply_risk_multiplier(lot_size, market_context.get("risk_multiplier", 1.0))


            
            if lot_size <= 0:
                continue

            # Layer 7: Virtual Execution
            direction = signal['direction']
            mid_price = bar_dict['close']
            spread_price = bar_dict['spread']
            spread_price, slippage_pips = _apply_microstructure(
                spread_price,
                FIXED_SLIPPAGE_PIPS,
                bar_dict.get('atr_zscore'),
                bar_dict.get('timestamp')
            )
            half_spread = spread_price / 2.0
            slip_price = slippage_pips * PIP_SIZE

            if direction == "BUY":
                entry_exec_price = mid_price + half_spread + slip_price
            else:
                entry_exec_price = mid_price - half_spread - slip_price

            active_trade = {
                'time': datetime.fromtimestamp(current_bar_data['time']),
                'type': direction,
                'entry_price': entry_exec_price,
                'sl': signal['sl'],
                'tp': signal['tp'],
                'size': lot_size,
                'entry_bar_index': i,
                'structure': market_context.get('structure'),
                'strategy': signal.get('strategy'),
                'entry_hour': datetime.fromtimestamp(current_bar_data['time']).hour,
                'zscore': bar_dict.get('zscore'),
                'atr_zscore': bar_dict.get('atr_zscore'),
                'spread': spread_price,
                'stop_distance': signal.get('stop_distance'),
                'target_distance': signal.get('target_distance'),
                'slippage_pips': slippage_pips,
                'commission_per_lot': COMMISSION_PER_LOT
            }

    # 4. Generate Performance Report
    analyzer = PerformanceAnalyzer(
        trade_history, 
        BT_INITIAL_BALANCE, 
        BT_START_DATE, 
        BT_END_DATE
    )


    repo_print = analyzer.generate_report()
    return repo_print['print_report']


def opt_test(atr_period,
            ema_fast_period, 
            ema_slow_period, 
            adx_period, 
            zscore_period, 
            atr_zscore_period, 
            ext_mult, 
            rr_min, 
            atr_multiplier, 
            med_spread, 
            max_spread_mult, 
            exp_slippage,
            risk_per_trade,
            max_leverage,
            verbose=True
            ):

    # 1. Initialize and Fetch Data
    if not mt5.initialize():
        print("MT5 initialization failed")
        return

    print(f"Fetching {BT_SYMBOL} data for simulation...")
    rates = mt5.copy_rates_range(
        BT_SYMBOL, 
        mt5.TIMEFRAME_M2, 
        BT_START_DATE, 
        BT_END_DATE
    )
    mt5.shutdown()
    print(len(rates), "bars retrieved.")
    
    if rates is None or len(rates) < WARMUP_PERIOD:
        print("Insufficient historical data.")
        return

    # 2. Setup Virtual Environment
    equity = BT_INITIAL_BALANCE
    trade_history = []
    active_trade = None
    
    # Virtual State (Ref: Page 25)
    from state import TradingState
    bt_state = TradingState(trading_day=BT_START_DATE.strftime("%Y-%m-%d"))

    print(f"Simulation started: {len(rates)} bars.")

    # 3. Main Simulation Loop
    with _suppress_stdout(verbose):
        for i in range(WARMUP_PERIOD, len(rates)):
            # Ref Page 27: Extract window. window[-1] is the bar we are 'at'
            # window[-2] is the last completed bar we use for signals
            window = rates[i - WARMUP_PERIOD : i]
            current_bar_data = window[-1]

            # --- TRADE MANAGEMENT (Check Exits) ---
            if active_trade:
                # Check High/Low of current bar to see if SL or TP hit
                _maybe_move_breakeven(active_trade, current_bar_data)
                exit_data = check_exit_conditions(active_trade, current_bar_data)
                if exit_data:
                    gross_pnl = exit_data['raw_pnl']
                    commission_cost = active_trade.get('commission_per_lot', 0.0) * active_trade['size'] * 2.0
                    net_pnl = gross_pnl - commission_cost
                    swap_cost = _calc_swap(active_trade, datetime.fromtimestamp(current_bar_data['time']))
                    net_pnl -= swap_cost

                    equity += net_pnl

                    # Record Trade for PerformanceAnalyzer
                    trade_history.append({
                        'entry_time': active_trade['time'],
                        'exit_time': datetime.fromtimestamp(current_bar_data['time']),
                        'result': exit_data['result'],
                        'pnl': net_pnl,
                        'balance': equity,
                        'return_pct': net_pnl / (equity - net_pnl),
                        'type': active_trade['type'],
                        'structure': active_trade.get('structure'),
                        'strategy': active_trade.get('strategy'),
                        'entry_hour': active_trade.get('entry_hour'),
                        'zscore': active_trade.get('zscore'),
                        'atr_zscore': active_trade.get('atr_zscore'),
                        'spread': active_trade.get('spread'),
                        'stop_distance': active_trade.get('stop_distance'),
                        'target_distance': active_trade.get('target_distance')
                    })

                    # Update State for Psychology Layer (Cooldown)
                    bt_state.last_trade_bar = i
                    active_trade = None
                continue

            # --- THE HIERARCHICAL VETO PIPELINE ---

            # Layer 1 & Indicators (Data)
            bar_dict = opt_data_adapter(window, atr_period, ema_fast_period, ema_slow_period, adx_period, zscore_period, atr_zscore_period)

            # Layer 2: Regime (Context)
            market_context = regime.analyze_regime(bar_dict)
            if not market_context['trade_allowed']:
                continue

            # Layer 3: Strategy (Signal)
            #signal = strategy.evaluate_signal(bar_dict, market_context)
            signal = _select_sim_signal_by_bias(bar_dict, market_context, rr_min, atr_multiplier, ext_mult)
            if signal is None:
                continue

            # Layer 4: Psychology (Discipline)
            # Note: We pass the loop index 'i' as the bar index
            #if not psychology.backtest_check(bt_state, i): continue
            if not psychology.is_allowed(bt_state, bar_dict):
                continue
            if not session.is_allowed(bar_dict.get('timestamp')):
                continue

            # Layer 5: Costs (Friction)
            # We use fixed spread from config for the backtest
            current_spread_price = bar_dict['spread']

            costs_ok = costs.simulate_acceptable(
                current_spread_price,
                med_spread,
                max_spread_mult,
                exp_slippage,
                bar_dict.get('timestamp')
            )
            if not costs_ok:
                continue

            # Layer 6: Risk (Position Sizing)
            #lot_size = risk.calculate_position_size(equity, bar_dict['atr'])
            effective_risk = risk_per_trade * market_context.get("risk_multiplier", 1.0)
            if effective_risk <= 0:
                continue
            lot_size = risk.simulate_size(
                equity,
                signal['stop_distance'],
                bar_dict['close'],
                effective_risk,
                max_leverage
            )
            if lot_size <= 0:
                continue

            # Layer 7: Virtual Execution
            direction = signal['direction']
            mid_price = bar_dict['close']
            spread_price = bar_dict['spread']
            spread_price, slippage_pips = _apply_microstructure(
                spread_price,
                FIXED_SLIPPAGE_PIPS,
                bar_dict.get('atr_zscore'),
                bar_dict.get('timestamp')
            )
            half_spread = spread_price / 2.0
            slip_price = slippage_pips * PIP_SIZE

            if direction == "BUY":
                entry_exec_price = mid_price + half_spread + slip_price
            else:
                entry_exec_price = mid_price - half_spread - slip_price

            active_trade = {
                'time': datetime.fromtimestamp(current_bar_data['time']),
                'type': direction,
                'entry_price': entry_exec_price,
                'sl': signal['sl'],
                'tp': signal['tp'],
                'size': lot_size,
                'structure': market_context.get('structure'),
                'strategy': signal.get('strategy'),
                'entry_hour': datetime.fromtimestamp(current_bar_data['time']).hour,
                'zscore': bar_dict.get('zscore'),
                'atr_zscore': bar_dict.get('atr_zscore'),
                'spread': spread_price,
                'stop_distance': signal.get('stop_distance'),
                'target_distance': signal.get('target_distance'),
                'slippage_pips': slippage_pips,
                'commission_per_lot': COMMISSION_PER_LOT
            }

    # 4. Generate Performance Report
    analyzer = PerformanceAnalyzer(
        trade_history, 
        BT_INITIAL_BALANCE, 
        BT_START_DATE, 
        BT_END_DATE
    )

    repo_print = analyzer.generate_report()
    return repo_print['print_report']

def opt_data_adapter(window, atr_period, ema_fast_period, ema_slow_period, adx_period, zscore_period, atr_zscore_period):
    """Ref: Page 26 - Processed Bar Enrichment"""
    # Use window[-2] to avoid lookahead bias
    target_bar = window[-2]
    # Pass window[:-1] to avoid indicators seeing the 'future' bar
    metrics = indicators.simulate_indicators(window[:-1], atr_period, ema_fast_period, ema_slow_period, adx_period, zscore_period, atr_zscore_period)
    raw_spread_points = float(target_bar['spread'])
    actual_spread_price = raw_spread_points * 0.00001

    return {
        'bar_index': target_bar['time'],
        'timestamp': datetime.fromtimestamp(target_bar['time']),
        'close': target_bar['close'],
        'high': target_bar['high'],
        'low': target_bar['low'],
        'spread': actual_spread_price,
        "range": float(target_bar['high'] - target_bar['low']),
        'atr': metrics['atr'],
        'atr_zscore': metrics['atr_zscore'],
        **metrics
    }



def _run_simulation_core(start_date, end_date, verbose=True):
    # 1. Initialize and Fetch Data
    if not mt5.initialize():
        print("MT5 initialization failed")
        return None, []

    print(f"Fetching {BT_SYMBOL} data for simulation...")
    rates = mt5.copy_rates_range(
        BT_SYMBOL, 
        mt5.TIMEFRAME_M2, 
        start_date, 
        end_date
    )
    mt5.shutdown()
    print(len(rates), "bars retrieved.")
    
    if rates is None or len(rates) < WARMUP_PERIOD:
        print("Insufficient historical data.")
        return None, []

    # 2. Setup Virtual Environment
    equity = BT_INITIAL_BALANCE
    trade_history = []
    active_trade = None
    
    # Virtual State (Ref: Page 25)
    from state import TradingState
    bt_state = TradingState(trading_day=start_date.strftime("%Y-%m-%d"))

    print(f"Simulation started: {len(rates)} bars.")

    # 3. Main Simulation Loop
    with _suppress_stdout(verbose):
        for i in range(WARMUP_PERIOD, len(rates)):
            # Ref Page 27: Extract window. window[-1] is the bar we are 'at'
            # window[-2] is the last completed bar we use for signals
            window = rates[i - WARMUP_PERIOD : i]
            current_bar_data = window[-1] 
            
            # --- TRADE MANAGEMENT (Check Exits) ---
            if active_trade:
                # Check High/Low of current bar to see if SL or TP hit
                _maybe_move_breakeven(active_trade, current_bar_data)
                exit_data = check_exit_conditions(active_trade, current_bar_data)
                if exit_data:
                    gross_pnl = exit_data['raw_pnl']
                    commission_cost = active_trade.get('commission_per_lot', 0.0) * active_trade['size'] * 2.0
                    net_pnl = gross_pnl - commission_cost
                    swap_cost = _calc_swap(active_trade, datetime.fromtimestamp(current_bar_data['time']))
                    net_pnl -= swap_cost
                    
                    equity += net_pnl
                    
                    # Record Trade for PerformanceAnalyzer
                    trade_history.append({
                        'entry_time': active_trade['time'],
                        'exit_time': datetime.fromtimestamp(current_bar_data['time']),
                        'result': exit_data['result'],
                        'pnl': net_pnl,
                        'balance': equity,
                        'return_pct': net_pnl / (equity - net_pnl),
                        'type': active_trade['type'],
                        'structure': active_trade.get('structure'),
                        'strategy': active_trade.get('strategy'),
                        'entry_hour': active_trade.get('entry_hour'),
                        'zscore': active_trade.get('zscore'),
                        'atr_zscore': active_trade.get('atr_zscore'),
                        'spread': active_trade.get('spread'),
                        'stop_distance': active_trade.get('stop_distance'),
                        'target_distance': active_trade.get('target_distance')
                    })
                    
                    # Update State for Psychology Layer (Cooldown)
                    bt_state.last_trade_bar = i
                    active_trade = None
                    continue


            # --- THE HIERARCHICAL VETO PIPELINE ---
            
            # Layer 1 & Indicators (Data)
            bar_dict = data_adapter(window)

            
            # Layer 2: Regime (Context)
            market_context = regime.analyze_regime(bar_dict)
            if not market_context['trade_allowed']:
                continue
            
            # Layer 3: Strategy (Signal)
            #signal = strategy.evaluate_signal(bar_dict, market_context)
            signal = _select_signal_by_bias(bar_dict, market_context)
            if signal is None:
                continue
            
            # Layer 4: Psychology (Discipline)
            # Note: We pass the loop index 'i' as the bar index
            #if not psychology.backtest_check(bt_state, i): continue
            if not psychology.is_allowed(bt_state, bar_dict):
                continue
            if not session.is_allowed(bar_dict.get('timestamp')):
                continue
            
            # Layer 5: Costs (Friction)
            # We use fixed spread from config for the backtest
            current_spread_price = bar_dict['spread']

            costs_ok = costs.is_acceptable(current_spread_price, bar_dict.get('timestamp'))
            if not costs_ok:
                continue
            
            # Layer 6: Risk (Position Sizing)
            #lot_size = risk.calculate_position_size(equity, bar_dict['atr'])
            lot_size = risk.calculate_size(
                equity=equity,
                stop_distance_pips=signal['stop_distance'],
                current_price=bar_dict['close']
            )
            lot_size = _apply_risk_multiplier(lot_size, market_context.get("risk_multiplier", 1.0))
            if lot_size <= 0:
                continue

            # Layer 7: Virtual Execution
            direction = signal['direction']
            mid_price = bar_dict['close']
            spread_price = bar_dict['spread']
            half_spread = spread_price / 2.0
            spread_price, slippage_pips = _apply_microstructure(
                spread_price,
                FIXED_SLIPPAGE_PIPS,
                bar_dict.get('atr_zscore'),
                bar_dict.get('timestamp')
            )
            half_spread = spread_price / 2.0
            slip_price = slippage_pips * PIP_SIZE

            if direction == "BUY":
                entry_exec_price = mid_price + half_spread + slip_price
            else:
                entry_exec_price = mid_price - half_spread - slip_price

            active_trade = {
                'time': datetime.fromtimestamp(current_bar_data['time']),
                'type': direction,
                'entry_price': entry_exec_price,
                'sl': signal['sl'],
                'tp': signal['tp'],
                'size': lot_size,
                'entry_bar_index': i,
                'structure': market_context.get('structure'),
                'strategy': signal.get('strategy'),
                'entry_hour': datetime.fromtimestamp(current_bar_data['time']).hour,
                'zscore': bar_dict.get('zscore'),
                'atr_zscore': bar_dict.get('atr_zscore'),
                'spread': spread_price,
                'stop_distance': signal.get('stop_distance'),
                'target_distance': signal.get('target_distance'),
                'slippage_pips': slippage_pips,
                'commission_per_lot': COMMISSION_PER_LOT
            }

    # 4. Generate Performance Report
    analyzer = PerformanceAnalyzer(
        trade_history, 
        BT_INITIAL_BALANCE, 
        start_date, 
        end_date
    )
    repo_print = analyzer.generate_report()
    return repo_print['print_report'], trade_history

def run_simulation(verbose=True):
    report, _trades = _run_simulation_core(BT_START_DATE, BT_END_DATE, verbose=verbose)
    return report

def run_simulation_with_trades(verbose=True):
    return _run_simulation_core(BT_START_DATE, BT_END_DATE, verbose=verbose)

def run_simulation_window(start_date, end_date, verbose=True):
    return _run_simulation_core(start_date, end_date, verbose=verbose)


def data_adapter(window):
    """Ref: Page 26 - Processed Bar Enrichment"""
    # Use window[-2] to avoid lookahead bias
    target_bar = window[-2]
    # Pass window[:-1] to avoid indicators seeing the 'future' bar
    metrics = indicators.enrich_bar_with_indicators(window[:-1])
    raw_spread_points = float(target_bar['spread'])
    actual_spread_price = raw_spread_points * 0.00001

    return {
        'bar_index': target_bar['time'],
        'timestamp': datetime.fromtimestamp(target_bar['time']),
        'close': target_bar['close'],
        'high': target_bar['high'],
        'low': target_bar['low'],
        'spread': actual_spread_price,
        "range": float(target_bar['high'] - target_bar['low']),
        'atr': metrics['atr'],
        'atr_zscore': metrics['atr_zscore'],
        **metrics
    }

def check_exit_conditions(trade, current_bar):
    """
    Checks if a trade was stopped out or hit profit in the current bar
    and calculates raw PnL using bid/ask-aware fills with spread + slippage.

    - SL/TP triggers are evaluated on MID OHLC (current_bar['high'] / ['low']).
    - Fills:
        * BUY: enter at ask, exit at bid
        * SELL: enter at bid, exit at ask
    """
    contract_size = 100000
    direction = trade['type']
    size = trade['size']

    spread = trade.get('spread', 0.0)
    half_spread = spread / 2.0

    slippage_pips = trade.get('slippage_pips', 0.0)
    slippage_price = slippage_pips * PIP_SIZE

    entry_exec = trade['entry_price']

    mid_low = current_bar['low']
    mid_high = current_bar['high']

    hit_sl = False
    hit_tp = False

    if direction == 'BUY':
        if mid_low <= trade['sl']:
            hit_sl = True
        if mid_high >= trade['tp']:
            hit_tp = True
    else:
        if mid_high >= trade['sl']:
            hit_sl = True
        if mid_low <= trade['tp']:
            hit_tp = True

    if not hit_sl and not hit_tp:
        return None

    exit_side = 'SL' if hit_sl else 'TP'
    mid_exit = trade['sl'] if exit_side == 'SL' else trade['tp']

    if direction == 'BUY':
        exit_exec = mid_exit - half_spread - slippage_price
        raw_pnl = (exit_exec - entry_exec) * contract_size * size
    else:
        exit_exec = mid_exit + half_spread + slippage_price
        raw_pnl = (entry_exec - exit_exec) * contract_size * size

    result = 'LOSS' if exit_side == 'SL' else 'WIN'
    return {
        'result': result,
        'raw_pnl': raw_pnl,
    }

if __name__ == "__main__":
    report = run_simulation(verbose=False)
    if isinstance(report, dict):
        print("\n=== BACKTEST PERFORMANCE REPORT ===")
        for k, v in report.items():
            print(f"{k.ljust(20)}: {v}")
    else:
        print(report)
