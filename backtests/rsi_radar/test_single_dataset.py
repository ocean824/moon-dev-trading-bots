"""
Test RSI Radar on a single dataset for quick validation
"""

import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
import warnings
warnings.filterwarnings('ignore')

print("🚀 Testing RSI Radar Strategy on single dataset...")

# Load smaller dataset for faster testing
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1d-100wks-data.csv'

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows")

class RSIRadar(Strategy):
    """Simplified RSI Radar for testing"""

    # RSI periods to simulate different timeframes
    rsi_fast = 7
    rsi_standard = 14
    rsi_slow = 28

    # Trading thresholds
    rsi_oversold = 35
    rsi_overbought = 65

    # Risk management
    take_profit = 0.03
    stop_loss = 0.02

    def init(self):
        # Calculate RSI indicators
        self.rsi1 = self.I(talib.RSI, self.data.Close, self.rsi_fast)
        self.rsi2 = self.I(talib.RSI, self.data.Close, self.rsi_standard)
        self.rsi3 = self.I(talib.RSI, self.data.Close, self.rsi_slow)

    def next(self):
        if len(self.data) < 30:
            return

        # Get RSI values
        rsi_vals = [self.rsi1[-1], self.rsi2[-1], self.rsi3[-1]]

        # Check for NaN
        if any(np.isnan(v) for v in rsi_vals):
            return

        # Count signals
        oversold = sum(1 for r in rsi_vals if r < self.rsi_oversold)
        overbought = sum(1 for r in rsi_vals if r > self.rsi_overbought)

        price = self.data.Close[-1]

        # Trading logic
        if not self.position:
            if oversold >= 2:  # At least 2 RSIs oversold
                sl = price * (1 - self.stop_loss)
                tp = price * (1 + self.take_profit)
                self.buy(sl=sl, tp=tp, size=1000000)
            elif overbought >= 2:  # At least 2 RSIs overbought
                sl = price * (1 + self.stop_loss)
                tp = price * (1 - self.take_profit)
                self.sell(sl=sl, tp=tp, size=1000000)

# Run backtest
bt = Backtest(data, RSIRadar, cash=1000000, commission=0.00045)

print("\n🌙 ===== BACKTEST RESULTS ===== 🌙")
stats = bt.run()

# Print key metrics
print(f"\nKey Metrics:")
print(f"Return: {stats['Return [%]']:.2f}%")
print(f"Buy & Hold: {stats['Buy & Hold Return [%]']:.2f}%")
print(f"Sharpe Ratio: {stats['Sharpe Ratio']:.3f}" if not np.isnan(stats['Sharpe Ratio']) else "Sharpe Ratio: N/A")
print(f"Max Drawdown: {stats['Max. Drawdown [%]']:.2f}%")
print(f"Number of Trades: {stats['# Trades']}")
print(f"Win Rate: {stats['Win Rate [%]']:.1f}%" if not np.isnan(stats['Win Rate [%]']) else "Win Rate: N/A")
print(f"Profit Factor: {stats['Profit Factor']:.2f}" if not np.isnan(stats['Profit Factor']) else "Profit Factor: N/A")

print("\nFull Stats:")
print(stats)