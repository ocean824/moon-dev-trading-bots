"""
Moon Dev's MACD Fibonacci Strategy
===================================
MACD strategy with Fibonacci retracement levels for confirmation
Tests across all datasets with comprehensive stats output
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's MACD Fibonacci Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# MACD parameters
FAST_PERIOD = 12
SLOW_PERIOD = 26
SIGNAL_PERIOD = 9

# Fibonacci parameters
FIB_LOOKBACK = 50  # Periods to look back for swing high/low

# Risk management
TAKE_PROFIT_PERCENT = 3.0
STOP_LOSS_PERCENT = 2.0

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class MACDFibonacci(Strategy):
    """
    MACD Fibonacci Strategy
    - Uses MACD crossovers with Fibonacci retracement levels
    - Fibonacci levels provide support/resistance confirmation
    - Trades only when price is near key Fibonacci levels
    """
    
    # MACD parameters
    fast_period = FAST_PERIOD
    slow_period = SLOW_PERIOD
    signal_period = SIGNAL_PERIOD
    
    # Fibonacci parameters
    fib_lookback = FIB_LOOKBACK
    fib_tolerance = 0.02  # 2% tolerance for being "near" a Fibonacci level
    
    # Risk management
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100
    
    # Histogram momentum threshold
    histogram_threshold = 0.0001
    
    def calculate_fibonacci_levels(self, high_array, low_array, lookback):
        """Calculate Fibonacci retracement levels"""
        fib_levels_array = np.full((len(high_array), 5), np.nan)
        
        for i in range(lookback, len(high_array)):
            # Find swing high and low in lookback period
            swing_high = np.max(high_array[i-lookback:i])
            swing_low = np.min(low_array[i-lookback:i])
            
            # Calculate Fibonacci levels
            diff = swing_high - swing_low
            
            # Key Fibonacci retracement levels
            fib_levels_array[i, 0] = swing_low  # 0%
            fib_levels_array[i, 1] = swing_low + diff * 0.236  # 23.6%
            fib_levels_array[i, 2] = swing_low + diff * 0.382  # 38.2%
            fib_levels_array[i, 3] = swing_low + diff * 0.618  # 61.8%
            fib_levels_array[i, 4] = swing_high  # 100%
            
        return fib_levels_array
    
    def init(self):
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        
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
        
        # Calculate histogram momentum
        histogram_momentum = histogram_full - histogram_prev
        self.histogram_momentum = self.I(lambda: histogram_momentum, name='Histogram_Momentum')
        
        # Calculate Fibonacci levels
        fib_levels = self.calculate_fibonacci_levels(high.values, low.values, self.fib_lookback)
        
        self.fib_0 = self.I(lambda: fib_levels[:, 0], name='Fib_0%')
        self.fib_236 = self.I(lambda: fib_levels[:, 1], name='Fib_23.6%')
        self.fib_382 = self.I(lambda: fib_levels[:, 2], name='Fib_38.2%')
        self.fib_618 = self.I(lambda: fib_levels[:, 3], name='Fib_61.8%')
        self.fib_100 = self.I(lambda: fib_levels[:, 4], name='Fib_100%')
        
    def is_near_fibonacci_level(self, price):
        """Check if price is near a Fibonacci level"""
        if np.isnan(self.fib_236[-1]):
            return False, None
        
        fib_levels = [
            (self.fib_0[-1], '0%'),
            (self.fib_236[-1], '23.6%'),
            (self.fib_382[-1], '38.2%'),
            (self.fib_618[-1], '61.8%'),
            (self.fib_100[-1], '100%')
        ]
        
        for level, name in fib_levels:
            if abs(price - level) / price <= self.fib_tolerance:
                return True, name
        
        return False, None
    
    def next(self):
        # Skip if indicators not ready
        if np.isnan(self.macd[-1]) or np.isnan(self.signal[-1]) or np.isnan(self.histogram[-1]):
            return
        
        # Skip if previous values not ready
        if np.isnan(self.macd_prev[-1]) or np.isnan(self.signal_prev[-1]):
            return
        
        current_price = self.data.Close[-1]
        
        # Check if price is near a Fibonacci level
        near_fib, fib_level = self.is_near_fibonacci_level(current_price)
        
        # Detect MACD crossovers
        bullish_crossover = (self.macd_prev[-1] <= self.signal_prev[-1] and 
                            self.macd[-1] > self.signal[-1])
        
        bearish_crossover = (self.macd_prev[-1] >= self.signal_prev[-1] and 
                            self.macd[-1] < self.signal[-1])
        
        # Check histogram momentum
        histogram_increasing = self.histogram_momentum[-1] > self.histogram_threshold
        histogram_decreasing = self.histogram_momentum[-1] < -self.histogram_threshold
        
        # Check if histogram is positive or negative
        histogram_positive = self.histogram[-1] > 0
        histogram_negative = self.histogram[-1] < 0
        
        # Determine if we're at a support or resistance Fibonacci level
        at_support = near_fib and fib_level in ['23.6%', '38.2%', '61.8%'] and current_price < self.fib_618[-1]
        at_resistance = near_fib and fib_level in ['38.2%', '61.8%', '100%'] and current_price > self.fib_382[-1]
        
        if not self.position:
            # Long entry: MACD bullish crossover near Fibonacci support
            if bullish_crossover and histogram_increasing and histogram_positive and at_support:
                sl_price = current_price * (1 - self.stop_loss)
                tp_price = current_price * (1 + self.take_profit)
                self.buy(sl=sl_price, tp=tp_price)
            
            # Short entry: MACD bearish crossover near Fibonacci resistance
            elif bearish_crossover and histogram_decreasing and histogram_negative and at_resistance:
                sl_price = current_price * (1 + self.stop_loss)
                tp_price = current_price * (1 - self.take_profit)
                self.sell(sl=sl_price, tp=tp_price)
        
        # Exit conditions for existing positions
        elif self.position.is_long:
            # Exit long on bearish crossover or hitting resistance
            if bearish_crossover or (at_resistance and histogram_decreasing):
                self.position.close()
        
        elif self.position.is_short:
            # Exit short on bullish crossover or hitting support
            if bullish_crossover or (at_support and histogram_increasing):
                self.position.close()

# Run single backtest
bt = Backtest(data, MACDFibonacci, cash=100000, commission=0.00045)

print("\n🌙 ===== MACD FIBONACCI STRATEGY - DEFAULT PARAMETERS ===== 🌙")
print(f"Fast Period: {FAST_PERIOD}")
print(f"Slow Period: {SLOW_PERIOD}")
print(f"Signal Period: {SIGNAL_PERIOD}")
print(f"Fibonacci Lookback: {FIB_LOOKBACK}")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")

stats_default = bt.run()
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING MACD FIBONACCI STRATEGY ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from backtests.multi_data_tester import test_on_all_data
    
    # Test this strategy on all configured data sources
    results = test_on_all_data(MACDFibonacci, 'MACDFibonacci')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/MACDFibonacci_[timestamp].csv")