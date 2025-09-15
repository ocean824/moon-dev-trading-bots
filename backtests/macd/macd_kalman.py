"""
Moon Dev's MACD Kalman Strategy
================================
MACD strategy with Kalman filter for signal smoothing
Tests across all datasets with comprehensive stats output
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's MACD Kalman Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# MACD parameters
FAST_PERIOD = 12
SLOW_PERIOD = 26
SIGNAL_PERIOD = 9

# Kalman filter parameters
KALMAN_GAIN = 0.3  # Process noise / measurement noise ratio

# Risk management
TAKE_PROFIT_PERCENT = 3.0
STOP_LOSS_PERCENT = 2.0

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class MACDKalman(Strategy):
    """
    MACD Kalman Strategy
    - Uses MACD crossovers with Kalman filter for noise reduction
    - Kalman filter smooths MACD signals to reduce false signals
    - Enhanced signal quality for better trade entries
    """
    
    # MACD parameters
    fast_period = FAST_PERIOD
    slow_period = SLOW_PERIOD
    signal_period = SIGNAL_PERIOD
    
    # Kalman filter parameter
    kalman_gain = KALMAN_GAIN
    
    # Risk management
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100
    
    # Histogram momentum threshold
    histogram_threshold = 0.0001
    
    def apply_kalman_filter(self, data, gain=0.3):
        """Apply Kalman filter to smooth data"""
        filtered = np.zeros_like(data)
        filtered[0] = data[0] if not np.isnan(data[0]) else 0
        
        for i in range(1, len(data)):
            if np.isnan(data[i]):
                filtered[i] = filtered[i-1]
            else:
                # Simple 1D Kalman filter
                # Prediction: x_pred = x_prev
                # Update: x_new = x_pred + K * (measurement - x_pred)
                prediction = filtered[i-1]
                filtered[i] = prediction + gain * (data[i] - prediction)
        
        return filtered
    
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
        
        # Apply Kalman filter to smooth MACD signals
        macd_kalman = self.apply_kalman_filter(macd_full, self.kalman_gain)
        signal_kalman = self.apply_kalman_filter(signal_full, self.kalman_gain)
        histogram_kalman = self.apply_kalman_filter(histogram_full, self.kalman_gain)
        
        self.macd = self.I(lambda: macd_kalman, name='MACD_Kalman')
        self.signal = self.I(lambda: signal_kalman, name='Signal_Kalman')
        self.histogram = self.I(lambda: histogram_kalman, name='Histogram_Kalman')
        
        # Previous values for crossover detection
        macd_prev = np.roll(macd_kalman, 1)
        signal_prev = np.roll(signal_kalman, 1)
        histogram_prev = np.roll(histogram_kalman, 1)
        
        macd_prev[0] = np.nan
        signal_prev[0] = np.nan
        histogram_prev[0] = np.nan
        
        self.macd_prev = self.I(lambda: macd_prev, name='MACD_Prev')
        self.signal_prev = self.I(lambda: signal_prev, name='Signal_Prev')
        self.histogram_prev = self.I(lambda: histogram_prev, name='Histogram_Prev')
        
        # Calculate histogram momentum (rate of change)
        histogram_momentum = histogram_kalman - histogram_prev
        self.histogram_momentum = self.I(lambda: histogram_momentum, name='Histogram_Momentum')
        
        # Add trend filter using Kalman-filtered price
        price_kalman = self.apply_kalman_filter(close.values, self.kalman_gain * 0.5)
        self.price_kalman = self.I(lambda: price_kalman, name='Price_Kalman')
        
    def next(self):
        # Skip if indicators not ready
        if np.isnan(self.macd[-1]) or np.isnan(self.signal[-1]) or np.isnan(self.histogram[-1]):
            return
        
        # Skip if previous values not ready
        if np.isnan(self.macd_prev[-1]) or np.isnan(self.signal_prev[-1]):
            return
        
        current_price = self.data.Close[-1]
        
        # Detect MACD crossovers (with Kalman-smoothed values)
        bullish_crossover = (self.macd_prev[-1] <= self.signal_prev[-1] and 
                            self.macd[-1] > self.signal[-1])
        
        bearish_crossover = (self.macd_prev[-1] >= self.signal_prev[-1] and 
                            self.macd[-1] < self.signal[-1])
        
        # Check histogram momentum (Kalman-smoothed)
        histogram_increasing = self.histogram_momentum[-1] > self.histogram_threshold
        histogram_decreasing = self.histogram_momentum[-1] < -self.histogram_threshold
        
        # Check if histogram is positive or negative
        histogram_positive = self.histogram[-1] > 0
        histogram_negative = self.histogram[-1] < 0
        
        # Additional trend confirmation using Kalman-filtered price
        price_trend_up = self.price_kalman[-1] > self.price_kalman[-2] if not np.isnan(self.price_kalman[-2]) else False
        price_trend_down = self.price_kalman[-1] < self.price_kalman[-2] if not np.isnan(self.price_kalman[-2]) else False
        
        if not self.position:
            # Long entry conditions with Kalman confirmation
            if bullish_crossover and histogram_increasing and histogram_positive and price_trend_up:
                sl_price = current_price * (1 - self.stop_loss)
                tp_price = current_price * (1 + self.take_profit)
                self.buy(sl=sl_price, tp=tp_price)
            
            # Short entry conditions with Kalman confirmation
            elif bearish_crossover and histogram_decreasing and histogram_negative and price_trend_down:
                sl_price = current_price * (1 + self.stop_loss)
                tp_price = current_price * (1 - self.take_profit)
                self.sell(sl=sl_price, tp=tp_price)
        
        # Exit conditions for existing positions
        elif self.position.is_long:
            # Exit long on bearish crossover or significant histogram decrease
            if bearish_crossover or (histogram_decreasing and self.histogram[-1] < 0):
                self.position.close()
        
        elif self.position.is_short:
            # Exit short on bullish crossover or significant histogram increase
            if bullish_crossover or (histogram_increasing and self.histogram[-1] > 0):
                self.position.close()

# Run single backtest
bt = Backtest(data, MACDKalman, cash=100000, commission=0.00045)

print("\n🌙 ===== MACD KALMAN STRATEGY - DEFAULT PARAMETERS ===== 🌙")
print(f"Fast Period: {FAST_PERIOD}")
print(f"Slow Period: {SLOW_PERIOD}")
print(f"Signal Period: {SIGNAL_PERIOD}")
print(f"Kalman Gain: {KALMAN_GAIN}")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")

stats_default = bt.run()
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING MACD KALMAN STRATEGY ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from backtests.multi_data_tester import test_on_all_data
    
    # Test this strategy on all configured data sources
    results = test_on_all_data(MACDKalman, 'MACDKalman')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/MACDKalman_[timestamp].csv")