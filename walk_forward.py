"""
walk_forward.py - Simple walk-forward evaluation.
"""

from datetime import timedelta
from backtest_config import BT_START_DATE, BT_END_DATE
import back_test

def run_walk_forward(train_days=20, test_days=5, step_days=5, verbose=False):
    start = BT_START_DATE
    end = BT_END_DATE
    window = []

    test_start = start + timedelta(days=train_days)
    while test_start + timedelta(days=test_days) <= end:
        test_end = test_start + timedelta(days=test_days)
        report, _trades = back_test.run_simulation_window(test_start, test_end, verbose=verbose)
        window.append({
            "test_start": test_start.strftime("%Y-%m-%d"),
            "test_end": test_end.strftime("%Y-%m-%d"),
            "report": report
        })
        test_start += timedelta(days=step_days)

    return window

if __name__ == "__main__":
    results = run_walk_forward()
    for w in results:
        print("\n=== WALK-FORWARD WINDOW ===")
        print("Test:", w["test_start"], "->", w["test_end"])
        if isinstance(w["report"], dict):
            for k, v in w["report"].items():
                print(f"{k.ljust(20)}: {v}")
        else:
            print(w["report"])
