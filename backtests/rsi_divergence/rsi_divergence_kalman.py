"""
Moon Dev's RSI Divergence Kalman Strategy
==========================================
RSI divergence detection with Kalman filter noise reduction
Tests across all datasets with comprehensive stats output
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's RSI Divergence Kalman Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters - FIXED, NO OPTIMIZATION
RSI_PERIOD = 14
LOOKBACK_PERIOD = 10  # Simplified lookback
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
KALMAN_GAIN = 0.02  # Kalman filter gain (lower = smoother)
STOP_LOSS_PERCENT = 2.0
TAKE_PROFIT_PERCENT = 3.5

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

def kalman_filter(data, gain=0.02):
    """Simple Kalman filter implementation for smoothing"""
    filtered = np.zeros_like(data)
    filtered[0] = data[0] if not np.isnan(data[0]) else 0
    
    for i in range(1, len(data)):
        if np.isnan(data[i]):
            filtered[i] = filtered[i-1]
        else:
            filtered[i] = filtered[i-1] + gain * (data[i] - filtered[i-1])
    
    return filtered

class RSIDivergenceKalman(Strategy):
    """
    RSI Divergence with Kalman Filter Strategy - Simplified
    - Detect RSI divergences using rolling windows
    - Apply Kalman filter to reduce noise in price and RSI
    - Enter with stop-loss and take-profit
    """
    
    # Fixed parameters
    rsi_period = RSI_PERIOD
    lookback_period = LOOKBACK_PERIOD
    rsi_oversold = RSI_OVERSOLD
    rsi_overbought = RSI_OVERBOUGHT
    kalman_gain = KALMAN_GAIN
    stop_loss = STOP_LOSS_PERCENT / 100
    take_profit = TAKE_PROFIT_PERCENT / 100
    
    def init(self):
        close = pd.Series(self.data.Close)
        
        # Calculate RSI
        rsi = ta.rsi(close, length=self.rsi_period)
        
        # Ensure arrays are same length as data
        rsi_full = np.full(len(close), np.nan)
        rsi_full[-len(rsi):] = rsi.values
        
        # Apply Kalman filter to price and RSI
        price_kalman = kalman_filter(close.values, self.kalman_gain)
        rsi_kalman = kalman_filter(rsi_full, self.kalman_gain)
        
        self.price_kalman = self.I(lambda: price_kalman, name='Price_Kalman')
        self.rsi_kalman = self.I(lambda: rsi_kalman, name='RSI_Kalman')
        self.rsi = self.I(lambda: rsi_full, name='RSI_Raw')
        
        # Calculate rolling max/min on filtered data for divergence detection
        price_series = pd.Series(price_kalman)
        rsi_series = pd.Series(rsi_kalman)
        
        price_roll_max = price_series.rolling(window=self.lookback_period, min_periods=self.lookback_period).max()
        price_roll_min = price_series.rolling(window=self.lookback_period, min_periods=self.lookback_period).min()
        
        rsi_roll_max = rsi_series.rolling(window=self.lookback_period, min_periods=self.lookback_period).max()
        rsi_roll_min = rsi_series.rolling(window=self.lookback_period, min_periods=self.lookback_period).min()
        
        # Store as indicators
        self.price_max = self.I(lambda: price_roll_max.values, name='Price_Max')
        self.price_min = self.I(lambda: price_roll_min.values, name='Price_Min')
        self.rsi_max = self.I(lambda: rsi_roll_max.values, name='RSI_Max')
        self.rsi_min = self.I(lambda: rsi_roll_min.values, name='RSI_Min')
    
    def next(self):
        # Skip if indicators not ready
        if np.isnan(self.rsi_kalman[-1]) or np.isnan(self.price_max[-1]):
            return
        
        # Skip if we need more data for comparison
        if len(self.data) < self.lookback_period * 2:
            return
        
        current_price = self.data.Close[-1]
        current_price_kalman = self.price_kalman[-1]
        current_rsi = self.rsi[-1]  # Use raw RSI for oversold/overbought checks
        current_rsi_kalman = self.rsi_kalman[-1]
        
        # Get previous extremes (from lookback_period bars ago)
        prev_idx = -self.lookback_period
        if abs(prev_idx) >= len(self.data):
            return
            
        prev_price_high = self.price_max[prev_idx]
        prev_price_low = self.price_min[prev_idx]
        prev_rsi_high = self.rsi_max[prev_idx]
        prev_rsi_low = self.rsi_min[prev_idx]
        
        # Current extremes
        curr_price_high = self.price_max[-1]
        curr_price_low = self.price_min[-1]
        curr_rsi_high = self.rsi_max[-1]
        curr_rsi_low = self.rsi_min[-1]
        
        if not self.position:
            # Bullish divergence: Price makes lower low, RSI makes higher low (using Kalman filtered values)
            price_at_low = abs(current_price_kalman - curr_price_low) / current_price_kalman < 0.005
            price_lower_low = curr_price_low < prev_price_low * 0.995
            rsi_higher_low = curr_rsi_low > prev_rsi_low + 1
            rsi_oversold = current_rsi < self.rsi_oversold + 5
            
            # Additional confirmation: Kalman-filtered trend direction
            price_trend_up = current_price_kalman > self.price_kalman[-2] if len(self.data) > 1 else False
            
            if price_at_low and price_lower_low and rsi_higher_low and rsi_oversold:
                # Enter long position
                sl_price = current_price * (1 - self.stop_loss)
                tp_price = current_price * (1 + self.take_profit)
                self.buy(sl=sl_price, tp=tp_price)
            
            # Bearish divergence: Price makes higher high, RSI makes lower high (using Kalman filtered values)
            price_at_high = abs(current_price_kalman - curr_price_high) / current_price_kalman < 0.005
            price_higher_high = curr_price_high > prev_price_high * 1.005
            rsi_lower_high = curr_rsi_high < prev_rsi_high - 1
            rsi_overbought = current_rsi > self.rsi_overbought - 5
            
            # Additional confirmation: Kalman-filtered trend direction
            price_trend_down = current_price_kalman < self.price_kalman[-2] if len(self.data) > 1 else False
            
            if price_at_high and price_higher_high and rsi_lower_high and rsi_overbought:
                # Enter short position
                sl_price = current_price * (1 + self.stop_loss)
                tp_price = current_price * (1 - self.take_profit)
                self.sell(sl=sl_price, tp=tp_price)

# Run single backtest - NO OPTIMIZATION
bt = Backtest(data, RSIDivergenceKalman, cash=100000, commission=0.00045)

print("\n🌙 ===== RSI DIVERGENCE KALMAN - FIXED PARAMETERS ===== 🌙")
print(f"RSI Period: {RSI_PERIOD}")
print(f"Lookback Period: {LOOKBACK_PERIOD}")
print(f"Kalman Gain: {KALMAN_GAIN}")
print(f"RSI Oversold: {RSI_OVERSOLD}")
print(f"RSI Overbought: {RSI_OVERBOUGHT}")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")

stats = bt.run()
print(stats)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING RSI DIVERGENCE KALMAN ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    # Test this strategy on all configured data sources
    results = test_on_all_data(RSIDivergenceKalman, 'RSIDivergenceKalman')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/RSIDivergenceKalman.csv")