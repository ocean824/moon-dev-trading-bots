"""
Supertrend Base Strategy
========================
Core implementation of the Supertrend indicator for trend-following trading.

The Supertrend indicator uses ATR to create dynamic support and resistance levels:
- Upper band = hl2 - (ATR * multiplier)
- Lower band = hl2 + (ATR * multiplier)
- Bands trail price action and only move in the direction of the trend
- Buy signal: Trend changes from bearish (-1) to bullish (1)
- Sell signal: Trend changes from bullish (1) to bearish (-1)
"""

import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy

print("🚀 Moon Dev's Supertrend Base Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Supertrend parameters
ATR_PERIOD = 10
ATR_MULTIPLIER = 2.0  # Reduced for more sensitivity
TAKE_PROFIT_PERCENT = 3.0  # Smaller targets
STOP_LOSS_PERCENT = 2.0  # Tighter stops

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class SupertrendBase(Strategy):
    # Strategy parameters
    atr_period = ATR_PERIOD
    atr_multiplier = ATR_MULTIPLIER
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100

    def init(self):
        # Calculate ATR
        self.atr = self.I(talib.ATR, self.data.High, self.data.Low, self.data.Close, self.atr_period)

        # Calculate HL2 (average of high and low)
        hl2 = (self.data.High + self.data.Low) / 2

        # Initialize arrays for bands and trend
        basic_upper = hl2 + (self.atr_multiplier * self.atr)  # Upper band (resistance)
        basic_lower = hl2 - (self.atr_multiplier * self.atr)  # Lower band (support)

        # Create arrays to hold the final bands
        final_upper = np.zeros(len(self.data))
        final_lower = np.zeros(len(self.data))
        supertrend = np.zeros(len(self.data))
        direction = np.zeros(len(self.data))

        # Initialize first values
        if self.atr_period < len(self.data):
            final_upper[self.atr_period] = basic_upper[self.atr_period]
            final_lower[self.atr_period] = basic_lower[self.atr_period]

        # Calculate Supertrend
        for i in range(self.atr_period + 1, len(self.data)):
            # Current basic bands
            curr_basic_upper = basic_upper[i]
            curr_basic_lower = basic_lower[i]

            # Upper band logic (resistance) - trails down in downtrend
            if curr_basic_upper < final_upper[i-1] or self.data.Close[i-1] > final_upper[i-1]:
                final_upper[i] = curr_basic_upper
            else:
                final_upper[i] = final_upper[i-1]

            # Lower band logic (support) - trails up in uptrend
            if curr_basic_lower > final_lower[i-1] or self.data.Close[i-1] < final_lower[i-1]:
                final_lower[i] = curr_basic_lower
            else:
                final_lower[i] = final_lower[i-1]

            # Determine current direction
            if i == self.atr_period + 1:
                if self.data.Close[i] <= final_upper[i]:
                    direction[i] = -1  # Bearish
                else:
                    direction[i] = 1   # Bullish
            else:
                # Previous trend was bearish
                if direction[i-1] == -1:
                    if self.data.Close[i] > final_upper[i]:
                        direction[i] = 1  # Switch to bullish
                    else:
                        direction[i] = -1  # Stay bearish
                # Previous trend was bullish
                else:
                    if self.data.Close[i] < final_lower[i]:
                        direction[i] = -1  # Switch to bearish
                    else:
                        direction[i] = 1  # Stay bullish

            # Set supertrend line based on direction
            if direction[i] == -1:
                supertrend[i] = final_upper[i]
            else:
                supertrend[i] = final_lower[i]

        # Store as indicators
        self.supertrend = self.I(lambda: supertrend)
        self.direction = self.I(lambda: direction)

    def next(self):
        # Skip if we don't have enough data
        if len(self.data) < self.atr_period + 2:
            return

        # Get current and previous direction
        curr_dir = self.direction[-1]
        prev_dir = self.direction[-2] if len(self.direction) > 1 else 0

        # Skip if no valid direction
        if curr_dir == 0 or prev_dir == 0:
            return

        # Check for direction change
        if not self.position:
            # Buy signal: trend changes from bearish to bullish
            if prev_dir == -1 and curr_dir == 1:
                self.buy()

        else:
            # Sell signal: trend changes from bullish to bearish
            if curr_dir == -1:  # Exit on any bearish signal
                self.position.close()

# Run single backtest (default behavior)
bt = Backtest(data, SupertrendBase, cash=10000000, commission=0.00045)

print("\n🌙 ===== SUPERTREND BASE - DEFAULT PARAMETERS ===== 🌙")
print(f"ATR Period: {ATR_PERIOD}")
print(f"ATR Multiplier: {ATR_MULTIPLIER}")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")

stats_default = bt.run()
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING SUPERTREND BASE ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(SupertrendBase, 'supertrend_base', cash=10000000)

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/supertrend_base_[timestamp].csv")