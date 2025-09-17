"""
Quick test of Bull vs Bear Sessions Base strategy on single dataset
"""

import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy

print("🚀 Quick Test - Bull vs Bear Sessions Base Strategy 🌙")

# Use smaller dataset for testing
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1d-100wks-data.csv'

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows")

class BullBearSessionsSimple(Strategy):
    """Simplified Bull vs Bear Sessions for testing"""

    # Strategy parameters
    lookback = 20
    volume_threshold = 0.6
    take_profit = 0.03
    stop_loss = 0.02

    def init(self):
        # Simple volume-based bull/bear indicator
        def calculate_bull_bear_ratio(close, open_, volume):
            """Calculate simple bull vs bear volume ratio"""
            n = len(close)
            bull_ratio = np.zeros(n)

            for i in range(self.lookback, n):
                period_close = close[i-self.lookback:i]
                period_open = open_[i-self.lookback:i]
                period_volume = volume[i-self.lookback:i]

                bull_volume = 0
                bear_volume = 0

                for j in range(len(period_close)):
                    if period_close[j] >= period_open[j]:
                        bull_volume += period_volume[j]
                    else:
                        bear_volume += period_volume[j]

                total_volume = bull_volume + bear_volume
                if total_volume > 0:
                    bull_ratio[i] = bull_volume / total_volume
                else:
                    bull_ratio[i] = 0.5

            return bull_ratio

        # Calculate bull/bear ratio
        bull_ratio = calculate_bull_bear_ratio(
            self.data.Close,
            self.data.Open,
            self.data.Volume
        )

        self.bull_ratio = self.I(lambda: bull_ratio, name="BullRatio")

        # Simple moving averages for trend
        self.sma_short = self.I(talib.SMA, self.data.Close, timeperiod=10)
        self.sma_long = self.I(talib.SMA, self.data.Close, timeperiod=30)

        # Volume moving average
        self.volume_ma = self.I(talib.SMA, self.data.Volume, timeperiod=20)

    def next(self):
        # Skip if not enough data
        if len(self.data) < 30:
            return

        # Get current values
        current_price = self.data.Close[-1]
        current_bull_ratio = self.bull_ratio[-1]
        current_volume = self.data.Volume[-1]

        # Check volume filter
        if current_volume < self.volume_ma[-1] * 0.5:
            return

        # Position management
        if not self.position:
            # Long entry: Strong bull ratio with uptrend
            if current_bull_ratio > self.volume_threshold and self.sma_short[-1] > self.sma_long[-1]:
                sl = current_price * (1 - self.stop_loss)
                tp = current_price * (1 + self.take_profit)
                self.buy(sl=sl, tp=tp)

            # Short entry: Strong bear ratio with downtrend
            elif current_bull_ratio < (1 - self.volume_threshold) and self.sma_short[-1] < self.sma_long[-1]:
                sl = current_price * (1 + self.stop_loss)
                tp = current_price * (1 - self.take_profit)
                self.sell(sl=sl, tp=tp)

# Run backtest
bt = Backtest(data, BullBearSessionsSimple, cash=1000000, commission=0.00045)

print("\n🌙 Running Simple Bull vs Bear Sessions Test...")
stats = bt.run()

print("\n📊 BACKTEST RESULTS:")
print(stats)

print("\n✅ Test completed successfully!")