"""
Moon Dev's Three Mountains & Three Rivers with Bollinger Bands Strategy
========================================================================
Combines pattern recognition with Bollinger Bands for extreme detection
Uses band extremes and squeezes to confirm pattern breakouts
Tests across all datasets with comprehensive stats output
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
from scipy.signal import argrelextrema
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Three Mountains & Rivers Bollinger Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Pattern detection parameters
LOOKBACK_PERIOD = 20
MIN_PATTERN_BARS = 15
MAX_PATTERN_BARS = 60
PEAK_TOLERANCE = 0.02
CONFIRMATION_BARS = 2

# Bollinger Bands parameters
BB_PERIOD = 20
BB_STD = 2.0
BB_SQUEEZE_THRESHOLD = 0.01  # Minimum band width for squeeze detection

# Risk management
TAKE_PROFIT_PERCENT = 4.0
STOP_LOSS_PERCENT = 2.0

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class ThreeMountainsRiversBollinger(Strategy):
    """
    Three Mountains & Rivers with Bollinger Bands Strategy
    - Uses Bollinger Bands to identify pattern extremes
    - Confirms patterns when peaks/troughs align with band extremes
    - Utilizes band squeeze for breakout timing
    """
    
    # Pattern parameters
    lookback = LOOKBACK_PERIOD
    min_bars = MIN_PATTERN_BARS
    max_bars = MAX_PATTERN_BARS
    peak_tolerance = PEAK_TOLERANCE
    confirmation_bars = CONFIRMATION_BARS
    
    # Bollinger parameters
    bb_period = BB_PERIOD
    bb_std = BB_STD
    bb_squeeze_threshold = BB_SQUEEZE_THRESHOLD
    
    # Risk management
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100
    
    def init(self):
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        volume = pd.Series(self.data.Volume)
        
        # Calculate Bollinger Bands
        bb_result = ta.bbands(close, length=self.bb_period, std=self.bb_std)
        
        # Extract BB components
        bb_upper = bb_result[f'BBU_{self.bb_period}_{self.bb_std}']
        bb_middle = bb_result[f'BBM_{self.bb_period}_{self.bb_std}']
        bb_lower = bb_result[f'BBL_{self.bb_period}_{self.bb_std}']
        bb_bandwidth = bb_result[f'BBB_{self.bb_period}_{self.bb_std}']
        bb_percent = bb_result[f'BBP_{self.bb_period}_{self.bb_std}']
        
        # Ensure arrays are same length as data
        bb_upper_full = np.full(len(close), np.nan)
        bb_middle_full = np.full(len(close), np.nan)
        bb_lower_full = np.full(len(close), np.nan)
        bb_bandwidth_full = np.full(len(close), np.nan)
        bb_percent_full = np.full(len(close), np.nan)
        
        bb_upper_full[-len(bb_upper):] = bb_upper.values
        bb_middle_full[-len(bb_middle):] = bb_middle.values
        bb_lower_full[-len(bb_lower):] = bb_lower.values
        bb_bandwidth_full[-len(bb_bandwidth):] = bb_bandwidth.values
        bb_percent_full[-len(bb_percent):] = bb_percent.values
        
        self.bb_upper = self.I(lambda: bb_upper_full, name='BB_Upper')
        self.bb_middle = self.I(lambda: bb_middle_full, name='BB_Middle')
        self.bb_lower = self.I(lambda: bb_lower_full, name='BB_Lower')
        self.bb_bandwidth = self.I(lambda: bb_bandwidth_full, name='BB_Bandwidth')
        self.bb_percent = self.I(lambda: bb_percent_full, name='BB_Percent')
        
        # Detect Bollinger Band squeeze (low volatility)
        bb_squeeze = np.zeros(len(close))
        for i in range(len(close)):
            if not np.isnan(bb_bandwidth_full[i]):
                # Squeeze when bandwidth is below threshold
                if bb_bandwidth_full[i] < self.bb_squeeze_threshold:
                    bb_squeeze[i] = 1
        
        self.bb_squeeze = self.I(lambda: bb_squeeze, name='BB_Squeeze')
        
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
        
        # Pattern signals with Bollinger confirmation
        mountains_signal = np.zeros(len(close))
        rivers_signal = np.zeros(len(close))
        
        for i in range(len(close)):
            # Three Mountains detection with Bollinger
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
                            
                            # Check if peaks touched or exceeded upper band
                            peak_at_upper = False
                            for peak_idx in [idx1, idx2, idx3]:
                                if not np.isnan(bb_upper_full[peak_idx]):
                                    if high.iloc[peak_idx] >= bb_upper_full[peak_idx] * 0.98:
                                        peak_at_upper = True
                                        break
                            
                            # Check current position relative to bands
                            below_middle = close.iloc[i] < bb_middle_full[i] if not np.isnan(bb_middle_full[i]) else False
                            
                            # Pattern confirmed if:
                            # 1. At least one peak touched upper band (overextension)
                            # 2. Price broke below peaks and middle band
                            # 3. Optional: squeeze released (volatility expanding)
                            if (peak_at_upper and below_middle and 
                                close.iloc[i] < peak3 * 0.98):
                                mountains_signal[i] = -1
            
            # Three Rivers detection with Bollinger
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
                            
                            # Check if troughs touched or breached lower band
                            trough_at_lower = False
                            for trough_idx in [idx1, idx2, idx3]:
                                if not np.isnan(bb_lower_full[trough_idx]):
                                    if low.iloc[trough_idx] <= bb_lower_full[trough_idx] * 1.02:
                                        trough_at_lower = True
                                        break
                            
                            # Check current position relative to bands
                            above_middle = close.iloc[i] > bb_middle_full[i] if not np.isnan(bb_middle_full[i]) else False
                            
                            # Pattern confirmed if:
                            # 1. At least one trough touched lower band (overextension)
                            # 2. Price broke above troughs and middle band
                            # 3. Optional: squeeze released (volatility expanding)
                            if (trough_at_lower and above_middle and 
                                close.iloc[i] > trough3 * 1.02):
                                rivers_signal[i] = 1
        
        self.mountains_signal = self.I(lambda: mountains_signal, name='Mountains_Signal')
        self.rivers_signal = self.I(lambda: rivers_signal, name='Rivers_Signal')
        
        # Band position indicator
        band_position = np.zeros(len(close))
        for i in range(len(close)):
            if not np.isnan(bb_percent_full[i]):
                if bb_percent_full[i] > 1.0:
                    band_position[i] = 2  # Above upper band
                elif bb_percent_full[i] > 0.5:
                    band_position[i] = 1  # Upper half
                elif bb_percent_full[i] > 0:
                    band_position[i] = -1  # Lower half
                else:
                    band_position[i] = -2  # Below lower band
        
        self.band_position = self.I(lambda: band_position, name='Band_Position')
        
        # Pattern state tracking
        self.confirmation_counter = 0
        self.pattern_type = 0
        self.squeeze_released = False
        
    def next(self):
        # Skip if indicators not ready
        if np.isnan(self.bb_upper[-1]) or np.isnan(self.bb_lower[-1]):
            return
        
        current_price = self.data.Close[-1]
        current_volume = self.data.Volume[-1]
        
        # Check for new pattern signals
        if self.mountains_signal[-1] == -1:
            self.pattern_type = -1
            self.confirmation_counter = 0
            # Check if coming out of squeeze
            self.squeeze_released = self.bb_squeeze[-2] == 1 and self.bb_squeeze[-1] == 0
        elif self.rivers_signal[-1] == 1:
            self.pattern_type = 1
            self.confirmation_counter = 0
            # Check if coming out of squeeze
            self.squeeze_released = self.bb_squeeze[-2] == 1 and self.bb_squeeze[-1] == 0
        
        # Increment confirmation counter
        if self.pattern_type != 0:
            self.confirmation_counter += 1
        
        # Bollinger Band conditions
        at_upper = current_price >= self.bb_upper[-1] * 0.98
        at_lower = current_price <= self.bb_lower[-1] * 1.02
        above_middle = current_price > self.bb_middle[-1]
        below_middle = current_price < self.bb_middle[-1]
        
        # Band width expanding (volatility increasing)
        band_expanding = self.bb_bandwidth[-1] > self.bb_bandwidth[-2] if self.bb_bandwidth[-2] > 0 else False
        
        # Volume confirmation
        volume_surge = current_volume > self.volume_avg[-1] * 1.2 if self.volume_avg[-1] > 0 else False
        
        if not self.position:
            # Three Rivers - bullish entry with Bollinger confirmation
            if (self.pattern_type == 1 and 
                self.confirmation_counter >= self.confirmation_bars and
                self.confirmation_counter <= self.confirmation_bars + 5):
                
                # Enter if:
                # 1. Price crossed above middle band
                # 2. Coming from lower band extreme
                # 3. Band width expanding (breakout) or squeeze released
                if (above_middle and 
                    (self.band_position[-2] <= -1 or at_lower) and
                    (band_expanding or self.squeeze_released)):
                    
                    sl_price = current_price * (1 - self.stop_loss)
                    
                    # Adjust TP based on band position and volatility
                    if self.squeeze_released and volume_surge:
                        tp_price = current_price * (1 + self.take_profit * 1.5)  # Squeeze breakout
                    elif at_lower:
                        tp_price = self.bb_upper[-1]  # Target upper band
                    else:
                        tp_price = current_price * (1 + self.take_profit)
                    
                    self.buy(sl=sl_price, tp=tp_price)
                    self.pattern_type = 0
                    self.confirmation_counter = 0
                    self.squeeze_released = False
            
            # Three Mountains - bearish entry with Bollinger confirmation
            elif (self.pattern_type == -1 and 
                  self.confirmation_counter >= self.confirmation_bars and
                  self.confirmation_counter <= self.confirmation_bars + 5):
                
                # Enter if:
                # 1. Price crossed below middle band
                # 2. Coming from upper band extreme
                # 3. Band width expanding (breakout) or squeeze released
                if (below_middle and 
                    (self.band_position[-2] >= 1 or at_upper) and
                    (band_expanding or self.squeeze_released)):
                    
                    sl_price = current_price * (1 + self.stop_loss)
                    
                    # Adjust TP based on band position and volatility
                    if self.squeeze_released and volume_surge:
                        tp_price = current_price * (1 - self.take_profit * 1.5)  # Squeeze breakout
                    elif at_upper:
                        tp_price = self.bb_lower[-1]  # Target lower band
                    else:
                        tp_price = current_price * (1 - self.take_profit)
                    
                    self.sell(sl=sl_price, tp=tp_price)
                    self.pattern_type = 0
                    self.confirmation_counter = 0
                    self.squeeze_released = False
        
        # Reset pattern if too old
        if self.confirmation_counter > self.confirmation_bars + 10:
            self.pattern_type = 0
            self.confirmation_counter = 0
            self.squeeze_released = False
        
        # Exit management with Bollinger Bands
        if self.position:
            if self.position.is_long:
                # Exit on bearish pattern or hitting upper band
                if self.mountains_signal[-1] == -1 or at_upper:
                    self.position.close()
                # Exit if price falls back below middle band after entry
                elif below_middle and self.data.Close[-2] > self.bb_middle[-2]:
                    self.position.close()
                # Exit if band squeeze detected (volatility contraction)
                elif self.bb_squeeze[-1] == 1 and self.bb_squeeze[-2] == 0:
                    self.position.close()
                    
            elif self.position.is_short:
                # Exit on bullish pattern or hitting lower band
                if self.rivers_signal[-1] == 1 or at_lower:
                    self.position.close()
                # Exit if price rises back above middle band after entry
                elif above_middle and self.data.Close[-2] < self.bb_middle[-2]:
                    self.position.close()
                # Exit if band squeeze detected (volatility contraction)
                elif self.bb_squeeze[-1] == 1 and self.bb_squeeze[-2] == 0:
                    self.position.close()

# Run single backtest
bt = Backtest(data, ThreeMountainsRiversBollinger, cash=100000, commission=0.00045)

print("\n🌙 ===== THREE MOUNTAINS & RIVERS BOLLINGER - DEFAULT PARAMETERS ===== 🌙")
print(f"Lookback Period: {LOOKBACK_PERIOD}")
print(f"Bollinger Period: {BB_PERIOD}, Std Dev: {BB_STD}")
print(f"Squeeze Threshold: {BB_SQUEEZE_THRESHOLD}")
print(f"Pattern Bar Range: {MIN_PATTERN_BARS}-{MAX_PATTERN_BARS}")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")

stats_default = bt.run()
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING THREE MOUNTAINS & RIVERS BOLLINGER ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from backtests.multi_data_tester import test_on_all_data
    
    # Test this strategy on all configured data sources
    results = test_on_all_data(ThreeMountainsRiversBollinger, 'ThreeMountainsRiversBollinger')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/ThreeMountainsRiversBollinger.csv")