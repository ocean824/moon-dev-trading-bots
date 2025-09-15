"""
Moon Dev's Three Mountains & Three Rivers with Fibonacci Strategy
==================================================================
Combines pattern recognition with Fibonacci retracement levels
Uses Fib levels to confirm pattern targets and improve exit timing
Tests across all datasets with comprehensive stats output
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
from scipy.signal import argrelextrema
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Three Mountains & Rivers Fibonacci Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Pattern detection parameters
LOOKBACK_PERIOD = 20
MIN_PATTERN_BARS = 15
MAX_PATTERN_BARS = 60
PEAK_TOLERANCE = 0.02
CONFIRMATION_BARS = 2

# Fibonacci levels
FIB_LEVELS = [0.236, 0.382, 0.5, 0.618, 0.786]
FIB_EXTENSION = [1.272, 1.618]

# Risk management
TAKE_PROFIT_PERCENT = 4.5  # Slightly higher for Fib targets
STOP_LOSS_PERCENT = 2.0

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

def calculate_fibonacci_levels(high, low, is_uptrend=True):
    """
    Calculate Fibonacci retracement and extension levels
    """
    diff = high - low
    
    if is_uptrend:
        # Retracement levels from high
        retracements = {
            'fib_236': high - diff * 0.236,
            'fib_382': high - diff * 0.382,
            'fib_500': high - diff * 0.500,
            'fib_618': high - diff * 0.618,
            'fib_786': high - diff * 0.786
        }
        # Extension levels
        extensions = {
            'fib_1272': high + diff * 0.272,
            'fib_1618': high + diff * 0.618
        }
    else:
        # Retracement levels from low
        retracements = {
            'fib_236': low + diff * 0.236,
            'fib_382': low + diff * 0.382,
            'fib_500': low + diff * 0.500,
            'fib_618': low + diff * 0.618,
            'fib_786': low + diff * 0.786
        }
        # Extension levels
        extensions = {
            'fib_1272': low - diff * 0.272,
            'fib_1618': low - diff * 0.618
        }
    
    return retracements, extensions

class ThreeMountainsRiversFibonacci(Strategy):
    """
    Three Mountains & Rivers with Fibonacci Strategy
    - Uses Fibonacci retracements to confirm pattern validity
    - Sets targets based on Fibonacci extension levels
    - Improves entry/exit timing with key Fib levels
    """
    
    # Pattern parameters
    lookback = LOOKBACK_PERIOD
    min_bars = MIN_PATTERN_BARS
    max_bars = MAX_PATTERN_BARS
    peak_tolerance = PEAK_TOLERANCE
    confirmation_bars = CONFIRMATION_BARS
    
    # Fibonacci parameters
    fib_levels = FIB_LEVELS
    fib_extensions = FIB_EXTENSION
    
    # Risk management
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100
    
    def init(self):
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        volume = pd.Series(self.data.Volume)
        
        # Find peaks and troughs
        peaks = argrelextrema(high.values, np.greater, order=self.lookback)[0]
        troughs = argrelextrema(low.values, np.less, order=self.lookback)[0]
        
        peak_array = np.zeros(len(close))
        trough_array = np.zeros(len(close))
        
        peak_array[peaks] = high.iloc[peaks].values
        trough_array[troughs] = low.iloc[troughs].values
        
        self.peaks = self.I(lambda: peak_array, name='Peaks')
        self.troughs = self.I(lambda: trough_array, name='Troughs')
        
        # Calculate rolling high/low for Fibonacci
        rolling_high = high.rolling(window=50).max()
        rolling_low = low.rolling(window=50).min()
        
        self.rolling_high = self.I(lambda: rolling_high.values, name='Rolling_High')
        self.rolling_low = self.I(lambda: rolling_low.values, name='Rolling_Low')
        
        # Calculate dynamic Fibonacci levels
        fib_support = np.zeros(len(close))
        fib_resistance = np.zeros(len(close))
        
        for i in range(50, len(close)):
            if not np.isnan(rolling_high.iloc[i]) and not np.isnan(rolling_low.iloc[i]):
                # Calculate key Fibonacci level (0.618)
                diff = rolling_high.iloc[i] - rolling_low.iloc[i]
                fib_support[i] = rolling_high.iloc[i] - diff * 0.618
                fib_resistance[i] = rolling_low.iloc[i] + diff * 0.618
        
        self.fib_support = self.I(lambda: fib_support, name='Fib_Support')
        self.fib_resistance = self.I(lambda: fib_resistance, name='Fib_Resistance')
        
        # Volume average
        volume_sma = ta.sma(volume, length=20)
        self.volume_avg = self.I(lambda: volume_sma.values, name='Volume_Avg')
        
        # Pattern signals with Fibonacci confirmation
        mountains_signal = np.zeros(len(close))
        rivers_signal = np.zeros(len(close))
        pattern_targets = np.zeros(len(close))
        
        for i in range(len(close)):
            # Three Mountains detection
            if i >= self.max_bars * 3:
                recent_peaks = []
                for j in range(i - self.max_bars * 3, i):
                    if peak_array[j] > 0:
                        recent_peaks.append((j, peak_array[j]))
                
                if len(recent_peaks) >= 3:
                    last_three = recent_peaks[-3:]
                    idx1, peak1 = last_three[0]
                    idx2, peak2 = last_three[1]
                    idx3, peak3 = last_three[2]
                    
                    avg_peak = (peak1 + peak2 + peak3) / 3
                    if (abs(peak1 - avg_peak) / avg_peak <= self.peak_tolerance and
                        abs(peak2 - avg_peak) / avg_peak <= self.peak_tolerance and
                        abs(peak3 - avg_peak) / avg_peak <= self.peak_tolerance):
                        
                        if (self.min_bars <= idx2 - idx1 <= self.max_bars and
                            self.min_bars <= idx3 - idx2 <= self.max_bars):
                            
                            # Find the lowest trough between peaks for Fib calculation
                            pattern_low = low.iloc[idx1:i].min()
                            
                            # Check if price broke below key Fibonacci support
                            if close.iloc[i] < peak3 * 0.98 and close.iloc[i] < fib_support[i]:
                                mountains_signal[i] = -1
                                # Set target at Fibonacci extension
                                pattern_targets[i] = pattern_low - (avg_peak - pattern_low) * 0.618
            
            # Three Rivers detection
            if i >= self.max_bars * 3:
                recent_troughs = []
                for j in range(i - self.max_bars * 3, i):
                    if trough_array[j] > 0:
                        recent_troughs.append((j, trough_array[j]))
                
                if len(recent_troughs) >= 3:
                    last_three = recent_troughs[-3:]
                    idx1, trough1 = last_three[0]
                    idx2, trough2 = last_three[1]
                    idx3, trough3 = last_three[2]
                    
                    avg_trough = (trough1 + trough2 + trough3) / 3
                    if (abs(trough1 - avg_trough) / avg_trough <= self.peak_tolerance and
                        abs(trough2 - avg_trough) / avg_trough <= self.peak_tolerance and
                        abs(trough3 - avg_trough) / avg_trough <= self.peak_tolerance):
                        
                        if (self.min_bars <= idx2 - idx1 <= self.max_bars and
                            self.min_bars <= idx3 - idx2 <= self.max_bars):
                            
                            # Find the highest peak between troughs for Fib calculation
                            pattern_high = high.iloc[idx1:i].max()
                            
                            # Check if price broke above key Fibonacci resistance
                            if close.iloc[i] > trough3 * 1.02 and close.iloc[i] > fib_resistance[i]:
                                rivers_signal[i] = 1
                                # Set target at Fibonacci extension
                                pattern_targets[i] = pattern_high + (pattern_high - avg_trough) * 0.618
        
        self.mountains_signal = self.I(lambda: mountains_signal, name='Mountains_Signal')
        self.rivers_signal = self.I(lambda: rivers_signal, name='Rivers_Signal')
        self.pattern_targets = self.I(lambda: pattern_targets, name='Pattern_Targets')
        
        # Track pattern state
        self.confirmation_counter = 0
        self.pattern_type = 0
        self.pattern_target = 0
        self.entry_price = 0
        
    def next(self):
        current_price = self.data.Close[-1]
        current_volume = self.data.Volume[-1]
        
        # Check for new pattern signals
        if self.mountains_signal[-1] == -1:
            self.pattern_type = -1
            self.confirmation_counter = 0
            self.pattern_target = self.pattern_targets[-1] if self.pattern_targets[-1] != 0 else 0
        elif self.rivers_signal[-1] == 1:
            self.pattern_type = 1
            self.confirmation_counter = 0
            self.pattern_target = self.pattern_targets[-1] if self.pattern_targets[-1] != 0 else 0
        
        # Increment confirmation counter
        if self.pattern_type != 0:
            self.confirmation_counter += 1
        
        # Check Fibonacci level alignment
        near_fib_support = abs(current_price - self.fib_support[-1]) / current_price < 0.01 if self.fib_support[-1] > 0 else False
        near_fib_resistance = abs(current_price - self.fib_resistance[-1]) / current_price < 0.01 if self.fib_resistance[-1] > 0 else False
        
        if not self.position:
            # Three Rivers - bullish entry
            if (self.pattern_type == 1 and 
                self.confirmation_counter >= self.confirmation_bars and
                self.confirmation_counter <= self.confirmation_bars + 5):
                
                # Enter if price is above Fibonacci resistance or bouncing from support
                if current_price > self.fib_resistance[-1] or near_fib_support:
                    sl_price = current_price * (1 - self.stop_loss)
                    
                    # Use Fibonacci target if available, otherwise default
                    if self.pattern_target > current_price:
                        tp_price = min(self.pattern_target, current_price * (1 + self.take_profit * 1.5))
                    else:
                        tp_price = current_price * (1 + self.take_profit)
                    
                    self.buy(sl=sl_price, tp=tp_price)
                    self.entry_price = current_price
                    self.pattern_type = 0
                    self.confirmation_counter = 0
            
            # Three Mountains - bearish entry
            elif (self.pattern_type == -1 and 
                  self.confirmation_counter >= self.confirmation_bars and
                  self.confirmation_counter <= self.confirmation_bars + 5):
                
                # Enter if price is below Fibonacci support or rejected from resistance
                if current_price < self.fib_support[-1] or near_fib_resistance:
                    sl_price = current_price * (1 + self.stop_loss)
                    
                    # Use Fibonacci target if available, otherwise default
                    if self.pattern_target < current_price and self.pattern_target > 0:
                        tp_price = max(self.pattern_target, current_price * (1 - self.take_profit * 1.5))
                    else:
                        tp_price = current_price * (1 - self.take_profit)
                    
                    self.sell(sl=sl_price, tp=tp_price)
                    self.entry_price = current_price
                    self.pattern_type = 0
                    self.confirmation_counter = 0
        
        # Reset pattern if too old
        if self.confirmation_counter > self.confirmation_bars + 10:
            self.pattern_type = 0
            self.confirmation_counter = 0
            self.pattern_target = 0
        
        # Exit management with Fibonacci levels
        if self.position:
            if self.position.is_long:
                # Exit on bearish pattern or hitting resistance
                if self.mountains_signal[-1] == -1:
                    self.position.close()
                # Take partial profits at Fibonacci levels
                elif self.entry_price > 0 and current_price > self.entry_price * 1.02:
                    profit_pct = (current_price - self.entry_price) / self.entry_price
                    # Exit if near major Fibonacci resistance
                    if near_fib_resistance and profit_pct > 0.01:
                        self.position.close()
                        
            elif self.position.is_short:
                # Exit on bullish pattern or hitting support
                if self.rivers_signal[-1] == 1:
                    self.position.close()
                # Take partial profits at Fibonacci levels
                elif self.entry_price > 0 and current_price < self.entry_price * 0.98:
                    profit_pct = (self.entry_price - current_price) / self.entry_price
                    # Exit if near major Fibonacci support
                    if near_fib_support and profit_pct > 0.01:
                        self.position.close()

# Run single backtest
bt = Backtest(data, ThreeMountainsRiversFibonacci, cash=100000, commission=0.00045)

print("\n🌙 ===== THREE MOUNTAINS & RIVERS FIBONACCI - DEFAULT PARAMETERS ===== 🌙")
print(f"Lookback Period: {LOOKBACK_PERIOD}")
print(f"Fibonacci Levels: {FIB_LEVELS}")
print(f"Pattern Bar Range: {MIN_PATTERN_BARS}-{MAX_PATTERN_BARS}")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")

stats_default = bt.run()
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING THREE MOUNTAINS & RIVERS FIBONACCI ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from backtests.multi_data_tester import test_on_all_data
    
    # Test this strategy on all configured data sources
    results = test_on_all_data(ThreeMountainsRiversFibonacci, 'ThreeMountainsRiversFibonacci')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/ThreeMountainsRiversFibonacci.csv")