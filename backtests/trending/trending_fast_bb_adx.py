import pandas as pd
import numpy as np
import talib
from backtesting import Strategy

print("Moon Dev's Fast Bollinger-ADX Intraday Trend Following Loading...")

class FastBBADXTrend(Strategy):
    # Parameters
    take_profit = 0.06  # 6% take profit for intraday
    stop_loss = 0.03    # 3% stop loss
    bb_period = 15      # Shorter BB period for faster signals
    bb_std = 2
    adx_period = 14
    adx_threshold = 25  # Minimum ADX for trend strength
    
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
        if len(self.data) < max(self.bb_period, self.adx_period) + 10:
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
                
                # Exit if price touches middle band or trend weakens
                elif current_price <= self.bb_middle[-1] or self.adx[-1] < 20:
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
                
                # Exit if price touches middle band or trend weakens
                elif current_price >= self.bb_middle[-1] or self.adx[-1] < 20:
                    self.position.close()
                    self.entry_price = None
                    self.position_type = None
        
        else:
            # Entry logic - Only enter when ADX shows strong trend
            if self.adx[-1] > self.adx_threshold:
                # Long: Break above upper band with uptrend confirmation
                if (current_price > self.bb_upper[-1] and 
                    self.data.Close[-2] <= self.bb_upper[-2] and
                    self.plus_di[-1] > self.minus_di[-1] and
                    current_price > self.bb_middle[-1]):
                    self.buy()
                    self.entry_price = current_price
                    self.position_type = 'long'
                
                # Short: Break below lower band with downtrend confirmation
                elif (current_price < self.bb_lower[-1] and 
                      self.data.Close[-2] >= self.bb_lower[-2] and
                      self.minus_di[-1] > self.plus_di[-1] and
                      current_price < self.bb_middle[-1]):
                    self.sell()
                    self.entry_price = current_price
                    self.position_type = 'short'

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING FAST BB-ADX INTRADAY TREND ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    results = test_on_all_data(FastBBADXTrend, 'FastBBADXTrend')
    
    if results is not None:
        print("\nTesting complete! Results saved in: ./results/FastBBADXTrend.csv")