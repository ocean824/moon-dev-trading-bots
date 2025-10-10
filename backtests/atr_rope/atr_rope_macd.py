"""
ATR Rope with MACD Strategy
============================
Combines ATR Rope smoothing with MACD for trend confirmation and momentum.

Enhancements:
- Uses MACD to confirm trend direction
- MACD histogram for momentum strength
- Better timing of trend changes
"""

import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy

print("🚀 Moon Dev's ATR Rope + MACD Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
ATR_PERIOD = 14
ATR_MULTIPLIER = 0.5
ROPE_SMOOTH_PERIOD = 3
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
TAKE_PROFIT_ATR_MULT = 2.0
STOP_LOSS_ATR_MULT = 1.0

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class ATRRopeMACD(Strategy):
    # Strategy parameters
    atr_period = ATR_PERIOD
    atr_multiplier = ATR_MULTIPLIER
    rope_smooth = ROPE_SMOOTH_PERIOD
    macd_fast = MACD_FAST
    macd_slow = MACD_SLOW
    macd_signal = MACD_SIGNAL
    tp_atr = TAKE_PROFIT_ATR_MULT
    sl_atr = STOP_LOSS_ATR_MULT

    def init(self):
        """Initialize indicators including MACD"""
        # ATR for volatility measurement
        self.atr = self.I(talib.ATR, self.data.High, self.data.Low, self.data.Close, self.atr_period)

        # MACD indicators
        macd, macd_signal, macd_hist = talib.MACD(
            self.data.Close,
            fastperiod=self.macd_fast,
            slowperiod=self.macd_slow,
            signalperiod=self.macd_signal
        )
        self.macd = self.I(lambda: macd)
        self.macd_signal = self.I(lambda: macd_signal)
        self.macd_hist = self.I(lambda: macd_hist)

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

        # MACD momentum tracking
        self.macd_bullish = self.I(lambda: (macd > macd_signal) & (macd_hist > 0))
        self.macd_bearish = self.I(lambda: (macd < macd_signal) & (macd_hist < 0))

    def next(self):
        """Execute trading logic with MACD confirmation"""
        # Skip if not enough data
        if len(self.data) < max(self.atr_period + self.rope_smooth, self.macd_slow + self.macd_signal):
            return

        # Get current values
        current_price = self.data.Close[-1]
        current_rope = self.rope[-1]
        current_direction = self.direction[-1]
        prev_direction = self.direction[-2] if len(self.direction) > 1 else 0
        current_atr = self.atr[-1]
        current_macd = self.macd[-1]
        current_signal = self.macd_signal[-1]
        current_hist = self.macd_hist[-1]
        prev_hist = self.macd_hist[-2] if len(self.macd_hist) > 1 else 0

        # Skip if indicators invalid
        if pd.isna(current_atr) or current_atr == 0 or pd.isna(current_macd):
            return

        # Check consolidation status
        was_consolidating = self.in_consolidation[-2] if len(self.in_consolidation) > 1 else False
        is_consolidating = self.in_consolidation[-1]

        # MACD conditions
        macd_bullish = current_macd > current_signal and current_hist > 0
        macd_bearish = current_macd < current_signal and current_hist < 0
        macd_crossover_bull = current_hist > 0 and prev_hist <= 0
        macd_crossover_bear = current_hist < 0 and prev_hist >= 0

        if not self.position:
            # Entry logic with MACD confirmation

            # 1. Breakout from consolidation with MACD confirmation
            if was_consolidating and not is_consolidating:
                if current_direction == 1 and macd_bullish:
                    # Bullish breakout with MACD confirmation
                    sl_price = current_price - (current_atr * self.sl_atr)
                    # Increase TP on strong MACD
                    tp_mult = self.tp_atr * 1.3 if abs(current_hist) > abs(prev_hist) else self.tp_atr
                    tp_price = current_price + (current_atr * tp_mult)
                    self.buy(sl=sl_price, tp=tp_price, size=1000000)

                elif current_direction == -1 and macd_bearish:
                    # Bearish breakout with MACD confirmation
                    sl_price = current_price + (current_atr * self.sl_atr)
                    tp_mult = self.tp_atr * 1.3 if abs(current_hist) > abs(prev_hist) else self.tp_atr
                    tp_price = current_price - (current_atr * tp_mult)
                    self.sell(sl=sl_price, tp=tp_price, size=1000000)

            # 2. Trend reversal with MACD crossover
            elif prev_direction != current_direction and current_direction != 0:
                if current_direction == 1 and macd_crossover_bull:
                    # Bearish to bullish with MACD crossover
                    sl_price = current_price - (current_atr * self.sl_atr)
                    tp_price = current_price + (current_atr * self.tp_atr)
                    self.buy(sl=sl_price, tp=tp_price, size=1000000)

                elif current_direction == -1 and macd_crossover_bear:
                    # Bullish to bearish with MACD crossover
                    sl_price = current_price + (current_atr * self.sl_atr)
                    tp_price = current_price - (current_atr * self.tp_atr)
                    self.sell(sl=sl_price, tp=tp_price, size=1000000)

            # 3. Strong trend continuation with MACD momentum
            elif current_direction != 0:
                distance_from_rope = abs(current_price - current_rope)

                if distance_from_rope < current_atr * 0.5:
                    if current_direction == 1 and current_price > current_rope and macd_bullish:
                        # Bullish bounce with MACD momentum
                        # Check for increasing momentum
                        if abs(current_hist) > abs(prev_hist):
                            sl_price = current_rope - (current_atr * self.sl_atr)
                            tp_price = current_price + (current_atr * self.tp_atr)
                            self.buy(sl=sl_price, tp=tp_price, size=1000000)

                    elif current_direction == -1 and current_price < current_rope and macd_bearish:
                        # Bearish bounce with MACD momentum
                        if abs(current_hist) > abs(prev_hist):
                            sl_price = current_rope + (current_atr * self.sl_atr)
                            tp_price = current_price - (current_atr * self.tp_atr)
                            self.sell(sl=sl_price, tp=tp_price, size=1000000)

            # 4. MACD divergence signals
            # Bullish divergence: Price making lower lows but MACD making higher lows
            if current_direction >= 0 and macd_crossover_bull:
                # Check if price near lower band
                if current_price < self.rope[-1] + current_atr * 0.5:
                    sl_price = current_price - (current_atr * self.sl_atr)
                    tp_price = current_price + (current_atr * self.tp_atr * 1.5)
                    self.buy(sl=sl_price, tp=tp_price, size=1000000)

            # Bearish divergence: Price making higher highs but MACD making lower highs
            elif current_direction <= 0 and macd_crossover_bear:
                # Check if price near upper band
                if current_price > self.rope[-1] - current_atr * 0.5:
                    sl_price = current_price + (current_atr * self.sl_atr)
                    tp_price = current_price - (current_atr * self.tp_atr * 1.5)
                    self.sell(sl=sl_price, tp=tp_price, size=1000000)

        else:
            # Exit logic with MACD considerations

            if self.position.is_long:
                # Exit on bearish rope or MACD turning bearish
                if current_direction == -1 or macd_crossover_bear:
                    self.position.close()
                # Exit on MACD momentum loss
                elif macd_bearish and abs(current_hist) > abs(prev_hist):
                    self.position.close()

            elif self.position.is_short:
                # Exit on bullish rope or MACD turning bullish
                if current_direction == 1 or macd_crossover_bull:
                    self.position.close()
                # Exit on MACD momentum loss
                elif macd_bullish and abs(current_hist) > abs(prev_hist):
                    self.position.close()

# Run single backtest
bt = Backtest(data, ATRRopeMACD, cash=1000000, commission=0.00045)

print("\n🌙 ===== ATR ROPE + MACD - DEFAULT PARAMETERS ===== 🌙")
print(f"ATR Period: {ATR_PERIOD}")
print(f"ATR Multiplier: {ATR_MULTIPLIER}")
print(f"MACD Fast/Slow/Signal: {MACD_FAST}/{MACD_SLOW}/{MACD_SIGNAL}")
print(f"Take Profit ATR: {TAKE_PROFIT_ATR_MULT}")
print(f"Stop Loss ATR: {STOP_LOSS_ATR_MULT}")

stats_default = bt.run()
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING ATR ROPE + MACD ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from backtests.multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(ATRRopeMACD, 'ATRRopeMACD')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/ATRRopeMACD.csv")