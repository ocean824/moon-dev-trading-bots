import pandas as pd
import numpy as np
import talib
from backtesting import Strategy

print("Moon Dev's Golden Cross Trend Following Loading...")

class GoldenCrossTrend(Strategy):
    # Parameters
    take_profit = 0.20  # 20% take profit for strong trends
    stop_loss = 0.10    # 10% stop loss
    fast_ma = 50
    slow_ma = 200
    
    def init(self):
        # Calculate moving averages
        self.ma50 = self.I(talib.SMA, self.data.Close, timeperiod=self.fast_ma)
        self.ma200 = self.I(talib.SMA, self.data.Close, timeperiod=self.slow_ma)
        
        # Track entry price for exits
        self.entry_price = None
    
    def next(self):
        # Skip if we don't have enough data
        if len(self.data) < self.slow_ma + 1:
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
            
            # Death cross - MA50 crosses below MA200
            elif self.ma50[-1] < self.ma200[-1] and self.ma50[-2] >= self.ma200[-2]:
                self.position.close()
                self.entry_price = None
        
        else:
            # Entry logic - Golden cross: MA50 crosses above MA200
            if self.ma50[-1] > self.ma200[-1] and self.ma50[-2] <= self.ma200[-2]:
                self.buy()
                self.entry_price = self.data.Close[-1]

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING GOLDEN CROSS TREND ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    results = test_on_all_data(GoldenCrossTrend, 'GoldenCrossTrend')
    
    if results is not None:
        print("\nTesting complete! Results saved in: ./results/GoldenCrossTrend.csv")