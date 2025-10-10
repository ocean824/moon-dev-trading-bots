"""
Supertrend Multi-Timeframe Strategy
===================================
Supertrend indicator with multiple timeframe confirmation.

Features:
- Primary Supertrend on current timeframe
- Secondary Supertrend with longer period for higher timeframe confirmation
- Enter only when both timeframes align
- Exit on either timeframe reversal
"""

import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy

print("🚀 Moon Dev's Supertrend Multi-Timeframe Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
ATR_PERIOD_FAST = 10  # Lower timeframe
ATR_MULTIPLIER_FAST = 3.0
ATR_PERIOD_SLOW = 20  # Higher timeframe equivalent
ATR_MULTIPLIER_SLOW = 3.5
TAKE_PROFIT_PERCENT = 6.0
STOP_LOSS_PERCENT = 3.0

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class SupertrendMTF(Strategy):
    # Strategy parameters
    atr_period_fast = ATR_PERIOD_FAST
    atr_multiplier_fast = ATR_MULTIPLIER_FAST
    atr_period_slow = ATR_PERIOD_SLOW
    atr_multiplier_slow = ATR_MULTIPLIER_SLOW
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100

    def calculate_supertrend(self, atr_period, atr_multiplier):
        """Helper function to calculate Supertrend"""
        # Calculate ATR
        atr = talib.ATR(self.data.High, self.data.Low, self.data.Close, atr_period)

        # Calculate HL2
        hl2 = (self.data.High + self.data.Low) / 2

        # Initialize arrays
        basic_upper = hl2 + (atr_multiplier * atr)  # Upper band (resistance)
        basic_lower = hl2 - (atr_multiplier * atr)  # Lower band (support)

        final_upper = np.zeros(len(self.data))
        final_lower = np.zeros(len(self.data))
        supertrend = np.zeros(len(self.data))
        direction = np.zeros(len(self.data))

        # Initialize first values
        if atr_period < len(self.data):
            final_upper[atr_period] = basic_upper[atr_period]
            final_lower[atr_period] = basic_lower[atr_period]

        # Calculate Supertrend
        for i in range(atr_period + 1, len(self.data)):
            # Current basic bands
            curr_basic_upper = basic_upper[i]
            curr_basic_lower = basic_lower[i]

            # Upper band logic (resistance)
            if curr_basic_upper < final_upper[i-1] or self.data.Close[i-1] > final_upper[i-1]:
                final_upper[i] = curr_basic_upper
            else:
                final_upper[i] = final_upper[i-1]

            # Lower band logic (support)
            if curr_basic_lower > final_lower[i-1] or self.data.Close[i-1] < final_lower[i-1]:
                final_lower[i] = curr_basic_lower
            else:
                final_lower[i] = final_lower[i-1]

            # Determine trend direction
            if i == atr_period + 1:
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

            # Set supertrend value
            if direction[i] == -1:
                supertrend[i] = final_upper[i]
            else:
                supertrend[i] = final_lower[i]

        return supertrend, direction

    def init(self):
        # Calculate fast Supertrend (lower timeframe)
        supertrend_fast, direction_fast = self.calculate_supertrend(
            self.atr_period_fast, self.atr_multiplier_fast
        )
        self.supertrend_fast = self.I(lambda: supertrend_fast)
        self.direction_fast = self.I(lambda: direction_fast)

        # Calculate slow Supertrend (higher timeframe)
        supertrend_slow, direction_slow = self.calculate_supertrend(
            self.atr_period_slow, self.atr_multiplier_slow
        )
        self.supertrend_slow = self.I(lambda: supertrend_slow)
        self.direction_slow = self.I(lambda: direction_slow)

    def next(self):
        # Skip if we don't have enough data
        if len(self.data) < max(self.atr_period_fast, self.atr_period_slow) + 2:
            return

        # Get current and previous directions for both timeframes
        curr_dir_fast = self.direction_fast[-1]
        prev_dir_fast = self.direction_fast[-2] if len(self.direction_fast) > 1 else 0

        curr_dir_slow = self.direction_slow[-1]
        prev_dir_slow = self.direction_slow[-2] if len(self.direction_slow) > 1 else 0

        # Skip if no valid direction
        if curr_dir_fast == 0 or prev_dir_fast == 0 or curr_dir_slow == 0:
            return

        # Check for direction changes
        if not self.position:
            # Buy signal: Both timeframes turn bullish
            fast_bullish = prev_dir_fast == -1 and curr_dir_fast == 1
            slow_bullish = curr_dir_slow == 1  # Higher TF should already be bullish

            if fast_bullish and slow_bullish:
                current_price = self.data.Close[-1]
                sl_price = current_price * (1 - self.stop_loss)
                tp_price = current_price * (1 + self.take_profit)
                self.buy()

        else:
            # Sell signal: Either timeframe turns bearish
            if curr_dir_fast == -1 or curr_dir_slow == -1:
                self.position.close()

# Run single backtest (default behavior)
bt = Backtest(data, SupertrendMTF, cash=10000000, commission=0.00045)

print("\n🌙 ===== SUPERTREND MULTI-TIMEFRAME - DEFAULT PARAMETERS ===== 🌙")
print(f"Fast ATR Period: {ATR_PERIOD_FAST}")
print(f"Fast ATR Multiplier: {ATR_MULTIPLIER_FAST}")
print(f"Slow ATR Period: {ATR_PERIOD_SLOW}")
print(f"Slow ATR Multiplier: {ATR_MULTIPLIER_SLOW}")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")

stats_default = bt.run()
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING SUPERTREND MULTI-TIMEFRAME ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(SupertrendMTF, 'supertrend_mtf', cash=10000000)

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/supertrend_mtf_[timestamp].csv")