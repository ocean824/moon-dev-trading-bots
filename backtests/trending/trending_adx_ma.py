import pandas as pd
import numpy as np
import talib
from backtesting import Strategy

print("Moon Dev's ADX-MA Trend Strength Following Loading...")

class ADXMATrend(Strategy):
    # Parameters
    take_profit = 0.15  # 15% take profit
    stop_loss = 0.08    # 8% stop loss
    fast_ma = 50
    slow_ma = 200
    adx_period = 14
    adx_threshold = 25  # Minimum ADX for trend strength
    
    def init(self):
        # Calculate moving averages
        self.ma50 = self.I(talib.SMA, self.data.Close, timeperiod=self.fast_ma)
        self.ma200 = self.I(talib.SMA, self.data.Close, timeperiod=self.slow_ma)
        
        # Calculate ADX for trend strength
        self.adx = self.I(talib.ADX, self.data.High, self.data.Low, self.data.Close, timeperiod=self.adx_period)
        
        # Calculate +DI and -DI for direction
        self.plus_di = self.I(talib.PLUS_DI, self.data.High, self.data.Low, self.data.Close, timeperiod=self.adx_period)
        self.minus_di = self.I(talib.MINUS_DI, self.data.High, self.data.Low, self.data.Close, timeperiod=self.adx_period)
        
        # Track entry price and position type
        self.entry_price = None
        self.position_type = None  # 'long' or 'short'
    
    def next(self):
        # Skip if we don't have enough data
        if len(self.data) < self.slow_ma + 1:
            return
        
        current_price = self.data.Close[-1]
        
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
                
                # Exit if trend weakens or reverses
                elif self.adx[-1] < 20 or self.ma50[-1] < self.ma200[-1]:
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
                
                # Exit if trend weakens or reverses
                elif self.adx[-1] < 20 or self.ma50[-1] > self.ma200[-1]:
                    self.position.close()
                    self.entry_price = None
                    self.position_type = None
        
        else:
            # Entry logic - Only enter when ADX shows strong trend
            if self.adx[-1] > self.adx_threshold:
                # Long: Golden cross with strong trend
                if (self.ma50[-1] > self.ma200[-1] and 
                    self.ma50[-2] <= self.ma200[-2] and
                    self.plus_di[-1] > self.minus_di[-1]):
                    self.buy()
                    self.entry_price = current_price
                    self.position_type = 'long'
                
                # Short: Death cross with strong trend
                elif (self.ma50[-1] < self.ma200[-1] and 
                      self.ma50[-2] >= self.ma200[-2] and
                      self.minus_di[-1] > self.plus_di[-1]):
                    self.sell()
                    self.entry_price = current_price
                    self.position_type = 'short'

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING ADX-MA TREND STRENGTH ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    results = test_on_all_data(ADXMATrend, 'ADXMATrend')
    
    if results is not None:
        print("\nTesting complete! Results saved in: ./results/ADXMATrend.csv")