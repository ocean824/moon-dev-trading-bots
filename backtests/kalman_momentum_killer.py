'''
Moon Dev's Kalman Momentum Killer 📉
Short-only strategy detecting when uptrend momentum dies
Catches trend reversals before they become obvious! 🌙
'''

import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
from backtesting.lib import crossover

class KalmanFilter:
    """
    Simple Kalman Filter for price smoothing
    Moon Dev's momentum detection weapon! 📉
    """
    def __init__(self, process_variance=1e-5, measurement_variance=1e-1):
        self.process_variance = process_variance
        self.measurement_variance = measurement_variance
        self.posteri_estimate = None
        self.posteri_error_estimate = None
        
    def filter(self, measurement):
        if self.posteri_estimate is None:
            self.posteri_estimate = measurement
            self.posteri_error_estimate = 1.0
            return measurement
            
        # Prediction step
        priori_estimate = self.posteri_estimate
        priori_error_estimate = self.posteri_error_estimate + self.process_variance
        
        # Update step
        blending_factor = priori_error_estimate / (priori_error_estimate + self.measurement_variance)
        self.posteri_estimate = priori_estimate + blending_factor * (measurement - priori_estimate)
        self.posteri_error_estimate = (1 - blending_factor) * priori_error_estimate
        
        return self.posteri_estimate

def apply_kalman_filter(prices):
    """Apply Kalman filter to price series - Moon Dev's trend smoothing magic! ✨"""
    kf = KalmanFilter()
    filtered_prices = []
    
    for price in prices:
        filtered_price = kf.filter(price)
        filtered_prices.append(filtered_price)
    
    return np.array(filtered_prices)

def calculate_slope(values, window=5):
    """Calculate slope of Kalman filtered values - Moon Dev's momentum detector! 📈"""
    if len(values) < window:
        return np.zeros(len(values))
    
    slopes = []
    for i in range(len(values)):
        if i < window - 1:
            slopes.append(0)
        else:
            # Calculate slope using linear regression over window
            y = values[i-window+1:i+1]
            x = np.arange(len(y))
            slope = np.polyfit(x, y, 1)[0]
            slopes.append(slope)
    
    return np.array(slopes)

# Load the filtered data with Moon Dev's adaptive header detection! 🎯
print("📊 Loading Moon Dev's crypto data with smart header detection... 🌙")
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/SOLUSD-1d-1000wks-data.csv'

# 🌙 MOON DEV Adaptive header detection for different data sources
print("🔍 Moon Dev is checking data headers... 🌙")
# First, peek at the headers to determine format
sample_df = pd.read_csv(data_path, nrows=1)
headers = sample_df.columns.tolist()
print(f"📋 Moon Dev found these headers: {headers} 🚀")

# Determine which datetime column to use
if 'timestamp' in headers:
    datetime_col = 'timestamp'
    print("⏰ Moon Dev detected 'timestamp' column! 🌙")
elif 'datetime' in headers:
    datetime_col = 'datetime'
    print("⏰ Moon Dev detected 'datetime' column! 🌙")
else:
    raise ValueError("🌙 MOON DEV Error: No 'timestamp' or 'datetime' column found!")

# Now load the full data with the correct datetime column
print(f"📈 Moon Dev is loading data using '{datetime_col}' column... 🚀")
data = pd.read_csv(data_path, parse_dates=[datetime_col], index_col=datetime_col)

print(f"🚀 Data loaded! Shape: {data.shape} - Moon Dev is ready to rock! 🌙")
print(f"📊 Moon Dev's data columns: {list(data.columns)} 🌙")

# Kalman Momentum Killer Strategy (Short Only)
class KalmanMomentumKillerStrategy(Strategy):
    slope_window = 5        # Window for slope calculation
    slope_threshold = -0.05 # Moderate negative slope
    min_price_level = 8     # Reasonable minimum price
    take_profit = 0.08      # 8% profit target (balanced)
    stop_loss = 0.04        # 4% stop loss (balanced risk)

    def init(self):
        # Apply Kalman filter to close prices
        self.kalman_prices = self.I(apply_kalman_filter, self.data.Close)
        
        # Calculate slope of Kalman filtered prices
        self.kalman_slope = self.I(calculate_slope, self.kalman_prices, self.slope_window)

    def next(self):
        if len(self.data) < self.slope_window + 5:  # Need enough data points
            return

        current_price = self.data.Close[-1]
        current_slope = self.kalman_slope[-1]
        kalman_price = self.kalman_prices[-1]
        
        # Skip if we have NaN values
        if np.isnan(current_slope) or np.isnan(kalman_price):
            return
        
        # BALANCED APPROACH: Generate trades but with better conditions
        # Two conditions: negative slope AND price above trend
        price_deviation = (current_price - kalman_price) / kalman_price
        
        # Short when:
        # 1. Moderate negative slope (momentum turning down)
        # 2. Price is above Kalman trend (overextended, even slightly)
        if (current_slope < -0.05 and         # Moderate negative slope
            price_deviation > 0.005 and       # Price even 0.5% above trend
            current_price > 8 and             # Basic minimum price
            not self.position):
            
            self.sell(
                sl=current_price * (1 + self.stop_loss),
                tp=current_price * (1 - self.take_profit)
            )

# Ensure necessary columns are present and rename correctly
print("🔧 Moon Dev is preparing the data columns... 🌙")
print(f"📊 Current data shape: {data.shape} 🌙")

# Adaptive column handling based on actual number of columns
if data.shape[1] == 5:
    # Standard 5 columns: open, high, low, close, volume
    data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
    print("✅ Moon Dev detected 5 columns - standard format! 🚀")
elif data.shape[1] == 6:
    # 6 columns: includes trailing comma column
    data.columns = ['Open', 'High', 'Low', 'Close', 'Volume', 'Unnamed: 6']
    # Drop the unnecessary trailing column
    data.drop(columns=['Unnamed: 6'], inplace=True)
    print("✅ Moon Dev detected 6 columns - dropped trailing comma column! 🚀")
else:
    raise ValueError(f"🌙 MOON DEV Error: Expected 5 or 6 columns, got {data.shape[1]} columns!")

print(f"🎯 Final data columns: {list(data.columns)} 🌙")
print("✅ Data columns ready for Moon Dev's analysis! 🚀")

# Create and configure the backtest
print("🎯 Setting up Moon Dev's Kalman Momentum Killer backtest... 🌙")
bt = Backtest(data, KalmanMomentumKillerStrategy, cash=1000000, commission=0.002)

# Run the backtest with default parameters and print the results
print("⭐ Running Moon Dev's default parameters test... 🚀")
stats_default = bt.run()
print("🌙 === MOON DEV'S KALMAN MOMENTUM KILLER DEFAULT RESULTS === 🌙")
print(stats_default)
print("🚀" * 50)

# Now perform the optimization - Moon Dev's parameter hunting! 🎯
print("🔍 Moon Dev is optimizing Momentum Killer parameters... This might take a while! 🌙")
optimization_results = bt.optimize(
    slope_window=range(3, 8, 1),  # 3 to 7 window for slope
    slope_threshold=[-i / 100 for i in range(2, 15, 2)],  # -0.02 to -0.14 slope threshold (balanced)
    take_profit=[i / 100 for i in range(6, 15, 2)],  # 6% to 14% TP
    stop_loss=[i / 100 for i in range(3, 8, 1)],     # 3% to 7% SL
    maximize='Equity Final [$]',
    constraint=lambda param: param.slope_window > 0 and param.take_profit > param.stop_loss
)

print("🎉 Moon Dev's Momentum Killer optimization complete! Here are the results: 🚀")
print("🌙" * 60)
print(optimization_results)
print("🌙" * 60)

# Print the best optimized values with Moon Dev flair!
print("⭐ === MOON DEV'S OPTIMAL MOMENTUM KILLER PARAMETERS === ⭐")
print(f"📊 Best Slope Window: {optimization_results._strategy.slope_window}")
print(f"📉 Best Slope Threshold: {optimization_results._strategy.slope_threshold:.2f}")
print(f"💰 Best Take Profit: {optimization_results._strategy.take_profit:.1%}")
print(f"🛡️ Best Stop Loss: {optimization_results._strategy.stop_loss:.1%}")
print("🚀 Moon Dev's Momentum Killer is ready to destroy uptrends! 🌙") 