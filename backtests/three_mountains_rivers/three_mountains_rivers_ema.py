"""
Moon Dev's Three Mountains & Three Rivers with EMA Strategy
============================================================
Combines pattern recognition with EMA trend confirmation
Uses multiple EMA timeframes to validate pattern signals
Tests across all datasets with comprehensive stats output
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
from scipy.signal import argrelextrema
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Three Mountains & Rivers EMA Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Pattern detection parameters
LOOKBACK_PERIOD = 20
MIN_PATTERN_BARS = 15
MAX_PATTERN_BARS = 60
PEAK_TOLERANCE = 0.02
CONFIRMATION_BARS = 2

# EMA periods
EMA_FAST = 9
EMA_MEDIUM = 21
EMA_SLOW = 50

# Risk management
TAKE_PROFIT_PERCENT = 4.0
STOP_LOSS_PERCENT = 2.0

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class ThreeMountainsRiversEMA(Strategy):
    """
    Three Mountains & Rivers with EMA Strategy
    - Uses triple EMA system for trend confirmation
    - Validates patterns with EMA alignment
    - Improves entry timing with EMA crossovers
    """
    
    # Pattern parameters
    lookback = LOOKBACK_PERIOD
    min_bars = MIN_PATTERN_BARS
    max_bars = MAX_PATTERN_BARS
    peak_tolerance = PEAK_TOLERANCE
    confirmation_bars = CONFIRMATION_BARS
    
    # EMA parameters
    ema_fast = EMA_FAST
    ema_medium = EMA_MEDIUM
    ema_slow = EMA_SLOW
    
    # Risk management
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100
    
    def init(self):
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        volume = pd.Series(self.data.Volume)
        
        # Calculate EMAs
        ema_fast = ta.ema(close, length=self.ema_fast)
        ema_medium = ta.ema(close, length=self.ema_medium)
        ema_slow = ta.ema(close, length=self.ema_slow)
        
        self.ema_fast_line = self.I(lambda: ema_fast.values, name='EMA_Fast')
        self.ema_medium_line = self.I(lambda: ema_medium.values, name='EMA_Medium')
        self.ema_slow_line = self.I(lambda: ema_slow.values, name='EMA_Slow')
        
        # EMA trend strength (distance between EMAs)
        ema_spread = np.zeros(len(close))
        for i in range(len(close)):
            if not np.isnan(ema_fast.iloc[i]) and not np.isnan(ema_slow.iloc[i]):
                ema_spread[i] = (ema_fast.iloc[i] - ema_slow.iloc[i]) / ema_slow.iloc[i]
        
        self.ema_spread = self.I(lambda: ema_spread, name='EMA_Spread')
        
        # EMA alignment signal (1: bullish, -1: bearish, 0: neutral)
        ema_alignment = np.zeros(len(close))
        for i in range(len(close)):
            if (not np.isnan(ema_fast.iloc[i]) and 
                not np.isnan(ema_medium.iloc[i]) and 
                not np.isnan(ema_slow.iloc[i])):
                
                # Bullish alignment: fast > medium > slow
                if ema_fast.iloc[i] > ema_medium.iloc[i] > ema_slow.iloc[i]:
                    ema_alignment[i] = 1
                # Bearish alignment: fast < medium < slow
                elif ema_fast.iloc[i] < ema_medium.iloc[i] < ema_slow.iloc[i]:
                    ema_alignment[i] = -1
        
        self.ema_alignment = self.I(lambda: ema_alignment, name='EMA_Alignment')
        
        # Find peaks and troughs
        peaks = argrelextrema(high.values, np.greater, order=self.lookback)[0]
        troughs = argrelextrema(low.values, np.less, order=self.lookback)[0]
        
        peak_array = np.zeros(len(close))
        trough_array = np.zeros(len(close))
        
        peak_array[peaks] = high.iloc[peaks].values
        trough_array[troughs] = low.iloc[troughs].values
        
        self.peaks = self.I(lambda: peak_array, name='Peaks')
        self.troughs = self.I(lambda: trough_array, name='Troughs')
        
        # Volume average
        volume_sma = ta.sma(volume, length=20)
        self.volume_avg = self.I(lambda: volume_sma.values, name='Volume_Avg')
        
        # Pattern signals with EMA confirmation
        mountains_signal = np.zeros(len(close))
        rivers_signal = np.zeros(len(close))
        
        for i in range(len(close)):
            # Three Mountains detection with EMA confirmation
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
                            
                            # Confirm with bearish EMA alignment or price below EMAs
                            if (close.iloc[i] < peak3 * 0.98 and 
                                (ema_alignment[i] == -1 or 
                                 (close.iloc[i] < ema_medium.iloc[i] and 
                                  close.iloc[i] < ema_slow.iloc[i]))):
                                mountains_signal[i] = -1
            
            # Three Rivers detection with EMA confirmation
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
                            
                            # Confirm with bullish EMA alignment or price above EMAs
                            if (close.iloc[i] > trough3 * 1.02 and 
                                (ema_alignment[i] == 1 or 
                                 (close.iloc[i] > ema_medium.iloc[i] and 
                                  close.iloc[i] > ema_slow.iloc[i]))):
                                rivers_signal[i] = 1
        
        self.mountains_signal = self.I(lambda: mountains_signal, name='Mountains_Signal')
        self.rivers_signal = self.I(lambda: rivers_signal, name='Rivers_Signal')
        
        # EMA crossover signals
        ema_cross_bull = np.zeros(len(close))
        ema_cross_bear = np.zeros(len(close))
        
        for i in range(1, len(close)):
            if (not np.isnan(ema_fast.iloc[i]) and not np.isnan(ema_medium.iloc[i]) and
                not np.isnan(ema_fast.iloc[i-1]) and not np.isnan(ema_medium.iloc[i-1])):
                
                # Bullish crossover
                if ema_fast.iloc[i-1] <= ema_medium.iloc[i-1] and ema_fast.iloc[i] > ema_medium.iloc[i]:
                    ema_cross_bull[i] = 1
                # Bearish crossover
                elif ema_fast.iloc[i-1] >= ema_medium.iloc[i-1] and ema_fast.iloc[i] < ema_medium.iloc[i]:
                    ema_cross_bear[i] = 1
        
        self.ema_cross_bull = self.I(lambda: ema_cross_bull, name='EMA_Cross_Bull')
        self.ema_cross_bear = self.I(lambda: ema_cross_bear, name='EMA_Cross_Bear')
        
        # Pattern state tracking
        self.confirmation_counter = 0
        self.pattern_type = 0
        
    def next(self):
        current_price = self.data.Close[-1]
        current_volume = self.data.Volume[-1]
        
        # Skip if EMAs not ready
        if np.isnan(self.ema_fast_line[-1]) or np.isnan(self.ema_slow_line[-1]):
            return
        
        # Check for new pattern signals
        if self.mountains_signal[-1] == -1:
            self.pattern_type = -1
            self.confirmation_counter = 0
        elif self.rivers_signal[-1] == 1:
            self.pattern_type = 1
            self.confirmation_counter = 0
        
        # Increment confirmation counter
        if self.pattern_type != 0:
            self.confirmation_counter += 1
        
        # EMA trend strength check
        strong_trend = abs(self.ema_spread[-1]) > 0.01  # 1% spread indicates strong trend
        
        # Volume confirmation
        volume_surge = current_volume > self.volume_avg[-1] * 1.2 if self.volume_avg[-1] > 0 else False
        
        if not self.position:
            # Three Rivers - bullish entry with EMA confirmation
            if (self.pattern_type == 1 and 
                self.confirmation_counter >= self.confirmation_bars and
                self.confirmation_counter <= self.confirmation_bars + 5):
                
                # Enter if EMAs aligned bullishly or recent bullish crossover
                if (self.ema_alignment[-1] == 1 or 
                    self.ema_cross_bull[-1] == 1 or
                    (current_price > self.ema_medium_line[-1] and 
                     self.ema_fast_line[-1] > self.ema_medium_line[-1])):
                    
                    sl_price = current_price * (1 - self.stop_loss)
                    
                    # Adjust TP based on trend strength
                    if strong_trend and self.ema_alignment[-1] == 1:
                        tp_price = current_price * (1 + self.take_profit * 1.25)
                    else:
                        tp_price = current_price * (1 + self.take_profit)
                    
                    self.buy(sl=sl_price, tp=tp_price)
                    self.pattern_type = 0
                    self.confirmation_counter = 0
            
            # Three Mountains - bearish entry with EMA confirmation
            elif (self.pattern_type == -1 and 
                  self.confirmation_counter >= self.confirmation_bars and
                  self.confirmation_counter <= self.confirmation_bars + 5):
                
                # Enter if EMAs aligned bearishly or recent bearish crossover
                if (self.ema_alignment[-1] == -1 or 
                    self.ema_cross_bear[-1] == 1 or
                    (current_price < self.ema_medium_line[-1] and 
                     self.ema_fast_line[-1] < self.ema_medium_line[-1])):
                    
                    sl_price = current_price * (1 + self.stop_loss)
                    
                    # Adjust TP based on trend strength
                    if strong_trend and self.ema_alignment[-1] == -1:
                        tp_price = current_price * (1 - self.take_profit * 1.25)
                    else:
                        tp_price = current_price * (1 - self.take_profit)
                    
                    self.sell(sl=sl_price, tp=tp_price)
                    self.pattern_type = 0
                    self.confirmation_counter = 0
        
        # Reset pattern if too old
        if self.confirmation_counter > self.confirmation_bars + 10:
            self.pattern_type = 0
            self.confirmation_counter = 0
        
        # Exit management with EMA signals
        if self.position:
            if self.position.is_long:
                # Exit on bearish pattern, EMA bearish cross, or alignment change
                if (self.mountains_signal[-1] == -1 or 
                    self.ema_cross_bear[-1] == 1 or
                    (self.ema_alignment[-1] == -1 and current_price < self.ema_medium_line[-1])):
                    self.position.close()
                    
            elif self.position.is_short:
                # Exit on bullish pattern, EMA bullish cross, or alignment change
                if (self.rivers_signal[-1] == 1 or 
                    self.ema_cross_bull[-1] == 1 or
                    (self.ema_alignment[-1] == 1 and current_price > self.ema_medium_line[-1])):
                    self.position.close()

# Run single backtest
bt = Backtest(data, ThreeMountainsRiversEMA, cash=100000, commission=0.00045)

print("\n🌙 ===== THREE MOUNTAINS & RIVERS EMA - DEFAULT PARAMETERS ===== 🌙")
print(f"Lookback Period: {LOOKBACK_PERIOD}")
print(f"EMA Periods: {EMA_FAST}/{EMA_MEDIUM}/{EMA_SLOW}")
print(f"Pattern Bar Range: {MIN_PATTERN_BARS}-{MAX_PATTERN_BARS}")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")

stats_default = bt.run()
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING THREE MOUNTAINS & RIVERS EMA ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from backtests.multi_data_tester import test_on_all_data
    
    # Test this strategy on all configured data sources
    results = test_on_all_data(ThreeMountainsRiversEMA, 'ThreeMountainsRiversEMA')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/ThreeMountainsRiversEMA.csv")