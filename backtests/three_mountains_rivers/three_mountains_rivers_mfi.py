"""
Moon Dev's Three Mountains & Three Rivers with MFI Strategy
============================================================
Combines pattern recognition with Money Flow Index for volume confirmation
Uses MFI divergences and extremes to validate pattern signals
Tests across all datasets with comprehensive stats output
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
from scipy.signal import argrelextrema
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Three Mountains & Rivers MFI Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Pattern detection parameters
LOOKBACK_PERIOD = 20
MIN_PATTERN_BARS = 15
MAX_PATTERN_BARS = 60
PEAK_TOLERANCE = 0.02
CONFIRMATION_BARS = 2

# MFI parameters
MFI_PERIOD = 14
MFI_OVERSOLD = 20
MFI_OVERBOUGHT = 80
MFI_DIVERGENCE_THRESHOLD = 10  # Minimum MFI difference for divergence

# Risk management
TAKE_PROFIT_PERCENT = 4.0
STOP_LOSS_PERCENT = 2.0

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class ThreeMountainsRiversMFI(Strategy):
    """
    Three Mountains & Rivers with MFI Strategy
    - Uses Money Flow Index to confirm pattern with volume analysis
    - Identifies divergences between price patterns and money flow
    - Filters entries based on MFI extremes and crossovers
    """
    
    # Pattern parameters
    lookback = LOOKBACK_PERIOD
    min_bars = MIN_PATTERN_BARS
    max_bars = MAX_PATTERN_BARS
    peak_tolerance = PEAK_TOLERANCE
    confirmation_bars = CONFIRMATION_BARS
    
    # MFI parameters
    mfi_period = MFI_PERIOD
    mfi_oversold = MFI_OVERSOLD
    mfi_overbought = MFI_OVERBOUGHT
    mfi_divergence_threshold = MFI_DIVERGENCE_THRESHOLD
    
    # Risk management
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100
    
    def init(self):
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        volume = pd.Series(self.data.Volume)
        
        # Calculate MFI
        mfi = ta.mfi(high, low, close, volume, length=self.mfi_period)
        
        # Ensure MFI array is same length as data
        mfi_full = np.full(len(close), np.nan)
        mfi_full[-len(mfi):] = mfi.values
        
        self.mfi = self.I(lambda: mfi_full, name='MFI')
        
        # MFI zones (oversold, neutral, overbought)
        mfi_zone = np.zeros(len(close))
        for i in range(len(close)):
            if not np.isnan(mfi_full[i]):
                if mfi_full[i] <= self.mfi_oversold:
                    mfi_zone[i] = -1  # Oversold
                elif mfi_full[i] >= self.mfi_overbought:
                    mfi_zone[i] = 1   # Overbought
                else:
                    mfi_zone[i] = 0   # Neutral
        
        self.mfi_zone = self.I(lambda: mfi_zone, name='MFI_Zone')
        
        # Find peaks and troughs
        peaks = argrelextrema(high.values, np.greater, order=self.lookback)[0]
        troughs = argrelextrema(low.values, np.less, order=self.lookback)[0]
        
        peak_array = np.zeros(len(close))
        trough_array = np.zeros(len(close))
        
        peak_array[peaks] = high.iloc[peaks].values
        trough_array[troughs] = low.iloc[troughs].values
        
        self.peaks = self.I(lambda: peak_array, name='Peaks')
        self.troughs = self.I(lambda: trough_array, name='Troughs')
        
        # Volume average for additional confirmation
        volume_sma = ta.sma(volume, length=20)
        self.volume_avg = self.I(lambda: volume_sma.values, name='Volume_Avg')
        
        # Detect MFI divergences
        mfi_bull_div = np.zeros(len(close))
        mfi_bear_div = np.zeros(len(close))
        
        # Find MFI peaks and troughs for divergence analysis
        if len(mfi) > self.lookback * 2:
            mfi_peaks = argrelextrema(mfi.values, np.greater, order=self.lookback//2)[0]
            mfi_troughs = argrelextrema(mfi.values, np.less, order=self.lookback//2)[0]
            
            # Map MFI peaks/troughs to full array indices
            mfi_peaks_full = [i + (len(close) - len(mfi)) for i in mfi_peaks]
            mfi_troughs_full = [i + (len(close) - len(mfi)) for i in mfi_troughs]
        else:
            mfi_peaks_full = []
            mfi_troughs_full = []
        
        # Pattern signals with MFI confirmation
        mountains_signal = np.zeros(len(close))
        rivers_signal = np.zeros(len(close))
        
        for i in range(len(close)):
            # Three Mountains detection with MFI
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
                            
                            # Check MFI conditions
                            mfi_current = mfi_full[i] if not np.isnan(mfi_full[i]) else 50
                            mfi_at_peak1 = mfi_full[idx1] if not np.isnan(mfi_full[idx1]) else 50
                            mfi_at_peak3 = mfi_full[idx3] if not np.isnan(mfi_full[idx3]) else 50
                            
                            # Bearish divergence: higher price peaks but lower MFI
                            bearish_divergence = (peak3 >= peak1 and 
                                                 mfi_at_peak3 < mfi_at_peak1 - self.mfi_divergence_threshold)
                            
                            # Pattern confirmed if:
                            # 1. Price broke below peaks
                            # 2. MFI showing bearish divergence OR MFI is overbought
                            # 3. MFI is declining
                            if (close.iloc[i] < peak3 * 0.98 and 
                                (bearish_divergence or mfi_current > self.mfi_overbought * 0.9) and
                                mfi_current < mfi_at_peak3):
                                mountains_signal[i] = -1
            
            # Three Rivers detection with MFI
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
                            
                            # Check MFI conditions
                            mfi_current = mfi_full[i] if not np.isnan(mfi_full[i]) else 50
                            mfi_at_trough1 = mfi_full[idx1] if not np.isnan(mfi_full[idx1]) else 50
                            mfi_at_trough3 = mfi_full[idx3] if not np.isnan(mfi_full[idx3]) else 50
                            
                            # Bullish divergence: lower price troughs but higher MFI
                            bullish_divergence = (trough3 <= trough1 and 
                                                mfi_at_trough3 > mfi_at_trough1 + self.mfi_divergence_threshold)
                            
                            # Pattern confirmed if:
                            # 1. Price broke above troughs
                            # 2. MFI showing bullish divergence OR MFI is oversold
                            # 3. MFI is rising
                            if (close.iloc[i] > trough3 * 1.02 and 
                                (bullish_divergence or mfi_current < self.mfi_oversold * 1.1) and
                                mfi_current > mfi_at_trough3):
                                rivers_signal[i] = 1
        
        self.mountains_signal = self.I(lambda: mountains_signal, name='Mountains_Signal')
        self.rivers_signal = self.I(lambda: rivers_signal, name='Rivers_Signal')
        
        # MFI momentum (rate of change)
        mfi_momentum = np.zeros(len(close))
        for i in range(5, len(close)):
            if not np.isnan(mfi_full[i]) and not np.isnan(mfi_full[i-5]):
                mfi_momentum[i] = mfi_full[i] - mfi_full[i-5]
        
        self.mfi_momentum = self.I(lambda: mfi_momentum, name='MFI_Momentum')
        
        # Pattern state tracking
        self.confirmation_counter = 0
        self.pattern_type = 0
        
    def next(self):
        # Skip if MFI not ready
        if np.isnan(self.mfi[-1]):
            return
        
        current_price = self.data.Close[-1]
        current_volume = self.data.Volume[-1]
        current_mfi = self.mfi[-1]
        
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
        
        # MFI conditions
        mfi_oversold = current_mfi <= self.mfi_oversold
        mfi_overbought = current_mfi >= self.mfi_overbought
        mfi_rising = self.mfi_momentum[-1] > 0
        mfi_falling = self.mfi_momentum[-1] < 0
        
        # Volume confirmation
        volume_surge = current_volume > self.volume_avg[-1] * 1.2 if self.volume_avg[-1] > 0 else False
        
        if not self.position:
            # Three Rivers - bullish entry with MFI confirmation
            if (self.pattern_type == 1 and 
                self.confirmation_counter >= self.confirmation_bars and
                self.confirmation_counter <= self.confirmation_bars + 5):
                
                # Enter if:
                # 1. MFI is oversold or rising from oversold
                # 2. MFI momentum is positive
                # 3. Optional: volume surge for extra confirmation
                if ((mfi_oversold or (current_mfi < 40 and mfi_rising)) and 
                    self.mfi_momentum[-1] > 0):
                    
                    sl_price = current_price * (1 - self.stop_loss)
                    
                    # Adjust TP based on MFI strength
                    if mfi_oversold and volume_surge:
                        tp_price = current_price * (1 + self.take_profit * 1.5)  # Strong reversal signal
                    elif current_mfi < 30:
                        tp_price = current_price * (1 + self.take_profit * 1.25)
                    else:
                        tp_price = current_price * (1 + self.take_profit)
                    
                    self.buy(sl=sl_price, tp=tp_price)
                    self.pattern_type = 0
                    self.confirmation_counter = 0
            
            # Three Mountains - bearish entry with MFI confirmation
            elif (self.pattern_type == -1 and 
                  self.confirmation_counter >= self.confirmation_bars and
                  self.confirmation_counter <= self.confirmation_bars + 5):
                
                # Enter if:
                # 1. MFI is overbought or falling from overbought
                # 2. MFI momentum is negative
                # 3. Optional: volume surge for extra confirmation
                if ((mfi_overbought or (current_mfi > 60 and mfi_falling)) and 
                    self.mfi_momentum[-1] < 0):
                    
                    sl_price = current_price * (1 + self.stop_loss)
                    
                    # Adjust TP based on MFI strength
                    if mfi_overbought and volume_surge:
                        tp_price = current_price * (1 - self.take_profit * 1.5)  # Strong reversal signal
                    elif current_mfi > 70:
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
        
        # Exit management with MFI
        if self.position:
            if self.position.is_long:
                # Exit on bearish pattern or MFI overbought with declining momentum
                if (self.mountains_signal[-1] == -1 or 
                    (current_mfi > self.mfi_overbought and mfi_falling)):
                    self.position.close()
                # Exit if MFI divergence appears (price up but MFI down)
                elif (current_price > self.data.Close[-5] and 
                      current_mfi < self.mfi[-5] - self.mfi_divergence_threshold):
                    self.position.close()
                    
            elif self.position.is_short:
                # Exit on bullish pattern or MFI oversold with rising momentum
                if (self.rivers_signal[-1] == 1 or 
                    (current_mfi < self.mfi_oversold and mfi_rising)):
                    self.position.close()
                # Exit if MFI divergence appears (price down but MFI up)
                elif (current_price < self.data.Close[-5] and 
                      current_mfi > self.mfi[-5] + self.mfi_divergence_threshold):
                    self.position.close()

# Run single backtest
bt = Backtest(data, ThreeMountainsRiversMFI, cash=100000, commission=0.00045)

print("\n🌙 ===== THREE MOUNTAINS & RIVERS MFI - DEFAULT PARAMETERS ===== 🌙")
print(f"Lookback Period: {LOOKBACK_PERIOD}")
print(f"MFI Period: {MFI_PERIOD}")
print(f"MFI Levels: Oversold<{MFI_OVERSOLD}, Overbought>{MFI_OVERBOUGHT}")
print(f"Pattern Bar Range: {MIN_PATTERN_BARS}-{MAX_PATTERN_BARS}")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")

stats_default = bt.run()
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING THREE MOUNTAINS & RIVERS MFI ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from backtests.multi_data_tester import test_on_all_data
    
    # Test this strategy on all configured data sources
    results = test_on_all_data(ThreeMountainsRiversMFI, 'ThreeMountainsRiversMFI')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/ThreeMountainsRiversMFI.csv")