"""
🌙 Moon Dev's SMA + Kalman Filter Strategy 🌙
==============================================
SMA crossover with Kalman filter for smoothing and trend confirmation.
Kalman filter reduces noise and provides better signal quality.

Strategy Rules:
- LONG: Fast SMA crosses above slow SMA AND Kalman trend is UP
- SHORT: Fast SMA crosses below slow SMA AND Kalman trend is DOWN
- Kalman trend = Kalman filtered price > its own MA
- Exit on opposite signal or TP/SL

The Kalman filter is like a smart smoothing algorithm that adapts to market conditions!

4HOUR POST  MAY HOUSE
                                                                                                                                 
✨ OPTIMIZED RESULTS ✨
============================================================
Start                     2025-05-01 00:00:00
End                       2025-09-07 04:00:00
Duration                    129 days 04:00:00
Exposure Time [%]                    4.896907
Equity Final [$]                 14069.243001
Equity Peak [$]                  14069.243001
Return [%]                           40.69243
Buy & Hold Return [%]              -84.964778
Return (Ann.) [%]                  160.794597
Volatility (Ann.) [%]               76.594191
Sharpe Ratio                         2.099305
Sortino Ratio                        8.237583
Calmar Ratio                        28.401994
Max. Drawdown [%]                   -5.661384
Avg. Drawdown [%]                   -4.516202
Max. Drawdown Duration       17 days 04:00:00
Avg. Drawdown Duration        8 days 03:00:00
# Trades                                   27
Win Rate [%]                        81.481481
Best Trade [%]                       2.805611
Worst Trade [%]                     -5.189621
Avg. Trade [%]                       1.272496
Max. Trade Duration           0 days 12:00:00
Avg. Trade Duration           0 days 02:00:00
Profit Factor                        2.375274
Expectancy [%]                       1.321694
SQN                                  2.040774
_strategy                 SMAwithKalmanStr...
_equity_curve                             ...
_trades                          Size  Ent...
dtype: object

🎯 BEST PARAMETERS FOUND:
============================================================
Fast SMA: 15
Slow SMA: 20
Kalman Process Variance: 0.1
Kalman Measurement Variance: 0.01
Kalman MA Period: 5
Take Profit: 3.0%
Stop Loss: 5.0%
"""

import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
from backtesting.lib import crossover
import matplotlib.pyplot as plt

# Four data sources ready to swap - pick one!
# 4H timeframe data:
#data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/HYPE_4h_20251020_130820_historical.csv'
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/birdeye/DitHyRMQiSDhn5cnKMJV2CDDt6sVct96YrECiM49pump-4H-300days-data.csv'

# 1D timeframe data:
#data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/HYPE_1d_20251020_140859_historical.csv'
#data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/birdeye/DitHyRMQiSDhn5cnKMJV2CDDt6sVct96YrECiM49pump-1D-300days-data.csv'

# Load data
data = pd.read_csv(data_path)

# Standardize column names
if 'timestamp' in data.columns:
    data = data.rename(columns={'timestamp': 'datetime'})
if 'date' in data.columns:
    data = data.rename(columns={'date': 'datetime'})

# Parse datetime and set as index
data['datetime'] = pd.to_datetime(data['datetime'])
data = data.set_index('datetime')

# Ensure we have the right column names
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Sort index
data = data.sort_index(ascending=True)

def kalman_filter(prices, process_variance=0.01, measurement_variance=0.1):
    """
    Apply Kalman filter to price series
    Lower process_variance = smoother output
    Higher measurement_variance = less trust in raw data
    """
    n = len(prices)
    filtered = np.zeros(n)

    # Initial estimates
    x_hat = prices[0]  # Initial state estimate
    P = 1.0  # Initial estimation error covariance

    for i in range(n):
        # Prediction step
        x_hat_minus = x_hat
        P_minus = P + process_variance

        # Update step
        K = P_minus / (P_minus + measurement_variance)  # Kalman gain
        x_hat = x_hat_minus + K * (prices[i] - x_hat_minus)
        P = (1 - K) * P_minus

        filtered[i] = x_hat

    return filtered

class SMAwithKalmanStrategy(Strategy):
    # Parameters to optimize
    sma_fast = 10  # Fast moving average
    sma_slow = 30  # Slow moving average
    kalman_process_var = 0.01  # Kalman filter process variance
    kalman_measure_var = 0.1   # Kalman filter measurement variance
    kalman_ma = 10  # MA period for Kalman trend
    take_profit = 0.03  # 3% take profit
    stop_loss = 0.05    # 5% stop loss

    def init(self):
        # Calculate Simple Moving Averages
        self.fast_sma = self.I(talib.SMA, self.data.Close, self.sma_fast)
        self.slow_sma = self.I(talib.SMA, self.data.Close, self.sma_slow)

        # Apply Kalman filter to closing prices
        kalman_prices = kalman_filter(
            np.array(self.data.Close),
            self.kalman_process_var,
            self.kalman_measure_var
        )
        self.kalman_filtered = self.I(lambda: kalman_prices, name='Kalman')

        # Calculate MA of Kalman filtered prices for trend
        self.kalman_ma_line = self.I(talib.SMA, self.kalman_filtered, self.kalman_ma)

    def next(self):
        price = self.data.Close[-1]

        # Skip if we don't have enough data
        if len(self.data) < max(self.sma_slow, self.kalman_ma):
            return

        # Determine Kalman trend
        kalman_trend_up = self.kalman_filtered[-1] > self.kalman_ma_line[-1]
        kalman_trend_down = self.kalman_filtered[-1] < self.kalman_ma_line[-1]

        # Check for crossovers with Kalman filter confirmation
        if crossover(self.fast_sma, self.slow_sma) and kalman_trend_up:
            # Golden cross with Kalman confirmation - go LONG
            if not self.position:
                self.buy(
                    sl=price * (1 - self.stop_loss),
                    tp=price * (1 + self.take_profit)
                )
            elif self.position.is_short:
                self.position.close()
                self.buy(
                    sl=price * (1 - self.stop_loss),
                    tp=price * (1 + self.take_profit)
                )

        elif crossover(self.slow_sma, self.fast_sma) and kalman_trend_down:
            # Death cross with Kalman confirmation - go SHORT
            if not self.position:
                self.sell(
                    sl=price * (1 + self.stop_loss),
                    tp=price * (1 - self.take_profit)
                )
            elif self.position.is_long:
                self.position.close()
                self.sell(
                    sl=price * (1 + self.stop_loss),
                    tp=price * (1 - self.take_profit)
                )

# Run backtest with initial parameters
bt = Backtest(data, SMAwithKalmanStrategy, cash=10000, commission=0.002)

print("\n" + "="*60)
print("🌙 SMA + KALMAN FILTER STRATEGY - INITIAL RESULTS 🌙")
print("="*60)
initial_stats = bt.run()
print(initial_stats)

# Show plot
try:
    bt.plot(filename=None, superimpose=False)  # Disable superimpose to avoid HYPE data issues
except Exception as e:
    print(f"⚠️ Could not display plot: {e}")
    print("Continuing without plot...")

# Optimize parameters
print("\n" + "="*60)
print("🚀 OPTIMIZING PARAMETERS...")
print("="*60)

optimization_results = bt.optimize(
    sma_fast=range(5, 25, 5),
    sma_slow=range(20, 50, 10),
    kalman_process_var=[0.001, 0.01, 0.1],
    kalman_measure_var=[0.01, 0.1, 0.5],
    kalman_ma=[5, 10, 15],
    take_profit=[0.02, 0.03, 0.04],
    stop_loss=[0.03, 0.04, 0.05],
    maximize='Sharpe Ratio',
    constraint=lambda p: p.sma_fast < p.sma_slow
)

print("\n✨ OPTIMIZED RESULTS ✨")
print("="*60)
print(optimization_results)

print("\n🎯 BEST PARAMETERS FOUND:")
print("="*60)
print(f"Fast SMA: {optimization_results._strategy.sma_fast}")
print(f"Slow SMA: {optimization_results._strategy.sma_slow}")
print(f"Kalman Process Variance: {optimization_results._strategy.kalman_process_var}")
print(f"Kalman Measurement Variance: {optimization_results._strategy.kalman_measure_var}")
print(f"Kalman MA Period: {optimization_results._strategy.kalman_ma}")
print(f"Take Profit: {optimization_results._strategy.take_profit:.1%}")
print(f"Stop Loss: {optimization_results._strategy.stop_loss:.1%}")

# Run with optimized parameters
optimized_stats = bt.run(
    sma_fast=optimization_results._strategy.sma_fast,
    sma_slow=optimization_results._strategy.sma_slow,
    kalman_process_var=optimization_results._strategy.kalman_process_var,
    kalman_measure_var=optimization_results._strategy.kalman_measure_var,
    kalman_ma=optimization_results._strategy.kalman_ma,
    take_profit=optimization_results._strategy.take_profit,
    stop_loss=optimization_results._strategy.stop_loss
)

# Show optimized plot
print("\n📊 Showing optimized strategy plot...")
try:
    bt.plot(filename=None, superimpose=False)  # Disable superimpose to avoid HYPE data issues
except Exception as e:
    print(f"⚠️ Could not display plot: {e}")
    print("Continuing without plot...")

print("\n🏁 SMA + KALMAN FILTER STRATEGY COMPLETE!")
print("Kalman filter provides adaptive smoothing for cleaner signals.")