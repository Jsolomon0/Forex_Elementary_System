"""
regime.py - The Market Context Engine
Purpose: Classify market conditions to filter trading opportunities.
Ref: Pages 6, 10, 15, 29, 30
"""

from config import VOL_Z_COMPRESSION, VOL_Z_EXPANSION, ADX_TREND_THRESHOLD

def analyze_regime(bar):
    """
    Ref: Page 29 - Three-Axis Classification
    Main entry point for the Context Layer.
    """
    
    # 1. VOLATILITY AXIS (Measures: ATR Z-score)
    volatility_state = classify_volatility(bar['atr_zscore'])
    
    # 2. STRUCTURE AXIS (Measures: ADX + EMA Slope)
    structure_state = classify_structure(bar)
    
    # 3. DECISION LOGIC (Ref: Page 30 - Decision Matrix)
    trade_allowed = True
    reason = "Normal conditions"

    # RULE 1: Compression Check
    if volatility_state == "compression":
        # Ref: Page 10 - "Edges don't work"
        trade_allowed = False
        reason = "VETO: Market in compression (too quiet)"

    # RULE 2: Whipsaw Check
    elif volatility_state == "expansion" and structure_state == "range":
        # Ref: Page 30 - "High volatility + no trend = whipsaw hell"
        trade_allowed = False
        reason = "VETO: High volatility range (whipsaw risk)"

    # RULE 3: Selective expansion
    elif volatility_state == "expansion" and structure_state == "trend":
        # Ref: Page 11 - Allowed but typically requires caution/reduced size
        trade_allowed = True
        reason = "Expansion trend (proceed with caution)"

    # RULE 4: Dead Market
    elif bar['atr_zscore'] < -2.0:
        trade_allowed = False
        reason = "VETO: Dead market"

    return {
        "volatility": volatility_state,
        "structure": structure_state,
        "trade_allowed": trade_allowed,
        "veto_reason": reason if not trade_allowed else None
    }

def classify_volatility(zscore):
    """
    Ref: Page 10 - Volatility Axis logic
    -2σ to -1σ: Compression
    -1σ to +1σ: Normal
    +1σ to +2σ: Expansion
    """
    if zscore < VOL_Z_COMPRESSION:
        return "compression"
    elif zscore > VOL_Z_EXPANSION:
        return "expansion"
    else:
        return "normal"

def classify_structure(bar):
    """
    Ref: Page 15 - Structure Check
    Uses ADX for strength and EMA slope for directionality.
    """
    # Calculate EMA Slope (Current EMA Fast vs Previous EMA Fast)
    # Note: In a production script, you'd compare current bar to bar-1
    # For this implementation, we assume a trend exists if ADX is strong
    if bar['adx'] > ADX_TREND_THRESHOLD:
        return "trend"
    else:
        return "range"

def get_real_world_impact_preview():
    """
    Ref: Page 30 - Real-World Impact
    Documentation of expected outcomes.
    """
    return {
        "without_filtering": "45% win rate (compression kills it)",
        "with_filtering": "55% win rate (only good setups)"
    }