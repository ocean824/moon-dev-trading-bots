import pandas as pd
import numpy as np
import talib
from backtesting import Strategy

print("🚀 Moon Dev's FlowScope VWAP Strategy Loading... 🌙")

class FlowScopeVWAP(Strategy):
    """
    FlowScope VWAP Strategy - Volume Profile with VWAP Context

    This strategy combines volume profile POC analysis with VWAP (Volume Weighted Average Price)
    to provide additional price context. VWAP acts as a dynamic support/resistance level
    that complements the POC levels for better entry and exit timing.
    """

    # Parameters
    profile_period = 20  # Number of candles to include in volume profile
    volume_bins = 10  # Number of price levels in the profile
    imbalance_threshold = 0.65  # 65% buy volume for long, 35% for short
    take_profit = 0.03
    stop_loss = 0.02
    min_volume_percentile = 50  # Minimum volume percentile for valid signals
    vwap_period = 20  # VWAP calculation period
    vwap_std_multiplier = 2.0  # Standard deviation bands multiplier

    def init(self):
        # Initialize volume moving average for filtering
        self.volume_ma = self.I(talib.SMA, self.data.Volume, timeperiod=self.profile_period)

        # Calculate VWAP and bands
        def calculate_vwap_with_bands(high, low, close, volume, period, std_mult):
            """
            Calculate VWAP with upper and lower bands based on standard deviation
            """
            typical_price = (high + low + close) / 3
            vwap = np.zeros(len(close))
            vwap_upper = np.zeros(len(close))
            vwap_lower = np.zeros(len(close))

            for i in range(period, len(close)):
                # Calculate VWAP for the period
                period_volume = volume[i-period+1:i+1]
                period_typical = typical_price[i-period+1:i+1]

                total_volume = np.sum(period_volume)
                if total_volume > 0:
                    vwap[i] = np.sum(period_typical * period_volume) / total_volume

                    # Calculate standard deviation for bands
                    squared_diff = np.power(period_typical - vwap[i], 2)
                    variance = np.sum(squared_diff * period_volume) / total_volume
                    std_dev = np.sqrt(variance)

                    vwap_upper[i] = vwap[i] + (std_dev * std_mult)
                    vwap_lower[i] = vwap[i] - (std_dev * std_mult)
                else:
                    vwap[i] = close[i]
                    vwap_upper[i] = close[i]
                    vwap_lower[i] = close[i]

            return vwap, vwap_upper, vwap_lower

        vwap, vwap_upper, vwap_lower = calculate_vwap_with_bands(
            self.data.High, self.data.Low, self.data.Close,
            self.data.Volume, self.vwap_period, self.vwap_std_multiplier
        )

        self.vwap = self.I(lambda: vwap)
        self.vwap_upper = self.I(lambda: vwap_upper)
        self.vwap_lower = self.I(lambda: vwap_lower)

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

                # Initialize volume arrays for each price level
                buy_volume_profile = np.zeros(bins)
                sell_volume_profile = np.zeros(bins)

                # Distribute volume across price levels for each candle
                for j in range(period):
                    candle_high = period_high[j]
                    candle_low = period_low[j]
                    candle_close = period_close[j]
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
        if len(self.data) < max(self.profile_period, self.vwap_period):
            return

        # Current values
        current_price = self.data.Close[-1]
        current_volume = self.data.Volume[-1]
        poc_price = self.poc_price[-1]
        buy_percentage = self.poc_buy_percentage[-1]
        poc_volume = self.poc_volume[-1]
        volume_avg = self.volume_ma[-1]

        # VWAP values
        current_vwap = self.vwap[-1]
        current_vwap_upper = self.vwap_upper[-1]
        current_vwap_lower = self.vwap_lower[-1]

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
                # Exit if price breaks below VWAP after being above
                elif current_price < current_vwap and self.data.Close[-2] > self.vwap[-2]:
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
                # Exit if price breaks above VWAP after being below
                elif current_price > current_vwap and self.data.Close[-2] < self.vwap[-2]:
                    self.position.close()
                    self.entry_price = None

        else:
            # Entry logic - Volume imbalance at POC with VWAP context

            # Check if current volume is significant
            volume_percentile = (current_volume >= volume_avg * 0.5)

            # Price near POC (within 0.5% of POC)
            near_poc = abs(current_price - poc_price) / poc_price <= 0.005

            # VWAP position
            above_vwap = current_price > current_vwap
            below_vwap = current_price < current_vwap
            near_vwap_lower = abs(current_price - current_vwap_lower) / current_vwap_lower <= 0.01
            near_vwap_upper = abs(current_price - current_vwap_upper) / current_vwap_upper <= 0.01

            if near_poc and volume_percentile and poc_volume > 0:
                # Long signal: Strong buy volume imbalance at POC
                long_conditions = [
                    buy_percentage >= self.imbalance_threshold,
                    self.data.Low[-1] <= poc_price <= self.data.High[-1],  # POC touched
                ]

                # Enhanced long conditions with VWAP
                vwap_long_conditions = [
                    below_vwap and near_vwap_lower,  # Bouncing from lower band
                    current_price > self.data.Low[-1] + (self.data.High[-1] - self.data.Low[-1]) * 0.3,  # Not at candle low
                ]

                if all(long_conditions):
                    # Extra confirmation if we're below VWAP and near lower band
                    if any(vwap_long_conditions):
                        self.buy()
                        self.entry_price = current_price
                    # Or if POC is above VWAP (strong support)
                    elif poc_price > current_vwap:
                        self.buy()
                        self.entry_price = current_price

                # Short signal: Strong sell volume imbalance at POC
                short_conditions = [
                    buy_percentage <= (1 - self.imbalance_threshold),
                    self.data.Low[-1] <= poc_price <= self.data.High[-1],  # POC touched
                ]

                # Enhanced short conditions with VWAP
                vwap_short_conditions = [
                    above_vwap and near_vwap_upper,  # Rejected from upper band
                    current_price < self.data.High[-1] - (self.data.High[-1] - self.data.Low[-1]) * 0.3,  # Not at candle high
                ]

                if all(short_conditions):
                    # Extra confirmation if we're above VWAP and near upper band
                    if any(vwap_short_conditions):
                        self.sell()
                        self.entry_price = current_price
                    # Or if POC is below VWAP (strong resistance)
                    elif poc_price < current_vwap:
                        self.sell()
                        self.entry_price = current_price


# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING FLOWSCOPE VWAP STRATEGY ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    results = test_on_all_data(FlowScopeVWAP, 'FlowScopeVWAP')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/FlowScopeVWAP.csv")