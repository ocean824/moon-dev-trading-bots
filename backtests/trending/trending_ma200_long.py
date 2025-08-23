import pandas as pd
import numpy as np
import talib
from backtesting import Strategy

print("Moon Dev's MA200 Long-Only Trend Following Loading...")

class MA200LongTrend(Strategy):
    # Parameters
    take_profit = 0.15  # 15% take profit for longer trends
    stop_loss = 0.08    # 8% stop loss
    ma_period = 200
    
    def init(self):
        # Calculate 200-period moving average
        self.ma200 = self.I(talib.SMA, self.data.Close, timeperiod=self.ma_period)
        
        # Track entry price for exits
        self.entry_price = None
    
    def next(self):
        # Skip if we don't have enough data
        if len(self.data) < self.ma_period + 1:
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
            
            # Exit if price falls below MA200
            elif current_price < self.ma200[-1]:
                self.position.close()
                self.entry_price = None
        
        else:
            # Entry logic - Price crosses above MA200
            if self.data.Close[-1] > self.ma200[-1] and self.data.Close[-2] <= self.ma200[-2]:
                self.buy()
                self.entry_price = self.data.Close[-1]

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING MA200 LONG-ONLY TREND ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    results = test_on_all_data(MA200LongTrend, 'MA200LongTrend')
    
    if results is not None:
        print("\nTesting complete! Results saved in: ./results/MA200LongTrend.csv")