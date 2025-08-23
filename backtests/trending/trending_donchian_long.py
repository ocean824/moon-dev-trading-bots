import pandas as pd
import numpy as np
import talib
from backtesting import Strategy

print("Moon Dev's Donchian Channel Long-Only Trend Following Loading...")

class DonchianLongTrend(Strategy):
    # Parameters
    take_profit = 0.12  # 12% take profit
    stop_loss = 0.06    # 6% stop loss
    donchian_period = 20
    
    def init(self):
        # Calculate Donchian Channel (20-period high/low)
        self.upper_band = self.I(talib.MAX, self.data.High, timeperiod=self.donchian_period)
        self.lower_band = self.I(talib.MIN, self.data.Low, timeperiod=self.donchian_period)
        self.middle_band = self.I(lambda h, l: (h + l) / 2, self.upper_band, self.lower_band)
        
        # Track entry price for exits
        self.entry_price = None
    
    def next(self):
        # Skip if we don't have enough data
        if len(self.data) < self.donchian_period + 1:
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
            
            # Exit if price breaks below middle band
            elif current_price < self.middle_band[-1]:
                self.position.close()
                self.entry_price = None
        
        else:
            # Entry logic - Breakout above upper Donchian band
            if self.data.Close[-1] > self.upper_band[-2]:  # Compare with previous upper band
                self.buy()
                self.entry_price = self.data.Close[-1]

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING DONCHIAN LONG-ONLY TREND ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    results = test_on_all_data(DonchianLongTrend, 'DonchianLongTrend')
    
    if results is not None:
        print("\nTesting complete! Results saved in: ./results/DonchianLongTrend.csv")