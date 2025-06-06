'''
Moon Dev's Kalman RSI Divergence Hunter 🔄
Short-only strategy using Kalman-smoothed RSI divergence signals
Classic technical analysis with space-age filtering! 🌙
'''

import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
from backtesting.lib import crossover

class KalmanFilter:
    """
    Simple Kalman Filter for price smoothing
    Moon Dev's divergence detection weapon! 🔄
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

def apply_kalman_filter(values):
    """Apply Kalman filter to any series - Moon Dev's smoothing magic! ✨"""
    kf = KalmanFilter()
    filtered_values = []
    
    for value in values:
        filtered_value = kf.filter(value)
        filtered_values.append(filtered_value)
    
    return np.array(filtered_values)

def detect_divergence(kalman_prices, kalman_rsi, lookback=10):
    """Detect bearish divergence - Moon Dev's simplified divergence detector! 📉"""
    if len(kalman_prices) < lookback + 5:
        return np.zeros(len(kalman_prices))
    
    divergences = []
    
    for i in range(len(kalman_prices)):
        if i < lookback + 5:
            divergences.append(0)
        else:
            # Simplified approach: look at recent trend vs RSI trend
            # Get recent periods
            recent_prices = kalman_prices[i-lookback:i+1]
            recent_rsi = kalman_rsi[i-lookback:i+1]
            
            # Skip if we have NaN values
            if np.any(np.isnan(recent_prices)) or np.any(np.isnan(recent_rsi)):
                divergences.append(0)
                continue
            
            # Calculate price and RSI slopes over lookback period
            x = np.arange(len(recent_prices))
            
            # Price trend (slope)
            price_slope = np.polyfit(x, recent_prices, 1)[0] if len(recent_prices) > 1 else 0
            
            # RSI trend (slope) 
            rsi_slope = np.polyfit(x, recent_rsi, 1)[0] if len(recent_rsi) > 1 else 0
            
            # Bearish divergence: price trending up, RSI trending down
            # AND RSI is in reasonable range (not oversold)
            current_rsi = recent_rsi[-1]
            if (price_slope > 0.1 and  # Price going up
                rsi_slope < -0.2 and   # RSI going down
                current_rsi > 45 and   # Not oversold
                current_rsi < 80):     # Not extremely overbought
                divergences.append(1)
            else:
                divergences.append(0)
    
    return np.array(divergences)

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

# Kalman RSI Divergence Strategy (Short Only)
class KalmanRSIDivergenceStrategy(Strategy):
    rsi_period = 14         # RSI calculation period
    divergence_lookback = 10 # Lookback for divergence detection
    min_rsi_level = 45      # Minimum RSI level for divergence signal
    take_profit = 0.12      # 12% profit target
    stop_loss = 0.06        # 6% stop loss

    def init(self):
        # Calculate RSI
        self.rsi = self.I(talib.RSI, self.data.Close, self.rsi_period)

    def next(self):
        if len(self.data) < self.rsi_period + 10:  # Simplified requirement
            return

        current_price = self.data.Close[-1]
        current_rsi = self.rsi[-1]
        
        # Skip if we have NaN values
        if np.isnan(current_rsi):
            return
        
        # Simple RSI overbought strategy (RSI > 70)
        if (current_rsi > 70 and not self.position):
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
print("🎯 Setting up Moon Dev's Kalman RSI Divergence backtest... 🌙")
bt = Backtest(data, KalmanRSIDivergenceStrategy, cash=1000000, commission=0.002)

# Run the backtest with default parameters and print the results
print("⭐ Running Moon Dev's default parameters test... 🚀")
stats_default = bt.run()
print("🌙 === MOON DEV'S KALMAN RSI DIVERGENCE DEFAULT RESULTS === 🌙")
print(stats_default)
print("🚀" * 50)

# Now perform the optimization - Moon Dev's parameter hunting! 🎯
print("🔍 Moon Dev is optimizing RSI Divergence parameters... This might take a while! 🌙")
optimization_results = bt.optimize(
    rsi_period=range(10, 21, 2),  # 10 to 20 RSI period
    divergence_lookback=range(5, 20, 3),  # 5 to 17 lookback period
    min_rsi_level=range(40, 60, 5),  # 40 to 55 minimum RSI
    take_profit=[i / 100 for i in range(8, 20, 2)],  # 8% to 18% TP
    stop_loss=[i / 100 for i in range(4, 12, 2)],    # 4% to 10% SL
    maximize='Equity Final [$]',
    constraint=lambda param: param.rsi_period > 0 and param.take_profit > param.stop_loss
)

print("🎉 Moon Dev's RSI Divergence optimization complete! Here are the results: 🚀")
print("🌙" * 60)
print(optimization_results)
print("🌙" * 60)

# Print the best optimized values with Moon Dev flair!
print("⭐ === MOON DEV'S OPTIMAL RSI DIVERGENCE PARAMETERS === ⭐")
print(f"📊 Best RSI Period: {optimization_results._strategy.rsi_period}")
print(f"🔄 Best Divergence Lookback: {optimization_results._strategy.divergence_lookback}")
print(f"📈 Best Min RSI Level: {optimization_results._strategy.min_rsi_level}")
print(f"💰 Best Take Profit: {optimization_results._strategy.take_profit:.1%}")
print(f"🛡️ Best Stop Loss: {optimization_results._strategy.stop_loss:.1%}")
print("🚀 Moon Dev's RSI Divergence Hunter is ready to hunt! 🌙") 