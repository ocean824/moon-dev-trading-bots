"""
Periodic Linear Regression Strategy - OPTIMIZED VERSION
========================================================
Optimized parameters for better performance.
"""

import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy

print("🚀 Moon Dev's Periodic Linear Regression - OPTIMIZED 🌙")

# Load multiple data sources for testing
data_configs = [
    ('/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv', 'BTC-1h'),
    ('/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/ETHUSD-1h-250wks-data.csv', 'ETH-1h'),
    ('/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/SOLUSD-1h-250wks-data.csv', 'SOL-1h'),
]

class PeriodicLinearRegressionOptimized(Strategy):
    # Optimized parameters
    lookback = 50  # Longer lookback for smoother regression
    band_mult = 2.0  # Wider bands to reduce false signals
    rsi_period = 21  # Longer RSI for better momentum reading

    # Entry thresholds
    rsi_oversold = 35
    rsi_overbought = 65
    min_slope = 0.0001  # Minimum slope for trend confirmation

    def init(self):
        # Linear regression and components
        self.linreg = self.I(talib.LINEARREG, self.data.Close, self.lookback)
        self.slope = self.I(talib.LINEARREG_SLOPE, self.data.Close, self.lookback)
        self.angle = self.I(talib.LINEARREG_ANGLE, self.data.Close, self.lookback)

        # Bands
        self.std = self.I(talib.STDDEV, self.data.Close, self.lookback)
        self.upper = self.I(lambda: self.linreg + self.band_mult * self.std)
        self.lower = self.I(lambda: self.linreg - self.band_mult * self.std)

        # Momentum indicators
        self.rsi = self.I(talib.RSI, self.data.Close, self.rsi_period)
        self.macd = self.I(talib.MACD, self.data.Close, 12, 26, 9)[0]

        # Volume indicator
        self.volume_sma = self.I(talib.SMA, self.data.Volume, 20)

    def next(self):
        # Skip if not enough data
        if len(self.data) < self.lookback + 1:
            return

        # Current values
        price = self.data.Close[-1]
        reg = self.linreg[-1]
        slope = self.slope[-1]
        angle = self.angle[-1]
        upper = self.upper[-1]
        lower = self.lower[-1]
        rsi = self.rsi[-1]
        macd = self.macd[-1]
        volume = self.data.Volume[-1]
        avg_volume = self.volume_sma[-1]

        # Previous values for crossover detection
        prev_price = self.data.Close[-2]
        prev_reg = self.linreg[-2]
        prev_macd = self.macd[-2]

        # Skip if NaN
        if np.isnan(reg) or np.isnan(rsi) or np.isnan(macd):
            return

        # Position sizing based on volatility
        position_size = 0.95  # Use 95% of available equity

        # Entry logic
        if not self.position:
            # Long entry conditions:
            # 1. Price near lower band (value zone)
            # 2. Positive slope and angle
            # 3. RSI not overbought
            # 4. MACD turning positive
            # 5. Volume confirmation
            if (price > lower and price < reg and
                slope > self.min_slope and angle > 0 and
                rsi < self.rsi_overbought and rsi > self.rsi_oversold and
                macd > prev_macd and
                volume > avg_volume * 0.8):

                # Set dynamic stop loss and take profit
                stop_loss = lower * 0.98  # 2% below lower band
                take_profit = upper  # Target upper band

                self.buy(size=position_size, sl=stop_loss, tp=take_profit)

            # Short entry conditions:
            # 1. Price near upper band (resistance zone)
            # 2. Negative slope and angle
            # 3. RSI not oversold
            # 4. MACD turning negative
            # 5. Volume confirmation
            elif (price < upper and price > reg and
                  slope < -self.min_slope and angle < 0 and
                  rsi > self.rsi_oversold and rsi < self.rsi_overbought and
                  macd < prev_macd and
                  volume > avg_volume * 0.8):

                # Set dynamic stop loss and take profit
                stop_loss = upper * 1.02  # 2% above upper band
                take_profit = lower  # Target lower band

                self.sell(size=position_size, sl=stop_loss, tp=take_profit)

        # Dynamic exit conditions
        else:
            if self.position.is_long:
                # Exit long if:
                # 1. Strong bearish reversal
                # 2. RSI extremely overbought
                # 3. Price breaks below regression with momentum
                if (angle < -10 or rsi > 80 or
                    (price < reg and slope < -self.min_slope * 2)):
                    self.position.close()

            elif self.position.is_short:
                # Exit short if:
                # 1. Strong bullish reversal
                # 2. RSI extremely oversold
                # 3. Price breaks above regression with momentum
                if (angle > 10 or rsi < 20 or
                    (price > reg and slope > self.min_slope * 2)):
                    self.position.close()

# Test on multiple assets
results = {}

for data_path, name in data_configs:
    try:
        print(f"\n📊 Testing {name}...")

        # Load data
        data = pd.read_csv(data_path, parse_dates=['datetime'], index_col='datetime')
        data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        data = data.sort_index()
        data = data.dropna()

        # Use last 2 years for consistency
        data = data[-17520:] if len(data) > 17520 else data

        # Run backtest
        bt = Backtest(data, PeriodicLinearRegressionOptimized,
                     cash=1000000, commission=0.00045, margin=1/5)

        stats = bt.run()
        results[name] = stats

        # Display results
        print(f"Trades: {stats['# Trades']}")
        if stats['# Trades'] > 0:
            print(f"Win Rate: {stats['Win Rate [%]']:.2f}%")
            print(f"Return: {stats['Return [%]']:.2f}%")
            print(f"Sharpe: {stats['Sharpe Ratio']:.2f}" if not np.isnan(stats['Sharpe Ratio']) else "Sharpe: N/A")
            print(f"Max DD: {stats['Max. Drawdown [%]']:.2f}%")

    except Exception as e:
        print(f"Error testing {name}: {e}")
        continue

# Summary
print("\n" + "="*60)
print("SUMMARY OF RESULTS:")
print("="*60)

for name, stats in results.items():
    if stats['# Trades'] > 0:
        print(f"\n{name}:")
        print(f"  Trades: {stats['# Trades']}")
        print(f"  Return: {stats['Return [%]']:.2f}%")
        print(f"  Win Rate: {stats['Win Rate [%]']:.2f}%")
        print(f"  Sharpe: {stats['Sharpe Ratio']:.2f}" if not np.isnan(stats['Sharpe Ratio']) else "  Sharpe: N/A")