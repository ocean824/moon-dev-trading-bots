"""
Volume Profile Value Area Breakout Strategy
Trades breakouts above VAH (Value Area High) and breakdowns below VAL (Value Area Low).
Uses volume confirmation and pivot points as additional filters.
Implements trailing stops using value area boundaries.
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from multi_data_tester import test_on_all_data

class VolumeProfileBreakout(Strategy):
    # Volume Profile Parameters
    profile_period = 30  # Number of bars to calculate volume profile
    value_area_pct = 0.68  # 68% of volume for value area

    # Breakout Parameters
    breakout_confirmation_bars = 2  # Bars to confirm breakout
    volume_surge_multiplier = 1.618  # Golden ratio for volume surge
    use_pivot_filter = True  # Use pivot points as filter

    # Pivot Parameters
    pivot_lookback = 10  # Bars for pivot detection
    pivot_lookahead = 5  # Bars for pivot confirmation

    # Risk Management
    stop_loss_pct = 0.015  # 1.5% initial stop loss
    trail_using_value_area = True  # Trail stop using VAL/VAH
    target_multiplier = 2.0  # Risk/reward ratio

    # Additional Filters
    min_value_area_width = 0.005  # Minimum 0.5% width for valid value area
    use_momentum_filter = True
    momentum_period = 10

    def init(self):
        # Price and volume data
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        volume = pd.Series(self.data.Volume)

        # Calculate volume profile levels
        self.poc = self.I(self.calculate_poc, close, volume, high, low, self.profile_period)
        self.vah = self.I(self.calculate_vah, close, volume, high, low, self.profile_period, self.value_area_pct)
        self.val = self.I(self.calculate_val, close, volume, high, low, self.profile_period, self.value_area_pct)

        # Value area width
        self.va_width = self.I(lambda: (self.vah - self.val) / self.poc)

        # Detect pivot points
        self.pivot_highs = self.I(self.detect_pivot_highs, high, self.pivot_lookback, self.pivot_lookahead)
        self.pivot_lows = self.I(self.detect_pivot_lows, low, self.pivot_lookback, self.pivot_lookahead)

        # Volume analysis
        self.volume_sma = self.I(ta.sma, volume, 20)
        self.volume_ratio = self.I(lambda: volume / self.volume_sma)

        # Momentum indicator (Rate of Change)
        self.roc = self.I(ta.roc, close, self.momentum_period)

        # ATR for volatility-based stops
        self.atr = self.I(ta.atr, high, low, close, 14)

        # MACD for trend confirmation
        macd = ta.macd(close, fast=12, slow=26, signal=9)
        self.macd_line = self.I(lambda: macd['MACD_12_26_9'] if 'MACD_12_26_9' in macd.columns else pd.Series(np.zeros(len(close))))
        self.macd_signal = self.I(lambda: macd['MACDs_12_26_9'] if 'MACDs_12_26_9' in macd.columns else pd.Series(np.zeros(len(close))))

    def calculate_volume_profile(self, close, volume, high, low, period):
        """Calculate complete volume profile"""
        result_poc = []
        result_vah = []
        result_val = []

        for i in range(len(close)):
            if i < period - 1:
                result_poc.append(close.iloc[i])
                result_vah.append(high.iloc[i])
                result_val.append(low.iloc[i])
            else:
                # Get period data
                period_close = close.iloc[i-period+1:i+1]
                period_high = high.iloc[i-period+1:i+1]
                period_low = low.iloc[i-period+1:i+1]
                period_volume = volume.iloc[i-period+1:i+1]

                price_range = period_high.max() - period_low.min()
                if price_range > 0:
                    # Create bins
                    num_bins = min(30, period)
                    bins = np.linspace(period_low.min(), period_high.max(), num_bins)

                    # Build volume profile
                    volume_profile = {}
                    for j in range(len(period_close)):
                        typical_price = (period_high.iloc[j] + period_low.iloc[j] + period_close.iloc[j]) / 3
                        bin_idx = np.digitize(typical_price, bins) - 1
                        bin_idx = min(max(0, bin_idx), len(bins)-2)
                        bin_price = (bins[bin_idx] + bins[bin_idx+1]) / 2

                        if bin_price not in volume_profile:
                            volume_profile[bin_price] = 0
                        volume_profile[bin_price] += period_volume.iloc[j]

                    if volume_profile:
                        # Find POC
                        poc = max(volume_profile, key=volume_profile.get)

                        # Calculate Value Area
                        total_volume = sum(volume_profile.values())
                        va_volume = total_volume * 0.68

                        # Sort by volume and find value area
                        sorted_prices = sorted(volume_profile.items(), key=lambda x: x[1], reverse=True)
                        accumulated_volume = 0
                        va_prices = []

                        for price, vol in sorted_prices:
                            accumulated_volume += vol
                            va_prices.append(price)
                            if accumulated_volume >= va_volume:
                                break

                        vah = max(va_prices) if va_prices else period_high.max()
                        val = min(va_prices) if va_prices else period_low.min()
                    else:
                        poc = period_close.mean()
                        vah = period_high.max()
                        val = period_low.min()
                else:
                    poc = period_close.mean()
                    vah = period_high.max()
                    val = period_low.min()

                result_poc.append(poc)
                result_vah.append(vah)
                result_val.append(val)

        return result_poc, result_vah, result_val

    def calculate_poc(self, close, volume, high, low, period):
        """Calculate Point of Control"""
        poc, _, _ = self.calculate_volume_profile(close, volume, high, low, period)
        return pd.Series(poc, index=close.index)

    def calculate_vah(self, close, volume, high, low, period, value_area_pct):
        """Calculate Value Area High"""
        _, vah, _ = self.calculate_volume_profile(close, volume, high, low, period)
        return pd.Series(vah, index=close.index)

    def calculate_val(self, close, volume, high, low, period, value_area_pct):
        """Calculate Value Area Low"""
        _, _, val = self.calculate_volume_profile(close, volume, high, low, period)
        return pd.Series(val, index=close.index)

    def detect_pivot_highs(self, high, lookback, lookahead):
        """Detect pivot high points"""
        result = []
        for i in range(len(high)):
            if i < lookback or i >= len(high) - lookahead:
                result.append(0)
            else:
                is_pivot = True
                current_high = high.iloc[i]

                for j in range(1, lookback + 1):
                    if high.iloc[i-j] >= current_high:
                        is_pivot = False
                        break

                if is_pivot:
                    for j in range(1, lookahead + 1):
                        if high.iloc[i+j] > current_high:
                            is_pivot = False
                            break

                result.append(1 if is_pivot else 0)

        return pd.Series(result, index=high.index)

    def detect_pivot_lows(self, low, lookback, lookahead):
        """Detect pivot low points"""
        result = []
        for i in range(len(low)):
            if i < lookback or i >= len(low) - lookahead:
                result.append(0)
            else:
                is_pivot = True
                current_low = low.iloc[i]

                for j in range(1, lookback + 1):
                    if low.iloc[i-j] <= current_low:
                        is_pivot = False
                        break

                if is_pivot:
                    for j in range(1, lookahead + 1):
                        if low.iloc[i+j] < current_low:
                            is_pivot = False
                            break

                result.append(1 if is_pivot else 0)

        return pd.Series(result, index=low.index)

    def next(self):
        # Skip if not enough data
        if len(self.data) < self.profile_period + 10:
            return

        # Current values
        current_price = self.data.Close[-1]
        current_high = self.data.High[-1]
        current_low = self.data.Low[-1]
        current_vah = self.vah[-1]
        current_val = self.val[-1]
        current_poc = self.poc[-1]
        current_volume_ratio = self.volume_ratio[-1]
        current_va_width = self.va_width[-1]
        current_roc = self.roc[-1] if len(self.roc) > 0 else 0
        current_atr = self.atr[-1]

        # Check for valid value area
        if current_va_width < self.min_value_area_width:
            return

        # Check for pivot points if filter is enabled
        has_pivot_high = any(self.pivot_highs[-5:]) if self.use_pivot_filter and len(self.pivot_highs) >= 5 else True
        has_pivot_low = any(self.pivot_lows[-5:]) if self.use_pivot_filter and len(self.pivot_lows) >= 5 else True

        if not self.position:
            # Long Breakout: Price breaks above VAH with volume surge
            vah_breakout = current_price > current_vah and self.data.Close[-2] <= self.vah[-2]
            volume_surge = current_volume_ratio > self.volume_surge_multiplier
            momentum_confirmed = not self.use_momentum_filter or current_roc > 0

            if vah_breakout and volume_surge and momentum_confirmed:
                # Confirmation: Check if breakout holds for specified bars
                if self.breakout_confirmation_bars > 1:
                    confirmed = all(self.data.Close[-i] > self.vah[-i] for i in range(1, min(self.breakout_confirmation_bars, len(self.data))))
                else:
                    confirmed = True

                if confirmed:
                    # Set stop loss at VAL or below entry
                    sl_price = max(current_val, current_price * (1 - self.stop_loss_pct))

                    # Set target based on multiplier
                    risk = current_price - sl_price
                    tp_price = current_price + (risk * self.target_multiplier)

                    self.buy(sl=sl_price, tp=tp_price)

            # Short Breakout: Price breaks below VAL with volume surge
            val_breakdown = current_price < current_val and self.data.Close[-2] >= self.val[-2]
            momentum_confirmed_short = not self.use_momentum_filter or current_roc < 0

            if val_breakdown and volume_surge and momentum_confirmed_short:
                # Confirmation: Check if breakdown holds for specified bars
                if self.breakout_confirmation_bars > 1:
                    confirmed = all(self.data.Close[-i] < self.val[-i] for i in range(1, min(self.breakout_confirmation_bars, len(self.data))))
                else:
                    confirmed = True

                if confirmed:
                    # Set stop loss at VAH or above entry
                    sl_price = min(current_vah, current_price * (1 + self.stop_loss_pct))

                    # Set target based on multiplier
                    risk = sl_price - current_price
                    tp_price = current_price - (risk * self.target_multiplier)

                    self.sell(sl=sl_price, tp=tp_price)

        else:
            # Trail stops using value area boundaries
            if self.trail_using_value_area:
                if self.position.is_long:
                    # Trail stop at VAL
                    new_sl = current_val
                    if hasattr(self.position, 'sl') and new_sl > self.position.sl:
                        self.position.sl = new_sl

                    # Exit if price falls back into value area after breakout
                    if current_price < current_vah:
                        self.position.close()

                elif self.position.is_short:
                    # Trail stop at VAH
                    new_sl = current_vah
                    if hasattr(self.position, 'sl') and new_sl < self.position.sl:
                        self.position.sl = new_sl

                    # Exit if price rises back into value area after breakdown
                    if current_price > current_val:
                        self.position.close()

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

print("Volume Profile Value Area Breakout Strategy Loading...")
print(f"Loading data from: {DATA_PATH}")

# Load and prepare data
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()

print(f"Data loaded! {len(data)} rows")

# Run single backtest
bt = Backtest(data, VolumeProfileBreakout, cash=1000000, commission=0.001)

print("\n===== Volume Profile Breakout Strategy - DEFAULT PARAMETERS =====")
print(f"Profile Period: {VolumeProfileBreakout.profile_period}")
print(f"Value Area %: {VolumeProfileBreakout.value_area_pct * 100}%")
print(f"Volume Surge Multiplier: {VolumeProfileBreakout.volume_surge_multiplier}x")
print(f"Stop Loss: {VolumeProfileBreakout.stop_loss_pct * 100}%")
print(f"Target Multiplier: {VolumeProfileBreakout.target_multiplier}x")

stats = bt.run()
print(stats)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING VOLUME PROFILE BREAKOUT ON ALL DATA SOURCES")
    print("="*80)

    results = test_on_all_data(VolumeProfileBreakout, 'VolumeProfileBreakout')

    if results is not None:
        print("\nTesting complete! Results saved in: ./results/VolumeProfileBreakout.csv")