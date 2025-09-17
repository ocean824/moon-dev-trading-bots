"""
RSI Radar Simple Multi Time Frame Strategy
===========================================
Simplified version of the RSI Radar strategy for faster execution.
Uses RSI from multiple simulated timeframes to generate trading signals.

Moon Dev's Implementation 🌙
"""

import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's RSI Radar Simple Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class RSIRadarSimple(Strategy):
    """
    Simplified RSI Radar Strategy

    Uses 3 RSI periods to simulate multiple timeframes:
    - Fast RSI (7 period) - simulates shorter timeframe
    - Standard RSI (14 period) - current timeframe
    - Slow RSI (28 period) - simulates longer timeframe

    Buy when 2 out of 3 RSIs are oversold
    Sell when 2 out of 3 RSIs are overbought
    """

    # Strategy parameters
    rsi_fast_period = 7
    rsi_standard_period = 14
    rsi_slow_period = 28
    rsi_oversold = 35
    rsi_overbought = 65
    votes_required = 2
    take_profit = 0.025  # 2.5%
    stop_loss = 0.015    # 1.5%

    def init(self):
        # Calculate three RSI indicators
        self.rsi_fast = self.I(talib.RSI, self.data.Close, self.rsi_fast_period)
        self.rsi_standard = self.I(talib.RSI, self.data.Close, self.rsi_standard_period)
        self.rsi_slow = self.I(talib.RSI, self.data.Close, self.rsi_slow_period)

    def next(self):
        # Skip if we don't have enough data
        if len(self.data) < self.rsi_slow_period + 1:
            return

        price = self.data.Close[-1]

        # Count oversold and overbought votes
        oversold_votes = 0
        overbought_votes = 0

        # Check each RSI
        for rsi in [self.rsi_fast[-1], self.rsi_standard[-1], self.rsi_slow[-1]]:
            if not np.isnan(rsi):
                if rsi < self.rsi_oversold:
                    oversold_votes += 1
                elif rsi > self.rsi_overbought:
                    overbought_votes += 1

        # Trading logic
        if not self.position:
            # Long entry
            if oversold_votes >= self.votes_required:
                sl = price * (1 - self.stop_loss)
                tp = price * (1 + self.take_profit)
                self.buy(sl=sl, tp=tp, size=1000000)

            # Short entry
            elif overbought_votes >= self.votes_required:
                sl = price * (1 + self.stop_loss)
                tp = price * (1 - self.take_profit)
                self.sell(sl=sl, tp=tp, size=1000000)

# Run backtest
bt = Backtest(data, RSIRadarSimple, cash=1000000, commission=0.00045)

print("\n🌙 ===== RSI RADAR SIMPLE - RUNNING BACKTEST ===== 🌙")
stats = bt.run()
print(stats)

# Show visualization
try:
    bt.plot()
except:
    pass

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING RSI RADAR SIMPLE ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(RSIRadarSimple, 'RSIRadar_Simple')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/RSIRadar_Simple.csv")