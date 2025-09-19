"""
Volume Profile Base Strategy
Based on TradingView Volume Profile indicator with pivot anchored analysis.
Enters when price crosses above VAL (Value Area Low) and exits at VAH (Value Area High).
Uses pivot points for additional confirmation and tracks volume patterns.
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

class VolumeProfileBase(Strategy):
    # Volume Profile Parameters
    profile_period = 30  # Number of bars to calculate volume profile
    value_area_pct = 0.68  # 68% of volume for value area (1 std dev)

    # Pivot Parameters
    pivot_lookback = 10  # Bars to look back for pivot high/low
    pivot_lookahead = 5  # Bars to look ahead for pivot confirmation

    # Trading Parameters
    volume_ma_period = 20  # Moving average period for volume
    volume_threshold = 1.2  # Minimum volume multiplier to trade
    stop_loss_pct = 0.02  # 2% stop loss
    take_profit_pct = 0.04  # 4% take profit

    def init(self):
        # Price and volume data
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        volume = pd.Series(self.data.Volume)

        # Calculate volume-weighted price for better profile
        self.vwap = self.I(self.calculate_vwap, close, volume, high, low)

        # Calculate volume profile levels
        self.poc = self.I(self.calculate_poc, close, volume, self.profile_period)
        self.vah = self.I(self.calculate_vah, close, volume, self.profile_period, self.value_area_pct)
        self.val = self.I(self.calculate_val, close, volume, self.profile_period, self.value_area_pct)

        # Detect pivot points
        self.pivot_highs = self.I(self.detect_pivot_highs, high, self.pivot_lookback, self.pivot_lookahead)
        self.pivot_lows = self.I(self.detect_pivot_lows, low, self.pivot_lookback, self.pivot_lookahead)

        # Volume analysis
        self.volume_sma = self.I(ta.sma, volume, self.volume_ma_period)
        self.volume_ratio = self.I(lambda: volume / self.volume_sma)

        # RSI for additional filtering
        self.rsi = self.I(ta.rsi, close, 14)

    def calculate_vwap(self, close, volume, high, low):
        """Calculate Volume Weighted Average Price"""
        typical_price = (high + low + close) / 3
        cumulative_volume = volume.cumsum()
        cumulative_tp_volume = (typical_price * volume).cumsum()

        vwap = np.where(cumulative_volume > 0,
                        cumulative_tp_volume / cumulative_volume,
                        typical_price)
        return pd.Series(vwap, index=close.index)

    def calculate_poc(self, close, volume, period):
        """Calculate Point of Control (highest volume price level) - Simplified"""
        # Use volume-weighted average price as a simpler POC approximation
        result = []
        for i in range(len(close)):
            if i < period - 1:
                result.append(close.iloc[i])
            else:
                period_close = close.iloc[i-period+1:i+1]
                period_volume = volume.iloc[i-period+1:i+1]

                # Simple volume-weighted average as POC
                if period_volume.sum() > 0:
                    poc = (period_close * period_volume).sum() / period_volume.sum()
                else:
                    poc = period_close.mean()

                result.append(poc)

        return pd.Series(result, index=close.index)

    def calculate_vah(self, close, volume, period, value_area_pct):
        """Calculate Value Area High - Simplified"""
        # Use percentile based on volume-weighted distribution
        result = []
        for i in range(len(close)):
            if i < period - 1:
                result.append(close.iloc[i])
            else:
                period_close = close.iloc[i-period+1:i+1]
                period_volume = volume.iloc[i-period+1:i+1]

                # Weight prices by volume and find upper percentile
                high_pct = 50 + (value_area_pct * 100 / 2)
                if period_volume.sum() > 0:
                    # Volume-weighted percentile approximation
                    sorted_data = period_close.sort_values()
                    cumsum_volume = period_volume.loc[sorted_data.index].cumsum()
                    total_volume = cumsum_volume.iloc[-1]

                    target_volume = total_volume * (high_pct / 100)
                    idx = (cumsum_volume >= target_volume).idxmax()
                    vah = sorted_data.loc[idx] if idx else period_close.max()
                else:
                    vah = period_close.quantile(high_pct / 100)

                result.append(vah)

        return pd.Series(result, index=close.index)

    def calculate_val(self, close, volume, period, value_area_pct):
        """Calculate Value Area Low - Simplified"""
        # Use percentile based on volume-weighted distribution
        result = []
        for i in range(len(close)):
            if i < period - 1:
                result.append(close.iloc[i])
            else:
                period_close = close.iloc[i-period+1:i+1]
                period_volume = volume.iloc[i-period+1:i+1]

                # Weight prices by volume and find lower percentile
                low_pct = 50 - (value_area_pct * 100 / 2)
                if period_volume.sum() > 0:
                    # Volume-weighted percentile approximation
                    sorted_data = period_close.sort_values()
                    cumsum_volume = period_volume.loc[sorted_data.index].cumsum()
                    total_volume = cumsum_volume.iloc[-1]

                    target_volume = total_volume * (low_pct / 100)
                    idx = (cumsum_volume >= target_volume).idxmax()
                    val = sorted_data.loc[idx] if idx else period_close.min()
                else:
                    val = period_close.quantile(low_pct / 100)

                result.append(val)

        return pd.Series(result, index=close.index)

    def detect_pivot_highs(self, high, lookback, lookahead):
        """Detect pivot high points"""
        result = []
        for i in range(len(high)):
            if i < lookback or i >= len(high) - lookahead:
                result.append(0)
            else:
                # Check if this is a pivot high
                is_pivot = True
                current_high = high.iloc[i]

                # Check previous bars
                for j in range(1, lookback + 1):
                    if high.iloc[i-j] >= current_high:
                        is_pivot = False
                        break

                # Check future bars
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
                # Check if this is a pivot low
                is_pivot = True
                current_low = low.iloc[i]

                # Check previous bars
                for j in range(1, lookback + 1):
                    if low.iloc[i-j] <= current_low:
                        is_pivot = False
                        break

                # Check future bars
                if is_pivot:
                    for j in range(1, lookahead + 1):
                        if low.iloc[i+j] < current_low:
                            is_pivot = False
                            break

                result.append(1 if is_pivot else 0)

        return pd.Series(result, index=low.index)

    def next(self):
        # Skip if we don't have enough data
        if len(self.data) < self.profile_period + 10:
            return

        # Current values
        current_price = self.data.Close[-1]
        current_volume_ratio = self.volume_ratio[-1]
        current_rsi = self.rsi[-1]

        # Volume profile levels
        current_poc = self.poc[-1]
        current_vah = self.vah[-1]
        current_val = self.val[-1]

        # Check if we have pivot points
        has_recent_pivot_low = any(self.pivot_lows[-5:]) if len(self.pivot_lows) >= 5 else False
        has_recent_pivot_high = any(self.pivot_highs[-5:]) if len(self.pivot_highs) >= 5 else False

        # Position management
        if not self.position:
            # Long entry conditions
            # 1. Price crosses above VAL
            # 2. Volume is above average
            # 3. Optional: Near a pivot low for better entry
            # 4. RSI not overbought
            price_above_val = current_price > current_val and self.data.Close[-2] <= self.val[-2]
            volume_confirmation = current_volume_ratio > self.volume_threshold
            rsi_not_overbought = current_rsi < 70

            if price_above_val and volume_confirmation and rsi_not_overbought:
                # Set stop loss and take profit
                sl_price = current_val * (1 - self.stop_loss_pct)
                tp_price = current_vah  # Target the VAH

                # Ensure we have a positive risk/reward
                if tp_price > current_price * 1.01:  # At least 1% potential profit
                    self.buy(sl=sl_price, tp=tp_price)

            # Short entry conditions (if price breaks below VAH with volume)
            price_below_vah = current_price < current_vah and self.data.Close[-2] >= self.vah[-2]
            rsi_not_oversold = current_rsi > 30

            if price_below_vah and volume_confirmation and rsi_not_oversold:
                # Set stop loss and take profit for short
                sl_price = current_vah * (1 + self.stop_loss_pct)
                tp_price = current_val  # Target the VAL

                # Ensure we have a positive risk/reward
                if tp_price < current_price * 0.99:  # At least 1% potential profit
                    self.sell(sl=sl_price, tp=tp_price)

        else:
            # Exit conditions for long positions
            if self.position.is_long:
                # Exit if price reaches VAH or breaks below VAL
                if current_price >= current_vah or current_price < current_val * 0.98:
                    self.position.close()

            # Exit conditions for short positions
            elif self.position.is_short:
                # Exit if price reaches VAL or breaks above VAH
                if current_price <= current_val or current_price > current_vah * 1.02:
                    self.position.close()

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

print("Volume Profile Base Strategy Loading...")
print(f"Loading data from: {DATA_PATH}")

# Load and prepare data
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()

print(f"Data loaded! {len(data)} rows")

# Run single backtest
bt = Backtest(data, VolumeProfileBase, cash=1000000, commission=0.001)

print("\n===== Volume Profile Base Strategy - DEFAULT PARAMETERS =====")
print(f"Profile Period: {VolumeProfileBase.profile_period}")
print(f"Value Area %: {VolumeProfileBase.value_area_pct * 100}%")
print(f"Volume Threshold: {VolumeProfileBase.volume_threshold}x")
print(f"Stop Loss: {VolumeProfileBase.stop_loss_pct * 100}%")
print(f"Take Profit: {VolumeProfileBase.take_profit_pct * 100}%")

stats = bt.run()
print(stats)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING VOLUME PROFILE BASE ON ALL DATA SOURCES")
    print("="*80)

    results = test_on_all_data(VolumeProfileBase, 'VolumeProfileBase')

    if results is not None:
        print("\nTesting complete! Results saved in: ./results/VolumeProfileBase.csv")