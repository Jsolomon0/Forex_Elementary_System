# optimizer.py
import optuna
import data, regime, strategy, risk
import MetaTrader5 as mt5
from config import SYMBOL
import indicators
# Import production modules
import data, indicators, regime, strategy, psychology, costs, risk
# Import simulation settings
from backtest_config import *
from performance import PerformanceAnalyzer

def objective_ind(trial):
    """
    The function Optuna will try to maximize.
    We define the 'Search Space' here.
    """
    # 1. HYPERPARAMETERS TO OPTIMIZE

    # 1.1 indicator hyperparameters
    atr_period = trial.suggest_int("atr_p", 7, 20)
    ema_fast_period = trial.suggest_int("ema_f", 5, 20)
    ema_slow_period = trial.suggest_int("ema_s", 50, 200)
    adx_period = trial.suggest_int("adx_p", 5, 20)
    zscore_period = trial.suggest_int("z_p", 15, 30)
    atr_zscore_period = trial.suggest_int("atr_z_p", 5, 20)




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
    for i in range(WARMUP_PERIOD, len(rates)):
        # Ref Page 27: Extract window. window[-1] is the bar we are 'at'
        # window[-2] is the last completed bar we use for signals
        window = rates[i - WARMUP_PERIOD : i]
        current_bar_data = window[-1] 
        
        # --- TRADE MANAGEMENT (Check Exits) ---
        if active_trade:
            # Check High/Low of current bar to see if SL or TP hit
            exit_data = check_exit_conditions(active_trade, current_bar_data)
            if exit_data:
                # Calculate PnL with Slippage (Ref: Page 40)
                slippage_loss = FIXED_SLIPPAGE_PIPS * 0.00010 * 100000 * active_trade['size']
                net_pnl = exit_data['raw_pnl'] - slippage_loss
                
                equity += net_pnl
                
                # Record Trade for PerformanceAnalyzer
                trade_history.append({
                    'entry_time': active_trade['time'],
                    'exit_time': datetime.fromtimestamp(current_bar_data['time']),
                    'result': exit_data['result'],
                    'pnl': net_pnl,
                    'balance': equity,
                    'return_pct': net_pnl / (equity - net_pnl),
                    'type': active_trade['type']
                })
                
                # Update State for Psychology Layer (Cooldown)
                bt_state.last_trade_bar = i
                active_trade = None
            continue

        # --- THE HIERARCHICAL VETO PIPELINE ---
        
        # Layer 1 & Indicators (Data)
        bar_dict = data_adapter(window, atr_period, ema_fast_period, ema_slow_period, adx_period, zscore_period, atr_zscore_period)

        
        # Layer 2: Regime (Context)
        market_context = regime.analyze_regime(bar_dict)
        if not market_context['trade_allowed']: continue
        
        # Layer 3: Strategy (Signal)
        #signal = strategy.evaluate_signal(bar_dict, market_context)
        signal = strategy.evaluate_strategy(bar_dict, market_context)
        if signal is None: continue
        
        # Layer 4: Psychology (Discipline)
        # Note: We pass the loop index 'i' as the bar index
        #if not psychology.backtest_check(bt_state, i): continue
        if not psychology.is_allowed(bt_state, bar_dict): continue
        
        # Layer 5: Costs (Friction)
        # We use fixed spread from config for the backtest

        current_spread_price = bar_dict['spread']

        costs_ok = costs.is_acceptable(current_spread_price)
        if not costs_ok: continue
        
        # Layer 6: Risk (Position Sizing)
        #lot_size = risk.calculate_position_size(equity, bar_dict['atr'])
        lot_size = risk.calculate_size(
            equity,
            signal['stop_distance'],
            bar_dict['close']
            
            )
            


        
        if lot_size <= 0: continue

        # Layer 7: Virtual Execution
        active_trade = {
            'time': datetime.fromtimestamp(current_bar_data['time']),
            'type': signal['direction'],
            'entry_price': bar_dict['close'],
            'sl': signal['sl'],
            'tp': signal['tp'],
            'size': lot_size
        }

    # 4. Generate Performance Report
    analyzer = PerformanceAnalyzer(
        trade_history, 
        BT_INITIAL_BALANCE, 
        BT_START_DATE, 
        BT_END_DATE
    )

    report = analyzer.generate_report()

    maxing = (report["win_rate"] * report["sharpe_ratio"] * report["net_profit"]) / (abs(report["mdd"]) + 1e-6)

    return maxing


def objective(trial):
    """
    The function Optuna will try to maximize.
    We define the 'Search Space' here.
    """
    # 1. HYPERPARAMETERS TO OPTIMIZE

    # 1.1 indicator hyperparameters
    atr_period = trial.suggest_int("atr_p", 10, 20)
    #atr_multiplier = trial.suggest_float("atr_mult", 1.0, 3.0)
    ema_fast_period = trial.suggest_int("ema_f", 10, 30)
    ema_slow_period = trial.suggest_int("ema_s", 40, 80)
    adx_period = trial.suggest_int("adx_p", 10, 20)
    zscore_period = trial.suggest_int("z_p", 15, 30)
    #adx_threshold = trial.suggest_int("adx_th", 20, 35)
    #at_zscore_th = trial.suggest_int("atr_z_th", -1.0, 1.0)
    atr_zscore_period = trial.suggest_int("atr_z_p", 15, 30)

    """
    # 1.2 regime hyperparameters
    vol_z_compression = trial.suggest_float("vol_z_comp", -2.0, 0.0)
    vol_z_expansion = trial.suggest_float("vol_z_exp", 0.0, 2.0)
    adx_threshold = trial.suggest_int("adx_th", 20, 50)
    """
    # 1.3 strategy hyperparameters
    atr_multiplier = trial.suggest_float("atr_mult", 1.0, 3.0)
    rr_min = trial.suggest_float("rr_min", 2.0, 4.0)
    ext_mult = trial.suggest_float("ext_mult", 1.0, 3.0)

    # 1.4 psychology hyperparameters
    #max_trade = trial.suggest_int("max_trades", 3, 10)

    # 1.5 cost hyperparameters
    med_spread = trial.suggest_float("med_spread", 0.00005, 0.0002)
    max_spread_mult = trial.suggest_float("max_spread_mult", 1.2, 2.0)
    exp_slippage = trial.suggest_float("exp_slippage", 1.0, 3.0)

    # 1.6 risk hyperparameters
    risk_per_trade = trial.suggest_float("risk_per_trade", 0.002, 0.01)
    max_leverage = trial.suggest_float("max_leverage", 3.0, 10.0)


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
    for i in range(WARMUP_PERIOD, len(rates)):
        # Ref Page 27: Extract window. window[-1] is the bar we are 'at'
        # window[-2] is the last completed bar we use for signals
        window = rates[i - WARMUP_PERIOD : i]
        current_bar_data = window[-1] 
        
        # --- TRADE MANAGEMENT (Check Exits) ---
        if active_trade:
            # Check High/Low of current bar to see if SL or TP hit
            exit_data = check_exit_conditions(active_trade, current_bar_data)
            if exit_data:
                # Calculate PnL with Slippage (Ref: Page 40)
                slippage_loss = FIXED_SLIPPAGE_PIPS * 0.00010 * 100000 * active_trade['size']
                net_pnl = exit_data['raw_pnl'] - slippage_loss
                
                equity += net_pnl
                
                # Record Trade for PerformanceAnalyzer
                trade_history.append({
                    'entry_time': active_trade['time'],
                    'exit_time': datetime.fromtimestamp(current_bar_data['time']),
                    'result': exit_data['result'],
                    'pnl': net_pnl,
                    'balance': equity,
                    'return_pct': net_pnl / (equity - net_pnl),
                    'type': active_trade['type']
                })
                
                # Update State for Psychology Layer (Cooldown)
                bt_state.last_trade_bar = i
                active_trade = None
            continue

        # --- THE HIERARCHICAL VETO PIPELINE ---
        
        # Layer 1 & Indicators (Data)
        bar_dict = data_adapter(window, atr_period, ema_fast_period, ema_slow_period, adx_period, zscore_period, atr_zscore_period)

        
        # Layer 2: Regime (Context)
        market_context = regime.analyze_regime(bar_dict)
        if not market_context['trade_allowed']: continue
        
        # Layer 3: Strategy (Signal)
        #signal = strategy.evaluate_signal(bar_dict, market_context)
        signal = strategy.simulate_strategy(bar_dict, market_context, ext_mult, rr_min, atr_multiplier)
        if signal is None: continue
        
        # Layer 4: Psychology (Discipline)
        # Note: We pass the loop index 'i' as the bar index
        #if not psychology.backtest_check(bt_state, i): continue
        if not psychology.is_allowed(bt_state, bar_dict): continue
        
        # Layer 5: Costs (Friction)
        # We use fixed spread from config for the backtest

        current_spread_price = bar_dict['spread']

        costs_ok = costs.simulate_acceptable(current_spread_price, med_spread, max_spread_mult, exp_slippage)
        if not costs_ok: continue
        
        # Layer 6: Risk (Position Sizing)
        #lot_size = risk.calculate_position_size(equity, bar_dict['atr'])
        lot_size = risk.simulate_size(
            equity,
            signal['stop_distance'],
            bar_dict['close'],
            risk_per_trade,
            max_leverage
            
            )
            


        
        if lot_size <= 0: continue

        # Layer 7: Virtual Execution
        active_trade = {
            'time': datetime.fromtimestamp(current_bar_data['time']),
            'type': signal['direction'],
            'entry_price': bar_dict['close'],
            'sl': signal['sl'],
            'tp': signal['tp'],
            'size': lot_size
        }

    # 4. Generate Performance Report
    analyzer = PerformanceAnalyzer(
        trade_history, 
        BT_INITIAL_BALANCE, 
        BT_START_DATE, 
        BT_END_DATE
    )

    report = analyzer.generate_report()

    maxing = (report["win_rate"] * report["sharpe_ratio"] * report["net_profit"]) / (abs(report["mdd"]) + 1e-6)

    return maxing

def data_adapter(window, atr_period, ema_fast_period, ema_slow_period, adx_period, zscore_period, atr_zscore_period):
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

def check_exit_conditions(trade, current_bar):
    """
    Checks if a trade was stopped out or hit profit.
    Calculates raw price-to-price PnL.
    """
    # 1 lot EURUSD = $10 per pip. 
    contract_size = 100000
    
    if trade['type'] == 'BUY':
        if current_bar['low'] <= trade['sl']:
            pnl = (trade['sl'] - trade['entry_price']) * contract_size * trade['size']
            return {'result': 'LOSS', 'raw_pnl': pnl}
        if current_bar['high'] >= trade['tp']:
            pnl = (trade['tp'] - trade['entry_price']) * contract_size * trade['size']
            return {'result': 'WIN', 'raw_pnl': pnl}
            
    elif trade['type'] == 'SELL':
        if current_bar['high'] >= trade['sl']:
            pnl = (trade['entry_price'] - trade['sl']) * contract_size * trade['size']
            return {'result': 'LOSS', 'raw_pnl': pnl}
        if current_bar['low'] <= trade['tp']:
            pnl = (trade['entry_price'] - trade['tp']) * contract_size * trade['size']
            return {'result': 'WIN', 'raw_pnl': pnl}
            
    return None



# Load historical data once for speed
def get_history():
    if not mt5.initialize(): return []
    # Fetch 5000 bars (roughly 1 week of M1 data)
    rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M1, 0, 5000)
    return rates

HISTORY = get_history()

def objective0(trial):
    """
    The function Optuna will try to maximize.
    We define the 'Search Space' here.
    """
    # 1. HYPERPARAMETERS TO OPTIMIZE

    # 1.1 indicator hyperparameters
    atr_period = trial.suggest_int("atr_p", 10, 20)
    #atr_multiplier = trial.suggest_float("atr_mult", 1.0, 3.0)
    ema_fast_period = trial.suggest_int("ema_f", 10, 30)
    ema_slow_period = trial.suggest_int("ema_s", 40, 80)
    adx_period = trial.suggest_int("adx_p", 10, 20)
    zscore_period = trial.suggest_int("z_p", 15, 30)
    #adx_threshold = trial.suggest_int("adx_th", 20, 35)
    #at_zscore_th = trial.suggest_int("atr_z_th", -1.0, 1.0)
    atr_zscore_period = trial.suggest_int("atr_z_p", 15, 30)

    """
    # 1.2 regime hyperparameters
    vol_z_compression = trial.suggest_float("vol_z_comp", -2.0, 0.0)
    vol_z_expansion = trial.suggest_float("vol_z_exp", 0.0, 2.0)
    adx_threshold = trial.suggest_int("adx_th", 20, 50)
    """
    # 1.3 strategy hyperparameters
    atr_multiplier = trial.suggest_float("atr_mult", 1.0, 3.0)
    rr_min = trial.suggest_float("rr_min", 2.0, 4.0)
    ext_mult = trial.suggest_float("ext_mult", 1.0, 3.0)

    # 1.4 psychology hyperparameters
    max_trade = trial.suggest_int("max_trades", 3, 10)

    # 1.5 cost hyperparameters
    med_spread = trial.suggest_float("med_spread", 0.00005, 0.0002)
    max_spread_mult = trial.suggest_float("max_spread_mult", 1.2, 2.0)
    exp_slippage = trial.suggest_float("exp_slippage", 1.0, 3.0)

    # 1.6 risk hyperparameters
    risk_per_trade = trial.suggest_float("risk_per_trade", 0.002, 0.01)
    max_leverage = trial.suggest_float("max_leverage", 3.0, 10.0)

    # 2. SIMULATE TRADING
    balance = 1000.0
    equity_history = []
    trades = 0
    wins = 0

    # Iterate through history (skipping first 100 for indicator warmup)
    for i in range(100, len(HISTORY)):
        current_rates = HISTORY[:i]

        # Mocking the layers with trial parameters
        # (You'd need to modify your functions slightly to accept parameters)
        metrics = indicators.simulate_indicators(current_rates, atr_period, ema_fast_period, ema_slow_period, adx_period, zscore_period, atr_zscore_period)
        
        if metrics['adx'] > adx_threshold: # Simple Regime check
            signal = simulate_strategy(metrics)
            if signal:
                trades += 1
                # Simple P&L calc
                is_win = mock_trade_result(current_rates, signal, atr_multiplier)
                if is_win:
                    wins += 1
                    balance += (balance * 0.01) # 1% win
                else:
                    balance -= (balance * 0.005) # 0.5% loss (Risk Layer)

    # 3. DEFINE THE SCORE (The "Fitness" function)
    if trades < 10: return 0.0 # Ignore trials with too few trades
    
    win_rate = wins / trades
    # We want to maximize Win Rate + Trade Frequency (Efficiency)
    return win_rate * trades 

# --- RUN THE OPTIMIZATION ---
#def run_optimizer():

study = optuna.create_study(direction="maximize")
study.optimize(objective, n_trials=100)

print("Best Parameters found:")
print(study.best_params)