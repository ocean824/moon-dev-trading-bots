import pandas as pd
import numpy as np
import talib
from backtesting import Strategy

print("🚀 Moon Dev's FlowScope Base Strategy Loading... 🌙")

class FlowScopeBase(Strategy):
    """
    FlowScope Base Strategy - Volume Profile with POC Analysis

    This strategy creates volume profiles showing buy/sell volume distribution
    at different price levels, identifies the Point of Control (POC), and
    trades based on volume imbalances at these key levels.
    """

    # Parameters
    profile_period = 20  # Number of candles to include in volume profile
    volume_bins = 10  # Number of price levels in the profile
    imbalance_threshold = 0.65  # 65% buy volume for long, 35% for short
    take_profit = 0.03
    stop_loss = 0.02
    min_volume_percentile = 50  # Minimum volume percentile for valid signals

    def init(self):
        # Initialize volume moving average for filtering
        self.volume_ma = self.I(talib.SMA, self.data.Volume, timeperiod=self.profile_period)

        # Calculate volume profile and POC
        def calculate_volume_profile(high, low, close, open_, volume, period, bins):
            """
            Calculate volume profile with buy/sell distribution
            Returns: POC price, buy percentage at POC, total volume at POC
            """
            result_poc = np.zeros(len(high))
            result_buy_pct = np.zeros(len(high))
            result_poc_volume = np.zeros(len(high))

            for i in range(period, len(high)):
                # Get data for the profile period
                period_high = high[i-period+1:i+1]
                period_low = low[i-period+1:i+1]
                period_close = close[i-period+1:i+1]
                period_open = open_[i-period+1:i+1]
                period_volume = volume[i-period+1:i+1]

                # Define price range for the profile
                profile_high = np.max(period_high)
                profile_low = np.min(period_low)

                if profile_high == profile_low:
                    result_poc[i] = profile_high
                    result_buy_pct[i] = 0.5
                    result_poc_volume[i] = np.sum(period_volume)
                    continue

                # Create price bins
                price_levels = np.linspace(profile_low, profile_high, bins)
                bin_width = (profile_high - profile_low) / (bins - 1)

                # Initialize volume arrays for each price level
                buy_volume_profile = np.zeros(bins)
                sell_volume_profile = np.zeros(bins)

                # Distribute volume across price levels for each candle
                for j in range(period):
                    candle_high = period_high[j]
                    candle_low = period_low[j]
                    candle_close = period_close[j]
                    candle_open = period_open[j]
                    candle_volume = period_volume[j]

                    # Calculate buy/sell volume using close position within candle
                    candle_range = candle_high - candle_low
                    if candle_range > 0:
                        # Buy volume proportion (close proximity to high)
                        buy_ratio = (candle_close - candle_low) / candle_range
                        sell_ratio = (candle_high - candle_close) / candle_range
                    else:
                        buy_ratio = 0.5
                        sell_ratio = 0.5

                    buy_vol = candle_volume * buy_ratio
                    sell_vol = candle_volume * sell_ratio

                    # Distribute volume across touched price levels
                    for k, price in enumerate(price_levels):
                        # Check if this price level was touched by the candle
                        if candle_low <= price <= candle_high:
                            # Simple uniform distribution across touched levels
                            touched_levels = np.sum((candle_low <= price_levels) & (price_levels <= candle_high))
                            if touched_levels > 0:
                                buy_volume_profile[k] += buy_vol / touched_levels
                                sell_volume_profile[k] += sell_vol / touched_levels

                # Find POC (price level with maximum total volume)
                total_volume_profile = buy_volume_profile + sell_volume_profile
                poc_index = np.argmax(total_volume_profile)

                # Store results
                result_poc[i] = price_levels[poc_index]
                poc_total_vol = total_volume_profile[poc_index]

                if poc_total_vol > 0:
                    result_buy_pct[i] = buy_volume_profile[poc_index] / poc_total_vol
                else:
                    result_buy_pct[i] = 0.5

                result_poc_volume[i] = poc_total_vol

            return result_poc, result_buy_pct, result_poc_volume

        # Calculate volume profile indicators
        poc, buy_pct, poc_vol = calculate_volume_profile(
            self.data.High, self.data.Low, self.data.Close,
            self.data.Open, self.data.Volume,
            self.profile_period, self.volume_bins
        )

        self.poc_price = self.I(lambda: poc)
        self.poc_buy_percentage = self.I(lambda: buy_pct)
        self.poc_volume = self.I(lambda: poc_vol)

        # Track entry price for exits
        self.entry_price = None

    def next(self):
        # Skip if we don't have enough data
        if len(self.data) < self.profile_period:
            return

        # Current values
        current_price = self.data.Close[-1]
        current_volume = self.data.Volume[-1]
        poc_price = self.poc_price[-1]
        buy_percentage = self.poc_buy_percentage[-1]
        poc_volume = self.poc_volume[-1]
        volume_avg = self.volume_ma[-1]

        # Check if we have a position
        if self.position:
            # Exit logic
            if self.position.is_long:
                # Take profit for long
                if current_price >= self.entry_price * (1 + self.take_profit):
                    self.position.close()
                    self.entry_price = None
                # Stop loss for long
                elif current_price <= self.entry_price * (1 - self.stop_loss):
                    self.position.close()
                    self.entry_price = None

            elif self.position.is_short:
                # Take profit for short (price goes down)
                if current_price <= self.entry_price * (1 - self.take_profit):
                    self.position.close()
                    self.entry_price = None
                # Stop loss for short (price goes up)
                elif current_price >= self.entry_price * (1 + self.stop_loss):
                    self.position.close()
                    self.entry_price = None

        else:
            # Entry logic - Volume imbalance at POC

            # Check if current volume is significant
            volume_percentile = (current_volume >= volume_avg * 0.5)

            # Price near POC (within 0.5% of POC)
            near_poc = abs(current_price - poc_price) / poc_price <= 0.005

            if near_poc and volume_percentile and poc_volume > 0:
                # Long signal: Strong buy volume imbalance at POC
                if buy_percentage >= self.imbalance_threshold:
                    # Additional confirmation: price bouncing from below POC
                    if self.data.Low[-1] <= poc_price <= self.data.High[-1]:
                        self.buy()
                        self.entry_price = current_price

                # Short signal: Strong sell volume imbalance at POC
                elif buy_percentage <= (1 - self.imbalance_threshold):
                    # Additional confirmation: price rejected from above POC
                    if self.data.Low[-1] <= poc_price <= self.data.High[-1]:
                        self.sell()
                        self.entry_price = current_price


# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING FLOWSCOPE BASE STRATEGY ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    results = test_on_all_data(FlowScopeBase, 'FlowScopeBase')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/FlowScopeBase.csv")