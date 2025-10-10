"""
ATR Rope with RSI Strategy
==========================
Combines ATR Rope smoothing with RSI confirmation for improved entry signals.

Enhancements:
- Uses RSI to confirm trend strength
- Filters out weak signals in overbought/oversold zones
- Better timing for trend reversals
"""

import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy

print("🚀 Moon Dev's ATR Rope + RSI Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
ATR_PERIOD = 14
ATR_MULTIPLIER = 0.5
ROPE_SMOOTH_PERIOD = 3
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
RSI_NEUTRAL_HIGH = 60
RSI_NEUTRAL_LOW = 40
TAKE_PROFIT_ATR_MULT = 2.0
STOP_LOSS_ATR_MULT = 1.0

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class ATRRopeRSI(Strategy):
    # Strategy parameters
    atr_period = ATR_PERIOD
    atr_multiplier = ATR_MULTIPLIER
    rope_smooth = ROPE_SMOOTH_PERIOD
    rsi_period = RSI_PERIOD
    rsi_ob = RSI_OVERBOUGHT
    rsi_os = RSI_OVERSOLD
    rsi_nh = RSI_NEUTRAL_HIGH
    rsi_nl = RSI_NEUTRAL_LOW
    tp_atr = TAKE_PROFIT_ATR_MULT
    sl_atr = STOP_LOSS_ATR_MULT

    def init(self):
        """Initialize indicators including RSI"""
        # ATR for volatility measurement
        self.atr = self.I(talib.ATR, self.data.High, self.data.Low, self.data.Close, self.atr_period)

        # RSI for momentum confirmation
        self.rsi = self.I(talib.RSI, self.data.Close, self.rsi_period)

        # Calculate rope smoother
        close_prices = self.data.Close
        close_array = np.array(close_prices)

        # Initialize rope array
        rope = np.zeros(len(close_array))
        direction = np.zeros(len(close_array))

        # Start with first valid price
        rope[0] = close_array[0]

        # Calculate rope smoothing
        for i in range(1, len(close_array)):
            if i < self.atr_period:
                rope[i] = close_array[i]
                direction[i] = 1 if close_array[i] > close_array[i-1] else -1
            else:
                # Get current ATR value
                atr_val = self.atr[i]
                if pd.isna(atr_val) or atr_val == 0:
                    rope[i] = rope[i-1]
                    direction[i] = direction[i-1]
                    continue

                # Calculate ATR threshold
                threshold = atr_val * self.atr_multiplier

                # Calculate price change from rope
                price_change = close_array[i] - rope[i-1]

                # Update rope based on threshold
                if abs(price_change) > threshold:
                    if price_change > 0:
                        rope[i] = rope[i-1] + (price_change - threshold)
                        direction[i] = 1
                    else:
                        rope[i] = rope[i-1] + (price_change + threshold)
                        direction[i] = -1
                else:
                    rope[i] = rope[i-1]
                    direction[i] = 0

        # Apply smoothing to rope using numpy
        rope_smoothed = pd.Series(rope).rolling(window=self.rope_smooth, min_periods=1).mean().values

        # Store as indicators
        self.rope = self.I(lambda: rope_smoothed)
        self.direction = self.I(lambda: direction)

        # Calculate bands
        self.upper_band = self.I(lambda: self.rope + self.atr * self.atr_multiplier)
        self.lower_band = self.I(lambda: self.rope - self.atr * self.atr_multiplier)

        # Track consolidation
        self.in_consolidation = self.I(lambda: direction == 0)

    def next(self):
        """Execute trading logic with RSI confirmation"""
        # Skip if not enough data
        if len(self.data) < max(self.atr_period + self.rope_smooth, self.rsi_period):
            return

        # Get current values
        current_price = self.data.Close[-1]
        current_rope = self.rope[-1]
        current_direction = self.direction[-1]
        prev_direction = self.direction[-2] if len(self.direction) > 1 else 0
        current_atr = self.atr[-1]
        current_rsi = self.rsi[-1]

        # Skip if indicators invalid
        if pd.isna(current_atr) or current_atr == 0 or pd.isna(current_rsi):
            return

        # Check consolidation status
        was_consolidating = self.in_consolidation[-2] if len(self.in_consolidation) > 1 else False
        is_consolidating = self.in_consolidation[-1]

        if not self.position:
            # Entry logic with RSI confirmation

            # 1. Breakout from consolidation with RSI confirmation
            if was_consolidating and not is_consolidating:
                if current_direction == 1 and current_rsi > self.rsi_nl and current_rsi < self.rsi_ob:
                    # Bullish breakout with RSI not overbought
                    sl_price = current_price - (current_atr * self.sl_atr)
                    tp_price = current_price + (current_atr * self.tp_atr)
                    self.buy(sl=sl_price, tp=tp_price, size=1000000)

                elif current_direction == -1 and current_rsi < self.rsi_nh and current_rsi > self.rsi_os:
                    # Bearish breakout with RSI not oversold
                    sl_price = current_price + (current_atr * self.sl_atr)
                    tp_price = current_price - (current_atr * self.tp_atr)
                    self.sell(sl=sl_price, tp=tp_price, size=1000000)

            # 2. Trend reversal with RSI divergence confirmation
            elif prev_direction != current_direction and current_direction != 0:
                if current_direction == 1 and prev_direction == -1:
                    # Bearish to bullish with RSI oversold bounce
                    if current_rsi < self.rsi_nl or (current_rsi > self.rsi_os and current_rsi < 50):
                        sl_price = current_price - (current_atr * self.sl_atr)
                        tp_price = current_price + (current_atr * self.tp_atr)
                        self.buy(sl=sl_price, tp=tp_price, size=1000000)

                elif current_direction == -1 and prev_direction == 1:
                    # Bullish to bearish with RSI overbought reversal
                    if current_rsi > self.rsi_nh or (current_rsi < self.rsi_ob and current_rsi > 50):
                        sl_price = current_price + (current_atr * self.sl_atr)
                        tp_price = current_price - (current_atr * self.tp_atr)
                        self.sell(sl=sl_price, tp=tp_price, size=1000000)

            # 3. Strong trend continuation with RSI momentum
            elif current_direction != 0:
                distance_from_rope = abs(current_price - current_rope)

                if distance_from_rope < current_atr * 0.5:
                    if current_direction == 1 and current_price > current_rope:
                        # Bullish bounce with RSI momentum
                        if self.rsi_nl < current_rsi < self.rsi_ob:
                            sl_price = current_rope - (current_atr * self.sl_atr)
                            tp_price = current_price + (current_atr * self.tp_atr)
                            self.buy(sl=sl_price, tp=tp_price, size=1000000)

                    elif current_direction == -1 and current_price < current_rope:
                        # Bearish bounce with RSI momentum
                        if self.rsi_os < current_rsi < self.rsi_nh:
                            sl_price = current_rope + (current_atr * self.sl_atr)
                            tp_price = current_price - (current_atr * self.tp_atr)
                            self.sell(sl=sl_price, tp=tp_price, size=1000000)

            # 4. RSI extremes with rope support
            if current_rsi < self.rsi_os and current_direction >= 0:
                # Oversold with non-bearish rope
                sl_price = current_price - (current_atr * self.sl_atr)
                tp_price = current_price + (current_atr * self.tp_atr)
                self.buy(sl=sl_price, tp=tp_price, size=1000000)

            elif current_rsi > self.rsi_ob and current_direction <= 0:
                # Overbought with non-bullish rope
                sl_price = current_price + (current_atr * self.sl_atr)
                tp_price = current_price - (current_atr * self.tp_atr)
                self.sell(sl=sl_price, tp=tp_price, size=1000000)

        else:
            # Exit logic with RSI confirmation

            if self.position.is_long:
                # Exit long on bearish rope or extreme overbought
                if current_direction == -1 or current_rsi > self.rsi_ob + 5:
                    self.position.close()

            elif self.position.is_short:
                # Exit short on bullish rope or extreme oversold
                if current_direction == 1 or current_rsi < self.rsi_os - 5:
                    self.position.close()

# Run single backtest
bt = Backtest(data, ATRRopeRSI, cash=1000000, commission=0.00045)

print("\n🌙 ===== ATR ROPE + RSI - DEFAULT PARAMETERS ===== 🌙")
print(f"ATR Period: {ATR_PERIOD}")
print(f"ATR Multiplier: {ATR_MULTIPLIER}")
print(f"RSI Period: {RSI_PERIOD}")
print(f"RSI OB/OS: {RSI_OVERBOUGHT}/{RSI_OVERSOLD}")
print(f"Take Profit ATR: {TAKE_PROFIT_ATR_MULT}")
print(f"Stop Loss ATR: {STOP_LOSS_ATR_MULT}")

stats_default = bt.run()
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING ATR ROPE + RSI ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from backtests.multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(ATRRopeRSI, 'ATRRopeRSI')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/ATRRopeRSI.csv")