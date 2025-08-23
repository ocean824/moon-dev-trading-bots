import pandas as pd
import numpy as np
import talib
from backtesting import Strategy

print("Moon Dev's Volume-MA Trend Following Loading...")

class VolumeMATrend(Strategy):
    # Parameters
    take_profit = 0.14  # 14% take profit
    stop_loss = 0.07    # 7% stop loss
    fast_ma = 50
    slow_ma = 200
    volume_ma_period = 20
    volume_multiplier = 1.5  # Volume must be 1.5x average
    
    def init(self):
        # Calculate moving averages
        self.ma50 = self.I(talib.SMA, self.data.Close, timeperiod=self.fast_ma)
        self.ma200 = self.I(talib.SMA, self.data.Close, timeperiod=self.slow_ma)
        
        # Calculate volume moving average
        self.volume_ma = self.I(talib.SMA, self.data.Volume, timeperiod=self.volume_ma_period)
        
        # Track entry price and position type
        self.entry_price = None
        self.position_type = None  # 'long' or 'short'
    
    def next(self):
        # Skip if we don't have enough data
        if len(self.data) < self.slow_ma + 1:
            return
        
        current_price = self.data.Close[-1]
        current_volume = self.data.Volume[-1]
        
        # Check if we have a position
        if self.position:
            # Exit logic based on position type
            if self.position_type == 'long':
                # Take profit for long
                if current_price >= self.entry_price * (1 + self.take_profit):
                    self.position.close()
                    self.entry_price = None
                    self.position_type = None
                
                # Stop loss for long
                elif current_price <= self.entry_price * (1 - self.stop_loss):
                    self.position.close()
                    self.entry_price = None
                    self.position_type = None
                
                # Exit if trend reverses
                elif self.ma50[-1] < self.ma200[-1]:
                    self.position.close()
                    self.entry_price = None
                    self.position_type = None
            
            elif self.position_type == 'short':
                # Take profit for short
                if current_price <= self.entry_price * (1 - self.take_profit):
                    self.position.close()
                    self.entry_price = None
                    self.position_type = None
                
                # Stop loss for short
                elif current_price >= self.entry_price * (1 + self.stop_loss):
                    self.position.close()
                    self.entry_price = None
                    self.position_type = None
                
                # Exit if trend reverses
                elif self.ma50[-1] > self.ma200[-1]:
                    self.position.close()
                    self.entry_price = None
                    self.position_type = None
        
        else:
            # Entry logic - MA crossovers with volume confirmation
            # Check for volume spike
            volume_spike = current_volume > (self.volume_ma[-1] * self.volume_multiplier)
            
            # Long: Golden cross with volume confirmation
            if (self.ma50[-1] > self.ma200[-1] and 
                self.ma50[-2] <= self.ma200[-2] and
                volume_spike):
                self.buy()
                self.entry_price = current_price
                self.position_type = 'long'
            
            # Short: Death cross with volume confirmation
            elif (self.ma50[-1] < self.ma200[-1] and 
                  self.ma50[-2] >= self.ma200[-2] and
                  volume_spike):
                self.sell()
                self.entry_price = current_price
                self.position_type = 'short'

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING VOLUME-MA TREND ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    results = test_on_all_data(VolumeMATrend, 'VolumeMATrend')
    
    if results is not None:
        print("\nTesting complete! Results saved in: ./results/VolumeMATrend.csv")