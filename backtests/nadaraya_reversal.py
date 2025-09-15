import pandas as pd
import numpy as np
import talib
from backtesting import Strategy

print("🚀 Moon Dev's Nadaraya-Watson Reversal Strategy Loading... 🌙")

class NadarayaWatsonReversal(Strategy):
    # Parameters
    bandwidth = 100
    kernel_type = 'gaussian'
    atr_period = 14
    atr_multiplier_stop = 2.0
    atr_multiplier_target = 3.0
    volume_confirm_period = 20
    volume_threshold = 1.2
    min_distance = 0.001  # Minimum distance from NW line to trigger (0.1%)
    
    def init(self):
        # Calculate ATR for stops
        self.atr = self.I(talib.ATR, self.data.High, self.data.Low, self.data.Close, timeperiod=self.atr_period)
        
        # Calculate volume MA for confirmation
        self.volume_ma = self.I(talib.SMA, self.data.Volume, timeperiod=self.volume_confirm_period)
        
        # Calculate Nadaraya-Watson estimator
        def nadaraya_watson(prices, bandwidth=100, kernel='gaussian'):
            nw_line = np.zeros(len(prices))
            prices_array = np.array(prices)
            
            for i in range(len(prices)):
                if i < bandwidth:
                    nw_line[i] = prices_array[i]
                else:
                    weights = []
                    values = []
                    
                    for j in range(max(0, i - bandwidth), i + 1):
                        distance = abs(i - j)
                        
                        if kernel == 'gaussian':
                            # Gaussian kernel with bandwidth as std dev parameter
                            weight = np.exp(-(distance**2) / (2 * (bandwidth/4)**2))
                        else:
                            # Default uniform kernel
                            weight = 1.0 if distance <= bandwidth else 0.0
                        
                        weights.append(weight)
                        values.append(prices_array[j])
                    
                    weights = np.array(weights)
                    values = np.array(values)
                    
                    if weights.sum() > 0:
                        nw_line[i] = (weights * values).sum() / weights.sum()
                    else:
                        nw_line[i] = prices_array[i]
            
            return nw_line
        
        # Apply NW to close prices
        self.nw_line = self.I(nadaraya_watson, self.data.Close, self.bandwidth, self.kernel_type)
        
        # Calculate distance from price to NW line
        def calc_distance(close, nw):
            return (close - nw) / nw
        
        self.distance = self.I(calc_distance, self.data.Close, self.nw_line)
        
        # Track entry details
        self.entry_price = None
        self.entry_atr = None
        self.is_long = None
    
    def next(self):
        # Skip if we don't have enough data
        if len(self.data) < self.bandwidth:
            return
        
        # Current values
        current_price = self.data.Close[-1]
        current_nw = self.nw_line[-1]
        current_distance = self.distance[-1]
        prev_distance = self.distance[-2] if len(self.distance) > 1 else 0
        current_volume = self.data.Volume[-1]
        volume_avg = self.volume_ma[-1]
        current_atr = self.atr[-1]
        
        # Check if we have a position
        if self.position:
            # Exit logic based on position type
            if self.is_long:
                # Long exit conditions
                stop_price = self.entry_price - (self.entry_atr * self.atr_multiplier_stop)
                target_price = self.entry_price + (self.entry_atr * self.atr_multiplier_target)
                
                if current_price <= stop_price:
                    self.position.close()
                    self.entry_price = None
                    self.is_long = None
                elif current_price >= target_price:
                    self.position.close()
                    self.entry_price = None
                    self.is_long = None
                # Exit if price crosses far above NW line (reversal failed)
                elif current_distance > 0.02:  # 2% above NW line
                    self.position.close()
                    self.entry_price = None
                    self.is_long = None
            
            else:  # Short position
                # Short exit conditions
                stop_price = self.entry_price + (self.entry_atr * self.atr_multiplier_stop)
                target_price = self.entry_price - (self.entry_atr * self.atr_multiplier_target)
                
                if current_price >= stop_price:
                    self.position.close()
                    self.entry_price = None
                    self.is_long = None
                elif current_price <= target_price:
                    self.position.close()
                    self.entry_price = None
                    self.is_long = None
                # Exit if price crosses far below NW line (reversal failed)
                elif current_distance < -0.02:  # 2% below NW line
                    self.position.close()
                    self.entry_price = None
                    self.is_long = None
        
        else:
            # Entry logic - Look for bounces off NW line
            volume_confirm = current_volume > (volume_avg * self.volume_threshold)
            
            # Long entry - Price bouncing up from NW line
            if (prev_distance < -self.min_distance and  # Was below NW line
                current_distance > prev_distance and  # Moving back up
                abs(current_distance) < self.min_distance * 2 and  # Close to NW line
                volume_confirm):  # Volume confirmation
                
                self.buy()
                self.entry_price = current_price
                self.entry_atr = current_atr
                self.is_long = True
            
            # Short entry - Price bouncing down from NW line
            elif (prev_distance > self.min_distance and  # Was above NW line
                  current_distance < prev_distance and  # Moving back down
                  abs(current_distance) < self.min_distance * 2 and  # Close to NW line
                  volume_confirm):  # Volume confirmation
                
                self.sell()
                self.entry_price = current_price
                self.entry_atr = current_atr
                self.is_long = False

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING NADARAYA-WATSON REVERSAL STRATEGY ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    results = test_on_all_data(NadarayaWatsonReversal, 'NadarayaWatsonReversal')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/NadarayaWatsonReversal.csv")