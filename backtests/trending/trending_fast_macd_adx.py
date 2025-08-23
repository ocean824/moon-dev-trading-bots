import pandas as pd
import numpy as np
import talib
from backtesting import Strategy

print("Moon Dev's Fast MACD-ADX Trend Following Loading...")

class FastMACDADXTrend(Strategy):
    # Parameters
    take_profit = 0.07  # 7% take profit for fast trades
    stop_loss = 0.035   # 3.5% stop loss
    macd_fast = 6       # Faster MACD settings
    macd_slow = 13
    macd_signal = 5
    adx_period = 14
    adx_threshold = 25  # Minimum ADX for trend strength
    
    def init(self):
        # Calculate Fast MACD
        self.macd, self.macd_signal, self.macd_hist = self.I(
            talib.MACD, 
            self.data.Close,
            fastperiod=self.macd_fast,
            slowperiod=self.macd_slow,
            signalperiod=self.macd_signal
        )
        
        # Calculate ADX for trend strength
        self.adx = self.I(talib.ADX, self.data.High, self.data.Low, self.data.Close, timeperiod=self.adx_period)
        
        # Calculate +DI and -DI for direction confirmation
        self.plus_di = self.I(talib.PLUS_DI, self.data.High, self.data.Low, self.data.Close, timeperiod=self.adx_period)
        self.minus_di = self.I(talib.MINUS_DI, self.data.High, self.data.Low, self.data.Close, timeperiod=self.adx_period)
        
        # Track entry price and position type
        self.entry_price = None
        self.position_type = None  # 'long' or 'short'
    
    def next(self):
        # Skip if we don't have enough data
        if len(self.data) < max(self.macd_slow, self.adx_period) + 10:
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
                
                # Exit if MACD histogram turns negative or trend weakens
                elif self.macd_hist[-1] < 0 or self.adx[-1] < 20:
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
                
                # Exit if MACD histogram turns positive or trend weakens
                elif self.macd_hist[-1] > 0 or self.adx[-1] < 20:
                    self.position.close()
                    self.entry_price = None
                    self.position_type = None
        
        else:
            # Entry logic - Only enter when ADX shows strong trend
            if self.adx[-1] > self.adx_threshold:
                # Long: MACD crosses above signal with positive histogram and uptrend
                if (self.macd[-1] > self.macd_signal[-1] and 
                    self.macd[-2] <= self.macd_signal[-2] and
                    self.macd_hist[-1] > 0 and
                    self.plus_di[-1] > self.minus_di[-1]):
                    self.buy()
                    self.entry_price = current_price
                    self.position_type = 'long'
                
                # Short: MACD crosses below signal with negative histogram and downtrend
                elif (self.macd[-1] < self.macd_signal[-1] and 
                      self.macd[-2] >= self.macd_signal[-2] and
                      self.macd_hist[-1] < 0 and
                      self.minus_di[-1] > self.plus_di[-1]):
                    self.sell()
                    self.entry_price = current_price
                    self.position_type = 'short'

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING FAST MACD-ADX TREND ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    results = test_on_all_data(FastMACDADXTrend, 'FastMACDADXTrend')
    
    if results is not None:
        print("\nTesting complete! Results saved in: ./results/FastMACDADXTrend.csv")