"""
regime.py - The Market Context Engine
Purpose: Classify market conditions to filter trading opportunities.
Ref: Pages 6, 10, 15, 29, 30
"""
"""
regime.py - The Market Context Engine
Purpose: Classify market conditions to filter and shape trading opportunities.
Ref: Pages 6, 10, 15, 29, 30
"""

from config import (
    VOL_Z_COMPRESSION,
    VOL_Z_EXPANSION,
    VOL_Z_EXTREME,       # NEW: extreme expansion threshold
    ADX_TREND_THRESHOLD,
)


def analyze_regime(bar):
    """
    Main entry point for the Context Layer.

    Returns a richer regime object:

    {
        "volatility": "compression|normal|expansion|extreme_expansion",
        "structure": "trend|range",
        "trade_allowed": bool,
        "veto_reason": str|None,
        "regime_label": "<vol>_<struct>",
        "risk_multiplier": float,          # scales RISK_PER_TRADE
        "strategy_bias": "trend"|"mean_reversion"|None,
    }
    """

    zscore = bar["atr_zscore"]

    # 1. VOLATILITY AXIS (ATR Z-score)
    vol_state = classify_volatility(zscore)

    # 2. STRUCTURE AXIS (ADX + EMA Slope)
    struct_state = classify_structure(bar)

    # 3. DECISION LOGIC (Refined Decision Matrix)
    trade_allowed = True
    veto_reason = None
    risk_multiplier = 1.0
    strategy_bias = None

    regime_label = f"{vol_state}_{struct_state}"

    # RULE 1: Dead / deep compression market
    # Extreme low volatility → edges generally fail
    if vol_state == "compression" or zscore < -2.0:
        trade_allowed = False
        veto_reason = "VETO: compression/dead market (no edge)"
        risk_multiplier = 0.0
        strategy_bias = None

    # RULE 2: High-volatility range = whipsaw / spike zone
    elif vol_state in ("expansion", "extreme_expansion") and struct_state == "range":
        trade_allowed = False
        veto_reason = "VETO: high-volatility range (whipsaw risk)"
        risk_multiplier = 0.0
        strategy_bias = None

    # RULE 3: Expansion trend – allowed, but reduced risk
    elif vol_state == "expansion" and struct_state == "trend":
        trade_allowed = True
        veto_reason = None
        risk_multiplier = 0.7     # 70% of base risk
        strategy_bias = "trend"

    # RULE 4: Extreme expansion trend – very cautious
    elif vol_state == "extreme_expansion" and struct_state == "trend":
        trade_allowed = True
        veto_reason = None
        risk_multiplier = 0.5     # 50% of base risk
        strategy_bias = "trend"

    # RULE 5: Normal regimes
    else:
        if struct_state == "trend":
            trade_allowed = True
            veto_reason = None
            risk_multiplier = 1.0
            strategy_bias = "trend"
        else:  # "range"
            trade_allowed = True
            veto_reason = None
            risk_multiplier = 1.0
            strategy_bias = "mean_reversion"

    htf_trend = classify_htf_trend(bar)
    regime_label = f"{vol_state}_{struct_state}_{htf_trend}"


    return {
        "volatility": vol_state,
        "structure": struct_state,
        "trade_allowed": trade_allowed,
        "veto_reason": veto_reason,
        "regime_label": regime_label,
        "risk_multiplier": risk_multiplier,
        "strategy_bias": strategy_bias,
            "htf_trend": htf_trend,

    }

def classify_htf_trend(bar) -> str:
    """
    Higher Timeframe Trend Bias (proxy version).

    For now we approximate HTF trend using the slow EMA as a
    stand-in for the bigger picture. Later this can be replaced
    with a true multi-timeframe signal (e.g., H1 EMA).

    Returns:
        "up"   -> higher timeframe bias is bullish
        "down" -> higher timeframe bias is bearish
        "flat" -> no strong bias
    """

    ema_slow = bar.get("ema_slow")
    close = bar.get("close")

    if ema_slow is None or ema_slow == 0.0 or close is None:
        return "flat"

    # Simple proxy rule:
    # - Price above slow EMA -> uptrend bias
    # - Price below slow EMA -> downtrend bias
    # - Very close to EMA    -> flat / indecisive
    threshold = ema_slow * 0.001  # ~0.1% band

    if close > ema_slow + threshold:
        return "up"
    elif close < ema_slow - threshold:
        return "down"
    else:
        return "flat"


def classify_volatility(zscore: float) -> str:
    """
    Volatility Axis:
    - z < VOL_Z_COMPRESSION      -> compression
    - VOL_Z_COMPRESSION..EXPANSION -> normal
    - EXPANSION..EXTREME         -> expansion
    - z > VOL_Z_EXTREME          -> extreme_expansion
    """
    if zscore < VOL_Z_COMPRESSION:
        return "compression"
    elif zscore > VOL_Z_EXTREME:
        return "extreme_expansion"
    elif zscore > VOL_Z_EXPANSION:
        return "expansion"
    else:
        return "normal"


def classify_structure(bar) -> str:
    """
    Structure Axis: Uses ADX for trend strength.
    (EMA slope can be added later if needed.)
    """
    if bar["adx"] > ADX_TREND_THRESHOLD:
        return "trend"
    else:
        return "range"


def get_real_world_impact_preview():
    """
    Documentation of expected outcomes with refined regime usage.
    """
    return {
        "compression_dead": "No trades; avoids grinding losses in dead markets.",
        "normal_trend": "Prime trend-following; full risk.",
        "normal_range": "Prime mean-reversion; full risk.",
        "expansion_trend": "Trend continuation with reduced size.",
        "extreme_expansion_trend": "Very cautious trend trades (half size).",
        "expansion_range": "Vetoed; typical whipsaw conditions.",
    }
