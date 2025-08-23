import pandas as pd
import numpy as np
import talib
from backtesting import Strategy

print("Moon Dev's Fast MA-ADX Trend Following Loading...")

class FastMAADXTrend(Strategy):
    # Parameters
    take_profit = 0.08  # 8% take profit for faster trades
    stop_loss = 0.04    # 4% stop loss
    fast_ma = 10
    slow_ma = 30
    adx_period = 14
    adx_threshold = 25  # Minimum ADX for trend strength
    
    def init(self):
        # Calculate fast moving averages
        self.ma10 = self.I(talib.SMA, self.data.Close, timeperiod=self.fast_ma)
        self.ma30 = self.I(talib.SMA, self.data.Close, timeperiod=self.slow_ma)
        
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
        if len(self.data) < self.slow_ma + 10:
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
                
                # Exit if fast MA crosses below slow MA or trend weakens
                elif self.ma10[-1] < self.ma30[-1] or self.adx[-1] < 20:
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
                
                # Exit if fast MA crosses above slow MA or trend weakens
                elif self.ma10[-1] > self.ma30[-1] or self.adx[-1] < 20:
                    self.position.close()
                    self.entry_price = None
                    self.position_type = None
        
        else:
            # Entry logic - Only enter when ADX shows strong trend
            if self.adx[-1] > self.adx_threshold:
                # Long: Fast MA crosses above slow MA with strong trend
                if (self.ma10[-1] > self.ma30[-1] and 
                    self.ma10[-2] <= self.ma30[-2] and
                    self.plus_di[-1] > self.minus_di[-1]):
                    self.buy()
                    self.entry_price = current_price
                    self.position_type = 'long'
                
                # Short: Fast MA crosses below slow MA with strong trend
                elif (self.ma10[-1] < self.ma30[-1] and 
                      self.ma10[-2] >= self.ma30[-2] and
                      self.minus_di[-1] > self.plus_di[-1]):
                    self.sell()
                    self.entry_price = current_price
                    self.position_type = 'short'

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING FAST MA-ADX TREND ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    results = test_on_all_data(FastMAADXTrend, 'FastMAADXTrend')
    
    if results is not None:
        print("\nTesting complete! Results saved in: ./results/FastMAADXTrend.csv")