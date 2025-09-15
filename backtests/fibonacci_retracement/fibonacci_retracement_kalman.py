"""
Moon Dev's Fibonacci Retracement + Kalman Filter Strategy
=========================================================
Fibonacci retracement with Kalman filter for noise reduction
Tests across all datasets with comprehensive stats output
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Fibonacci Retracement + Kalman Filter Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters - FIXED, NO OPTIMIZATION
SWING_LOOKBACK = 30  # Periods to identify swing highs/lows
MIN_SWING_DIFF = 0.02  # Minimum 2% difference for valid swing
FIB_ENTRY_LEVEL = 0.618  # Enter at 61.8% retracement
FIB_SECONDARY_LEVEL = 0.382  # Secondary entry at 38.2%
STOP_LOSS_PERCENT = 3.0  # Stop loss percentage
TAKE_PROFIT_PERCENT = 5.0  # Take profit percentage
TREND_MA_PERIOD = 50  # MA period for trend determination
KALMAN_GAIN = 0.01  # Kalman filter gain parameter

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

def kalman_filter(prices, kalman_gain=0.01):
    """
    Simple 1D Kalman filter for price smoothing
    """
    n = len(prices)
    filtered = np.zeros(n)
    
    # Initial values
    filtered[0] = prices[0]
    error_est = 1.0
    
    for i in range(1, n):
        # Prediction update
        error_est = error_est + kalman_gain
        
        # Measurement update
        k_gain = error_est / (error_est + kalman_gain)
        filtered[i] = filtered[i-1] + k_gain * (prices[i] - filtered[i-1])
        error_est = (1 - k_gain) * error_est
    
    return filtered

class FibonacciRetracementKalman(Strategy):
    """
    Fibonacci Retracement + Kalman Filter Strategy
    - Use Kalman filter to smooth price data and reduce noise
    - Identify cleaner swing highs and lows
    - Calculate Fibonacci levels on filtered data
    - Enter trades with reduced false signals
    """
    
    # Swing detection parameters
    swing_lookback = SWING_LOOKBACK
    min_swing_diff = MIN_SWING_DIFF
    
    # Fibonacci levels
    fib_entry = FIB_ENTRY_LEVEL
    fib_secondary = FIB_SECONDARY_LEVEL
    
    # Risk management
    stop_loss = STOP_LOSS_PERCENT / 100
    take_profit = TAKE_PROFIT_PERCENT / 100
    
    # Filter parameters
    trend_ma_period = TREND_MA_PERIOD
    kalman_gain = KALMAN_GAIN
    
    def init(self):
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        
        # Apply Kalman filter to prices
        kalman_close = kalman_filter(close.values, self.kalman_gain)
        kalman_high = kalman_filter(high.values, self.kalman_gain)
        kalman_low = kalman_filter(low.values, self.kalman_gain)
        
        self.kalman_close = self.I(lambda: kalman_close, name='Kalman_Close')
        self.kalman_high = self.I(lambda: kalman_high, name='Kalman_High')
        self.kalman_low = self.I(lambda: kalman_low, name='Kalman_Low')
        
        # Calculate trend MA on filtered data
        kalman_series = pd.Series(kalman_close)
        ma = ta.sma(kalman_series, length=self.trend_ma_period)
        ma_full = np.full(len(close), np.nan)
        ma_full[-len(ma):] = ma.values
        self.ma = self.I(lambda: ma_full, name='MA')
        
        # Calculate rolling highs and lows on Kalman filtered data
        kalman_high_series = pd.Series(kalman_high)
        kalman_low_series = pd.Series(kalman_low)
        
        swing_high = kalman_high_series.rolling(window=self.swing_lookback, min_periods=self.swing_lookback).max()
        swing_low = kalman_low_series.rolling(window=self.swing_lookback, min_periods=self.swing_lookback).min()
        
        self.swing_high = self.I(lambda: swing_high.values, name='Swing_High')
        self.swing_low = self.I(lambda: swing_low.values, name='Swing_Low')
        
        # Track Fibonacci levels
        self.fib_0 = None
        self.fib_236 = None
        self.fib_382 = None
        self.fib_50 = None
        self.fib_618 = None
        self.fib_100 = None
        
        # Track entry info
        self.entry_price = None
        self.in_position = False
    
    def calculate_fib_levels(self, swing_high, swing_low, is_uptrend):
        """Calculate Fibonacci retracement levels"""
        if is_uptrend:
            diff = swing_high - swing_low
            self.fib_0 = swing_low
            self.fib_236 = swing_low + diff * 0.236
            self.fib_382 = swing_low + diff * 0.382
            self.fib_50 = swing_low + diff * 0.5
            self.fib_618 = swing_low + diff * 0.618
            self.fib_100 = swing_high
        else:
            diff = swing_high - swing_low
            self.fib_0 = swing_high
            self.fib_236 = swing_high - diff * 0.236
            self.fib_382 = swing_high - diff * 0.382
            self.fib_50 = swing_high - diff * 0.5
            self.fib_618 = swing_high - diff * 0.618
            self.fib_100 = swing_low
    
    def next(self):
        # Skip if indicators not ready
        if np.isnan(self.ma[-1]) or np.isnan(self.swing_high[-1]) or np.isnan(self.swing_low[-1]):
            return
        
        # Skip if we need more data
        if len(self.data) < self.swing_lookback * 2:
            return
        
        # Use both raw and Kalman filtered prices
        current_price = self.data.Close[-1]
        kalman_price = self.kalman_close[-1]
        current_ma = self.ma[-1]
        
        # Determine trend using Kalman filtered price
        is_uptrend = kalman_price > current_ma
        
        # Get current swing levels (from Kalman filtered data)
        current_swing_high = self.swing_high[-1]
        current_swing_low = self.swing_low[-1]
        
        # Check if we have a significant swing range
        swing_range = (current_swing_high - current_swing_low) / current_swing_low
        if swing_range < self.min_swing_diff:
            return
        
        # Calculate Fibonacci levels
        self.calculate_fib_levels(current_swing_high, current_swing_low, is_uptrend)
        
        if not self.position:
            # Use Kalman price for cleaner signal detection
            if is_uptrend:
                # In uptrend, buy at retracements
                # Check if Kalman price is at 61.8% retracement
                if self.fib_618 is not None:
                    at_618 = abs(kalman_price - self.fib_618) / kalman_price < 0.01
                    above_618 = kalman_price > self.fib_618
                    price_confirm = current_price > self.fib_618 * 0.995  # Raw price confirmation
                    
                    if at_618 and above_618 and price_confirm:
                        sl_price = current_price * (1 - self.stop_loss)
                        tp_price = current_price * (1 + self.take_profit)
                        self.buy(sl=sl_price, tp=tp_price)
                        self.entry_price = current_price
                        self.in_position = True
                        return
                
                # Check if Kalman price is at 38.2% retracement
                if self.fib_382 is not None:
                    at_382 = abs(kalman_price - self.fib_382) / kalman_price < 0.01
                    above_382 = kalman_price > self.fib_382
                    price_confirm = current_price > self.fib_382 * 0.995
                    
                    if at_382 and above_382 and price_confirm:
                        sl_price = current_price * (1 - self.stop_loss)
                        tp_price = current_price * (1 + self.take_profit)
                        self.buy(sl=sl_price, tp=tp_price)
                        self.entry_price = current_price
                        self.in_position = True
                        return
            
            else:
                # In downtrend, sell at retracements
                # Check if Kalman price is at 61.8% retracement
                if self.fib_618 is not None:
                    at_618 = abs(kalman_price - self.fib_618) / kalman_price < 0.01
                    below_618 = kalman_price < self.fib_618
                    price_confirm = current_price < self.fib_618 * 1.005  # Raw price confirmation
                    
                    if at_618 and below_618 and price_confirm:
                        sl_price = current_price * (1 + self.stop_loss)
                        tp_price = current_price * (1 - self.take_profit)
                        self.sell(sl=sl_price, tp=tp_price)
                        self.entry_price = current_price
                        self.in_position = True
                        return
                
                # Check if Kalman price is at 38.2% retracement
                if self.fib_382 is not None:
                    at_382 = abs(kalman_price - self.fib_382) / kalman_price < 0.01
                    below_382 = kalman_price < self.fib_382
                    price_confirm = current_price < self.fib_382 * 1.005
                    
                    if at_382 and below_382 and price_confirm:
                        sl_price = current_price * (1 + self.stop_loss)
                        tp_price = current_price * (1 - self.take_profit)
                        self.sell(sl=sl_price, tp=tp_price)
                        self.entry_price = current_price
                        self.in_position = True
                        return
        else:
            # Reset position flag when out of position
            if not self.position:
                self.in_position = False

# Run single backtest (default behavior)
bt = Backtest(data, FibonacciRetracementKalman, cash=100000, commission=0.00045)

print("\n🌙 ===== FIBONACCI RETRACEMENT + KALMAN FILTER - FIXED PARAMETERS ===== 🌙")
print(f"Swing Lookback: {SWING_LOOKBACK}")
print(f"Min Swing Difference: {MIN_SWING_DIFF * 100}%")
print(f"Primary Entry Level: {FIB_ENTRY_LEVEL * 100}%")
print(f"Secondary Entry Level: {FIB_SECONDARY_LEVEL * 100}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Trend MA Period: {TREND_MA_PERIOD}")
print(f"Kalman Gain: {KALMAN_GAIN}")

stats = bt.run()
print(stats)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING FIBONACCI RETRACEMENT + KALMAN FILTER ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    # Test this strategy on all configured data sources
    results = test_on_all_data(FibonacciRetracementKalman, 'FibonacciRetracementKalman')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/FibonacciRetracementKalman.csv")