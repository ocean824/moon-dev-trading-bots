"""
Moon Dev's Three Mountains & Three Rivers with ADX Strategy
============================================================
Combines pattern recognition with ADX for trend reversal strength
Uses ADX to confirm pattern breakouts and filter weak signals
Tests across all datasets with comprehensive stats output
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
from scipy.signal import argrelextrema
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Three Mountains & Rivers ADX Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Pattern detection parameters
LOOKBACK_PERIOD = 20
MIN_PATTERN_BARS = 15
MAX_PATTERN_BARS = 60
PEAK_TOLERANCE = 0.02
CONFIRMATION_BARS = 2

# ADX parameters
ADX_PERIOD = 14
ADX_TREND_THRESHOLD = 25  # ADX > 25 indicates strong trend
ADX_WEAK_THRESHOLD = 20   # ADX < 20 indicates weak/no trend
DI_THRESHOLD = 5           # Minimum DI difference for direction

# Risk management
TAKE_PROFIT_PERCENT = 4.0
STOP_LOSS_PERCENT = 2.0

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class ThreeMountainsRiversADX(Strategy):
    """
    Three Mountains & Rivers with ADX Strategy
    - Uses ADX to measure trend strength during pattern formation
    - Confirms reversals when ADX indicates weakening trend
    - Filters entries based on directional movement strength
    """
    
    # Pattern parameters
    lookback = LOOKBACK_PERIOD
    min_bars = MIN_PATTERN_BARS
    max_bars = MAX_PATTERN_BARS
    peak_tolerance = PEAK_TOLERANCE
    confirmation_bars = CONFIRMATION_BARS
    
    # ADX parameters
    adx_period = ADX_PERIOD
    adx_trend_threshold = ADX_TREND_THRESHOLD
    adx_weak_threshold = ADX_WEAK_THRESHOLD
    di_threshold = DI_THRESHOLD
    
    # Risk management
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100
    
    def init(self):
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        volume = pd.Series(self.data.Volume)
        
        # Calculate ADX and directional indicators
        adx_result = ta.adx(high, low, close, length=self.adx_period)
        
        # Extract ADX components
        adx_line = adx_result[f'ADX_{self.adx_period}']
        di_plus = adx_result[f'DMP_{self.adx_period}']
        di_minus = adx_result[f'DMN_{self.adx_period}']
        
        # Ensure arrays are same length as data
        adx_full = np.full(len(close), np.nan)
        di_plus_full = np.full(len(close), np.nan)
        di_minus_full = np.full(len(close), np.nan)
        
        adx_full[-len(adx_line):] = adx_line.values
        di_plus_full[-len(di_plus):] = di_plus.values
        di_minus_full[-len(di_minus):] = di_minus.values
        
        self.adx = self.I(lambda: adx_full, name='ADX')
        self.di_plus = self.I(lambda: di_plus_full, name='DI_Plus')
        self.di_minus = self.I(lambda: di_minus_full, name='DI_Minus')
        
        # Calculate DI difference for trend direction
        di_diff = di_plus_full - di_minus_full
        self.di_diff = self.I(lambda: di_diff, name='DI_Diff')
        
        # ADX trend strength classification
        adx_strength = np.zeros(len(close))
        for i in range(len(close)):
            if not np.isnan(adx_full[i]):
                if adx_full[i] > self.adx_trend_threshold:
                    adx_strength[i] = 2  # Strong trend
                elif adx_full[i] > self.adx_weak_threshold:
                    adx_strength[i] = 1  # Moderate trend
                else:
                    adx_strength[i] = 0  # Weak/no trend
        
        self.adx_strength = self.I(lambda: adx_strength, name='ADX_Strength')
        
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
        
        # Pattern signals with ADX confirmation
        mountains_signal = np.zeros(len(close))
        rivers_signal = np.zeros(len(close))
        
        for i in range(len(close)):
            # Three Mountains detection with ADX
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
                            
                            # Check ADX conditions for reversal
                            # Look for weakening trend (ADX declining) or exhaustion
                            adx_current = adx_full[i] if not np.isnan(adx_full[i]) else 0
                            adx_prev = adx_full[i-5] if i >= 5 and not np.isnan(adx_full[i-5]) else 0
                            
                            # Pattern confirmed if:
                            # 1. Price broke below peaks
                            # 2. ADX is declining (trend weakening) OR ADX is low (consolidation)
                            # 3. DI- is starting to dominate
                            if (close.iloc[i] < peak3 * 0.98 and 
                                (adx_current < adx_prev or adx_current < self.adx_trend_threshold) and
                                di_diff[i] < self.di_threshold):
                                mountains_signal[i] = -1
            
            # Three Rivers detection with ADX
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
                            
                            # Check ADX conditions for reversal
                            adx_current = adx_full[i] if not np.isnan(adx_full[i]) else 0
                            adx_prev = adx_full[i-5] if i >= 5 and not np.isnan(adx_full[i-5]) else 0
                            
                            # Pattern confirmed if:
                            # 1. Price broke above troughs
                            # 2. ADX is declining (trend weakening) OR ADX is low (consolidation)
                            # 3. DI+ is starting to dominate
                            if (close.iloc[i] > trough3 * 1.02 and 
                                (adx_current < adx_prev or adx_current < self.adx_trend_threshold) and
                                di_diff[i] > -self.di_threshold):
                                rivers_signal[i] = 1
        
        self.mountains_signal = self.I(lambda: mountains_signal, name='Mountains_Signal')
        self.rivers_signal = self.I(lambda: rivers_signal, name='Rivers_Signal')
        
        # ADX reversal detection (ADX turning up from low levels)
        adx_reversal = np.zeros(len(close))
        for i in range(1, len(close)):
            if not np.isnan(adx_full[i]) and not np.isnan(adx_full[i-1]):
                # ADX starting to rise from weak levels
                if adx_full[i] > adx_full[i-1] and adx_full[i-1] < self.adx_weak_threshold:
                    adx_reversal[i] = 1
        
        self.adx_reversal = self.I(lambda: adx_reversal, name='ADX_Reversal')
        
        # Pattern state tracking
        self.confirmation_counter = 0
        self.pattern_type = 0
        
    def next(self):
        # Skip if indicators not ready
        if np.isnan(self.adx[-1]) or np.isnan(self.di_plus[-1]) or np.isnan(self.di_minus[-1]):
            return
        
        current_price = self.data.Close[-1]
        current_volume = self.data.Volume[-1]
        
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
        
        # ADX and DI conditions
        adx_weak = self.adx[-1] < self.adx_weak_threshold
        adx_moderate = self.adx_weak_threshold <= self.adx[-1] < self.adx_trend_threshold
        adx_strong = self.adx[-1] >= self.adx_trend_threshold
        
        di_bullish = self.di_plus[-1] > self.di_minus[-1] + self.di_threshold
        di_bearish = self.di_minus[-1] > self.di_plus[-1] + self.di_threshold
        
        # Volume confirmation
        volume_surge = current_volume > self.volume_avg[-1] * 1.2 if self.volume_avg[-1] > 0 else False
        
        if not self.position:
            # Three Rivers - bullish entry with ADX confirmation
            if (self.pattern_type == 1 and 
                self.confirmation_counter >= self.confirmation_bars and
                self.confirmation_counter <= self.confirmation_bars + 5):
                
                # Enter if:
                # 1. DI+ is rising or crossing above DI-
                # 2. ADX is either weak (reversal from consolidation) or starting to rise
                # 3. Optional: ADX reversal signal
                if (di_bullish or self.di_diff[-1] > self.di_diff[-2]) and \
                   (adx_weak or self.adx[-1] > self.adx[-2] or self.adx_reversal[-1] == 1):
                    
                    sl_price = current_price * (1 - self.stop_loss)
                    
                    # Adjust TP based on ADX strength
                    if adx_strong and di_bullish:
                        tp_price = current_price * (1 + self.take_profit * 1.5)  # Strong trend = bigger target
                    elif adx_moderate:
                        tp_price = current_price * (1 + self.take_profit * 1.25)
                    else:
                        tp_price = current_price * (1 + self.take_profit)
                    
                    self.buy(sl=sl_price, tp=tp_price)
                    self.pattern_type = 0
                    self.confirmation_counter = 0
            
            # Three Mountains - bearish entry with ADX confirmation
            elif (self.pattern_type == -1 and 
                  self.confirmation_counter >= self.confirmation_bars and
                  self.confirmation_counter <= self.confirmation_bars + 5):
                
                # Enter if:
                # 1. DI- is rising or crossing above DI+
                # 2. ADX is either weak (reversal from consolidation) or starting to rise
                # 3. Optional: ADX reversal signal
                if (di_bearish or self.di_diff[-1] < self.di_diff[-2]) and \
                   (adx_weak or self.adx[-1] > self.adx[-2] or self.adx_reversal[-1] == 1):
                    
                    sl_price = current_price * (1 + self.stop_loss)
                    
                    # Adjust TP based on ADX strength
                    if adx_strong and di_bearish:
                        tp_price = current_price * (1 - self.take_profit * 1.5)  # Strong trend = bigger target
                    elif adx_moderate:
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
        
        # Exit management with ADX
        if self.position:
            if self.position.is_long:
                # Exit on bearish pattern or DI reversal with ADX confirmation
                if (self.mountains_signal[-1] == -1 or 
                    (di_bearish and self.adx[-1] > self.adx_weak_threshold)):
                    self.position.close()
                # Exit if trend exhaustion (ADX very high and turning down)
                elif self.adx[-1] > 40 and self.adx[-1] < self.adx[-2]:
                    self.position.close()
                    
            elif self.position.is_short:
                # Exit on bullish pattern or DI reversal with ADX confirmation
                if (self.rivers_signal[-1] == 1 or 
                    (di_bullish and self.adx[-1] > self.adx_weak_threshold)):
                    self.position.close()
                # Exit if trend exhaustion (ADX very high and turning down)
                elif self.adx[-1] > 40 and self.adx[-1] < self.adx[-2]:
                    self.position.close()

# Run single backtest
bt = Backtest(data, ThreeMountainsRiversADX, cash=100000, commission=0.00045)

print("\n🌙 ===== THREE MOUNTAINS & RIVERS ADX - DEFAULT PARAMETERS ===== 🌙")
print(f"Lookback Period: {LOOKBACK_PERIOD}")
print(f"ADX Period: {ADX_PERIOD}")
print(f"ADX Thresholds: Weak<{ADX_WEAK_THRESHOLD}, Strong>{ADX_TREND_THRESHOLD}")
print(f"Pattern Bar Range: {MIN_PATTERN_BARS}-{MAX_PATTERN_BARS}")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")

stats_default = bt.run()
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING THREE MOUNTAINS & RIVERS ADX ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from backtests.multi_data_tester import test_on_all_data
    
    # Test this strategy on all configured data sources
    results = test_on_all_data(ThreeMountainsRiversADX, 'ThreeMountainsRiversADX')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/ThreeMountainsRiversADX.csv")