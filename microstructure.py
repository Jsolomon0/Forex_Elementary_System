"""
microstructure.py - Lightweight market microstructure adjustments.
Applies session + volatility multipliers to spread and slippage.
"""

from datetime import datetime
from config import VOL_Z_COMPRESSION, VOL_Z_EXPANSION
from backtest_config import (
    MS_SESSION_MULT_ASIA,
    MS_SESSION_MULT_LONDON,
    MS_SESSION_MULT_NY,
    MS_SESSION_MULT_OFF,
    MS_VOL_MULT_COMPRESSION,
    MS_VOL_MULT_NORMAL,
    MS_VOL_MULT_EXPANSION,
    MS_VOL_MULT_EXTREME
)

VOL_Z_EXTREME = 2.0

def _get_session_multiplier(timestamp_utc):
    if isinstance(timestamp_utc, (int, float)):
        timestamp_utc = datetime.utcfromtimestamp(timestamp_utc)
    hour = timestamp_utc.hour
    if 0 <= hour < 7:
        return MS_SESSION_MULT_ASIA
    if 7 <= hour < 13:
        return MS_SESSION_MULT_LONDON
    if 13 <= hour < 21:
        return MS_SESSION_MULT_NY
    return MS_SESSION_MULT_OFF

def _get_vol_multiplier(atr_zscore):
    if atr_zscore is None:
        return MS_VOL_MULT_NORMAL
    if atr_zscore < VOL_Z_COMPRESSION:
        return MS_VOL_MULT_COMPRESSION
    if atr_zscore > VOL_Z_EXTREME:
        return MS_VOL_MULT_EXTREME
    if atr_zscore > VOL_Z_EXPANSION:
        return MS_VOL_MULT_EXPANSION
    return MS_VOL_MULT_NORMAL

def adjust_spread_slippage(base_spread_price, base_slippage_pips, atr_zscore, timestamp_utc=None):
    if timestamp_utc is None:
        timestamp_utc = datetime.utcnow()
    session_mult = _get_session_multiplier(timestamp_utc)
    vol_mult = _get_vol_multiplier(atr_zscore)
    spread_price = base_spread_price * session_mult * vol_mult
    slippage_pips = base_slippage_pips * session_mult * vol_mult
    return spread_price, slippage_pips
