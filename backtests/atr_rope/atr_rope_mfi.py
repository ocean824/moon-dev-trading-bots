"""
ATR Rope with MFI Strategy
===========================
Combines ATR Rope smoothing with Money Flow Index for volume-weighted momentum.

Enhancements:
- Uses MFI to confirm money flow direction
- Filters signals based on buying/selling pressure
- Better detection of accumulation/distribution
"""

import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy

print("🚀 Moon Dev's ATR Rope + MFI Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
ATR_PERIOD = 14
ATR_MULTIPLIER = 0.5
ROPE_SMOOTH_PERIOD = 3
MFI_PERIOD = 14
MFI_OVERBOUGHT = 80
MFI_OVERSOLD = 20
MFI_BULLISH = 50
MFI_BEARISH = 50
TAKE_PROFIT_ATR_MULT = 2.0
STOP_LOSS_ATR_MULT = 1.0

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class ATRRopeMFI(Strategy):
    # Strategy parameters
    atr_period = ATR_PERIOD
    atr_multiplier = ATR_MULTIPLIER
    rope_smooth = ROPE_SMOOTH_PERIOD
    mfi_period = MFI_PERIOD
    mfi_ob = MFI_OVERBOUGHT
    mfi_os = MFI_OVERSOLD
    mfi_bull = MFI_BULLISH
    mfi_bear = MFI_BEARISH
    tp_atr = TAKE_PROFIT_ATR_MULT
    sl_atr = STOP_LOSS_ATR_MULT

    def init(self):
        """Initialize indicators including MFI"""
        # ATR for volatility measurement
        self.atr = self.I(talib.ATR, self.data.High, self.data.Low, self.data.Close, self.atr_period)

        # Money Flow Index
        self.mfi = self.I(talib.MFI, self.data.High, self.data.Low, self.data.Close,
                         self.data.Volume, self.mfi_period)

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

        # MFI zones
        mfi_values = self.mfi
        self.mfi_bullish = self.I(lambda: mfi_values > self.mfi_bull)
        self.mfi_bearish = self.I(lambda: mfi_values < self.mfi_bear)

    def next(self):
        """Execute trading logic with MFI confirmation"""
        # Skip if not enough data
        if len(self.data) < max(self.atr_period + self.rope_smooth, self.mfi_period):
            return

        # Get current values
        current_price = self.data.Close[-1]
        current_rope = self.rope[-1]
        current_direction = self.direction[-1]
        prev_direction = self.direction[-2] if len(self.direction) > 1 else 0
        current_atr = self.atr[-1]
        current_mfi = self.mfi[-1]
        prev_mfi = self.mfi[-2] if len(self.mfi) > 1 else 50

        # Skip if indicators invalid
        if pd.isna(current_atr) or current_atr == 0 or pd.isna(current_mfi):
            return

        # Check consolidation status
        was_consolidating = self.in_consolidation[-2] if len(self.in_consolidation) > 1 else False
        is_consolidating = self.in_consolidation[-1]

        # MFI conditions
        mfi_strong_buy = current_mfi < self.mfi_os  # Oversold
        mfi_strong_sell = current_mfi > self.mfi_ob  # Overbought
        mfi_bullish = current_mfi > self.mfi_bull and current_mfi > prev_mfi
        mfi_bearish = current_mfi < self.mfi_bear and current_mfi < prev_mfi

        if not self.position:
            # Entry logic with MFI confirmation

            # 1. Breakout from consolidation with MFI confirmation
            if was_consolidating and not is_consolidating:
                if current_direction == 1 and (mfi_bullish or mfi_strong_buy):
                    # Bullish breakout with money flow confirmation
                    sl_price = current_price - (current_atr * self.sl_atr)
                    # Increase TP on strong MFI readings
                    tp_mult = self.tp_atr * 1.5 if mfi_strong_buy else self.tp_atr
                    tp_price = current_price + (current_atr * tp_mult)
                    self.buy(sl=sl_price, tp=tp_price, size=1000000)

                elif current_direction == -1 and (mfi_bearish or mfi_strong_sell):
                    # Bearish breakout with money flow confirmation
                    sl_price = current_price + (current_atr * self.sl_atr)
                    tp_mult = self.tp_atr * 1.5 if mfi_strong_sell else self.tp_atr
                    tp_price = current_price - (current_atr * tp_mult)
                    self.sell(sl=sl_price, tp=tp_price, size=1000000)

            # 2. Trend reversal with MFI divergence
            elif prev_direction != current_direction and current_direction != 0:
                if current_direction == 1 and prev_direction == -1:
                    # Bearish to bullish - check for MFI support
                    if mfi_strong_buy or (current_mfi > prev_mfi and current_mfi < 60):
                        sl_price = current_price - (current_atr * self.sl_atr)
                        tp_price = current_price + (current_atr * self.tp_atr)
                        self.buy(sl=sl_price, tp=tp_price, size=1000000)

                elif current_direction == -1 and prev_direction == 1:
                    # Bullish to bearish - check for MFI resistance
                    if mfi_strong_sell or (current_mfi < prev_mfi and current_mfi > 40):
                        sl_price = current_price + (current_atr * self.sl_atr)
                        tp_price = current_price - (current_atr * self.tp_atr)
                        self.sell(sl=sl_price, tp=tp_price, size=1000000)

            # 3. Strong trend continuation with MFI momentum
            elif current_direction != 0:
                distance_from_rope = abs(current_price - current_rope)

                if distance_from_rope < current_atr * 0.5:
                    if current_direction == 1 and current_price > current_rope:
                        # Bullish bounce with MFI momentum
                        if mfi_bullish and not mfi_strong_sell:
                            sl_price = current_rope - (current_atr * self.sl_atr)
                            tp_price = current_price + (current_atr * self.tp_atr)
                            self.buy(sl=sl_price, tp=tp_price, size=1000000)

                    elif current_direction == -1 and current_price < current_rope:
                        # Bearish bounce with MFI momentum
                        if mfi_bearish and not mfi_strong_buy:
                            sl_price = current_rope + (current_atr * self.sl_atr)
                            tp_price = current_price - (current_atr * self.tp_atr)
                            self.sell(sl=sl_price, tp=tp_price, size=1000000)

            # 4. MFI extreme reversals
            if mfi_strong_buy and current_direction >= 0:
                # Extreme oversold with non-bearish rope
                sl_price = current_price - (current_atr * self.sl_atr * 0.8)  # Tighter stop
                tp_price = current_price + (current_atr * self.tp_atr * 1.5)  # Higher target
                self.buy(sl=sl_price, tp=tp_price, size=1000000)

            elif mfi_strong_sell and current_direction <= 0:
                # Extreme overbought with non-bullish rope
                sl_price = current_price + (current_atr * self.sl_atr * 0.8)
                tp_price = current_price - (current_atr * self.tp_atr * 1.5)
                self.sell(sl=sl_price, tp=tp_price, size=1000000)

            # 5. MFI divergence patterns
            # Check for accumulation (price flat/down but MFI rising)
            if current_direction == 0 and current_mfi > prev_mfi and current_mfi < 70:
                if current_price >= current_rope:
                    sl_price = current_price - (current_atr * self.sl_atr)
                    tp_price = current_price + (current_atr * self.tp_atr)
                    self.buy(sl=sl_price, tp=tp_price, size=1000000)

            # Check for distribution (price flat/up but MFI falling)
            elif current_direction == 0 and current_mfi < prev_mfi and current_mfi > 30:
                if current_price <= current_rope:
                    sl_price = current_price + (current_atr * self.sl_atr)
                    tp_price = current_price - (current_atr * self.tp_atr)
                    self.sell(sl=sl_price, tp=tp_price, size=1000000)

        else:
            # Exit logic with MFI considerations

            if self.position.is_long:
                # Exit on bearish rope or MFI exhaustion
                if current_direction == -1:
                    self.position.close()
                # Exit on MFI turning bearish from overbought
                elif current_mfi > self.mfi_ob and current_mfi < prev_mfi:
                    self.position.close()
                # Exit on MFI breakdown below 50
                elif prev_mfi > 50 and current_mfi < 50:
                    self.position.close()

            elif self.position.is_short:
                # Exit on bullish rope or MFI exhaustion
                if current_direction == 1:
                    self.position.close()
                # Exit on MFI turning bullish from oversold
                elif current_mfi < self.mfi_os and current_mfi > prev_mfi:
                    self.position.close()
                # Exit on MFI breakout above 50
                elif prev_mfi < 50 and current_mfi > 50:
                    self.position.close()

# Run single backtest
bt = Backtest(data, ATRRopeMFI, cash=1000000, commission=0.00045)

print("\n🌙 ===== ATR ROPE + MFI - DEFAULT PARAMETERS ===== 🌙")
print(f"ATR Period: {ATR_PERIOD}")
print(f"ATR Multiplier: {ATR_MULTIPLIER}")
print(f"MFI Period: {MFI_PERIOD}")
print(f"MFI OB/OS: {MFI_OVERBOUGHT}/{MFI_OVERSOLD}")
print(f"Take Profit ATR: {TAKE_PROFIT_ATR_MULT}")
print(f"Stop Loss ATR: {STOP_LOSS_ATR_MULT}")

stats_default = bt.run()
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING ATR ROPE + MFI ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from backtests.multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(ATRRopeMFI, 'ATRRopeMFI')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/ATRRopeMFI.csv")