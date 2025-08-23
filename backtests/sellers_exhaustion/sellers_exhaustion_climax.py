import pandas as pd
import numpy as np
import talib
from backtesting import Strategy

print("🚀 Moon Dev's Climax Volume Analysis Loading... 🌙")

class ClimaxVolumeExhaustion(Strategy):
    # Parameters
    take_profit = 0.03
    stop_loss = 0.02
    volume_multiplier = 2.5  # Climax volume threshold
    rebound_threshold = 0.005  # 0.5% rebound from low
    lookback = 20
    
    def init(self):
        # Calculate volume moving average and standard deviation
        self.volume_ma = self.I(talib.SMA, self.data.Volume, timeperiod=self.lookback)
        
        # Calculate price momentum
        self.roc = self.I(talib.ROC, self.data.Close, timeperiod=1)
        
        # Track if we just had a climax bar
        def detect_climax(volume, volume_ma, close, low, high):
            # Volume spike detection
            volume_spike = volume > (volume_ma * self.volume_multiplier)
            
            # Price action - large red candle that rebounds
            candle_range = high - low
            # Avoid division by zero warning with proper masking
            with np.errstate(divide='ignore', invalid='ignore'):
                close_position = np.where(candle_range > 0, (close - low) / candle_range, 0.5)
            
            # Climax pattern: high volume, price rebounds from low
            climax = volume_spike & (close_position > 0.3)  # Close in upper 70% of range
            
            return climax.astype(float)
        
        self.climax_signal = self.I(detect_climax, 
                                   self.data.Volume, 
                                   self.volume_ma,
                                   self.data.Close,
                                   self.data.Low,
                                   self.data.High)
        
        # Track entry price for exits
        self.entry_price = None
    
    def next(self):
        # Skip if we don't have enough data
        if len(self.data) < self.lookback + 1:
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
            # Entry logic - Climax volume pattern
            if self.climax_signal[-1] > 0:
                # Additional confirmations
                recent_low = min(self.data.Low[-self.lookback:])
                at_new_low = self.data.Low[-1] <= recent_low * 1.01
                
                # Large red candle initially
                red_candle = self.data.Close[-1] < self.data.Open[-1]
                
                # But rebounded from the low
                rebound = (self.data.Close[-1] - self.data.Low[-1]) / self.data.Low[-1] > self.rebound_threshold
                
                if at_new_low and red_candle and rebound:
                    self.buy()
                    self.entry_price = self.data.Close[-1]

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING CLIMAX VOLUME EXHAUSTION ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    results = test_on_all_data(ClimaxVolumeExhaustion, 'ClimaxVolumeExhaustion')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/ClimaxVolumeExhaustion.csv")