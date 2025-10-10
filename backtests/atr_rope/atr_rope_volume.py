"""
ATR Rope with Volume Strategy
==============================
Combines ATR Rope smoothing with volume confirmation for stronger breakouts.

Enhancements:
- Uses volume to confirm breakouts
- Filters weak signals with low volume
- Better confirmation of trend strength
"""

import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy

print("🚀 Moon Dev's ATR Rope + Volume Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
ATR_PERIOD = 14
ATR_MULTIPLIER = 0.5
ROPE_SMOOTH_PERIOD = 3
VOLUME_MA_PERIOD = 20
VOLUME_THRESHOLD = 1.1  # Volume must be 1.1x average for confirmation
HIGH_VOLUME_MULT = 1.5  # High volume is 1.5x average
TAKE_PROFIT_ATR_MULT = 2.0
STOP_LOSS_ATR_MULT = 1.0

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class ATRRopeVolume(Strategy):
    # Strategy parameters
    atr_period = ATR_PERIOD
    atr_multiplier = ATR_MULTIPLIER
    rope_smooth = ROPE_SMOOTH_PERIOD
    volume_ma_period = VOLUME_MA_PERIOD
    volume_threshold = VOLUME_THRESHOLD
    high_volume_mult = HIGH_VOLUME_MULT
    tp_atr = TAKE_PROFIT_ATR_MULT
    sl_atr = STOP_LOSS_ATR_MULT

    def init(self):
        """Initialize indicators including volume analysis"""
        # ATR for volatility measurement
        self.atr = self.I(talib.ATR, self.data.High, self.data.Low, self.data.Close, self.atr_period)

        # Volume indicators
        self.volume_ma = self.I(talib.SMA, self.data.Volume, self.volume_ma_period)

        # Calculate volume ratio safely
        volume_ma_array = np.array(self.volume_ma)
        volume_array = np.array(self.data.Volume)
        volume_ratio = np.where(volume_ma_array > 0, volume_array / volume_ma_array, 1.0)
        self.volume_ratio = self.I(lambda: volume_ratio)

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

        # On-Balance Volume for trend confirmation
        obv = talib.OBV(self.data.Close, self.data.Volume)
        self.obv = self.I(lambda: obv)
        self.obv_ma = self.I(talib.SMA, self.obv, 20)

    def next(self):
        """Execute trading logic with volume confirmation"""
        # Skip if not enough data
        if len(self.data) < max(self.atr_period + self.rope_smooth, self.volume_ma_period):
            return

        # Get current values
        current_price = self.data.Close[-1]
        current_rope = self.rope[-1]
        current_direction = self.direction[-1]
        prev_direction = self.direction[-2] if len(self.direction) > 1 else 0
        current_atr = self.atr[-1]
        current_volume_ratio = self.volume_ratio[-1]
        current_obv = self.obv[-1]
        obv_ma = self.obv_ma[-1]

        # Skip if indicators invalid
        if pd.isna(current_atr) or current_atr == 0 or pd.isna(current_volume_ratio):
            return

        # Check consolidation status
        was_consolidating = self.in_consolidation[-2] if len(self.in_consolidation) > 1 else False
        is_consolidating = self.in_consolidation[-1]

        # Check volume conditions
        has_volume_confirmation = current_volume_ratio >= self.volume_threshold
        has_high_volume = current_volume_ratio >= self.high_volume_mult

        if not self.position:
            # Entry logic with volume confirmation

            # 1. Breakout from consolidation with volume spike
            if was_consolidating and not is_consolidating and has_volume_confirmation:
                if current_direction == 1:
                    # Bullish breakout with volume
                    sl_price = current_price - (current_atr * self.sl_atr)
                    # Increase TP on high volume breakouts
                    tp_mult = self.tp_atr * 1.5 if has_high_volume else self.tp_atr
                    tp_price = current_price + (current_atr * tp_mult)
                    self.buy(sl=sl_price, tp=tp_price, size=1000000)

                elif current_direction == -1:
                    # Bearish breakout with volume
                    sl_price = current_price + (current_atr * self.sl_atr)
                    tp_mult = self.tp_atr * 1.5 if has_high_volume else self.tp_atr
                    tp_price = current_price - (current_atr * tp_mult)
                    self.sell(sl=sl_price, tp=tp_price, size=1000000)

            # 2. Trend reversal with volume confirmation
            elif prev_direction != current_direction and current_direction != 0:
                if current_direction == 1 and prev_direction == -1 and has_volume_confirmation:
                    # Bearish to bullish with volume
                    if current_obv > obv_ma:  # OBV confirms buying pressure
                        sl_price = current_price - (current_atr * self.sl_atr)
                        tp_price = current_price + (current_atr * self.tp_atr)
                        self.buy(sl=sl_price, tp=tp_price, size=1000000)

                elif current_direction == -1 and prev_direction == 1 and has_volume_confirmation:
                    # Bullish to bearish with volume
                    if current_obv < obv_ma:  # OBV confirms selling pressure
                        sl_price = current_price + (current_atr * self.sl_atr)
                        tp_price = current_price - (current_atr * self.tp_atr)
                        self.sell(sl=sl_price, tp=tp_price, size=1000000)

            # 3. Strong trend continuation with volume
            elif current_direction != 0:
                distance_from_rope = abs(current_price - current_rope)

                if distance_from_rope < current_atr * 0.5:
                    if current_direction == 1 and current_price > current_rope:
                        # Bullish bounce with volume
                        if has_volume_confirmation and current_obv > obv_ma:
                            sl_price = current_rope - (current_atr * self.sl_atr)
                            tp_price = current_price + (current_atr * self.tp_atr)
                            self.buy(sl=sl_price, tp=tp_price, size=1000000)

                    elif current_direction == -1 and current_price < current_rope:
                        # Bearish bounce with volume
                        if has_volume_confirmation and current_obv < obv_ma:
                            sl_price = current_rope + (current_atr * self.sl_atr)
                            tp_price = current_price - (current_atr * self.tp_atr)
                            self.sell(sl=sl_price, tp=tp_price, size=1000000)

            # 4. High volume breakout signals
            if has_high_volume:
                # Check for volume-based breakout
                if current_price > self.upper_band[-1] and current_direction >= 0:
                    # Bullish volume breakout
                    sl_price = current_rope - (current_atr * self.sl_atr)
                    tp_price = current_price + (current_atr * self.tp_atr * 1.5)
                    self.buy(sl=sl_price, tp=tp_price, size=1000000)

                elif current_price < self.lower_band[-1] and current_direction <= 0:
                    # Bearish volume breakout
                    sl_price = current_rope + (current_atr * self.sl_atr)
                    tp_price = current_price - (current_atr * self.tp_atr * 1.5)
                    self.sell(sl=sl_price, tp=tp_price, size=1000000)

        else:
            # Exit logic with volume considerations

            if self.position.is_long:
                # Exit on bearish rope or volume divergence
                if current_direction == -1:
                    self.position.close()
                # Exit on volume exhaustion (very low volume)
                elif current_volume_ratio < 0.5:
                    self.position.close()

            elif self.position.is_short:
                # Exit on bullish rope or volume divergence
                if current_direction == 1:
                    self.position.close()
                # Exit on volume exhaustion
                elif current_volume_ratio < 0.5:
                    self.position.close()

# Run single backtest
bt = Backtest(data, ATRRopeVolume, cash=1000000, commission=0.00045)

print("\n🌙 ===== ATR ROPE + VOLUME - DEFAULT PARAMETERS ===== 🌙")
print(f"ATR Period: {ATR_PERIOD}")
print(f"ATR Multiplier: {ATR_MULTIPLIER}")
print(f"Volume MA Period: {VOLUME_MA_PERIOD}")
print(f"Volume Threshold: {VOLUME_THRESHOLD}")
print(f"Take Profit ATR: {TAKE_PROFIT_ATR_MULT}")
print(f"Stop Loss ATR: {STOP_LOSS_ATR_MULT}")

stats_default = bt.run()
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING ATR ROPE + VOLUME ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from backtests.multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(ATRRopeVolume, 'ATRRopeVolume')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/ATRRopeVolume.csv")