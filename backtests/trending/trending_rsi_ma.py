import pandas as pd
import numpy as np
import talib
from backtesting import Strategy

print("Moon Dev's RSI-MA Long/Short Trend Following Loading...")

class RSIMATrend(Strategy):
    # Parameters
    take_profit = 0.12  # 12% take profit
    stop_loss = 0.06    # 6% stop loss
    fast_ma = 50
    slow_ma = 200
    rsi_period = 14
    rsi_neutral = 50
    
    def init(self):
        # Calculate moving averages
        self.ma50 = self.I(talib.SMA, self.data.Close, timeperiod=self.fast_ma)
        self.ma200 = self.I(talib.SMA, self.data.Close, timeperiod=self.slow_ma)
        
        # Calculate RSI
        self.rsi = self.I(talib.RSI, self.data.Close, timeperiod=self.rsi_period)
        
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
                
                # Exit long if conditions no longer met
                elif self.ma50[-1] < self.ma200[-1] or self.rsi[-1] < self.rsi_neutral:
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
                
                # Exit short if conditions no longer met
                elif self.ma50[-1] > self.ma200[-1] or self.rsi[-1] > self.rsi_neutral:
                    self.position.close()
                    self.entry_price = None
                    self.position_type = None
        
        else:
            # Entry logic
            # Long when MA50 > MA200 and RSI > 50
            if self.ma50[-1] > self.ma200[-1] and self.rsi[-1] > self.rsi_neutral:
                # Check for recent crossover or RSI confirmation
                if (self.ma50[-2] <= self.ma200[-2] or 
                    (self.rsi[-2] <= self.rsi_neutral and self.rsi[-1] > self.rsi_neutral)):
                    self.buy()
                    self.entry_price = current_price
                    self.position_type = 'long'
            
            # Short when MA50 < MA200 and RSI < 50
            elif self.ma50[-1] < self.ma200[-1] and self.rsi[-1] < self.rsi_neutral:
                # Check for recent crossover or RSI confirmation
                if (self.ma50[-2] >= self.ma200[-2] or 
                    (self.rsi[-2] >= self.rsi_neutral and self.rsi[-1] < self.rsi_neutral)):
                    self.sell()
                    self.entry_price = current_price
                    self.position_type = 'short'

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING RSI-MA LONG/SHORT TREND ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    results = test_on_all_data(RSIMATrend, 'RSIMATrend')
    
    if results is not None:
        print("\nTesting complete! Results saved in: ./results/RSIMATrend.csv")