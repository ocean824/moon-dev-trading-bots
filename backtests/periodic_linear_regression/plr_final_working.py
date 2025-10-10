"""
Periodic Linear Regression Strategy - FINAL WORKING VERSION
============================================================
Using proper cash allocation for Bitcoin trading and simplified logic.
Based on the TradingView indicator with linear regression and bands.
"""

import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy

print("🚀 Moon Dev's Periodic Linear Regression - FINAL VERSION 🌙")

# Load data
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
# Use last 2 years for faster testing
data = data[-17520:]  # 24*365*2 hours
print(f"✅ Data loaded! {len(data)} rows (2 years)")

class PeriodicLinearRegression(Strategy):
    # Parameters matching the TradingView indicator
    lookback = 20  # Regression period
    band_mult = 1.5  # Band multiplier

    def init(self):
        # Calculate linear regression
        self.linreg = self.I(talib.LINEARREG, self.data.Close, self.lookback)

        # Calculate slope for direction
        self.slope = self.I(talib.LINEARREG_SLOPE, self.data.Close, self.lookback)

        # Standard deviation for bands
        self.std = self.I(talib.STDDEV, self.data.Close, self.lookback)

        # Bands
        self.upper = self.I(lambda: self.linreg + self.band_mult * self.std)
        self.lower = self.I(lambda: self.linreg - self.band_mult * self.std)

        # RSI for momentum confirmation
        self.rsi = self.I(talib.RSI, self.data.Close, 14)

    def next(self):
        # Skip if not enough data
        if len(self.data) < max(self.lookback, 14) + 1:
            return

        # Current values
        price = self.data.Close[-1]
        prev_price = self.data.Close[-2]
        reg = self.linreg[-1]
        prev_reg = self.linreg[-2]
        slope = self.slope[-1]
        upper = self.upper[-1]
        lower = self.lower[-1]
        rsi = self.rsi[-1]

        # Skip if NaN
        if np.isnan(reg) or np.isnan(prev_reg) or np.isnan(rsi):
            return

        # Entry logic
        if not self.position:
            # Long signal: Price crosses above regression with positive slope
            if prev_price < prev_reg and price >= reg and slope > 0:
                # Buy with 95% of equity
                self.buy(size=0.95)

            # Short signal: Price crosses below regression with negative slope
            elif prev_price > prev_reg and price <= reg and slope < 0:
                # Sell with 95% of equity
                self.sell(size=0.95)

        # Exit logic
        else:
            if self.position.is_long:
                # Exit long on:
                # 1. Price hits upper band (take profit)
                # 2. Price crosses below regression (stop loss)
                # 3. RSI overbought
                if price >= upper or (price < reg and slope < 0) or rsi > 75:
                    self.position.close()

            elif self.position.is_short:
                # Exit short on:
                # 1. Price hits lower band (take profit)
                # 2. Price crosses above regression (stop loss)
                # 3. RSI oversold
                if price <= lower or (price > reg and slope > 0) or rsi < 25:
                    self.position.close()

# Run backtest with proper cash for Bitcoin
bt = Backtest(data, PeriodicLinearRegression, cash=1000000, commission=0.00045, margin=1/5)

print("\n🌙 ===== PERIODIC LINEAR REGRESSION RESULTS ===== 🌙")
print(f"Testing on 2 years of BTC hourly data")
print(f"Lookback: {PeriodicLinearRegression.lookback} | Band Mult: {PeriodicLinearRegression.band_mult}")
print("-" * 50)

stats = bt.run()

# Display key metrics
print(f"\n📊 KEY METRICS:")
print(f"Total Trades: {stats['# Trades']}")
if stats['# Trades'] > 0:
    print(f"Win Rate: {stats['Win Rate [%]']:.2f}%")
    print(f"Return: {stats['Return [%]']:.2f}%")
    print(f"Sharpe: {stats['Sharpe Ratio']:.2f}" if not np.isnan(stats['Sharpe Ratio']) else "Sharpe: N/A")
    print(f"Max Drawdown: {stats['Max. Drawdown [%]']:.2f}%")
    print(f"Exposure Time: {stats['Exposure Time [%]']:.2f}%")
    print(f"Buy & Hold Return: {stats['Buy & Hold Return [%]']:.2f}%")

    print("\n✅ TRADES GENERATED SUCCESSFULLY!")
    print("\n" + "="*60)
    print("FULL BACKTEST STATISTICS:")
    print("="*60)
    print(stats)
else:
    print("❌ No trades generated")

# Show plot without saving
bt.plot(resample=False)