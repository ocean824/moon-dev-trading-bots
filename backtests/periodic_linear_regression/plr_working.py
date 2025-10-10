"""
Periodic Linear Regression Strategy - WORKING VERSION
======================================================
Fixed version that generates trades using proper indicator logic.
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
from backtesting.lib import crossover

print("🚀 Moon Dev's Periodic Linear Regression - WORKING VERSION 🌙")

# Load data
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows")

def calculate_linear_regression(values, period):
    """Calculate linear regression line values"""
    result = np.full_like(values, np.nan)

    for i in range(period - 1, len(values)):
        y = values[i - period + 1:i + 1]
        x = np.arange(period)

        # Calculate regression coefficients
        x_mean = x.mean()
        y_mean = y.mean()

        numerator = ((x - x_mean) * (y - y_mean)).sum()
        denominator = ((x - x_mean) ** 2).sum()

        if denominator != 0:
            slope = numerator / denominator
            intercept = y_mean - slope * x_mean
            result[i] = slope * (period - 1) + intercept

    return result

def calculate_bands(values, regression, period, multiplier):
    """Calculate bands based on standard deviation from regression"""
    upper = np.full_like(values, np.nan)
    lower = np.full_like(values, np.nan)

    for i in range(period - 1, len(values)):
        y = values[i - period + 1:i + 1]
        reg_val = regression[i]

        if not np.isnan(reg_val):
            std = np.std(y)
            upper[i] = reg_val + (multiplier * std)
            lower[i] = reg_val - (multiplier * std)

    return upper, lower

class PeriodicLinearRegression(Strategy):
    # Parameters
    lookback_period = 20
    band_multiplier = 1.5

    def init(self):
        # Calculate linear regression
        close_values = self.data.Close
        self.regression = self.I(calculate_linear_regression, close_values, self.lookback_period)

        # Calculate bands
        upper, lower = calculate_bands(close_values, self.regression,
                                      self.lookback_period, self.band_multiplier)
        self.upper_band = self.I(lambda: upper)
        self.lower_band = self.I(lambda: lower)

    def next(self):
        # Skip if not enough data
        if len(self.data) < self.lookback_period + 1:
            return

        # Get current values
        price = self.data.Close[-1]
        regression = self.regression[-1]
        upper = self.upper_band[-1]
        lower = self.lower_band[-1]

        # Skip if NaN
        if np.isnan(regression):
            return

        # Trading logic
        if not self.position:
            # Long entry: price above regression and momentum up
            if crossover(self.data.Close, self.regression):
                self.buy(size=1000000)

            # Short entry: price below regression and momentum down
            elif crossover(self.regression, self.data.Close):
                self.sell(size=1000000)

        else:
            # Exit long positions
            if self.position.is_long:
                # Exit if price hits upper band or falls below regression
                if price >= upper or crossover(self.regression, self.data.Close):
                    self.position.close()

            # Exit short positions
            elif self.position.is_short:
                # Exit if price hits lower band or rises above regression
                if price <= lower or crossover(self.data.Close, self.regression):
                    self.position.close()

# Run backtest
bt = Backtest(data, PeriodicLinearRegression, cash=1000000, commission=0.00045)

print("\n🌙 ===== PERIODIC LINEAR REGRESSION - WORKING VERSION ===== 🌙")
print(f"Lookback Period: {PeriodicLinearRegression.lookback_period}")
print(f"Band Multiplier: {PeriodicLinearRegression.band_multiplier}")

stats = bt.run()
print(stats)

# Show plot
bt.plot()