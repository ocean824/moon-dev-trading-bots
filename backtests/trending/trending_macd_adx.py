import pandas as pd
import numpy as np
import talib
from backtesting import Strategy

print("Moon Dev's MACD-ADX Trend Strength Following Loading...")

class MACDADXTrend(Strategy):
    # Parameters
    take_profit = 0.12  # 12% take profit
    stop_loss = 0.06    # 6% stop loss
    macd_fast = 12
    macd_slow = 26
    macd_signal = 9
    adx_period = 14
    adx_threshold = 25  # Minimum ADX for trend strength
    
    def init(self):
        # Calculate MACD
        self.macd, self.macd_signal, self.macd_hist = self.I(
            talib.MACD, 
            self.data.Close,
            fastperiod=self.macd_fast,
            slowperiod=self.macd_slow,
            signalperiod=self.macd_signal
        )
        
        # Calculate ADX for trend strength
        self.adx = self.I(talib.ADX, self.data.High, self.data.Low, self.data.Close, timeperiod=self.adx_period)
        
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
                
                # Exit if MACD crosses below signal or trend weakens
                elif self.macd[-1] < self.macd_signal[-1] or self.adx[-1] < 20:
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
                
                # Exit if MACD crosses above signal or trend weakens
                elif self.macd[-1] > self.macd_signal[-1] or self.adx[-1] < 20:
                    self.position.close()
                    self.entry_price = None
                    self.position_type = None
        
        else:
            # Entry logic - Only enter when ADX shows strong trend
            if self.adx[-1] > self.adx_threshold:
                # Long: MACD crosses above signal with strong trend
                if (self.macd[-1] > self.macd_signal[-1] and 
                    self.macd[-2] <= self.macd_signal[-2] and
                    self.macd_hist[-1] > 0):
                    self.buy()
                    self.entry_price = current_price
                    self.position_type = 'long'
                
                # Short: MACD crosses below signal with strong trend
                elif (self.macd[-1] < self.macd_signal[-1] and 
                      self.macd[-2] >= self.macd_signal[-2] and
                      self.macd_hist[-1] < 0):
                    self.sell()
                    self.entry_price = current_price
                    self.position_type = 'short'

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING MACD-ADX TREND STRENGTH ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    results = test_on_all_data(MACDADXTrend, 'MACDADXTrend')
    
    if results is not None:
        print("\nTesting complete! Results saved in: ./results/MACDADXTrend.csv")