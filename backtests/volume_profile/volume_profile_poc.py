"""
Volume Profile POC Mean Reversion Strategy
Trades mean reversion to the Point of Control (POC) - the price level with highest volume.
Enters when price moves away from POC by a certain percentage and targets return to POC.
Uses volume confirmation for entries.
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

class VolumeProfilePOC(Strategy):
    # Volume Profile Parameters
    profile_period = 30  # Number of bars to calculate volume profile
    poc_distance_pct = 0.015  # 1.5% distance from POC to trigger entry
    poc_extreme_pct = 0.03  # 3% extreme distance for additional entries

    # Volume Parameters
    volume_ma_period = 20  # Moving average period for volume
    volume_threshold = 1.1  # Minimum volume multiplier to confirm entry

    # Risk Management
    stop_loss_pct = 0.02  # 2% stop loss
    take_profit_at_poc = True  # Exit at POC level
    trailing_stop_pct = 0.015  # 1.5% trailing stop

    # Additional Filters
    use_rsi_filter = True
    rsi_oversold = 35
    rsi_overbought = 65

    def init(self):
        # Price and volume data
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        volume = pd.Series(self.data.Volume)

        # Calculate POC (Point of Control)
        self.poc = self.I(self.calculate_poc, close, volume, high, low, self.profile_period)

        # Calculate distance from POC
        self.poc_distance = self.I(lambda: (close - self.poc) / self.poc)

        # Volume analysis
        self.volume_sma = self.I(ta.sma, volume, self.volume_ma_period)
        self.volume_ratio = self.I(lambda: volume / self.volume_sma)

        # RSI for additional filtering
        self.rsi = self.I(ta.rsi, close, 14)

        # ATR for dynamic stops
        self.atr = self.I(ta.atr, high, low, close, 14)

        # Bollinger Bands around POC for additional context
        poc_series = pd.Series(self.poc)
        self.poc_upper = self.I(lambda: self.poc + 2 * poc_series.rolling(20).std())
        self.poc_lower = self.I(lambda: self.poc - 2 * poc_series.rolling(20).std())

    def calculate_poc(self, close, volume, high, low, period):
        """Calculate Point of Control (highest volume price level)"""
        result = []

        for i in range(len(close)):
            if i < period - 1:
                # Not enough data, use current close
                result.append(close.iloc[i])
            else:
                # Get data for the period
                period_close = close.iloc[i-period+1:i+1]
                period_high = high.iloc[i-period+1:i+1]
                period_low = low.iloc[i-period+1:i+1]
                period_volume = volume.iloc[i-period+1:i+1]

                # Create price levels
                price_range = period_high.max() - period_low.min()
                if price_range > 0:
                    # Create bins for volume profile
                    num_bins = min(30, period)
                    bins = np.linspace(period_low.min(), period_high.max(), num_bins)

                    # Build volume profile
                    volume_profile = {}
                    for j in range(len(period_close)):
                        # Use typical price for better accuracy
                        typical_price = (period_high.iloc[j] + period_low.iloc[j] + period_close.iloc[j]) / 3

                        # Find the bin
                        bin_idx = np.digitize(typical_price, bins) - 1
                        bin_idx = min(max(0, bin_idx), len(bins)-2)
                        bin_price = (bins[bin_idx] + bins[bin_idx+1]) / 2

                        if bin_price not in volume_profile:
                            volume_profile[bin_price] = 0
                        volume_profile[bin_price] += period_volume.iloc[j]

                    # Find POC (price with highest volume)
                    if volume_profile:
                        poc = max(volume_profile, key=volume_profile.get)
                    else:
                        poc = period_close.mean()
                else:
                    poc = period_close.mean()

                result.append(poc)

        return pd.Series(result, index=close.index)

    def next(self):
        # Skip if we don't have enough data
        if len(self.data) < self.profile_period + 10:
            return

        # Current values
        current_price = self.data.Close[-1]
        current_poc = self.poc[-1]
        current_distance = self.poc_distance[-1]
        current_volume_ratio = self.volume_ratio[-1]
        current_rsi = self.rsi[-1]
        current_atr = self.atr[-1]

        # Position management
        if not self.position:
            # Long entry: Price below POC with volume confirmation
            if current_distance < -self.poc_distance_pct:
                volume_confirmed = current_volume_ratio > self.volume_threshold
                rsi_confirmed = not self.use_rsi_filter or current_rsi < self.rsi_oversold

                if volume_confirmed and rsi_confirmed:
                    # Dynamic stop loss based on ATR
                    atr_stop = max(self.stop_loss_pct * current_price, 1.5 * current_atr)
                    sl_price = current_price - atr_stop

                    # Take profit at POC or use trailing stop
                    if self.take_profit_at_poc:
                        tp_price = current_poc
                    else:
                        tp_price = current_price * (1 + abs(current_distance))

                    # Ensure positive risk/reward
                    if tp_price > current_price * 1.005:  # At least 0.5% potential
                        self.buy(sl=sl_price, tp=tp_price)

            # Short entry: Price above POC with volume confirmation
            elif current_distance > self.poc_distance_pct:
                volume_confirmed = current_volume_ratio > self.volume_threshold
                rsi_confirmed = not self.use_rsi_filter or current_rsi > self.rsi_overbought

                if volume_confirmed and rsi_confirmed:
                    # Dynamic stop loss based on ATR
                    atr_stop = max(self.stop_loss_pct * current_price, 1.5 * current_atr)
                    sl_price = current_price + atr_stop

                    # Take profit at POC or use trailing stop
                    if self.take_profit_at_poc:
                        tp_price = current_poc
                    else:
                        tp_price = current_price * (1 - abs(current_distance))

                    # Ensure positive risk/reward
                    if tp_price < current_price * 0.995:  # At least 0.5% potential
                        self.sell(sl=sl_price, tp=tp_price)

        else:
            # Position management
            if self.position.is_long:
                # Check if we've reached POC
                if abs(current_price - current_poc) < current_poc * 0.002:  # Within 0.2% of POC
                    self.position.close()
                # Trail stop if price moves favorably
                # Simplified exit without trailing stop

            elif self.position.is_short:
                # Check if we've reached POC
                if abs(current_price - current_poc) < current_poc * 0.002:  # Within 0.2% of POC
                    self.position.close()
                # Trail stop if price moves favorably
                # Simplified exit without trailing stop

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

print("Volume Profile POC Mean Reversion Strategy Loading...")
print(f"Loading data from: {DATA_PATH}")

# Load and prepare data
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()

print(f"Data loaded! {len(data)} rows")

# Run single backtest
bt = Backtest(data, VolumeProfilePOC, cash=1000000, commission=0.001)

print("\n===== Volume Profile POC Mean Reversion - DEFAULT PARAMETERS =====")
print(f"Profile Period: {VolumeProfilePOC.profile_period}")
print(f"POC Distance Trigger: {VolumeProfilePOC.poc_distance_pct * 100}%")
print(f"Volume Threshold: {VolumeProfilePOC.volume_threshold}x")
print(f"Stop Loss: {VolumeProfilePOC.stop_loss_pct * 100}%")
print(f"Take Profit at POC: {VolumeProfilePOC.take_profit_at_poc}")

stats = bt.run()
print(stats)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING VOLUME PROFILE POC MEAN REVERSION ON ALL DATA SOURCES")
    print("="*80)

    results = test_on_all_data(VolumeProfilePOC, 'VolumeProfilePOC')

    if results is not None:
        print("\nTesting complete! Results saved in: ./results/VolumeProfilePOC.csv")