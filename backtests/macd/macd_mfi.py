"""
Moon Dev's MACD MFI Strategy
=============================
MACD strategy with Money Flow Index for volume confirmation
Tests across all datasets with comprehensive stats output
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's MACD MFI Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# MACD parameters
FAST_PERIOD = 12
SLOW_PERIOD = 26
SIGNAL_PERIOD = 9

# MFI parameters
MFI_PERIOD = 14
MFI_OVERBOUGHT = 80
MFI_OVERSOLD = 20

# Risk management
TAKE_PROFIT_PERCENT = 3.0
STOP_LOSS_PERCENT = 2.0

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class MACDMFI(Strategy):
    """
    MACD MFI Strategy
    - Uses MACD crossovers with Money Flow Index confirmation
    - MFI provides volume-weighted momentum
    - Identifies overbought/oversold conditions with volume
    - Confirms MACD signals with money flow
    """
    
    # MACD parameters
    fast_period = FAST_PERIOD
    slow_period = SLOW_PERIOD
    signal_period = SIGNAL_PERIOD
    
    # MFI parameters
    mfi_period = MFI_PERIOD
    mfi_overbought = MFI_OVERBOUGHT
    mfi_oversold = MFI_OVERSOLD
    
    # Risk management
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100
    
    # Histogram momentum threshold
    histogram_threshold = 0.0001
    
    def init(self):
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        volume = pd.Series(self.data.Volume)
        
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
        
        # Calculate MFI (Money Flow Index)
        mfi_series = ta.mfi(high, low, close, volume, length=self.mfi_period)
        
        # Create full-length array for MFI
        mfi_full = np.full(len(close), np.nan)
        mfi_full[-len(mfi_series):] = mfi_series.values
        
        self.mfi = self.I(lambda: mfi_full, name='MFI')
        
        # Previous MFI values for divergence detection
        mfi_prev = np.roll(mfi_full, 1)
        mfi_prev[0] = np.nan
        self.mfi_prev = self.I(lambda: mfi_prev, name='MFI_Prev')
        
        # Calculate MFI slope for momentum
        mfi_slope = mfi_full - np.roll(mfi_full, 5)
        self.mfi_slope = self.I(lambda: mfi_slope, name='MFI_Slope')
        
        # Detect MFI divergences with price
        price_change = close.values - np.roll(close.values, 10)
        mfi_change = mfi_full - np.roll(mfi_full, 10)
        
        # Bullish divergence: price down, MFI up
        bullish_div = np.where((price_change < 0) & (mfi_change > 0), 1, 0)
        # Bearish divergence: price up, MFI down
        bearish_div = np.where((price_change > 0) & (mfi_change < 0), 1, 0)
        
        self.mfi_bullish_div = self.I(lambda: bullish_div, name='MFI_Bull_Div')
        self.mfi_bearish_div = self.I(lambda: bearish_div, name='MFI_Bear_Div')
        
    def next(self):
        # Skip if indicators not ready
        if (np.isnan(self.macd[-1]) or np.isnan(self.signal[-1]) or 
            np.isnan(self.histogram[-1]) or np.isnan(self.mfi[-1])):
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
        
        # MFI conditions
        mfi_oversold = self.mfi[-1] < self.mfi_oversold
        mfi_overbought = self.mfi[-1] > self.mfi_overbought
        mfi_neutral = self.mfi_oversold <= self.mfi[-1] <= self.mfi_overbought
        
        # MFI momentum
        mfi_rising = self.mfi[-1] > self.mfi_prev[-1] if not np.isnan(self.mfi_prev[-1]) else False
        mfi_falling = self.mfi[-1] < self.mfi_prev[-1] if not np.isnan(self.mfi_prev[-1]) else False
        mfi_momentum_strong = abs(self.mfi_slope[-1]) > 5 if not np.isnan(self.mfi_slope[-1]) else False
        
        # Check for MFI divergences
        has_bullish_divergence = self.mfi_bullish_div[-1] == 1
        has_bearish_divergence = self.mfi_bearish_div[-1] == 1
        
        if not self.position:
            # Long entry: MACD bullish with MFI confirmation
            # Best setup: MACD crossover with oversold MFI starting to rise
            if (bullish_crossover and histogram_increasing and histogram_positive and 
                (mfi_oversold or (mfi_neutral and mfi_rising)) and not mfi_overbought):
                sl_price = current_price * (1 - self.stop_loss)
                tp_price = current_price * (1 + self.take_profit)
                self.buy(sl=sl_price, tp=tp_price)
            
            # Alternative long: Bullish divergence with MACD confirmation
            elif (has_bullish_divergence and histogram_positive and 
                  self.macd[-1] > self.signal[-1] and mfi_rising):
                sl_price = current_price * (1 - self.stop_loss)
                tp_price = current_price * (1 + self.take_profit)
                self.buy(sl=sl_price, tp=tp_price)
            
            # Short entry: MACD bearish with MFI confirmation
            # Best setup: MACD crossover with overbought MFI starting to fall
            elif (bearish_crossover and histogram_decreasing and histogram_negative and 
                  (mfi_overbought or (mfi_neutral and mfi_falling)) and not mfi_oversold):
                sl_price = current_price * (1 + self.stop_loss)
                tp_price = current_price * (1 - self.take_profit)
                self.sell(sl=sl_price, tp=tp_price)
            
            # Alternative short: Bearish divergence with MACD confirmation
            elif (has_bearish_divergence and histogram_negative and 
                  self.macd[-1] < self.signal[-1] and mfi_falling):
                sl_price = current_price * (1 + self.stop_loss)
                tp_price = current_price * (1 - self.take_profit)
                self.sell(sl=sl_price, tp=tp_price)
        
        # Exit conditions for existing positions
        elif self.position.is_long:
            # Exit long if MFI becomes overbought or MACD turns bearish
            if (mfi_overbought and mfi_falling) or bearish_crossover or has_bearish_divergence:
                self.position.close()
        
        elif self.position.is_short:
            # Exit short if MFI becomes oversold or MACD turns bullish
            if (mfi_oversold and mfi_rising) or bullish_crossover or has_bullish_divergence:
                self.position.close()

# Run single backtest
bt = Backtest(data, MACDMFI, cash=100000, commission=0.00045)

print("\n🌙 ===== MACD MFI STRATEGY - DEFAULT PARAMETERS ===== 🌙")
print(f"Fast Period: {FAST_PERIOD}")
print(f"Slow Period: {SLOW_PERIOD}")
print(f"Signal Period: {SIGNAL_PERIOD}")
print(f"MFI Period: {MFI_PERIOD}")
print(f"MFI Overbought: {MFI_OVERBOUGHT}")
print(f"MFI Oversold: {MFI_OVERSOLD}")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")

stats_default = bt.run()
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING MACD MFI STRATEGY ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from backtests.multi_data_tester import test_on_all_data
    
    # Test this strategy on all configured data sources
    results = test_on_all_data(MACDMFI, 'MACDMFI')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/MACDMFI_[timestamp].csv")