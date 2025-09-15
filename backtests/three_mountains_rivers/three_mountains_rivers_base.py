"""
Moon Dev's Three Mountains & Three Rivers Base Strategy
========================================================
Implements the San Zan (Three Mountains) bearish pattern and San Sen (Three Rivers) bullish pattern
Uses peak/trough detection to identify triple tops and triple bottoms
Tests across all datasets with comprehensive stats output
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
from scipy.signal import argrelextrema
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Three Mountains & Rivers Base Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Pattern detection parameters
LOOKBACK_PERIOD = 20  # Period to look for peaks/troughs
MIN_PATTERN_BARS = 15  # Minimum bars between peaks/troughs
MAX_PATTERN_BARS = 60  # Maximum bars for pattern to be valid
PEAK_TOLERANCE = 0.02  # 2% tolerance for peak similarity
CONFIRMATION_BARS = 2  # Bars to wait for pattern confirmation

# Risk management
TAKE_PROFIT_PERCENT = 4.0
STOP_LOSS_PERCENT = 2.0

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class ThreeMountainsRiversBase(Strategy):
    """
    Three Mountains & Three Rivers Pattern Strategy
    - Three Mountains (San Zan): Triple top bearish pattern indicating trend reversal
    - Three Rivers (San Sen): Triple bottom bullish pattern indicating trend reversal
    - Uses local peak/trough detection to identify patterns
    - Confirms patterns with volume and price action
    """
    
    # Pattern parameters
    lookback = LOOKBACK_PERIOD
    min_bars = MIN_PATTERN_BARS
    max_bars = MAX_PATTERN_BARS
    peak_tolerance = PEAK_TOLERANCE
    confirmation_bars = CONFIRMATION_BARS
    
    # Risk management
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100
    
    def init(self):
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        volume = pd.Series(self.data.Volume)
        
        # Find local peaks (potential mountains)
        peaks = argrelextrema(high.values, np.greater, order=self.lookback)[0]
        
        # Find local troughs (potential rivers)
        troughs = argrelextrema(low.values, np.less, order=self.lookback)[0]
        
        # Create arrays to track peaks and troughs
        peak_array = np.zeros(len(close))
        trough_array = np.zeros(len(close))
        
        peak_array[peaks] = high.iloc[peaks].values
        trough_array[troughs] = low.iloc[troughs].values
        
        self.peaks = self.I(lambda: peak_array, name='Peaks')
        self.troughs = self.I(lambda: trough_array, name='Troughs')
        
        # Calculate average volume for volume confirmation
        volume_sma = ta.sma(volume, length=20)
        self.volume_avg = self.I(lambda: volume_sma.values, name='Volume_Avg')
        
        # Track pattern signals
        self.three_mountains = self.I(lambda: np.zeros(len(close)), name='Three_Mountains')
        self.three_rivers = self.I(lambda: np.zeros(len(close)), name='Three_Rivers')
        
        # Calculate pattern signals
        mountains_signal = np.zeros(len(close))
        rivers_signal = np.zeros(len(close))
        
        for i in range(len(close)):
            # Check for Three Mountains pattern
            if i >= self.max_bars * 3:
                recent_peaks = []
                for j in range(i - self.max_bars * 3, i):
                    if peak_array[j] > 0:
                        recent_peaks.append((j, peak_array[j]))
                
                if len(recent_peaks) >= 3:
                    # Get the last three peaks
                    last_three = recent_peaks[-3:]
                    idx1, peak1 = last_three[0]
                    idx2, peak2 = last_three[1]
                    idx3, peak3 = last_three[2]
                    
                    # Check if peaks are within tolerance (similar height)
                    avg_peak = (peak1 + peak2 + peak3) / 3
                    if (abs(peak1 - avg_peak) / avg_peak <= self.peak_tolerance and
                        abs(peak2 - avg_peak) / avg_peak <= self.peak_tolerance and
                        abs(peak3 - avg_peak) / avg_peak <= self.peak_tolerance):
                        
                        # Check spacing between peaks
                        if (self.min_bars <= idx2 - idx1 <= self.max_bars and
                            self.min_bars <= idx3 - idx2 <= self.max_bars):
                            
                            # Confirm with price below third peak
                            if close.iloc[i] < peak3 * 0.98:
                                mountains_signal[i] = -1  # Bearish signal
            
            # Check for Three Rivers pattern
            if i >= self.max_bars * 3:
                recent_troughs = []
                for j in range(i - self.max_bars * 3, i):
                    if trough_array[j] > 0:
                        recent_troughs.append((j, trough_array[j]))
                
                if len(recent_troughs) >= 3:
                    # Get the last three troughs
                    last_three = recent_troughs[-3:]
                    idx1, trough1 = last_three[0]
                    idx2, trough2 = last_three[1]
                    idx3, trough3 = last_three[2]
                    
                    # Check if troughs are within tolerance (similar depth)
                    avg_trough = (trough1 + trough2 + trough3) / 3
                    if (abs(trough1 - avg_trough) / avg_trough <= self.peak_tolerance and
                        abs(trough2 - avg_trough) / avg_trough <= self.peak_tolerance and
                        abs(trough3 - avg_trough) / avg_trough <= self.peak_tolerance):
                        
                        # Check spacing between troughs
                        if (self.min_bars <= idx2 - idx1 <= self.max_bars and
                            self.min_bars <= idx3 - idx2 <= self.max_bars):
                            
                            # Confirm with price above third trough
                            if close.iloc[i] > trough3 * 1.02:
                                rivers_signal[i] = 1  # Bullish signal
        
        self.mountains_signal = self.I(lambda: mountains_signal, name='Mountains_Signal')
        self.rivers_signal = self.I(lambda: rivers_signal, name='Rivers_Signal')
        
        # Pattern confirmation counter
        self.confirmation_counter = 0
        self.pattern_type = 0  # 0: none, 1: rivers, -1: mountains
        
    def next(self):
        current_price = self.data.Close[-1]
        current_volume = self.data.Volume[-1]
        
        # Check for new pattern signals
        if self.mountains_signal[-1] == -1:
            self.pattern_type = -1
            self.confirmation_counter = 0
        elif self.rivers_signal[-1] == 1:
            self.pattern_type = 1
            self.confirmation_counter = 0
        
        # Increment confirmation counter if pattern active
        if self.pattern_type != 0:
            self.confirmation_counter += 1
        
        # Volume confirmation
        volume_surge = current_volume > self.volume_avg[-1] * 1.2 if self.volume_avg[-1] > 0 else False
        
        if not self.position:
            # Three Rivers pattern - bullish entry
            if (self.pattern_type == 1 and 
                self.confirmation_counter >= self.confirmation_bars and
                self.confirmation_counter <= self.confirmation_bars + 5):
                
                # Additional confirmation: price should be trending up
                if current_price > self.data.Close[-2]:
                    sl_price = current_price * (1 - self.stop_loss)
                    tp_price = current_price * (1 + self.take_profit)
                    self.buy(sl=sl_price, tp=tp_price)
                    self.pattern_type = 0  # Reset pattern
                    self.confirmation_counter = 0
            
            # Three Mountains pattern - bearish entry
            elif (self.pattern_type == -1 and 
                  self.confirmation_counter >= self.confirmation_bars and
                  self.confirmation_counter <= self.confirmation_bars + 5):
                
                # Additional confirmation: price should be trending down
                if current_price < self.data.Close[-2]:
                    sl_price = current_price * (1 + self.stop_loss)
                    tp_price = current_price * (1 - self.take_profit)
                    self.sell(sl=sl_price, tp=tp_price)
                    self.pattern_type = 0  # Reset pattern
                    self.confirmation_counter = 0
        
        # Reset pattern if too much time has passed
        if self.confirmation_counter > self.confirmation_bars + 10:
            self.pattern_type = 0
            self.confirmation_counter = 0
        
        # Exit on opposite pattern signal
        if self.position:
            if self.position.is_long and self.mountains_signal[-1] == -1:
                self.position.close()
            elif self.position.is_short and self.rivers_signal[-1] == 1:
                self.position.close()

# Run single backtest
bt = Backtest(data, ThreeMountainsRiversBase, cash=100000, commission=0.00045)

print("\n🌙 ===== THREE MOUNTAINS & RIVERS BASE - DEFAULT PARAMETERS ===== 🌙")
print(f"Lookback Period: {LOOKBACK_PERIOD}")
print(f"Pattern Bar Range: {MIN_PATTERN_BARS}-{MAX_PATTERN_BARS}")
print(f"Peak Tolerance: {PEAK_TOLERANCE * 100}%")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")

stats_default = bt.run()
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING THREE MOUNTAINS & RIVERS BASE ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from backtests.multi_data_tester import test_on_all_data
    
    # Test this strategy on all configured data sources
    results = test_on_all_data(ThreeMountainsRiversBase, 'ThreeMountainsRiversBase')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/ThreeMountainsRiversBase.csv")