"""
Volume Profile Spike Strategy
Enters when volume exceeds moving average by 1.618x (golden ratio from the indicator).
Direction based on price position relative to POC.
Exits on volume normalization or price targets.
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

class VolumeProfileSpike(Strategy):
    # Volume Spike Parameters
    volume_spike_multiplier = 1.618  # Golden ratio from indicator
    volume_ma_period = 20  # Period for volume moving average
    volume_normalization_threshold = 1.1  # Exit when volume returns to near normal

    # Volume Profile Parameters
    profile_period = 30  # Number of bars to calculate volume profile
    value_area_pct = 0.68  # 68% of volume for value area

    # Trading Parameters
    poc_position_buffer = 0.002  # 0.2% buffer to determine position relative to POC
    stop_loss_pct = 0.015  # 1.5% stop loss
    take_profit_pct = 0.03  # 3% take profit
    use_dynamic_targets = True  # Use value area for targets

    # Additional Filters
    min_bars_between_trades = 5  # Avoid overtrading
    use_momentum_confirmation = True
    momentum_period = 10

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

        # Volume analysis
        self.volume_sma = self.I(ta.sma, volume, self.volume_ma_period)
        self.volume_ema = self.I(ta.ema, volume, self.volume_ma_period)
        self.volume_ratio = self.I(lambda: volume / self.volume_sma)

        # Detect volume spikes using the golden ratio
        self.volume_spike = self.I(lambda: (volume > self.volume_sma * self.volume_spike_multiplier).astype(int))

        # Price position relative to POC
        self.price_to_poc = self.I(lambda: (close - self.poc) / self.poc)

        # Volume-weighted indicators
        self.vwap = self.I(self.calculate_vwap, close, volume, high, low)
        self.vwma = self.I(self.calculate_vwma, close, volume, 20)

        # Momentum indicators
        self.roc = self.I(ta.roc, close, self.momentum_period)
        self.rsi = self.I(ta.rsi, close, 14)

        # ATR for volatility-based stops
        self.atr = self.I(ta.atr, high, low, close, 14)

        # Track bars since last trade
        self.bars_since_entry = 0

    def calculate_vwap(self, close, volume, high, low):
        """Calculate Volume Weighted Average Price"""
        typical_price = (high + low + close) / 3
        cumulative_volume = volume.cumsum()
        cumulative_tp_volume = (typical_price * volume).cumsum()

        vwap = np.where(cumulative_volume > 0,
                        cumulative_tp_volume / cumulative_volume,
                        typical_price)
        return pd.Series(vwap, index=close.index)

    def calculate_vwma(self, close, volume, period):
        """Calculate Volume Weighted Moving Average"""
        result = []
        for i in range(len(close)):
            if i < period - 1:
                result.append(close.iloc[i])
            else:
                period_close = close.iloc[i-period+1:i+1]
                period_volume = volume.iloc[i-period+1:i+1]

                if period_volume.sum() > 0:
                    vwma = (period_close * period_volume).sum() / period_volume.sum()
                else:
                    vwma = period_close.mean()

                result.append(vwma)

        return pd.Series(result, index=close.index)

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

    def next(self):
        # Skip if not enough data
        if len(self.data) < self.profile_period + 10:
            return

        # Update bars since entry
        if self.position:
            self.bars_since_entry += 1
        else:
            self.bars_since_entry = 0

        # Current values
        current_price = self.data.Close[-1]
        current_poc = self.poc[-1]
        current_vah = self.vah[-1]
        current_val = self.val[-1]
        current_volume_ratio = self.volume_ratio[-1]
        current_volume_spike = self.volume_spike[-1]
        current_price_to_poc = self.price_to_poc[-1]
        current_roc = self.roc[-1] if len(self.roc) > 0 else 0
        current_rsi = self.rsi[-1]
        current_atr = self.atr[-1]
        current_vwap = self.vwap[-1]

        if not self.position:
            # Check for volume spike (golden ratio 1.618x)
            if current_volume_spike == 1:
                # Determine direction based on price position relative to POC

                # Long: Volume spike when price is below POC
                if current_price_to_poc < -self.poc_position_buffer:
                    # Additional confirmations
                    momentum_ok = not self.use_momentum_confirmation or current_roc > -2
                    rsi_not_oversold = current_rsi > 20  # Avoid extreme oversold

                    # Price should be above VAL for support
                    above_val = current_price > current_val

                    if momentum_ok and rsi_not_oversold and above_val:
                        # Set stops and targets
                        sl_price = current_price * (1 - self.stop_loss_pct)

                        if self.use_dynamic_targets:
                            # Target POC or VAH
                            tp_price = min(current_poc, current_vah)
                        else:
                            tp_price = current_price * (1 + self.take_profit_pct)

                        # Ensure positive risk/reward
                        if tp_price > current_price * 1.01:
                            self.buy(sl=sl_price, tp=tp_price)

                # Short: Volume spike when price is above POC
                elif current_price_to_poc > self.poc_position_buffer:
                    # Additional confirmations
                    momentum_ok = not self.use_momentum_confirmation or current_roc < 2
                    rsi_not_overbought = current_rsi < 80  # Avoid extreme overbought

                    # Price should be below VAH for resistance
                    below_vah = current_price < current_vah

                    if momentum_ok and rsi_not_overbought and below_vah:
                        # Set stops and targets
                        sl_price = current_price * (1 + self.stop_loss_pct)

                        if self.use_dynamic_targets:
                            # Target POC or VAL
                            tp_price = max(current_poc, current_val)
                        else:
                            tp_price = current_price * (1 - self.take_profit_pct)

                        # Ensure positive risk/reward
                        if tp_price < current_price * 0.99:
                            self.sell(sl=sl_price, tp=tp_price)

        else:
            # Exit on volume normalization
            volume_normalized = current_volume_ratio < self.volume_normalization_threshold

            # Exit if volume returns to normal after minimum holding period
            if volume_normalized and self.bars_since_entry > self.min_bars_between_trades:
                self.position.close()

            # Additional exit conditions
            if self.position.is_long:
                # Exit if price reaches POC from below
                if current_price >= current_poc and self.position.entry_price < current_poc:
                    self.position.close()

                # Exit on bearish volume spike
                elif current_volume_spike == 1 and current_price < self.position.entry_price:
                    self.position.close()

            elif self.position.is_short:
                # Exit if price reaches POC from above
                if current_price <= current_poc and self.position.entry_price > current_poc:
                    self.position.close()

                # Exit on bullish volume spike
                elif current_volume_spike == 1 and current_price > self.position.entry_price:
                    self.position.close()

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

print("Volume Profile Spike Strategy Loading...")
print(f"Loading data from: {DATA_PATH}")

# Load and prepare data
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()

print(f"Data loaded! {len(data)} rows")

# Run single backtest
bt = Backtest(data, VolumeProfileSpike, cash=1000000, commission=0.001)

print("\n===== Volume Profile Spike Strategy - DEFAULT PARAMETERS =====")
print(f"Volume Spike Multiplier: {VolumeProfileSpike.volume_spike_multiplier}x (Golden Ratio)")
print(f"Volume MA Period: {VolumeProfileSpike.volume_ma_period}")
print(f"Profile Period: {VolumeProfileSpike.profile_period}")
print(f"Stop Loss: {VolumeProfileSpike.stop_loss_pct * 100}%")
print(f"Take Profit: {VolumeProfileSpike.take_profit_pct * 100}%")

stats = bt.run()
print(stats)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING VOLUME PROFILE SPIKE ON ALL DATA SOURCES")
    print("="*80)

    results = test_on_all_data(VolumeProfileSpike, 'VolumeProfileSpike')

    if results is not None:
        print("\nTesting complete! Results saved in: ./results/VolumeProfileSpike.csv")