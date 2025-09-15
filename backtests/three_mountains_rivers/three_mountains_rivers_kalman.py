"""
Moon Dev's Three Mountains & Three Rivers with Kalman Filter Strategy
======================================================================
Enhances pattern recognition using Kalman filter for price smoothing
Reduces false signals from noise while preserving true pattern structure
Tests across all datasets with comprehensive stats output
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
from scipy.signal import argrelextrema
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Three Mountains & Rivers Kalman Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Pattern detection parameters
LOOKBACK_PERIOD = 20
MIN_PATTERN_BARS = 15
MAX_PATTERN_BARS = 60
PEAK_TOLERANCE = 0.02
CONFIRMATION_BARS = 2

# Kalman filter parameters
KALMAN_GAIN = 0.05  # Lower = more smoothing, Higher = more responsive
PROCESS_VARIANCE = 0.01
MEASUREMENT_VARIANCE = 0.1

# Risk management
TAKE_PROFIT_PERCENT = 4.0
STOP_LOSS_PERCENT = 2.0

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

def kalman_filter(prices, gain=0.05, process_var=0.01, measure_var=0.1):
    """
    Apply Kalman filter to smooth price data
    """
    n = len(prices)
    filtered = np.zeros(n)
    
    # Initialize
    filtered[0] = prices[0]
    prediction_error = 1.0
    
    for i in range(1, n):
        # Prediction step
        prediction = filtered[i-1]
        prediction_error = prediction_error + process_var
        
        # Update step
        kalman_gain = prediction_error / (prediction_error + measure_var)
        filtered[i] = prediction + kalman_gain * (prices[i] - prediction)
        prediction_error = (1 - kalman_gain) * prediction_error
    
    return filtered

class ThreeMountainsRiversKalman(Strategy):
    """
    Three Mountains & Rivers with Kalman Filter Strategy
    - Uses Kalman filter to smooth price data for better pattern detection
    - Reduces noise-induced false signals
    - Maintains pattern integrity while filtering market noise
    """
    
    # Pattern parameters
    lookback = LOOKBACK_PERIOD
    min_bars = MIN_PATTERN_BARS
    max_bars = MAX_PATTERN_BARS
    peak_tolerance = PEAK_TOLERANCE
    confirmation_bars = CONFIRMATION_BARS
    
    # Kalman parameters
    kalman_gain = KALMAN_GAIN
    process_var = PROCESS_VARIANCE
    measure_var = MEASUREMENT_VARIANCE
    
    # Risk management
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100
    
    def init(self):
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        volume = pd.Series(self.data.Volume)
        
        # Apply Kalman filter to smooth prices
        close_filtered = kalman_filter(close.values, self.kalman_gain, self.process_var, self.measure_var)
        high_filtered = kalman_filter(high.values, self.kalman_gain, self.process_var, self.measure_var)
        low_filtered = kalman_filter(low.values, self.kalman_gain, self.process_var, self.measure_var)
        
        self.close_kalman = self.I(lambda: close_filtered, name='Close_Kalman')
        self.high_kalman = self.I(lambda: high_filtered, name='High_Kalman')
        self.low_kalman = self.I(lambda: low_filtered, name='Low_Kalman')
        
        # Find peaks and troughs on filtered data
        peaks = argrelextrema(high_filtered, np.greater, order=self.lookback)[0]
        troughs = argrelextrema(low_filtered, np.less, order=self.lookback)[0]
        
        # Create arrays to track peaks and troughs
        peak_array = np.zeros(len(close))
        trough_array = np.zeros(len(close))
        
        peak_array[peaks] = high_filtered[peaks]
        trough_array[troughs] = low_filtered[troughs]
        
        self.peaks = self.I(lambda: peak_array, name='Peaks')
        self.troughs = self.I(lambda: trough_array, name='Troughs')
        
        # Calculate average volume for confirmation
        volume_sma = ta.sma(volume, length=20)
        self.volume_avg = self.I(lambda: volume_sma.values, name='Volume_Avg')
        
        # Calculate volatility for adaptive thresholds
        returns = close.pct_change()
        volatility = ta.stdev(returns, length=20)
        self.volatility = self.I(lambda: volatility.values, name='Volatility')
        
        # Detect patterns on Kalman-filtered data
        mountains_signal = np.zeros(len(close))
        rivers_signal = np.zeros(len(close))
        
        for i in range(len(close)):
            # Adaptive tolerance based on volatility
            adaptive_tolerance = self.peak_tolerance
            if volatility.iloc[i] > 0:
                adaptive_tolerance = min(self.peak_tolerance * (1 + volatility.iloc[i]), 0.05)
            
            # Check for Three Mountains pattern
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
                    if (abs(peak1 - avg_peak) / avg_peak <= adaptive_tolerance and
                        abs(peak2 - avg_peak) / avg_peak <= adaptive_tolerance and
                        abs(peak3 - avg_peak) / avg_peak <= adaptive_tolerance):
                        
                        if (self.min_bars <= idx2 - idx1 <= self.max_bars and
                            self.min_bars <= idx3 - idx2 <= self.max_bars):
                            
                            # Confirm with Kalman price below peak
                            if close_filtered[i] < peak3 * 0.98:
                                # Additional confirmation: declining trend in filtered data
                                if close_filtered[i] < close_filtered[i-1]:
                                    mountains_signal[i] = -1
            
            # Check for Three Rivers pattern
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
                    if (abs(trough1 - avg_trough) / avg_trough <= adaptive_tolerance and
                        abs(trough2 - avg_trough) / avg_trough <= adaptive_tolerance and
                        abs(trough3 - avg_trough) / avg_trough <= adaptive_tolerance):
                        
                        if (self.min_bars <= idx2 - idx1 <= self.max_bars and
                            self.min_bars <= idx3 - idx2 <= self.max_bars):
                            
                            # Confirm with Kalman price above trough
                            if close_filtered[i] > trough3 * 1.02:
                                # Additional confirmation: rising trend in filtered data
                                if close_filtered[i] > close_filtered[i-1]:
                                    rivers_signal[i] = 1
        
        self.mountains_signal = self.I(lambda: mountains_signal, name='Mountains_Signal')
        self.rivers_signal = self.I(lambda: rivers_signal, name='Rivers_Signal')
        
        # Kalman trend for additional confirmation
        kalman_trend = np.zeros(len(close))
        for i in range(1, len(close)):
            if close_filtered[i] > close_filtered[i-1]:
                kalman_trend[i] = 1
            elif close_filtered[i] < close_filtered[i-1]:
                kalman_trend[i] = -1
        
        self.kalman_trend = self.I(lambda: kalman_trend, name='Kalman_Trend')
        
        # Pattern state tracking
        self.confirmation_counter = 0
        self.pattern_type = 0
        
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
        
        # Increment confirmation counter
        if self.pattern_type != 0:
            self.confirmation_counter += 1
        
        # Volume and trend confirmation
        volume_surge = current_volume > self.volume_avg[-1] * 1.2 if self.volume_avg[-1] > 0 else False
        trend_aligned = (self.pattern_type == 1 and self.kalman_trend[-1] == 1) or \
                       (self.pattern_type == -1 and self.kalman_trend[-1] == -1)
        
        if not self.position:
            # Three Rivers - bullish entry with Kalman confirmation
            if (self.pattern_type == 1 and 
                self.confirmation_counter >= self.confirmation_bars and
                self.confirmation_counter <= self.confirmation_bars + 5 and
                trend_aligned):
                
                # Check Kalman price is also rising
                if self.close_kalman[-1] > self.close_kalman[-2]:
                    sl_price = current_price * (1 - self.stop_loss)
                    tp_price = current_price * (1 + self.take_profit)
                    self.buy(sl=sl_price, tp=tp_price)
                    self.pattern_type = 0
                    self.confirmation_counter = 0
            
            # Three Mountains - bearish entry with Kalman confirmation
            elif (self.pattern_type == -1 and 
                  self.confirmation_counter >= self.confirmation_bars and
                  self.confirmation_counter <= self.confirmation_bars + 5 and
                  trend_aligned):
                
                # Check Kalman price is also falling
                if self.close_kalman[-1] < self.close_kalman[-2]:
                    sl_price = current_price * (1 + self.stop_loss)
                    tp_price = current_price * (1 - self.take_profit)
                    self.sell(sl=sl_price, tp=tp_price)
                    self.pattern_type = 0
                    self.confirmation_counter = 0
        
        # Reset pattern if too old
        if self.confirmation_counter > self.confirmation_bars + 10:
            self.pattern_type = 0
            self.confirmation_counter = 0
        
        # Exit on opposite signals or trend reversal
        if self.position:
            if self.position.is_long:
                if self.mountains_signal[-1] == -1 or self.kalman_trend[-1] == -1:
                    self.position.close()
            elif self.position.is_short:
                if self.rivers_signal[-1] == 1 or self.kalman_trend[-1] == 1:
                    self.position.close()

# Run single backtest
bt = Backtest(data, ThreeMountainsRiversKalman, cash=100000, commission=0.00045)

print("\n🌙 ===== THREE MOUNTAINS & RIVERS KALMAN - DEFAULT PARAMETERS ===== 🌙")
print(f"Lookback Period: {LOOKBACK_PERIOD}")
print(f"Kalman Gain: {KALMAN_GAIN}")
print(f"Pattern Bar Range: {MIN_PATTERN_BARS}-{MAX_PATTERN_BARS}")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")

stats_default = bt.run()
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING THREE MOUNTAINS & RIVERS KALMAN ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from backtests.multi_data_tester import test_on_all_data
    
    # Test this strategy on all configured data sources
    results = test_on_all_data(ThreeMountainsRiversKalman, 'ThreeMountainsRiversKalman')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/ThreeMountainsRiversKalman.csv")