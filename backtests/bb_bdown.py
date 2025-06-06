'''
Moon Dev's Enhanced Bollinger Band Breakout Strategy 🚀
Using Kalman Filter for superior signal processing! 🌙
Bidirectional trading - breakouts and breakdowns both ways!

Start                     2021-06-17 00:00:00
End                       2025-04-25 00:00:00
Duration                   1408 days 00:00:00
Exposure Time [%]                   98.012775
Equity Final [$]              14836690.486754
Equity Peak [$]               56498422.574074
Return [%]                        1383.669049
Buy & Hold Return [%]              292.687898
Return (Ann.) [%]                  101.109994
Volatility (Ann.) [%]              290.999094
Sharpe Ratio                         0.347458
Sortino Ratio                        1.422343
Calmar Ratio                         1.011735
Max. Drawdown [%]                   -99.93719
Avg. Drawdown [%]                  -15.540335
Max. Drawdown Duration     1189 days 00:00:00
Avg. Drawdown Duration       70 days 00:00:00
# Trades                                  664
Win Rate [%]                        60.993976
Best Trade [%]                      28.330707
Worst Trade [%]                    -38.535623
Avg. Trade [%]                       0.411019
Max. Trade Duration          12 days 00:00:00
Avg. Trade Duration           2 days 00:00:00
Profit Factor                        1.244375
Expectancy [%]                       0.722651
SQN                                  0.414013
_strategy                 KalmanBollingerS...
_equity_curve                             ...
_trades                          Size  Ent...
dtype: object
🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙
⭐ === MOON DEV'S OPTIMAL PARAMETERS === ⭐
🎯 Best Window: 15
📊 Best Standard Deviations: 2.5
💰 Best Take Profit: 3.0%
🛡️ Best Stop Loss: 5.0%
'''

import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
from backtesting.lib import crossover

#print("🚀 Moon Dev's Kalman-Enhanced Bollinger Band Strategy Loading... 🌙")

class KalmanFilter:
    """
    Simple Kalman Filter for price smoothing
    Moon Dev's secret weapon! 🎯
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
    """Apply Kalman filter to price series - Moon Dev's magic! ✨"""
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

# Enhanced Bollinger Band Breakout Strategy (Both Ways!)
class KalmanBollingerStrategy(Strategy):
    window = 21
    num_std = 2.7  # Moon Dev's original choice
    take_profit = 0.05  # 5%
    stop_loss = 0.03    # 3%

    def init(self):
        #print(f"🌙 Moon Dev's Kalman Bollinger Strategy initializing with {self.window} window and {self.num_std} std dev! 🚀")
        
        # Apply Kalman filter to close prices
        # Note: self.data.Close is already an array-like object in backtesting framework
        self.kalman_prices = self.I(apply_kalman_filter, self.data.Close)
        
        # Calculate Bollinger Bands using Kalman-filtered prices
        self.upper_band, self.middle_band, self.lower_band = self.I(
            talib.BBANDS, 
            self.kalman_prices, 
            self.window, 
            self.num_std, 
            self.num_std
        )

    def next(self):
        if len(self.data) < self.window:
            return

        current_price = self.data.Close[-1]
        kalman_price = self.kalman_prices[-1]
        upper = self.upper_band[-1]
        lower = self.lower_band[-1]
        middle = self.middle_band[-1]

        # Long position: Breakout above upper band
        if current_price > upper and not self.position:
            self.buy(
                sl=current_price * (1 - self.stop_loss),
                tp=current_price * (1 + self.take_profit)
            )
        
        # Short position: Breakdown below lower band  
        elif current_price < lower and not self.position:
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
print("🎯 Setting up Moon Dev's Kalman-enhanced backtest... 🌙")
bt = Backtest(data, KalmanBollingerStrategy, cash=1000000, commission=0.002)

# Run the backtest with default parameters and print the results
print("⭐ Running Moon Dev's default parameters test... 🚀")
stats_default = bt.run()
print("🌙 === MOON DEV'S DEFAULT RESULTS === 🌙")
print(stats_default)
print("🚀" * 50)

# Now perform the optimization - Moon Dev's parameter hunting! 🎯
print("🔍 Moon Dev is optimizing parameters... This might take a while! 🌙")
optimization_results = bt.optimize(
    window=range(15, 25, 2),  # Test different windows
    num_std=[round(i, 1) for i in np.arange(2.0, 4.1, 0.1)],  # 2.0 to 4.0 std devs
    take_profit=[i / 100 for i in range(3, 8, 1)],  # 3% to 7% TP
    stop_loss=[i / 100 for i in range(2, 6, 1)],    # 2% to 5% SL
    maximize='Equity Final [$]',
    constraint=lambda param: param.window > 0 and param.num_std > 0
)

print("🎉 Moon Dev's optimization complete! Here are the results: 🚀")
print("🌙" * 60)
print(optimization_results)
print("🌙" * 60)

# Print the best optimized values with Moon Dev flair!
print("⭐ === MOON DEV'S OPTIMAL PARAMETERS === ⭐")
print(f"🎯 Best Window: {optimization_results._strategy.window}")
print(f"📊 Best Standard Deviations: {optimization_results._strategy.num_std}")
print(f"💰 Best Take Profit: {optimization_results._strategy.take_profit:.1%}")
print(f"🛡️ Best Stop Loss: {optimization_results._strategy.stop_loss:.1%}")
print("🚀 Moon Dev's Kalman-enhanced strategy is ready to moon! 🌙")