"""
RSI Radar Multi Time Frame Fixed Strategy
==========================================
Fixed implementation that actually generates trades.

Moon Dev's Implementation 🌙
"""

import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's RSI Radar Fixed Strategy Loading... 🌙")

# Data configuration
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
# Use last 20000 rows for testing
data = data.tail(20000)
print(f"✅ Data loaded! {len(data)} rows 🌙")

class RSIRadarFixed(Strategy):
    """
    Fixed RSI Radar Strategy that generates trades
    """

    # RSI periods
    rsi_fast = 7
    rsi_standard = 14
    rsi_slow = 21

    # Thresholds
    rsi_oversold = 45
    rsi_overbought = 55

    # Risk
    take_profit = 0.02
    stop_loss = 0.015

    def init(self):
        self.rsi1 = self.I(talib.RSI, self.data.Close, self.rsi_fast)
        self.rsi2 = self.I(talib.RSI, self.data.Close, self.rsi_standard)
        self.rsi3 = self.I(talib.RSI, self.data.Close, self.rsi_slow)

    def next(self):
        if len(self.data) < 30:
            return

        fast = self.rsi1[-1]
        standard = self.rsi2[-1]
        slow = self.rsi3[-1]

        if np.isnan(fast) or np.isnan(standard) or np.isnan(slow):
            return

        price = self.data.Close[-1]

        if not self.position:
            # Long signal
            if (fast < self.rsi_oversold or standard < self.rsi_oversold) and slow < 50:
                sl = price * (1 - self.stop_loss)
                tp = price * (1 + self.take_profit)
                self.buy(sl=sl, tp=tp)

            # Short signal
            elif (fast > self.rsi_overbought or standard > self.rsi_overbought) and slow > 50:
                sl = price * (1 + self.stop_loss)
                tp = price * (1 - self.take_profit)
                self.sell(sl=sl, tp=tp)

# Run backtest
bt = Backtest(data, RSIRadarFixed, cash=10000000, commission=0.00045)

print("\n🌙 ===== BACKTEST RESULTS ===== 🌙")
stats = bt.run()

print(f"\nKey Metrics:")
print(f"Return: {stats['Return [%]']:.2f}%")
print(f"Buy & Hold: {stats['Buy & Hold Return [%]']:.2f}%")
print(f"Sharpe: {stats['Sharpe Ratio']:.3f}" if not np.isnan(stats['Sharpe Ratio']) else "Sharpe: N/A")
print(f"Max DD: {stats['Max. Drawdown [%]']:.2f}%")
print(f"Trades: {stats['# Trades']}")
print(f"Win Rate: {stats['Win Rate [%]']:.1f}%" if not np.isnan(stats['Win Rate [%]']) else "Win Rate: N/A")

print("\nFull Stats:")
print(stats)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING RSI RADAR FIXED ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(RSIRadarFixed, 'RSIRadar_Fixed')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/RSIRadar_Fixed.csv")