"""
state.py - The Memory
Purpose: Maintain system memory across ticks and crashes using Atomic Writes.
Ref: Pages 25, 26, 45, 53
"""

import json
import os
import tempfile
from dataclasses import dataclass, asdict
from datetime import datetime

@dataclass
class TradingState:
    """
    Data structure representing the system's memory.
    Ref: Page 25
    """
    trading_day: str = ""           # Format: "YYYY-MM-DD"
    trades_today: int = 0           # Counter for daily trade cap (0-5)
    last_trade_bar: int = 0         # Bar index of the last trade for cooldown
    risk_throttle: bool = False     # Active if slippage drift detected
    trading_disabled: bool = False  # Global Kill Switch status
    consecutive_losses: int = 0     # Current losing streak
    execution_failures: int = 0     # Count of failed order attempts
    last_update_ts: str = ""        # Last save timestamp

class StateManager:
    def __init__(self, file_path):
        self.file_path = file_path
        self.state = self.load()

    def load(self):
        """
        Loads the state from disk. If file doesn't exist, returns fresh state.
        Ref: Page 53 (Crash Recovery)
        """
        if not os.path.exists(self.file_path):
            return TradingState()
        
        try:
            with open(self.file_path, 'r') as f:
                data = json.load(f)
                return TradingState(**data)
        except Exception:
            # If file is corrupted, return fresh state to maintain 'Fail-Closed'
            return TradingState()

    def save(self):
        """
        Ref: Page 45 - The RIGHT WAY (Atomic Persistence)
        Prevents state corruption during mid-write crashes.
        """
        self.state.last_update_ts = datetime.utcnow().isoformat()
        data = asdict(self.state)
        
        # 1. Create a temporary file in the same directory as the target
        dir_name = os.path.dirname(self.file_path)
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)

        # 2. Use NamedTemporaryFile for safe writing
        with tempfile.NamedTemporaryFile('w', dir=dir_name, delete=False) as tmp:
            json.dump(data, tmp)
            tmp.flush()
            os.fsync(tmp.fileno())  # 3. Force write to physical disk
            temp_name = tmp.name

        # 4. Atomic operation: Replace old file with the new, verified file
        os.replace(temp_name, self.file_path)

    def reset_if_new_day(self):
        """
        Ref: Page 53 - Daily Reset Protection
        Clears trade counters at Midnight UTC.
        """
        today = datetime.utcnow().strftime("%Y-%m-%d")
        
        if self.state.trading_day != today:
            print(f"New trading day detected: {today}. Resetting counters.")
            self.state.trading_day = today
            self.state.trades_today = 0
            self.state.consecutive_losses = 0
            self.state.execution_failures = 0
            self.state.last_trade_bar = 0
            # Note: trading_disabled and risk_throttle persist until manual review
            self.save()

# Usage Example (How the main orchestrator uses it):
# manager = StateManager("state/trading_state.json")
# manager.reset_if_new_day()
# manager.state.trades_today += 1
# manager.save()