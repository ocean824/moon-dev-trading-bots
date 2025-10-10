"""
Simplified Supertrend Strategy
===============================
Simplified implementation focusing on generating trades.
"""

import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy

print("🚀 Moon Dev's Simplified Supertrend Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Supertrend parameters
ATR_PERIOD = 10
ATR_MULTIPLIER = 1.5  # More sensitive

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class SupertrendSimple(Strategy):
    # Strategy parameters
    atr_period = ATR_PERIOD
    atr_multiplier = ATR_MULTIPLIER

    def init(self):
        # Calculate ATR
        self.atr = self.I(talib.ATR, self.data.High, self.data.Low, self.data.Close, self.atr_period)

        # Calculate HL2
        hl2 = (self.data.High + self.data.Low) / 2

        # Calculate basic bands
        upper_band = hl2 + (self.atr_multiplier * self.atr)
        lower_band = hl2 - (self.atr_multiplier * self.atr)

        # Simplified trend determination
        trend = np.zeros(len(self.data))
        for i in range(self.atr_period, len(self.data)):
            if self.data.Close[i] > upper_band[i]:
                trend[i] = 1  # Bullish
            elif self.data.Close[i] < lower_band[i]:
                trend[i] = -1  # Bearish
            else:
                trend[i] = trend[i-1] if i > 0 else 0

        self.trend = self.I(lambda: trend)
        self.upper = self.I(lambda: upper_band)
        self.lower = self.I(lambda: lower_band)

    def next(self):
        # Skip if we don't have enough data
        if len(self.data) < self.atr_period + 2:
            return

        curr_trend = self.trend[-1]
        prev_trend = self.trend[-2]

        # Entry and exit logic
        if not self.position:
            # Buy when trend turns bullish
            if prev_trend <= 0 and curr_trend == 1:
                self.buy()
        else:
            # Sell when trend turns bearish
            if curr_trend == -1:
                self.position.close()

# Run single backtest
bt = Backtest(data, SupertrendSimple, cash=10000000, commission=0.00045)

print("\n🌙 ===== SIMPLIFIED SUPERTREND - DEFAULT PARAMETERS ===== 🌙")
print(f"ATR Period: {ATR_PERIOD}")
print(f"ATR Multiplier: {ATR_MULTIPLIER}")

stats_default = bt.run()
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING SIMPLIFIED SUPERTREND ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(SupertrendSimple, 'supertrend_simple', cash=10000000)

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/supertrend_simple_[timestamp].csv")