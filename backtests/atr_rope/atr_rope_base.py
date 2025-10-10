"""
ATR Rope Base Strategy
======================
Implements ATR-based rope smoothing for trend identification and trading.

The rope smoothing algorithm creates a smooth price line that only moves when
price exceeds an ATR threshold, similar to how a rope stabilizes movement.

Key Components:
- Rope Smoother: Tracks price with ATR threshold
- Direction Detection: Bullish (1), Bearish (-1), Flat (0)
- Consolidation Ranges: Identifies when rope is flat
- Entry on breakouts or trend changes
- ATR-based stops
"""

import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy

print("🚀 Moon Dev's ATR Rope Base Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
ATR_PERIOD = 14
ATR_MULTIPLIER = 0.5  # Lower for more frequent updates
ROPE_SMOOTH_PERIOD = 3  # Smoothing for rope calculation
TAKE_PROFIT_ATR_MULT = 2.0  # Take profit at 2x ATR
STOP_LOSS_ATR_MULT = 1.0  # Stop loss at 1x ATR

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class ATRRopeBase(Strategy):
    # Strategy parameters
    atr_period = ATR_PERIOD
    atr_multiplier = ATR_MULTIPLIER
    rope_smooth = ROPE_SMOOTH_PERIOD
    tp_atr = TAKE_PROFIT_ATR_MULT
    sl_atr = STOP_LOSS_ATR_MULT

    def init(self):
        """Initialize indicators and rope calculations"""
        # ATR for volatility measurement
        self.atr = self.I(talib.ATR, self.data.High, self.data.Low, self.data.Close, self.atr_period)

        # Calculate rope smoother (custom implementation)
        close_prices = self.data.Close
        close_array = np.array(close_prices)

        # Initialize rope array
        rope = np.zeros(len(close_array))
        direction = np.zeros(len(close_array))  # 1=up, -1=down, 0=flat

        # Start with first valid price
        rope[0] = close_array[0]

        # Calculate rope smoothing
        for i in range(1, len(close_array)):
            if i < self.atr_period:
                # Not enough data for ATR, just track price
                rope[i] = close_array[i]
                direction[i] = 1 if close_array[i] > close_array[i-1] else -1
            else:
                # Get current ATR value
                atr_val = self.atr[i]
                if pd.isna(atr_val) or atr_val == 0:
                    rope[i] = rope[i-1]
                    direction[i] = direction[i-1]
                    continue

                # Calculate ATR threshold for movement
                threshold = atr_val * self.atr_multiplier

                # Calculate price change from rope
                price_change = close_array[i] - rope[i-1]

                # Update rope based on threshold
                if abs(price_change) > threshold:
                    # Price moved beyond threshold - update rope
                    if price_change > 0:
                        # Upward movement
                        rope[i] = rope[i-1] + (price_change - threshold)
                        direction[i] = 1
                    else:
                        # Downward movement
                        rope[i] = rope[i-1] + (price_change + threshold)
                        direction[i] = -1
                else:
                    # Price within threshold - rope stays flat (consolidation)
                    rope[i] = rope[i-1]
                    direction[i] = 0  # Flat/consolidating

        # Apply smoothing to rope using numpy
        rope_smoothed = pd.Series(rope).rolling(window=self.rope_smooth, min_periods=1).mean().values

        # Store as indicators
        self.rope = self.I(lambda: rope_smoothed)
        self.direction = self.I(lambda: direction)

        # Calculate upper and lower ATR channels
        self.upper_band = self.I(lambda: self.rope + self.atr * self.atr_multiplier)
        self.lower_band = self.I(lambda: self.rope - self.atr * self.atr_multiplier)

        # Track consolidation ranges
        self.in_consolidation = self.I(lambda: direction == 0)

    def next(self):
        """Execute trading logic based on rope direction and consolidation breakouts"""
        # Skip if not enough data
        if len(self.data) < self.atr_period + self.rope_smooth + 2:
            return

        # Get current values
        current_price = self.data.Close[-1]
        current_rope = self.rope[-1]
        prev_rope = self.rope[-2]
        current_direction = self.direction[-1]
        prev_direction = self.direction[-2]
        current_atr = self.atr[-1]

        # Skip if ATR is invalid
        if pd.isna(current_atr) or current_atr <= 0:
            return

        # Calculate rope trend (simpler approach)
        rope_rising = current_rope > prev_rope
        rope_falling = current_rope < prev_rope

        if not self.position:
            # Entry logic - simplified for better signal generation

            # 1. Direction change signals (most reliable)
            if prev_direction != current_direction and current_direction != 0:
                if current_direction == 1:  # Turned bullish
                    sl_price = current_price - (current_atr * self.sl_atr)
                    tp_price = current_price + (current_atr * self.tp_atr)
                    self.buy(sl=sl_price, tp=tp_price, size=1000000)

                elif current_direction == -1:  # Turned bearish
                    sl_price = current_price + (current_atr * self.sl_atr)
                    tp_price = current_price - (current_atr * self.tp_atr)
                    self.sell(sl=sl_price, tp=tp_price, size=1000000)

            # 2. Rope trend following
            elif rope_rising and current_price > current_rope:
                # Bullish trend confirmed
                sl_price = current_rope - (current_atr * self.sl_atr)
                tp_price = current_price + (current_atr * self.tp_atr)
                self.buy(sl=sl_price, tp=tp_price, size=1000000)

            elif rope_falling and current_price < current_rope:
                # Bearish trend confirmed
                sl_price = current_rope + (current_atr * self.sl_atr)
                tp_price = current_price - (current_atr * self.tp_atr)
                self.sell(sl=sl_price, tp=tp_price, size=1000000)

            # 3. Breakout signals
            # Check for consolidation breakout (direction was 0, now it's not)
            if prev_direction == 0 and current_direction != 0:
                if current_direction == 1:  # Bullish breakout
                    sl_price = current_price - (current_atr * self.sl_atr)
                    tp_price = current_price + (current_atr * self.tp_atr)
                    self.buy(sl=sl_price, tp=tp_price, size=1000000)

                elif current_direction == -1:  # Bearish breakout
                    sl_price = current_price + (current_atr * self.sl_atr)
                    tp_price = current_price - (current_atr * self.tp_atr)
                    self.sell(sl=sl_price, tp=tp_price, size=1000000)

        else:
            # Exit logic - simplified

            if self.position.is_long:
                # Exit if rope turns bearish or price breaks below rope significantly
                if current_direction == -1 or (current_price < current_rope - current_atr):
                    self.position.close()

            elif self.position.is_short:
                # Exit if rope turns bullish or price breaks above rope significantly
                if current_direction == 1 or (current_price > current_rope + current_atr):
                    self.position.close()

# Run single backtest (default behavior)
bt = Backtest(data, ATRRopeBase, cash=1000000, commission=0.00045)

print("\n🌙 ===== ATR ROPE BASE - DEFAULT PARAMETERS ===== 🌙")
print(f"ATR Period: {ATR_PERIOD}")
print(f"ATR Multiplier: {ATR_MULTIPLIER}")
print(f"Rope Smoothing: {ROPE_SMOOTH_PERIOD}")
print(f"Take Profit ATR: {TAKE_PROFIT_ATR_MULT}")
print(f"Stop Loss ATR: {STOP_LOSS_ATR_MULT}")

stats_default = bt.run()
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING ATR ROPE BASE ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from backtests.multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(ATRRopeBase, 'ATRRopeBase')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/ATRRopeBase.csv")