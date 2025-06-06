'''
Moon Dev's Kalman Mean Reversion Sniper 🎯
Short-only strategy using Kalman filter for dynamic fair value
Catches overextended moves that snap back to reality! 🌙
'''

import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
from backtesting.lib import crossover

class KalmanFilter:
    """
    Simple Kalman Filter for price smoothing
    Moon Dev's mean reversion weapon! 🎯
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
    """Apply Kalman filter to price series - Moon Dev's fair value magic! ✨"""
    kf = KalmanFilter()
    filtered_prices = []
    
    for price in prices:
        filtered_price = kf.filter(price)
        filtered_prices.append(filtered_price)
    
    return np.array(filtered_prices)

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

# Kalman Mean Reversion Strategy (Short Only) - IMPROVED
class KalmanMeanReversionStrategy(Strategy):
    deviation_threshold = 0.12  # 12% deviation above fair value (much more selective)
    lookback_confirm = 5        # Confirmation period
    take_profit = 0.06         # 6% profit target (more realistic)
    stop_loss = 0.03           # 3% stop loss (tighter risk)

    def init(self):
        # Apply Kalman filter to close prices for fair value
        self.kalman_fair_value = self.I(apply_kalman_filter, self.data.Close)
        
        # Add RSI for additional confirmation
        self.rsi = self.I(talib.RSI, self.data.Close, 14)

    def next(self):
        if len(self.data) < 30:  # Need more data points for stability
            return

        current_price = self.data.Close[-1]
        fair_value = self.kalman_fair_value[-1]
        current_rsi = self.rsi[-1]
        
        # Skip if we have NaN values
        if np.isnan(fair_value) or np.isnan(current_rsi):
            return
        
        # Calculate deviation from fair value
        deviation = (current_price - fair_value) / fair_value
        
        # More selective entry conditions:
        # 1. Significant deviation (12%+)
        # 2. RSI overbought (75+) for additional confirmation
        # 3. Price has been above fair value for several periods (momentum exhaustion)
        recent_deviations = []
        for i in range(min(self.lookback_confirm, len(self.data))):
            if len(self.data) > i:
                past_price = self.data.Close[-1-i]
                past_fair = self.kalman_fair_value[-1-i]
                if not np.isnan(past_fair):
                    past_dev = (past_price - past_fair) / past_fair
                    recent_deviations.append(past_dev)
        
        avg_recent_deviation = np.mean(recent_deviations) if recent_deviations else 0
        
        # Short when ALL conditions are met:
        if (deviation > self.deviation_threshold and      # Significant overextension
            current_rsi > 75 and                         # Overbought momentum
            avg_recent_deviation > 0.08 and              # Sustained overextension
            current_price > 15 and                       # Reasonable price level
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
print("🎯 Setting up Moon Dev's Kalman Mean Reversion backtest... 🌙")
bt = Backtest(data, KalmanMeanReversionStrategy, cash=1000000, commission=0.002)

# Run the backtest with default parameters and print the results
print("⭐ Running Moon Dev's default parameters test... 🚀")
stats_default = bt.run()
print("🌙 === MOON DEV'S KALMAN MEAN REVERSION DEFAULT RESULTS === 🌙")
print(stats_default)
print("🚀" * 50)

# Now perform the optimization - Moon Dev's parameter hunting! 🎯
print("🔍 Moon Dev is optimizing Mean Reversion parameters... This might take a while! 🌙")
optimization_results = bt.optimize(
    deviation_threshold=[i / 100 for i in range(8, 20, 2)],  # 8% to 18% deviation threshold (much higher)
    lookback_confirm=range(3, 8, 1),                         # 3 to 7 confirmation periods
    take_profit=[i / 100 for i in range(4, 10, 1)],         # 4% to 9% TP (more conservative)
    stop_loss=[i / 100 for i in range(2, 5, 1)],            # 2% to 4% SL (tighter)
    maximize='Equity Final [$]',
    constraint=lambda param: param.deviation_threshold > 0 and param.take_profit > param.stop_loss
)

print("🎉 Moon Dev's Mean Reversion optimization complete! Here are the results: 🚀")
print("🌙" * 60)
print(optimization_results)
print("🌙" * 60)

# Print the best optimized values with Moon Dev flair!
print("⭐ === MOON DEV'S OPTIMAL MEAN REVERSION PARAMETERS === ⭐")
print(f"🎯 Best Deviation Threshold: {optimization_results._strategy.deviation_threshold:.1%}")
print(f"🔄 Best Lookback Confirmation: {optimization_results._strategy.lookback_confirm}")
print(f"💰 Best Take Profit: {optimization_results._strategy.take_profit:.1%}")
print(f"🛡️ Best Stop Loss: {optimization_results._strategy.stop_loss:.1%}")
print("🚀 Moon Dev's IMPROVED Mean Reversion Sniper is ready to hunt! 🌙") 