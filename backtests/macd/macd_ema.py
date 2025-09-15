"""
Moon Dev's MACD EMA Strategy
=============================
MACD strategy with EMA trend confirmation
Tests across all datasets with comprehensive stats output
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's MACD EMA Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# MACD parameters
FAST_PERIOD = 12
SLOW_PERIOD = 26
SIGNAL_PERIOD = 9

# EMA parameters for trend confirmation
EMA_SHORT = 20
EMA_MEDIUM = 50
EMA_LONG = 200

# Risk management
TAKE_PROFIT_PERCENT = 3.0
STOP_LOSS_PERCENT = 2.0

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class MACDEMA(Strategy):
    """
    MACD EMA Strategy
    - Uses MACD crossovers with EMA trend confirmation
    - Multiple EMAs (20, 50, 200) provide trend direction
    - Only trades in direction of the trend
    """
    
    # MACD parameters
    fast_period = FAST_PERIOD
    slow_period = SLOW_PERIOD
    signal_period = SIGNAL_PERIOD
    
    # EMA parameters
    ema_short = EMA_SHORT
    ema_medium = EMA_MEDIUM
    ema_long = EMA_LONG
    
    # Risk management
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100
    
    # Histogram momentum threshold
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
        
        # Calculate histogram momentum
        histogram_momentum = histogram_full - histogram_prev
        self.histogram_momentum = self.I(lambda: histogram_momentum, name='Histogram_Momentum')
        
        # Calculate EMAs for trend confirmation
        ema_short_series = ta.ema(close, length=self.ema_short)
        ema_medium_series = ta.ema(close, length=self.ema_medium)
        ema_long_series = ta.ema(close, length=self.ema_long)
        
        # Create full-length arrays for EMAs
        ema_short_full = np.full(len(close), np.nan)
        ema_medium_full = np.full(len(close), np.nan)
        ema_long_full = np.full(len(close), np.nan)
        
        ema_short_full[-len(ema_short_series):] = ema_short_series.values
        ema_medium_full[-len(ema_medium_series):] = ema_medium_series.values
        ema_long_full[-len(ema_long_series):] = ema_long_series.values
        
        self.ema_short = self.I(lambda: ema_short_full, name=f'EMA_{self.ema_short}')
        self.ema_medium = self.I(lambda: ema_medium_full, name=f'EMA_{self.ema_medium}')
        self.ema_long = self.I(lambda: ema_long_full, name=f'EMA_{self.ema_long}')
        
        # Calculate EMA slopes for trend strength
        ema_short_slope = ema_short_full - np.roll(ema_short_full, 5)
        ema_medium_slope = ema_medium_full - np.roll(ema_medium_full, 5)
        
        self.ema_short_slope = self.I(lambda: ema_short_slope, name='EMA_Short_Slope')
        self.ema_medium_slope = self.I(lambda: ema_medium_slope, name='EMA_Medium_Slope')
        
    def next(self):
        # Skip if indicators not ready
        if (np.isnan(self.macd[-1]) or np.isnan(self.signal[-1]) or 
            np.isnan(self.histogram[-1]) or np.isnan(self.ema_long[-1])):
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
        histogram_increasing = self.histogram_momentum[-1] > self.histogram_threshold
        histogram_decreasing = self.histogram_momentum[-1] < -self.histogram_threshold
        
        # Check if histogram is positive or negative
        histogram_positive = self.histogram[-1] > 0
        histogram_negative = self.histogram[-1] < 0
        
        # EMA trend analysis
        # Perfect bullish alignment: Short > Medium > Long
        bullish_ema_alignment = (self.ema_short[-1] > self.ema_medium[-1] > self.ema_long[-1])
        
        # Perfect bearish alignment: Short < Medium < Long
        bearish_ema_alignment = (self.ema_short[-1] < self.ema_medium[-1] < self.ema_long[-1])
        
        # Price position relative to EMAs
        price_above_short = current_price > self.ema_short[-1]
        price_below_short = current_price < self.ema_short[-1]
        price_above_medium = current_price > self.ema_medium[-1]
        price_below_medium = current_price < self.ema_medium[-1]
        
        # EMA slope confirmation (trend strength)
        uptrend_strong = self.ema_short_slope[-1] > 0 and self.ema_medium_slope[-1] > 0
        downtrend_strong = self.ema_short_slope[-1] < 0 and self.ema_medium_slope[-1] < 0
        
        if not self.position:
            # Long entry: MACD bullish with EMA uptrend confirmation
            if (bullish_crossover and histogram_increasing and histogram_positive and 
                bullish_ema_alignment and price_above_short and uptrend_strong):
                sl_price = current_price * (1 - self.stop_loss)
                tp_price = current_price * (1 + self.take_profit)
                self.buy(sl=sl_price, tp=tp_price)
            
            # Short entry: MACD bearish with EMA downtrend confirmation
            elif (bearish_crossover and histogram_decreasing and histogram_negative and 
                  bearish_ema_alignment and price_below_short and downtrend_strong):
                sl_price = current_price * (1 + self.stop_loss)
                tp_price = current_price * (1 - self.take_profit)
                self.sell(sl=sl_price, tp=tp_price)
        
        # Exit conditions for existing positions
        elif self.position.is_long:
            # Exit long if MACD turns bearish or price breaks below medium EMA
            if bearish_crossover or (price_below_medium and histogram_negative):
                self.position.close()
        
        elif self.position.is_short:
            # Exit short if MACD turns bullish or price breaks above medium EMA
            if bullish_crossover or (price_above_medium and histogram_positive):
                self.position.close()

# Run single backtest
bt = Backtest(data, MACDEMA, cash=100000, commission=0.00045)

print("\n🌙 ===== MACD EMA STRATEGY - DEFAULT PARAMETERS ===== 🌙")
print(f"Fast Period: {FAST_PERIOD}")
print(f"Slow Period: {SLOW_PERIOD}")
print(f"Signal Period: {SIGNAL_PERIOD}")
print(f"EMA Periods: {EMA_SHORT}, {EMA_MEDIUM}, {EMA_LONG}")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")

stats_default = bt.run()
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING MACD EMA STRATEGY ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from backtests.multi_data_tester import test_on_all_data
    
    # Test this strategy on all configured data sources
    results = test_on_all_data(MACDEMA, 'MACDEMA')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/MACDEMA_[timestamp].csv")