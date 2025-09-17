"""
RSI Radar Multi Time Frame Optimized Strategy
==============================================
Final optimized implementation of the RSI Radar concept.
Uses relaxed thresholds for better signal generation.

Moon Dev's Implementation 🌙
"""

import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's RSI Radar Optimized Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class RSIRadarOptimized(Strategy):
    """
    RSI Radar Optimized Strategy

    Uses 3 RSI periods to detect convergence of oversold/overbought conditions:
    - Fast RSI (7): Captures quick moves
    - Standard RSI (14): Main signal
    - Slow RSI (21): Confirms trend

    Entry requires only 1 RSI to trigger but checks overall momentum.
    """

    # RSI periods
    rsi_fast = 7
    rsi_standard = 14
    rsi_slow = 21

    # Entry thresholds - relaxed for more signals
    rsi_oversold = 45
    rsi_overbought = 55

    # Risk management
    take_profit = 0.02
    stop_loss = 0.015

    def init(self):
        # Calculate RSI indicators
        self.rsi1 = self.I(talib.RSI, self.data.Close, self.rsi_fast)
        self.rsi2 = self.I(talib.RSI, self.data.Close, self.rsi_standard)
        self.rsi3 = self.I(talib.RSI, self.data.Close, self.rsi_slow)

    def next(self):
        # Skip early periods
        if len(self.data) < 30:
            return

        # Get RSI values
        fast = self.rsi1[-1]
        standard = self.rsi2[-1]
        slow = self.rsi3[-1]

        # Check valid values
        if np.isnan(fast) or np.isnan(standard) or np.isnan(slow):
            return

        price = self.data.Close[-1]

        # Entry logic - need any RSI to be extreme but check momentum
        if not self.position:
            # Long: Any RSI oversold AND momentum turning up
            if (fast < self.rsi_oversold or standard < self.rsi_oversold) and slow < 50:
                sl = price * (1 - self.stop_loss)
                tp = price * (1 + self.take_profit)
                self.buy(sl=sl, tp=tp, size=1000000)

            # Short: Any RSI overbought AND momentum turning down
            elif (fast > self.rsi_overbought or standard > self.rsi_overbought) and slow > 50:
                sl = price * (1 + self.stop_loss)
                tp = price * (1 - self.take_profit)
                self.sell(sl=sl, tp=tp, size=1000000)

# Run backtest
bt = Backtest(data, RSIRadarOptimized, cash=1000000, commission=0.00045)

print("\n🌙 ===== RSI RADAR OPTIMIZED - RESULTS ===== 🌙")
stats = bt.run()

# Print key metrics
print(f"\nKey Performance Metrics:")
print(f"Return: {stats['Return [%]']:.2f}%")
print(f"Buy & Hold: {stats['Buy & Hold Return [%]']:.2f}%")
print(f"Sharpe Ratio: {stats['Sharpe Ratio']:.3f}" if not np.isnan(stats['Sharpe Ratio']) else "Sharpe Ratio: N/A")
print(f"Sortino Ratio: {stats['Sortino Ratio']:.3f}" if not np.isnan(stats['Sortino Ratio']) else "Sortino Ratio: N/A")
print(f"Max Drawdown: {stats['Max. Drawdown [%]']:.2f}%")
print(f"Number of Trades: {stats['# Trades']}")
print(f"Win Rate: {stats['Win Rate [%]']:.1f}%" if not np.isnan(stats['Win Rate [%]']) else "Win Rate: N/A")
print(f"Profit Factor: {stats['Profit Factor']:.2f}" if not np.isnan(stats['Profit Factor']) else "Profit Factor: N/A")

print("\nFull Statistics:")
print(stats)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING RSI RADAR OPTIMIZED ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(RSIRadarOptimized, 'RSIRadar_Optimized')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/RSIRadar_Optimized.csv")