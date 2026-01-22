# mock_data.py
import numpy as np
import time

class MarketSimulator:
    def __init__(self, start_price=1.1700):
        self.price = start_price
        self.history = []
        self.step_counter = 0
        
        # Pre-fill 100 bars to ensure EMA(50) is fully formed
        for _ in range(100):
            self.generate_next_bar(force_trend=True)

    def generate_next_bar(self, force_trend=False):
        self.step_counter += 1
        
        # Logic to trigger a Pullback every 20 bars
        is_pullback_bar = (self.step_counter % 5 == 0) and not force_trend
        
        # 1. Base prices
        open_p = self.price
        if self.step_counter % 5 == 0:
            force_trend = False

        if is_pullback_bar:
            # --- THE PULLBACK TRIGGER ---
            # We need a bar where Low is deep, but Close is high.
            # This simulates a "bounce" off the EMA.
            low_p = open_p - 0.009   # Sharp dip down
            close_p = open_p + 0.0002 # Closes slightly above open
            high_p = close_p + 0.0001
            print(f">>> SIMULATOR: Generating Pullback Bar (Step {self.step_counter})")
        else:
            # --- STANDARD UPTREND ---
            bias = 0.0004 # Steady rise to keep EMA_FAST > EMA_SLOW
            noise = np.random.normal(0, 0.0001)
            close_p = open_p + bias + noise
            high_p = max(open_p, close_p) + 0.0001
            low_p = min(open_p, close_p) - 0.0001

        bar = {
            'time': int(time.time()) + (self.step_counter * 60),
            'open': open_p,
            'high': high_p,
            'low': low_p,
            'close': close_p,
            'tick_volume': 100
        }
        
        self.price = close_p
        self.history.append(bar)
        
        if len(self.history) > 110:
            self.history.pop(0)
            
        return bar

    def get_rates(self, count):
        subset = self.history[-count:]
        dtype = [('time', '<i8'), ('open', '<f8'), ('high', '<f8'), 
                 ('low', '<f8'), ('close', '<f8'), ('tick_volume', '<i8')]
        rates = np.array([tuple(b.values()) for b in subset], dtype=dtype)
        return rates

# Initialize simulator
sim = MarketSimulator()