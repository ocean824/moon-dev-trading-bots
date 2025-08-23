import pandas as pd
import numpy as np
import talib
from backtesting import Strategy

print("Moon Dev's Bollinger Band Trend Following Loading...")

class BollingerTrend(Strategy):
    # Parameters
    take_profit = 0.10  # 10% take profit
    stop_loss = 0.05    # 5% stop loss
    bb_period = 20
    bb_std = 2
    trend_ma = 50
    
    def init(self):
        # Calculate Bollinger Bands
        self.bb_upper, self.bb_middle, self.bb_lower = self.I(
            talib.BBANDS, 
            self.data.Close, 
            timeperiod=self.bb_period,
            nbdevup=self.bb_std,
            nbdevdn=self.bb_std,
            matype=0
        )
        
        # Trend filter using MA
        self.trend_ma = self.I(talib.SMA, self.data.Close, timeperiod=self.trend_ma)
        
        # Track entry price and position type
        self.entry_price = None
        self.position_type = None  # 'long' or 'short'
    
    def next(self):
        # Skip if we don't have enough data
        if len(self.data) < max(self.bb_period, self.trend_ma) + 1:
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
                
                # Exit if price falls below middle band
                elif current_price < self.bb_middle[-1]:
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
                
                # Exit if price rises above middle band
                elif current_price > self.bb_middle[-1]:
                    self.position.close()
                    self.entry_price = None
                    self.position_type = None
        
        else:
            # Entry logic
            # Long: Break above upper band in uptrend
            if (current_price > self.bb_upper[-1] and 
                current_price > self.trend_ma[-1] and
                self.data.Close[-2] <= self.bb_upper[-2]):
                self.buy()
                self.entry_price = current_price
                self.position_type = 'long'
            
            # Short: Break below lower band in downtrend
            elif (current_price < self.bb_lower[-1] and 
                  current_price < self.trend_ma[-1] and
                  self.data.Close[-2] >= self.bb_lower[-2]):
                self.sell()
                self.entry_price = current_price
                self.position_type = 'short'

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING BOLLINGER TREND ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    results = test_on_all_data(BollingerTrend, 'BollingerTrend')
    
    if results is not None:
        print("\nTesting complete! Results saved in: ./results/BollingerTrend.csv")