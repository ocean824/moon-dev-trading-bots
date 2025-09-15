import pandas as pd
import numpy as np
import talib
from backtesting import Strategy

print("🚀 Moon Dev's FlowScope MFI Strategy Loading... 🌙")

class FlowScopeMFI(Strategy):
    """
    FlowScope MFI Strategy - Volume Profile with Money Flow Index

    This strategy combines volume profile POC analysis with MFI (Money Flow Index)
    to confirm volume/price relationships. MFI acts as a volume-weighted RSI,
    helping identify overbought/oversold conditions with volume confirmation.
    """

    # Parameters
    profile_period = 20  # Number of candles to include in volume profile
    volume_bins = 10  # Number of price levels in the profile
    imbalance_threshold = 0.65  # 65% buy volume for long, 35% for short
    take_profit = 0.03
    stop_loss = 0.02
    min_volume_percentile = 50  # Minimum volume percentile for valid signals
    mfi_period = 14  # Money Flow Index period
    mfi_oversold = 30  # MFI oversold level
    mfi_overbought = 70  # MFI overbought level
    mfi_extreme_oversold = 20  # Extreme oversold for stronger signals
    mfi_extreme_overbought = 80  # Extreme overbought for stronger signals

    def init(self):
        # Initialize volume moving average for filtering
        self.volume_ma = self.I(talib.SMA, self.data.Volume, timeperiod=self.profile_period)

        # Calculate MFI (Money Flow Index)
        self.mfi = self.I(talib.MFI, self.data.High, self.data.Low, self.data.Close,
                         self.data.Volume, timeperiod=self.mfi_period)

        # Calculate RSI for additional confirmation
        self.rsi = self.I(talib.RSI, self.data.Close, timeperiod=14)

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

        # Calculate MFI divergence indicator
        def calculate_mfi_divergence(close, mfi, period=5):
            """
            Detect bullish and bearish divergences between price and MFI
            """
            divergence = np.zeros(len(close))

            for i in range(period, len(close)):
                # Get recent data
                recent_close = close[i-period:i+1]
                recent_mfi = mfi[i-period:i+1]

                # Find local extremes
                price_min_idx = np.argmin(recent_close)
                price_max_idx = np.argmax(recent_close)
                mfi_min_idx = np.argmin(recent_mfi)
                mfi_max_idx = np.argmax(recent_mfi)

                # Bullish divergence: price makes lower low, MFI makes higher low
                if price_min_idx == period and mfi_min_idx < period:
                    if recent_close[-1] < recent_close[mfi_min_idx] and recent_mfi[-1] > recent_mfi[mfi_min_idx]:
                        divergence[i] = 1  # Bullish

                # Bearish divergence: price makes higher high, MFI makes lower high
                if price_max_idx == period and mfi_max_idx < period:
                    if recent_close[-1] > recent_close[mfi_max_idx] and recent_mfi[-1] < recent_mfi[mfi_max_idx]:
                        divergence[i] = -1  # Bearish

            return divergence

        self.mfi_divergence = self.I(calculate_mfi_divergence, self.data.Close, self.mfi, 5)

        # Track entry price for exits
        self.entry_price = None

    def next(self):
        # Skip if we don't have enough data
        if len(self.data) < max(self.profile_period, self.mfi_period * 2):
            return

        # Current values
        current_price = self.data.Close[-1]
        current_volume = self.data.Volume[-1]
        poc_price = self.poc_price[-1]
        buy_percentage = self.poc_buy_percentage[-1]
        poc_volume = self.poc_volume[-1]
        volume_avg = self.volume_ma[-1]

        # MFI and RSI values
        current_mfi = self.mfi[-1]
        current_rsi = self.rsi[-1]
        mfi_divergence = self.mfi_divergence[-1]

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
                # Exit if MFI becomes overbought
                elif current_mfi >= self.mfi_extreme_overbought:
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
                # Exit if MFI becomes oversold
                elif current_mfi <= self.mfi_extreme_oversold:
                    self.position.close()
                    self.entry_price = None

        else:
            # Entry logic - Volume imbalance at POC with MFI confirmation

            # Check if current volume is significant
            volume_percentile = (current_volume >= volume_avg * 0.5)

            # Price near POC (within 0.5% of POC)
            near_poc = abs(current_price - poc_price) / poc_price <= 0.005

            if near_poc and volume_percentile and poc_volume > 0:
                # Long signal: Strong buy volume imbalance at POC with oversold MFI
                long_conditions = [
                    buy_percentage >= self.imbalance_threshold,
                    self.data.Low[-1] <= poc_price <= self.data.High[-1],  # POC touched
                    current_mfi <= self.mfi_oversold,  # MFI oversold
                ]

                # Enhanced long conditions
                enhanced_long = [
                    current_mfi <= self.mfi_extreme_oversold,  # Extremely oversold
                    mfi_divergence > 0,  # Bullish divergence
                    current_rsi <= 35,  # RSI also oversold
                ]

                if all(long_conditions):
                    # Stronger signal with extreme conditions
                    if any(enhanced_long):
                        self.buy()
                        self.entry_price = current_price
                    # Regular signal with buy volume dominance
                    elif buy_percentage >= self.imbalance_threshold * 1.1:  # Require stronger imbalance
                        self.buy()
                        self.entry_price = current_price

                # Short signal: Strong sell volume imbalance at POC with overbought MFI
                short_conditions = [
                    buy_percentage <= (1 - self.imbalance_threshold),
                    self.data.Low[-1] <= poc_price <= self.data.High[-1],  # POC touched
                    current_mfi >= self.mfi_overbought,  # MFI overbought
                ]

                # Enhanced short conditions
                enhanced_short = [
                    current_mfi >= self.mfi_extreme_overbought,  # Extremely overbought
                    mfi_divergence < 0,  # Bearish divergence
                    current_rsi >= 65,  # RSI also overbought
                ]

                if all(short_conditions):
                    # Stronger signal with extreme conditions
                    if any(enhanced_short):
                        self.sell()
                        self.entry_price = current_price
                    # Regular signal with sell volume dominance
                    elif buy_percentage <= (1 - self.imbalance_threshold) * 0.9:  # Require stronger imbalance
                        self.sell()
                        self.entry_price = current_price


# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING FLOWSCOPE MFI STRATEGY ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    results = test_on_all_data(FlowScopeMFI, 'FlowScopeMFI')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/FlowScopeMFI.csv")