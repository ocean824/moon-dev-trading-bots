"""
RSI Radar Multi Time Frame Strategy V2
=======================================
Enhanced RSI Radar strategy with more relaxed parameters
and better entry/exit conditions.

Moon Dev's Implementation 🌙
"""

import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's RSI Radar V2 Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class RSIRadarV2(Strategy):
    """
    RSI Radar V2 Strategy

    Uses 3 RSI periods to simulate multiple timeframes:
    - Fast RSI (9 period) - simulates 15min-1hr
    - Standard RSI (14 period) - simulates 1hr-4hr
    - Slow RSI (21 period) - simulates 4hr-daily

    Buy when at least 1 RSI is oversold and none are overbought
    Sell when at least 1 RSI is overbought and none are oversold
    """

    # Strategy parameters
    rsi_fast = 9
    rsi_standard = 14
    rsi_slow = 21
    rsi_oversold = 40
    rsi_overbought = 60
    take_profit = 0.03  # 3%
    stop_loss = 0.02    # 2%

    def init(self):
        # Calculate three RSI indicators
        self.rsi1 = self.I(talib.RSI, self.data.Close, self.rsi_fast)
        self.rsi2 = self.I(talib.RSI, self.data.Close, self.rsi_standard)
        self.rsi3 = self.I(talib.RSI, self.data.Close, self.rsi_slow)

        print(f"✨ RSI Radar initialized with periods: {self.rsi_fast}, {self.rsi_standard}, {self.rsi_slow}")

    def next(self):
        # Skip if we don't have enough data
        if len(self.data) < 30:
            return

        price = self.data.Close[-1]

        # Get current RSI values
        rsi_values = []
        for rsi in [self.rsi1[-1], self.rsi2[-1], self.rsi3[-1]]:
            if not np.isnan(rsi):
                rsi_values.append(rsi)

        if len(rsi_values) < 3:
            return

        # Calculate conditions
        oversold_count = sum(1 for r in rsi_values if r < self.rsi_oversold)
        overbought_count = sum(1 for r in rsi_values if r > self.rsi_overbought)
        avg_rsi = np.mean(rsi_values)

        # Trading logic - more relaxed conditions
        if not self.position:
            # Long entry: At least one RSI oversold and average RSI below 50
            if oversold_count >= 1 and avg_rsi < 50 and overbought_count == 0:
                sl = price * (1 - self.stop_loss)
                tp = price * (1 + self.take_profit)
                self.buy(sl=sl, tp=tp, size=1000000)

            # Short entry: At least one RSI overbought and average RSI above 50
            elif overbought_count >= 1 and avg_rsi > 50 and oversold_count == 0:
                sl = price * (1 + self.stop_loss)
                tp = price * (1 - self.take_profit)
                self.sell(sl=sl, tp=tp, size=1000000)

        # Exit conditions
        elif self.position.is_long:
            # Exit long if any RSI becomes overbought
            if overbought_count >= 1 or avg_rsi > 70:
                self.position.close()

        elif self.position.is_short:
            # Exit short if any RSI becomes oversold
            if oversold_count >= 1 or avg_rsi < 30:
                self.position.close()

# Run backtest
bt = Backtest(data, RSIRadarV2, cash=1000000, commission=0.00045)

print("\n🌙 ===== RSI RADAR V2 - RUNNING BACKTEST ===== 🌙")
stats = bt.run()
print(stats)

# Optimization
print("\n🚀 Optimizing RSI Radar V2...")
optimization = bt.optimize(
    rsi_fast=range(7, 12, 2),
    rsi_standard=range(12, 18, 2),
    rsi_slow=range(18, 26, 3),
    rsi_oversold=range(30, 45, 5),
    rsi_overbought=range(55, 70, 5),
    maximize='Sortino Ratio',
    max_tries=200
)

print("\n🏆 OPTIMIZATION RESULTS:")
print(optimization)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING RSI RADAR V2 ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(RSIRadarV2, 'RSIRadar_V2')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/RSIRadar_V2.csv")