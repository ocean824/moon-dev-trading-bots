"""
Moon Dev's MACD Base Strategy
==============================
Uses MACD crossovers and histogram momentum to identify entry and exit points
Tests across all datasets with comprehensive stats output
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's MACD Base Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# MACD parameters
FAST_PERIOD = 12
SLOW_PERIOD = 26
SIGNAL_PERIOD = 9

# Risk management
TAKE_PROFIT_PERCENT = 3.0
STOP_LOSS_PERCENT = 2.0

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class MACDBase(Strategy):
    """
    MACD Base Strategy
    - Monitor MACD Line: Watch for crossovers between the MACD line and the signal line
    - Analyze Histogram: Use the MACD histogram to gauge momentum changes
    - Trade Execution: Enter long or short trades based on confirmed MACD crossovers
    """
    
    # MACD parameters
    fast_period = FAST_PERIOD
    slow_period = SLOW_PERIOD
    signal_period = SIGNAL_PERIOD
    
    # Risk management
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100
    
    # Histogram momentum threshold (minimum histogram change for confirmation)
    histogram_threshold = 0.0001
    
    def init(self):
        close = pd.Series(self.data.Close)
        
        # Calculate MACD
        macd_result = ta.macd(close, 
                              fast=self.fast_period, 
                              slow=self.slow_period, 
                              signal=self.signal_period)
        
        # Extract MACD components
        macd_line = macd_result[f'MACD_{self.fast_period}_{self.slow_period}_{self.signal_period}']
        signal_line = macd_result[f'MACDs_{self.fast_period}_{self.slow_period}_{self.signal_period}']
        histogram = macd_result[f'MACDh_{self.fast_period}_{self.slow_period}_{self.signal_period}']
        
        # Ensure arrays are same length as data
        macd_full = np.full(len(close), np.nan)
        signal_full = np.full(len(close), np.nan)
        histogram_full = np.full(len(close), np.nan)
        
        macd_full[-len(macd_line):] = macd_line.values
        signal_full[-len(signal_line):] = signal_line.values
        histogram_full[-len(histogram):] = histogram.values
        
        self.macd = self.I(lambda: macd_full, name='MACD')
        self.signal = self.I(lambda: signal_full, name='Signal')
        self.histogram = self.I(lambda: histogram_full, name='Histogram')
        
        # Previous values for crossover detection
        macd_prev = np.roll(macd_full, 1)
        signal_prev = np.roll(signal_full, 1)
        histogram_prev = np.roll(histogram_full, 1)
        
        macd_prev[0] = np.nan
        signal_prev[0] = np.nan
        histogram_prev[0] = np.nan
        
        self.macd_prev = self.I(lambda: macd_prev, name='MACD_Prev')
        self.signal_prev = self.I(lambda: signal_prev, name='Signal_Prev')
        self.histogram_prev = self.I(lambda: histogram_prev, name='Histogram_Prev')
        
        # Calculate histogram momentum (rate of change)
        histogram_momentum = histogram_full - histogram_prev
        self.histogram_momentum = self.I(lambda: histogram_momentum, name='Histogram_Momentum')
        
    def next(self):
        # Skip if indicators not ready
        if np.isnan(self.macd[-1]) or np.isnan(self.signal[-1]) or np.isnan(self.histogram[-1]):
            return
        
        # Skip if previous values not ready
        if np.isnan(self.macd_prev[-1]) or np.isnan(self.signal_prev[-1]):
            return
        
        current_price = self.data.Close[-1]
        
        # Detect MACD crossovers
        bullish_crossover = (self.macd_prev[-1] <= self.signal_prev[-1] and 
                            self.macd[-1] > self.signal[-1])
        
        bearish_crossover = (self.macd_prev[-1] >= self.signal_prev[-1] and 
                            self.macd[-1] < self.signal[-1])
        
        # Check histogram momentum
        histogram_increasing = self.histogram[-1] > self.histogram_prev[-1] + self.histogram_threshold
        histogram_decreasing = self.histogram[-1] < self.histogram_prev[-1] - self.histogram_threshold
        
        # Check if histogram is positive or negative for additional confirmation
        histogram_positive = self.histogram[-1] > 0
        histogram_negative = self.histogram[-1] < 0
        
        if not self.position:
            # Long entry conditions
            if bullish_crossover and histogram_increasing and histogram_positive:
                sl_price = current_price * (1 - self.stop_loss)
                tp_price = current_price * (1 + self.take_profit)
                self.buy(sl=sl_price, tp=tp_price)
            
            # Short entry conditions
            elif bearish_crossover and histogram_decreasing and histogram_negative:
                sl_price = current_price * (1 + self.stop_loss)
                tp_price = current_price * (1 - self.take_profit)
                self.sell(sl=sl_price, tp=tp_price)
        
        # Exit conditions for existing positions
        elif self.position.is_long:
            # Exit long on bearish crossover or significant histogram decrease
            if bearish_crossover or (histogram_decreasing and self.histogram[-1] < 0):
                self.position.close()
        
        elif self.position.is_short:
            # Exit short on bullish crossover or significant histogram increase
            if bullish_crossover or (histogram_increasing and self.histogram[-1] > 0):
                self.position.close()

# Run single backtest
bt = Backtest(data, MACDBase, cash=100000, commission=0.00045)

print("\n🌙 ===== MACD BASE STRATEGY - DEFAULT PARAMETERS ===== 🌙")
print(f"Fast Period: {FAST_PERIOD}")
print(f"Slow Period: {SLOW_PERIOD}")
print(f"Signal Period: {SIGNAL_PERIOD}")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")

stats_default = bt.run()
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING MACD BASE STRATEGY ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from backtests.multi_data_tester import test_on_all_data
    
    # Test this strategy on all configured data sources
    results = test_on_all_data(MACDBase, 'MACDBase')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/MACDBase_[timestamp].csv")