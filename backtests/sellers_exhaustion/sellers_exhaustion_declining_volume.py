import pandas as pd
import numpy as np
import talib
from backtesting import Strategy

print("🚀 Moon Dev's Declining Volume on Lower Lows Loading... 🌙")

class DecliningVolumeExhaustion(Strategy):
    # Parameters
    take_profit = 0.03
    stop_loss = 0.02
    lookback = 10
    volume_decline_threshold = 0.7  # Volume should be 70% or less of previous low's volume
    
    def init(self):
        # Track recent lows and their volumes
        self.low_ma = self.I(talib.SMA, self.data.Low, timeperiod=self.lookback)
        self.volume_ma = self.I(talib.SMA, self.data.Volume, timeperiod=self.lookback)
        
        # Detect lower lows with declining volume
        def detect_declining_volume_pattern(low, volume, lookback):
            pattern = np.zeros(len(low))
            
            for i in range(lookback, len(low)):
                # Find previous low point
                prev_low_idx = i - lookback + np.argmin(low[i-lookback:i])
                prev_low = low[prev_low_idx]
                prev_volume = volume[prev_low_idx]
                
                # Check for lower low
                if low[i] < prev_low:
                    # Check for declining volume
                    if volume[i] < prev_volume * self.volume_decline_threshold:
                        pattern[i] = 1.0
            
            return pattern
        
        self.divergence_signal = self.I(detect_declining_volume_pattern, 
                                       self.data.Low, 
                                       self.data.Volume, 
                                       self.lookback)
        
        # RSI for additional confirmation
        self.rsi = self.I(talib.RSI, self.data.Close, timeperiod=14)
        
        # Track entry price for exits
        self.entry_price = None
    
    def next(self):
        # Skip if we don't have enough data
        if len(self.data) < self.lookback * 2:
            return
        
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
            # Entry logic - Lower low with declining volume
            if self.divergence_signal[-1] > 0:
                # Additional confirmation: oversold RSI
                if self.rsi[-1] < 35:
                    # Check that we're making a new recent low
                    recent_low = min(self.data.Low[-self.lookback*2:])
                    if self.data.Low[-1] <= recent_low * 1.005:
                        self.buy()
                        self.entry_price = self.data.Close[-1]

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING DECLINING VOLUME EXHAUSTION ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    results = test_on_all_data(DecliningVolumeExhaustion, 'DecliningVolumeExhaustion')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/DecliningVolumeExhaustion.csv")