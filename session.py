"""
session.py - Time-of-day gate for trade entries.
Blocks entries outside allowed UTC hours.
"""

from datetime import datetime

# Block worst hours (UTC) identified in backtest analysis.
BLOCKED_HOURS_UTC = {3, 5, 10, 11, 12}

def is_allowed(timestamp_utc):
    """
    Returns True if trading is allowed at the given UTC timestamp.
    Accepts a datetime or a unix timestamp (seconds).
    """
    if timestamp_utc is None:
        return True
    if isinstance(timestamp_utc, (int, float)):
        timestamp_utc = datetime.utcfromtimestamp(timestamp_utc)
    return timestamp_utc.hour not in BLOCKED_HOURS_UTC
