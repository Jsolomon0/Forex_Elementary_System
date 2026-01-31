# backtest_cost.py
"""
backtest_cost.py - Execution & Financing Costs for Backtests

This module encapsulates the way we model:
- Commission on entries (per side, per lot)
- Slippage on fills (in pips)
- Overnight swap / financing (per day, in points)

It is used by the backtest engine to keep cost logic centralized and
aligned with backtest_config.py.
"""

import backtest_config as cfg


class ExecutionSimulator:
    """
    Utility class for simulating basic execution costs in backtests.

    All sizes are assumed to be in standard FX lots (1.0 = 100,000 units).
    """

    LOT_NOTIONAL = 100_000  # 1 standard FX lot
    PIP_SIZE = 0.00010      # EURUSD pip

    @staticmethod
    def calculate_entry_cost(size_lots: float) -> float:
        """
        Commission charged at entry, per side, per lot.

        Args:
            size_lots: Position size in lots.

        Returns:
            Commission cost in account currency (e.g. USD).
        """
        if size_lots <= 0:
            return 0.0
        # Per-side commission. Round-turn cost is 2x this amount.
        return float(size_lots * cfg.COMMISSION_PER_LOT)

    @staticmethod
    def get_fill_price(requested_price: float, direction: str) -> float:
        """
        Apply slippage to a requested fill price.

        Args:
            requested_price: The ideal / target price (e.g. mid or bid/ask).
            direction: "BUY" or "SELL".

        Returns:
            The executed price after applying slippage in an adverse direction.
        """
        if cfg.BACKTEST_SLIPPAGE_PIPS <= 0:
            return float(requested_price)

        # Convert pips to price distance; always adverse to the trader.
        slippage_raw = cfg.BACKTEST_SLIPPAGE_PIPS * ExecutionSimulator.PIP_SIZE

        if direction == "BUY":
            # Buy worse (higher) than requested
            return float(requested_price + slippage_raw)
        else:
            # Sell worse (lower) than requested
            return float(requested_price - slippage_raw)

    @staticmethod
    def calculate_swap(trade_type: str, entry_time, exit_time, size_lots: float) -> float:
        """
        Approximate overnight swap / financing cost for a position.

        Args:
            trade_type: "BUY" or "SELL".
            entry_time: datetime of trade entry.
            exit_time: datetime of trade exit.
            size_lots: Position size in lots.

        Returns:
            Total swap cost (or income if negative) over the holding period,
            in account currency.
        """
        if size_lots <= 0:
            return 0.0

        # Whole days between entry and exit; intraday trades get 0 by this model.
        days_held = (exit_time - entry_time).days
        if days_held <= 0:
            return 0.0

        # Points (broker convention) → price units via TICK_SIZE.
        if trade_type == "BUY":
            points_per_day = cfg.SWAP_LONG_POINTS
        else:
            points_per_day = cfg.SWAP_SHORT_POINTS

        if points_per_day == 0:
            return 0.0

        price_per_point = cfg.TICK_SIZE
        daily_swap_price = points_per_day * price_per_point

        # Notional value affected per day
        daily_swap_value = daily_swap_price * ExecutionSimulator.LOT_NOTIONAL * size_lots

        return float(daily_swap_value * days_held)
