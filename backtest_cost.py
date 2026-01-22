# backtest_cost.py
import backtest_config as cfg

class ExecutionSimulator:
    @staticmethod
    def calculate_entry_cost(size):
        return size * cfg.COMMISSION_PER_LOT

    @staticmethod
    def get_fill_price(requested_price, direction):
        slippage_raw = cfg.BACKTEST_SLIPPAGE_PIPS * 0.00010
        return requested_price + slippage_raw if direction == "BUY" else requested_price - slippage_raw

    @staticmethod
    def calculate_swap(trade_type, entry_time, exit_time, size):
        days = (exit_time - entry_time).days
        rate = cfg.SWAP_LONG_POINTS if trade_type == "BUY" else cfg.SWAP_SHORT_POINTS
        return (rate * cfg.TICK_SIZE) * 100000 * size * days