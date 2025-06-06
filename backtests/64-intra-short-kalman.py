'''
🌙 MOON DEV Intraday Short Selling with Kalman Filter Strategy 🚀
Enhanced parabolic move detection using Kalman filtering for smoother signals

This strategy uses a Kalman filter to smooth price data and detect parabolic moves
more accurately by reducing noise in the price signal.

🔥 Kalman Filter Benefits:
- Smoother price tracking
- Better noise reduction
- More accurate trend detection
- Adaptive to market conditions
'''

import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
from backtesting.lib import crossover

class KalmanFilter:
    """
    🌙 MOON DEV Simple Kalman Filter for price smoothing
    """
    def __init__(self, process_variance=1e-3, measurement_variance=1e-1):
        self.process_variance = process_variance      # Q - process noise
        self.measurement_variance = measurement_variance  # R - measurement noise
        self.posteri_estimate = 0.0                 # x_hat - posterior estimate
        self.posteri_error_estimate = 1.0           # P - posterior error estimate
        
    def update(self, measurement):
        """Update the Kalman filter with a new measurement"""
        # Prediction step
        priori_estimate = self.posteri_estimate
        priori_error_estimate = self.posteri_error_estimate + self.process_variance
        
        # Update step
        blending_factor = priori_error_estimate / (priori_error_estimate + self.measurement_variance)
        self.posteri_estimate = priori_estimate + blending_factor * (measurement - priori_estimate)
        self.posteri_error_estimate = (1 - blending_factor) * priori_error_estimate
        
        return self.posteri_estimate

def apply_kalman_filter(prices, process_var=1e-3, measurement_var=1e-1):
    """
    🌙 MOON DEV Apply Kalman filter to price series
    """
    kf = KalmanFilter(process_var, measurement_var)
    filtered_prices = []
    
    for price in prices:
        filtered_price = kf.update(price)
        filtered_prices.append(filtered_price)
    
    return np.array(filtered_prices)

# Load the data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-5m-70wks-data.csv'

print("🌙 MOON DEV Loading data for Kalman filtered strategy! 📊")

# 🌙 MOON DEV Adaptive header detection for different data sources
sample_df = pd.read_csv(data_path, nrows=1)
headers = sample_df.columns.tolist()

# Determine which datetime column to use
if 'timestamp' in headers:
    datetime_col = 'timestamp'
elif 'datetime' in headers:
    datetime_col = 'datetime'
else:
    raise ValueError("🌙 MOON DEV Error: No 'timestamp' or 'datetime' column found!")

# Load data with the correct datetime column
data = pd.read_csv(data_path, parse_dates=[datetime_col], index_col=datetime_col)

print(f"🌙 MOON DEV Data loaded successfully! Shape: {data.shape} 📈")

# Kalman Enhanced Parabolic Move Short Strategy
class KalmanParabolicMoveShort(Strategy):
    # Strategy Constants - MOON DEV Style! 🌙
    lookback_window = 20        # Window for threshold calculation
    std_dev_multiplier = 2.0    # Standard deviations from filtered mean
    take_profit = 0.04          # 4% take profit
    stop_loss = 0.02            # 2% stop loss
    process_variance = 1e-3     # Kalman filter process noise
    measurement_variance = 1e-1  # Kalman filter measurement noise
    
    def init(self):
        print("🌙 MOON DEV Initializing Kalman Filter Strategy! 🚀")
        
        # Apply Kalman filter to close prices
        close_prices = self.data.Close
        self.kalman_filtered = self.I(
            apply_kalman_filter, 
            close_prices, 
            self.process_variance, 
            self.measurement_variance
        )
        
        # Calculate rolling statistics on filtered prices
        self.rolling_mean = self.I(talib.SMA, self.kalman_filtered, self.lookback_window)
        self.rolling_std = self.I(talib.STDDEV, self.kalman_filtered, self.lookback_window)
        
        # Calculate upper threshold for parabolic detection
        self.upper_threshold = self.I(
            lambda: self.rolling_mean + (self.std_dev_multiplier * self.rolling_std)
        )
        
        print("🌙 MOON DEV Kalman filter and indicators initialized! ✨")

    def next(self):
        # Skip if not enough data
        if len(self.data) < self.lookback_window:
            return
            
        current_price = self.data.Close[-1]
        filtered_price = self.kalman_filtered[-1]
        threshold = self.upper_threshold[-1]
        
        # 🌙 MOON DEV Short when filtered price breaks above parabolic threshold
        if filtered_price > threshold and not self.position:
            print(f"🌙 MOON DEV Parabolic move detected! 📈")
            print(f"🎯 Current Price: ${current_price:.2f}")
            print(f"🔍 Filtered Price: ${filtered_price:.2f}")
            print(f"📊 Threshold: ${threshold:.2f}")
            print(f"🚀 Going SHORT on parabolic move! 📉")
            
            # Calculate stop loss and take profit levels
            stop_loss_price = current_price * (1 + self.stop_loss)
            take_profit_price = current_price * (1 - self.take_profit)
            
            print(f"🛡️ Stop Loss: ${stop_loss_price:.2f}")
            print(f"🎯 Take Profit: ${take_profit_price:.2f}")
            
            self.sell(
                sl=stop_loss_price,    # Stop loss above entry
                tp=take_profit_price   # Take profit below entry
            )

# Prepare data - convert lowercase columns to uppercase for backtesting.py
data.columns = [col.title() for col in data.columns]

print("🌙 MOON DEV Data prepared for backtesting! 🛠️")

# Create and configure the backtest
bt = Backtest(data, KalmanParabolicMoveShort, cash=100000, commission=0.002)

print("🌙 MOON DEV Running backtest with default parameters! ⚡")

# Run the backtest with default parameters
stats_default = bt.run()
print("\n🌙 MOON DEV Default Kalman Parameters Results:")
print("=" * 60)
print(stats_default)
print("=" * 60)

print("🌙 MOON DEV Starting optimization process! 🔧")

# Optimization parameters
optimization_results = bt.optimize(
    lookback_window=range(10, 31, 5),                          # 10, 15, 20, 25, 30
    std_dev_multiplier=[round(i, 1) for i in np.arange(1.0, 3.1, 0.2)],  # 1.0 to 3.0
    take_profit=[i / 100 for i in range(2, 8, 1)],            # 2% to 7%
    stop_loss=[i / 100 for i in range(1, 6, 1)],              # 1% to 5%
    process_variance=[1e-4, 1e-3, 1e-2],                      # Kalman process noise
    measurement_variance=[1e-2, 1e-1, 1e0],                   # Kalman measurement noise
    maximize='Equity Final [$]',
    constraint=lambda param: param.lookback_window > 0 and param.std_dev_multiplier > 0
)

print("\n🌙 MOON DEV Kalman Optimization Complete! Final Results:")
print("=" * 60)
print(optimization_results)
print("=" * 60)

print("\n🎯 MOON DEV Best Kalman Optimized Parameters:")
print(f"🔍 Lookback Window: {optimization_results._strategy.lookback_window}")
print(f"📊 Standard Deviations: {optimization_results._strategy.std_dev_multiplier}")
print(f"🎯 Take Profit: {optimization_results._strategy.take_profit:.1%}")
print(f"🛡️ Stop Loss: {optimization_results._strategy.stop_loss:.1%}")
print(f"🔧 Process Variance: {optimization_results._strategy.process_variance}")
print(f"📡 Measurement Variance: {optimization_results._strategy.measurement_variance}")
print("🌙 MOON DEV Kalman Strategy Complete! 🚀✨") 