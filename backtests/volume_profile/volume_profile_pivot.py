"""
Volume Profile Pivot Strategy
Enters at pivot lows when volume profile shows accumulation.
Exits at pivot highs when volume profile shows distribution.
Uses POC as dynamic support/resistance levels.
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

class VolumeProfilePivot(Strategy):
    # Volume Profile Parameters
    profile_period = 30  # Number of bars to calculate volume profile
    value_area_pct = 0.68  # 68% of volume for value area

    # Pivot Parameters
    pivot_lookback = 12  # Bars to look back for pivot
    pivot_lookahead = 6  # Bars to look ahead for confirmation
    pivot_strength = 2  # Number of lower highs/higher lows needed

    # Volume Analysis
    accumulation_threshold = 1.2  # Volume ratio for accumulation
    distribution_threshold = 1.3  # Volume ratio for distribution
    volume_ma_period = 20

    # POC Support/Resistance
    poc_buffer_pct = 0.003  # 0.3% buffer around POC

    # Risk Management
    stop_loss_pct = 0.02  # 2% stop loss
    take_profit_pct = 0.05  # 5% take profit
    use_poc_as_stop = True  # Use POC as dynamic stop

    def init(self):
        # Price and volume data
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        volume = pd.Series(self.data.Volume)
        open_price = pd.Series(self.data.Open)

        # Calculate volume profile levels
        self.poc = self.I(self.calculate_poc, close, volume, high, low, self.profile_period)
        self.vah = self.I(self.calculate_vah, close, volume, high, low, self.profile_period, self.value_area_pct)
        self.val = self.I(self.calculate_val, close, volume, high, low, self.profile_period, self.value_area_pct)

        # Detect pivot points with strength
        self.pivot_highs = self.I(self.detect_strong_pivot_highs, high, low, self.pivot_lookback, self.pivot_lookahead)
        self.pivot_lows = self.I(self.detect_strong_pivot_lows, high, low, self.pivot_lookback, self.pivot_lookahead)

        # Volume analysis for accumulation/distribution
        self.volume_sma = self.I(ta.sma, volume, self.volume_ma_period)
        self.volume_ratio = self.I(lambda: volume / self.volume_sma)

        # On-Balance Volume for accumulation/distribution confirmation
        self.obv = self.I(ta.obv, close, volume)
        self.obv_sma = self.I(ta.sma, pd.Series(self.obv), 20)

        # Accumulation/Distribution indicator
        self.ad = self.I(self.calculate_ad, high, low, close, volume)
        self.ad_sma = self.I(ta.sma, pd.Series(self.ad), 20)

        # RSI for momentum
        self.rsi = self.I(ta.rsi, close, 14)

        # ATR for volatility-based stops
        self.atr = self.I(ta.atr, high, low, close, 14)

    def calculate_poc(self, close, volume, high, low, period):
        """Calculate Point of Control"""
        result = []
        for i in range(len(close)):
            if i < period - 1:
                result.append(close.iloc[i])
            else:
                period_close = close.iloc[i-period+1:i+1]
                period_high = high.iloc[i-period+1:i+1]
                period_low = low.iloc[i-period+1:i+1]
                period_volume = volume.iloc[i-period+1:i+1]

                price_range = period_high.max() - period_low.min()
                if price_range > 0:
                    num_bins = min(30, period)
                    bins = np.linspace(period_low.min(), period_high.max(), num_bins)

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
                        poc = max(volume_profile, key=volume_profile.get)
                    else:
                        poc = period_close.mean()
                else:
                    poc = period_close.mean()

                result.append(poc)

        return pd.Series(result, index=close.index)

    def calculate_vah(self, close, volume, high, low, period, value_area_pct):
        """Calculate Value Area High"""
        result = []
        for i in range(len(close)):
            if i < period - 1:
                result.append(high.iloc[i])
            else:
                period_close = close.iloc[i-period+1:i+1]
                period_high = high.iloc[i-period+1:i+1]
                period_low = low.iloc[i-period+1:i+1]
                period_volume = volume.iloc[i-period+1:i+1]

                price_range = period_high.max() - period_low.min()
                if price_range > 0:
                    num_bins = min(30, period)
                    bins = np.linspace(period_low.min(), period_high.max(), num_bins)

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
                        total_volume = sum(volume_profile.values())
                        va_volume = total_volume * value_area_pct
                        sorted_prices = sorted(volume_profile.items(), key=lambda x: x[1], reverse=True)
                        accumulated_volume = 0
                        va_prices = []

                        for price, vol in sorted_prices:
                            accumulated_volume += vol
                            va_prices.append(price)
                            if accumulated_volume >= va_volume:
                                break

                        vah = max(va_prices) if va_prices else period_high.max()
                    else:
                        vah = period_high.max()
                else:
                    vah = period_high.max()

                result.append(vah)

        return pd.Series(result, index=close.index)

    def calculate_val(self, close, volume, high, low, period, value_area_pct):
        """Calculate Value Area Low"""
        result = []
        for i in range(len(close)):
            if i < period - 1:
                result.append(low.iloc[i])
            else:
                period_close = close.iloc[i-period+1:i+1]
                period_high = high.iloc[i-period+1:i+1]
                period_low = low.iloc[i-period+1:i+1]
                period_volume = volume.iloc[i-period+1:i+1]

                price_range = period_high.max() - period_low.min()
                if price_range > 0:
                    num_bins = min(30, period)
                    bins = np.linspace(period_low.min(), period_high.max(), num_bins)

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
                        total_volume = sum(volume_profile.values())
                        va_volume = total_volume * value_area_pct
                        sorted_prices = sorted(volume_profile.items(), key=lambda x: x[1], reverse=True)
                        accumulated_volume = 0
                        va_prices = []

                        for price, vol in sorted_prices:
                            accumulated_volume += vol
                            va_prices.append(price)
                            if accumulated_volume >= va_volume:
                                break

                        val = min(va_prices) if va_prices else period_low.min()
                    else:
                        val = period_low.min()
                else:
                    val = period_low.min()

                result.append(val)

        return pd.Series(result, index=close.index)

    def detect_strong_pivot_highs(self, high, low, lookback, lookahead):
        """Detect strong pivot high points"""
        result = []
        for i in range(len(high)):
            if i < lookback or i >= len(high) - lookahead:
                result.append(0)
            else:
                is_pivot = True
                current_high = high.iloc[i]
                strength_count = 0

                # Check for lower highs before
                for j in range(1, lookback + 1):
                    if high.iloc[i-j] < current_high:
                        strength_count += 1
                    elif high.iloc[i-j] >= current_high:
                        is_pivot = False
                        break

                # Check for lower highs after
                if is_pivot:
                    for j in range(1, lookahead + 1):
                        if high.iloc[i+j] > current_high:
                            is_pivot = False
                            break

                # Require minimum strength
                if strength_count < self.pivot_strength:
                    is_pivot = False

                result.append(1 if is_pivot else 0)

        return pd.Series(result, index=high.index)

    def detect_strong_pivot_lows(self, high, low, lookback, lookahead):
        """Detect strong pivot low points"""
        result = []
        for i in range(len(low)):
            if i < lookback or i >= len(low) - lookahead:
                result.append(0)
            else:
                is_pivot = True
                current_low = low.iloc[i]
                strength_count = 0

                # Check for higher lows before
                for j in range(1, lookback + 1):
                    if low.iloc[i-j] > current_low:
                        strength_count += 1
                    elif low.iloc[i-j] <= current_low:
                        is_pivot = False
                        break

                # Check for higher lows after
                if is_pivot:
                    for j in range(1, lookahead + 1):
                        if low.iloc[i+j] < current_low:
                            is_pivot = False
                            break

                # Require minimum strength
                if strength_count < self.pivot_strength:
                    is_pivot = False

                result.append(1 if is_pivot else 0)

        return pd.Series(result, index=low.index)

    def calculate_ad(self, high, low, close, volume):
        """Calculate Accumulation/Distribution indicator"""
        money_flow_mult = ((close - low) - (high - close)) / (high - low)
        money_flow_mult = money_flow_mult.fillna(0)
        money_flow_volume = money_flow_mult * volume
        ad = money_flow_volume.cumsum()
        return ad

    def next(self):
        # Skip if not enough data
        if len(self.data) < self.profile_period + 20:
            return

        # Current values
        current_price = self.data.Close[-1]
        current_poc = self.poc[-1]
        current_vah = self.vah[-1]
        current_val = self.val[-1]
        current_volume_ratio = self.volume_ratio[-1]
        current_rsi = self.rsi[-1]
        current_atr = self.atr[-1]

        # Check for pivot points (looking back a few bars for confirmation)
        is_pivot_low = self.pivot_lows[-3] == 1 if len(self.pivot_lows) >= 3 else False
        is_pivot_high = self.pivot_highs[-3] == 1 if len(self.pivot_highs) >= 3 else False

        # Check OBV and A/D trends for accumulation/distribution
        obv_rising = self.obv[-1] > self.obv_sma[-1] if len(self.obv_sma) > 0 else False
        ad_rising = self.ad[-1] > self.ad_sma[-1] if len(self.ad_sma) > 0 else False

        if not self.position:
            # Long Entry: Pivot low with accumulation
            if is_pivot_low:
                # Check for accumulation signals
                volume_accumulation = current_volume_ratio > self.accumulation_threshold
                indicator_accumulation = obv_rising and ad_rising
                rsi_not_overbought = current_rsi < 70

                # Price should be near or below POC for better entry
                near_poc = abs(current_price - current_poc) < current_poc * self.poc_buffer_pct
                below_poc = current_price < current_poc

                if volume_accumulation and indicator_accumulation and rsi_not_overbought and (near_poc or below_poc):
                    # Set stops
                    if self.use_poc_as_stop and current_price > current_poc:
                        sl_price = current_poc * (1 - self.poc_buffer_pct)
                    else:
                        sl_price = current_price * (1 - self.stop_loss_pct)

                    # Target the next resistance (VAH or recent high)
                    tp_price = min(current_vah, current_price * (1 + self.take_profit_pct))

                    # Ensure positive risk/reward
                    if tp_price > current_price * 1.01:
                        self.buy(sl=sl_price, tp=tp_price)

            # Short Entry: Pivot high with distribution
            elif is_pivot_high:
                # Check for distribution signals
                volume_distribution = current_volume_ratio > self.distribution_threshold
                indicator_distribution = not obv_rising and not ad_rising
                rsi_not_oversold = current_rsi > 30

                # Price should be near or above POC for better entry
                near_poc = abs(current_price - current_poc) < current_poc * self.poc_buffer_pct
                above_poc = current_price > current_poc

                if volume_distribution and indicator_distribution and rsi_not_oversold and (near_poc or above_poc):
                    # Set stops
                    if self.use_poc_as_stop and current_price < current_poc:
                        sl_price = current_poc * (1 + self.poc_buffer_pct)
                    else:
                        sl_price = current_price * (1 + self.stop_loss_pct)

                    # Target the next support (VAL or recent low)
                    tp_price = max(current_val, current_price * (1 - self.take_profit_pct))

                    # Ensure positive risk/reward
                    if tp_price < current_price * 0.99:
                        self.sell(sl=sl_price, tp=tp_price)

        else:
            # Dynamic stop management using POC
            if self.use_poc_as_stop:
                if self.position.is_long:
                    # Update stop to POC if price is above it
                    if current_price > current_poc:
                        new_sl = current_poc * (1 - self.poc_buffer_pct)
                        if hasattr(self.position, 'sl') and new_sl > self.position.sl:
                            self.position.sl = new_sl

                    # Exit at pivot high with distribution
                    if is_pivot_high and current_volume_ratio > self.distribution_threshold:
                        self.position.close()

                elif self.position.is_short:
                    # Update stop to POC if price is below it
                    if current_price < current_poc:
                        new_sl = current_poc * (1 + self.poc_buffer_pct)
                        if hasattr(self.position, 'sl') and new_sl < self.position.sl:
                            self.position.sl = new_sl

                    # Exit at pivot low with accumulation
                    if is_pivot_low and current_volume_ratio > self.accumulation_threshold:
                        self.position.close()

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

print("Volume Profile Pivot Strategy Loading...")
print(f"Loading data from: {DATA_PATH}")

# Load and prepare data
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()

print(f"Data loaded! {len(data)} rows")

# Run single backtest
bt = Backtest(data, VolumeProfilePivot, cash=1000000, commission=0.001)

print("\n===== Volume Profile Pivot Strategy - DEFAULT PARAMETERS =====")
print(f"Profile Period: {VolumeProfilePivot.profile_period}")
print(f"Pivot Lookback: {VolumeProfilePivot.pivot_lookback}")
print(f"Accumulation Threshold: {VolumeProfilePivot.accumulation_threshold}x")
print(f"Distribution Threshold: {VolumeProfilePivot.distribution_threshold}x")
print(f"Use POC as Stop: {VolumeProfilePivot.use_poc_as_stop}")

stats = bt.run()
print(stats)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING VOLUME PROFILE PIVOT ON ALL DATA SOURCES")
    print("="*80)

    results = test_on_all_data(VolumeProfilePivot, 'VolumeProfilePivot')

    if results is not None:
        print("\nTesting complete! Results saved in: ./results/VolumeProfilePivot.csv")