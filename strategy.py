"""
strategy.py - The Signal Generator
Purpose: Generate buy/sell signals when market regime permits.
Ref: Pages 6, 16, 30, 31, 32
"""

from datetime import datetime
from config import ATR_STOP_MULTIPLIER, RR_MIN, EXTENDED_MULTIPLIER

def evaluate_strategy(bar, regime_context):
    """
    Ref: Page 30 - "Strategy generates ideas. Risk, psychology, and costs 
    decide if they happen."
    """
    
    # 1. PRE-CONDITION: Is the regime tradable?
    # Ref: Page 16 - Phase 4: Signal Generation
    if not regime_context['trade_allowed']:
        #strategy_context['veto_reason'] = regime_context.get('veto_reason', 'Unfavorable regime')
        return None
    print("Regime Allowed")

    structure = regime_context['structure']
    bias = regime_context.get('strategy_bias')  # NEW: refined regime output
    print(f"Market Structure: {structure}, Strategy Bias: {bias}")
    signal = None

    # 2. SELECT STRATEGY BASED ON REGIME BIAS (with fallback to structure)
    if bias == "trend":
        print("Evaluating Trend Following Strategy (bias=trend)")
        signal = get_trend_following_signal(bar, regime_context)
    elif bias == "mean_reversion":
        print("Evaluating Mean Reversion Strategy (bias=mean_reversion)")
        signal = get_mean_reversion_signal(bar)
    else:
        # Fallback to legacy behavior if no bias provided
        if structure == "trend":
            print("Evaluating Trend Following Strategy (structure=trend)")
            signal = get_trend_following_signal(bar, regime_context)
        elif structure == "range":
            print("Evaluating Mean Reversion Strategy (structure=range)")
            signal = get_mean_reversion_signal(bar)

    # 3. APPLY UNIVERSAL FILTERS
    if signal:
        # Ref: Page 16 - "Avoid extended candles"
        # Prevents chasing price after a massive move
        if bar['range'] > (bar['atr'] * EXTENDED_MULTIPLIER):
            print("Extended candle vetoed. Range (", bar['range'], ") more than ATR multipler (", bar['atr'], ").")
            return None

        # Attach regime metadata if not already on the signal
        if "risk_multiplier" not in signal:
            signal["risk_multiplier"] = regime_context.get("risk_multiplier", 1.0)
        signal.setdefault("htf_trend", regime_context.get("htf_trend"))
        signal.setdefault("regime_label", regime_context.get("regime_label"))

    return signal

def get_trend_following_signal(bar, regime_context):
    """
    Strategy 1: Trend Following (Pullbacks)
    Ref: Page 31

    Now incorporates Higher Timeframe (HTF) trend bias into risk_multiplier.
    """
    
    direction = None
    strategy = "trend_following"    
    
    # ENTRY RULES:
    # EMA(20) > EMA(50) -> Trend is UP
    if bar['ema_fast'] > bar['ema_slow']:
        print("Trend is UP")
        # Wait for pullback: Price near EMA(20)
        # Logic: If low is below EMA_FAST but close is above (rejection)
        if bar['low'] <= bar['ema_fast'] and bar['close'] > bar['ema_fast']:
            print("Buy Allowed: low (", bar['low'], ") is below EMA_FAST (", bar['ema_fast'], ") and close (", bar['close'], ") is above EMA_FAST (", bar['ema_fast'], ").")
            direction = "BUY"
        elif bar['low'] > bar['ema_fast'] and bar['close'] > bar['ema_fast']:
            print(" Buy Not Allowed: low (", bar['low'], ") and close (", bar['close'], ") are above EMA_FAST (", bar['ema_fast'], ").")
        elif bar['low'] <= bar['ema_fast'] and not bar['close'] > bar['ema_fast']:
            print(" Buy Not Allowed: low (", bar['low'], ") is below EMA_FAST (", bar['ema_fast'], ") and close (", bar['close'], ") is below EMA_FAST (", bar['ema_fast'], ").")
        elif bar['low'] > bar['ema_fast'] and not bar['close'] > bar['ema_fast']:
            print(" Buy Not Allowed: low (", bar['low'], ") is above EMA_FAST (", bar['ema_fast'], ") and close (", bar['close'], ") is below EMA_FAST (", bar['ema_fast'], ").")

    # EMA(20) < EMA(50) -> Trend is DOWN
    elif bar['ema_fast'] < bar['ema_slow']:
        print("Trend is DOWN")
        # Wait for pullback: Price near EMA(20)
        # Logic: If high is above EMA_FAST but close is below (rejection)
        if bar['high'] >= bar['ema_fast'] and bar['close'] < bar['ema_fast']:
            print("Sell Allowed: High (", bar['high'], ") is above EMA_FAST (", bar['ema_fast'], ") and close (", bar['close'], ") is below EMA_FAST (", bar['ema_fast'], ").")
            direction = "SELL"
        elif not bar['high'] >= bar['ema_fast'] and bar['close'] < bar['ema_fast']:
            print(" Sell Not Allowed: High (", bar['high'], ") is below EMA_FAST (", bar['ema_fast'], ").")
        elif bar['high'] >= bar['ema_fast'] and not bar['close'] < bar['ema_fast']:
            print(" Sell Not Allowed: Close (", bar['close'], ") is above EMA_FAST (", bar['ema_fast'], ").")
        elif not bar['high'] >= bar['ema_fast'] and not bar['close'] < bar['ema_fast']:
            print(" Sell Not Allowed: High (", bar['high'], ") is below EMA_FAST (", bar['ema_fast'], ") and close (", bar['close'], ") is above EMA_FAST (", bar['ema_fast'], ").")

    if not direction:
        print("No direction for Trend Strategy.")
        return None

    # --- Build base signal (price/SL/TP) ---
    signal = construct_signal_dict(direction, bar, strategy)
    if not signal:
        return None

    # --- Higher Timeframe (HTF) Bias Integration into risk_multiplier ---
    htf_trend = regime_context.get("htf_trend", "flat")
    base_mult = regime_context.get("risk_multiplier", 1.0)

    # Direction alignment with HTF trend
    aligned = (
        (direction == "BUY" and htf_trend == "up") or
        (direction == "SELL" and htf_trend == "down")
    )

    if aligned:
        htf_mult = 1.0          # full risk when aligned
    elif htf_trend == "flat":
        htf_mult = 0.5          # reduced risk when HTF is flat
    else:
        htf_mult = 0.0          # counter-trend -> no trade

    final_mult = base_mult * htf_mult

    if final_mult <= 0.0:
        print(f"Trend signal vetoed by HTF bias: direction={direction}, htf_trend={htf_trend}")
        return None

    # Attach multipliers and regime info to the signal
    signal["risk_multiplier"] = final_mult
    signal["htf_trend"] = htf_trend
    signal["regime_label"] = regime_context.get("regime_label")

    return signal



def get_mean_reversion_signal(bar):
    """
    Strategy 2: Mean Reversion (Z-Score extremes)
    Ref: Page 31
    """
    print("Starting Mean Reversion Strategy")
    direction = None
    strategy = "mean_reversion"

    print("bar['zscore']:", bar['zscore'])
    
    # ENTRY RULES:
    # Z > +2 -> Overbought -> SELL
    if bar['zscore'] > 2.0:
        direction = "SELL"
    # Z < -2 -> Oversold -> BUY
    elif bar['zscore'] < -2.0:
        direction = "BUY"
    elif not bar['zscore'] > 2.0 and not bar['zscore'] < -2.0:
        print("Z-score is between -2 and +2.")

    if direction:
        return construct_signal_dict(direction, bar, strategy)
    else:
        print("No direction for Mean Reversion Strategy.")
    return None

def construct_signal_dict(direction, bar, strategy):
    """
    Ref: Page 31 & 32 - RIGHT WAY (Price-based)
    Ensures zero ambiguity for the execution layer.
    """
    entry_price = bar['close']
    atr = bar['atr']
    
    # Calculate Stop Loss distance
    # Ref: Page 31 - "1.5 * ATR"
    sl_distance = atr * ATR_STOP_MULTIPLIER
    
    # Calculate Take Profit distance
    # Ref: Page 31 - "3.0 * ATR (2:1 RR)"
    tp_distance = sl_distance * RR_MIN
    
    # Convert distances to actual price levels
    if direction == "BUY":
        sl = entry_price - sl_distance
        tp = entry_price + tp_distance
    else:
        sl = entry_price + sl_distance
        tp = entry_price - tp_distance

    return {
        "direction": direction,
        "strategy": strategy,
        "entry_price": float(entry_price),
        "sl": float(sl),
        "tp": float(tp),
        "stop_distance": float(sl_distance),
        "target_distance": float(tp_distance),
        "timestamp": datetime.utcnow().isoformat()
    }

#_______________________________________________________

def simulate_strategy(bar, regime_context, ext_mult, rr_mins, atr_mult):
    """
    Ref: Page 30 - "Strategy generates ideas. Risk, psychology, and costs 
    decide if they happen."
    """
    
    # 1. PRE-CONDITION: Is the regime tradable?
    # Ref: Page 16 - Phase 4: Signal Generation
    if not regime_context['trade_allowed']:
        #strategy_context['veto_reason'] = regime_context.get('veto_reason', 'Unfavorable regime')
        return None
    print("Regime Allowed")

    structure = regime_context['structure']
    print(f"Market Structure: {structure}")
    signal = None

    # 2. SELECT STRATEGY BASED ON STRUCTURE
    if structure == "trend":
        print("Evaluating Trend Following Strategy")
        signal = sim_get_trend_following_signal(bar, rr_mins, atr_mult)
    elif structure == "range":
        print("Evaluating Mean Reversion Strategy")
        signal = sim_get_mean_reversion_signal(bar, rr_mins, atr_mult)

    
    # 3. APPLY UNIVERSAL FILTERS
    if signal:
        # Ref: Page 16 - "Avoid extended candles"
        # Prevents chasing price after a massive move
        if bar['range'] > (bar['atr'] * ext_mult):
            print("Extended candle vetoed. Range (", bar['range'], ") more than ATR multipler (", bar['atr'], ").")
            return None
       
    return signal

def sim_get_trend_following_signal(bar, rr_mins, atr_mult):
    """
    Strategy 1: Trend Following (Pullbacks)
    Ref: Page 31
    """
    
    direction = None
    strategy = "trend_following"    
    
    # ENTRY RULES:
    # EMA(20) > EMA(50) -> Trend is UP
    if bar['ema_fast'] > bar['ema_slow']:
        print("Trend is UP")
        # Wait for pullback: Price near EMA(20)
        # Logic: If low is below EMA_FAST but close is above (rejection)
        if bar['low'] <= bar['ema_fast'] and bar['close'] > bar['ema_fast']:
            print("Buy Allowed:low ( ",bar['low'],")is below EMA_FAST (",bar['ema_fast'],") and close (",bar['close'],") is above EMA_FAST(",bar['ema_fast'],").")
            direction = "BUY"
        elif bar['low'] > bar['ema_fast'] and bar['close'] > bar['ema_fast']:
            print(" Buy Not Allowed: Low (",bar['low'],")is above EMA_FAST (",bar['ema_fast'],").")
        elif bar['low'] <= bar['ema_fast'] and bar['close'] < bar['ema_fast']:
            print(" Buy Not Allowed: Close (",bar['close'],") is below EMA_FAST(",bar['ema_fast'],").")
        elif not bar['low'] <= bar['ema_fast'] and not bar['close'] > bar['ema_fast']:
            print(" Buy Not Allowed: Low (",bar['low'],") is above EMA_FAST (",bar['ema_fast'],") and Close (",bar['close'],") is below EMA_FAST(",bar['ema_fast'],").")



    # Trend is DOWN
    elif bar['ema_fast'] < bar['ema_slow']:
        print("Trend is DOWN")
        # Wait for pullback to EMA_FAST
        if bar['high'] >= bar['ema_fast'] and bar['close'] < bar['ema_fast']:
            print("High (",bar['high'],") is above EMA_FAST (",bar['ema_fast'],") and close (",bar['close'],") is below EMA_FAST (",bar['ema_fast'],").")
            direction = "SELL"
        elif not bar['high'] >= bar['ema_fast'] and bar['close'] < bar['ema_fast']:
            print(" Sell Not Allowed: High (",bar['high'],")is below EMA_FAST (",bar['ema_fast'],").")
        elif bar['high'] >= bar['ema_fast'] and not bar['close'] < bar['ema_fast']:
            print(" Sell Not Allowed: Close (",bar['close'],")is above EMA_FAST (",bar['ema_fast'],").")
        elif not bar['high'] >= bar['ema_fast'] and not bar['close'] < bar['ema_fast']:
            print(" Sell Not Allowed: High (",bar['high'],") is below EMA_FAST (",bar['ema_fast'],") and Close (",bar['close'],") is above EMA_FAST (",bar['ema_fast'],").")

    if direction:
        return sim_construct_signal_dict(direction, bar, strategy, rr_mins, atr_mult)
    else:
        print("No direction for Trend Strategy.")
    return None

def sim_get_mean_reversion_signal(bar, rr_mins, atr_mult):
    """
    Strategy 2: Mean Reversion (Z-Score extremes)
    Ref: Page 31
    """
    print("Starting Mean Reversion Strategy")
    direction = None
    strategy = "mean_reversion"

    print("bar['zscore']:", bar['zscore'])
    
    # ENTRY RULES:
    # Z > +2 -> Overbought -> SELL
    if bar['zscore'] > 2.0:
        direction = "SELL"
    # Z < -2 -> Oversold -> BUY
    elif bar['zscore'] < -2.0:
        direction = "BUY"
    elif not bar['zscore'] > 2.0 and not bar['zscore'] < -2.0:
        print("Z-score is between -2 and +2.")

    if direction:
        return sim_construct_signal_dict(direction, bar, strategy, rr_mins, atr_mult)
    else:
        print("No direction for Mean Reversion Strategy.")
    return None

def sim_construct_signal_dict(direction, bar, strategy, rr_mins, atr_mult):
    """
    Ref: Page 31 & 32 - RIGHT WAY (Price-based)
    Ensures zero ambiguity for the execution layer.
    """
    entry_price = bar['close']
    atr = bar['atr']
    
    # Calculate Stop Loss distance
    # Ref: Page 31 - "1.5 * ATR"
    sl_distance = atr * atr_mult
    
    # Calculate Take Profit distance
    # Ref: Page 31 - "3.0 * ATR (2:1 RR)"
    tp_distance = sl_distance * rr_mins
    
    # Convert distances to actual price levels
    if direction == "BUY":
        sl = entry_price - sl_distance
        tp = entry_price + tp_distance
    else:
        sl = entry_price + sl_distance
        tp = entry_price - tp_distance

    return {
        "direction": direction,
        "strategy": strategy,
        "entry_price": float(entry_price),
        "sl": float(sl),
        "tp": float(tp),
        "stop_distance": float(sl_distance),
        "target_distance": float(tp_distance),
        "timestamp": datetime.utcnow().isoformat()
    }
