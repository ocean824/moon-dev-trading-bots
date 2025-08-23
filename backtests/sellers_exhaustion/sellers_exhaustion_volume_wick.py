import pandas as pd
import numpy as np
import talib
from backtesting import Strategy

print("🚀 Moon Dev's Volume Spike + Lower Wick Exhaustion Loading... 🌙")

class VolumeWickExhaustion(Strategy):
    # Parameters
    take_profit = 0.03
    stop_loss = 0.02
    volume_spike_multiplier = 2.0
    wick_ratio = 0.5  # Lower wick should be at least 50% of candle range
    lookback = 20
    
    def init(self):
        # Calculate volume moving average
        self.volume_ma = self.I(talib.SMA, self.data.Volume, timeperiod=self.lookback)
        
        # Calculate candle components
        high = self.data.High
        low = self.data.Low
        close = self.data.Close
        open_ = self.data.Open
        
        # Calculate lower wick ratio
        def calculate_wick_ratio(high, low, close, open_):
            candle_range = high - low
            body_bottom = np.minimum(close, open_)
            lower_wick = body_bottom - low
            
            # Avoid division by zero warning with proper masking
            with np.errstate(divide='ignore', invalid='ignore'):
                wick_ratio = np.where(candle_range > 0, lower_wick / candle_range, 0)
            return wick_ratio
        
        self.wick_ratio = self.I(calculate_wick_ratio, high, low, close, open_)
        
        # Track entry price for exits
        self.entry_price = None
    
    def next(self):
        # Skip if we don't have enough data
        if len(self.data) < self.lookback:
            return
        
        # Current values
        current_volume = self.data.Volume[-1]
        current_wick_ratio = self.wick_ratio[-1]
        volume_avg = self.volume_ma[-1]
        
        # Check if we have a position
        if self.position:
            # Exit logic
            current_price = self.data.Close[-1]
            
            # Take profit
            if current_price >= self.entry_price * (1 + self.take_profit):
                self.position.close()
                self.entry_price = None
            
            # Stop loss
            elif current_price <= self.entry_price * (1 - self.stop_loss):
                self.position.close()
                self.entry_price = None
        
        else:
            # Entry logic - Volume spike with long lower wick
            volume_spike = current_volume > (volume_avg * self.volume_spike_multiplier)
            long_lower_wick = current_wick_ratio >= self.wick_ratio
            red_candle = self.data.Close[-1] < self.data.Open[-1]
            
            # Check for seller exhaustion pattern
            if volume_spike and long_lower_wick and red_candle:
                # Additional confirmation: price is near recent lows
                recent_low = min(self.data.Low[-self.lookback:])
                if self.data.Low[-1] <= recent_low * 1.02:  # Within 2% of recent low
                    self.buy()
                    self.entry_price = self.data.Close[-1]

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING VOLUME SPIKE + LOWER WICK EXHAUSTION ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    results = test_on_all_data(VolumeWickExhaustion, 'VolumeWickExhaustion')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/VolumeWickExhaustion.csv")