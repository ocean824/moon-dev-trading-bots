"""
Moon Dev's Fibonacci Sequence Circles with MFI Strategy
=======================================================
Uses Fibonacci sequence-based circular levels with Money Flow Index
to confirm volume/price relationships at key levels.
Tests across all datasets with comprehensive stats output.
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
import talib
import warnings
warnings.filterwarnings('ignore')

class FibonacciCirclesMFI(Strategy):
    """
    Fibonacci Sequence Circles with MFI Strategy

    - Identifies pivot highs and lows using local extrema
    - Projects Fibonacci sequence levels as support/resistance zones
    - Uses MFI to confirm money flow at reversal points
    - Combines volume analysis with Fibonacci levels
    - Enhanced entries when MFI divergences align with Fib levels
    """

    # Fibonacci sequence for circle radii
    fib_sequence = [2, 3, 5, 8, 13, 21, 34, 55]

    # Pivot detection parameters
    pivot_lookback = 20
    pivot_threshold = 3

    # MFI parameters
    mfi_period = 14
    mfi_oversold = 20  # MFI below this is oversold
    mfi_overbought = 80  # MFI above this is overbought
    mfi_divergence_lookback = 10  # Bars to check for divergence

    # Trade parameters
    position_size = 0.95
    atr_period = 14
    stop_loss_atr = 1.8
    take_profit_atr = 4.0

    # Confirmation parameters
    level_tolerance = 0.003
    volume_multiplier = 1.5  # Volume spike threshold

    def init(self):
        """Initialize indicators including MFI"""
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        volume = pd.Series(self.data.Volume)

        # Calculate ATR
        self.atr = self.I(talib.ATR, high, low, close, self.atr_period)

        # Calculate MFI (Money Flow Index)
        self.mfi = self.I(talib.MFI, high, low, close, volume, self.mfi_period)

        # Calculate volume moving average for spike detection
        self.volume_sma = self.I(talib.SMA, volume, 20)

        # Find pivot highs and lows
        pivot_highs = []
        pivot_lows = []

        for i in range(len(high)):
            if i < self.pivot_threshold or i >= len(high) - self.pivot_threshold:
                pivot_highs.append(np.nan)
                pivot_lows.append(np.nan)
                continue

            # Check for pivot high
            is_pivot_high = True
            for j in range(1, self.pivot_threshold + 1):
                if high.iloc[i] <= high.iloc[i-j] or high.iloc[i] <= high.iloc[i+j]:
                    is_pivot_high = False
                    break

            # Check for pivot low
            is_pivot_low = True
            for j in range(1, self.pivot_threshold + 1):
                if low.iloc[i] >= low.iloc[i-j] or low.iloc[i] >= low.iloc[i+j]:
                    is_pivot_low = False
                    break

            pivot_highs.append(high.iloc[i] if is_pivot_high else np.nan)
            pivot_lows.append(low.iloc[i] if is_pivot_low else np.nan)

        # Store pivot points
        pivot_high_series = pd.Series(pivot_highs).fillna(method='ffill')
        pivot_low_series = pd.Series(pivot_lows).fillna(method='ffill')

        self.current_pivot_high = self.I(lambda: pivot_high_series.values, name='CurrentPivotHigh')
        self.current_pivot_low = self.I(lambda: pivot_low_series.values, name='CurrentPivotLow')

        # Calculate OBV for additional volume confirmation
        obv = [0]
        for i in range(1, len(close)):
            if close.iloc[i] > close.iloc[i-1]:
                obv.append(obv[-1] + volume.iloc[i])
            elif close.iloc[i] < close.iloc[i-1]:
                obv.append(obv[-1] - volume.iloc[i])
            else:
                obv.append(obv[-1])

        self.obv = self.I(lambda: obv, name='OBV')
        self.obv_sma = self.I(talib.SMA, pd.Series(obv), 20)

        # Calculate Bollinger Bands for MFI
        mfi_series = pd.Series([self.mfi[i] if i < len(self.mfi) else np.nan for i in range(len(close))])
        mfi_sma = talib.SMA(mfi_series, 20)
        mfi_std = mfi_series.rolling(20).std()

        self.mfi_upper = self.I(lambda: (mfi_sma + 2 * mfi_std).values, name='MFI_Upper')
        self.mfi_lower = self.I(lambda: (mfi_sma - 2 * mfi_std).values, name='MFI_Lower')

        # Track entry information
        self.entry_price = 0
        self.entry_atr = 0
        self.is_long = True
        self.entry_mfi = 0

    def calculate_fib_levels(self, pivot_price, atr_value, is_resistance=True):
        """Calculate Fibonacci circle levels from a pivot point"""
        if pd.isna(pivot_price) or pd.isna(atr_value) or atr_value <= 0:
            return []

        levels = []
        for fib_num in self.fib_sequence:
            # Adjust distance based on MFI extremes
            mfi = self.mfi[-1] if len(self.mfi) > 0 else 50
            mfi_mult = 1.0

            if not pd.isna(mfi):
                if mfi < 30:
                    mfi_mult = 0.9  # Tighter circles in oversold
                elif mfi > 70:
                    mfi_mult = 1.1  # Wider circles in overbought

            distance = fib_num * atr_value * 0.1 * mfi_mult

            if is_resistance:
                level = pivot_price + distance
            else:
                level = pivot_price - distance

            levels.append(level)

        return levels

    def check_level_touch(self, price, high, low, level, tolerance=None):
        """Check if price touches a Fibonacci level within tolerance"""
        if pd.isna(level):
            return False

        if tolerance is None:
            tolerance = self.level_tolerance

        upper_bound = level * (1 + tolerance)
        lower_bound = level * (1 - tolerance)

        return (low <= upper_bound and high >= lower_bound)

    def check_mfi_divergence(self, is_bullish=True):
        """Check for MFI divergence"""
        if len(self.data.Close) < self.mfi_divergence_lookback + 1:
            return False

        # Get recent price and MFI data
        prices = self.data.Close[-self.mfi_divergence_lookback:]
        mfi_values = [self.mfi[i] for i in range(-self.mfi_divergence_lookback, 0)]

        # Check for valid MFI values
        if any(pd.isna(val) for val in mfi_values):
            return False

        if is_bullish:
            # Bullish divergence: price makes lower low, MFI makes higher low
            price_trend = prices[-1] < min(prices[:-1])
            mfi_trend = mfi_values[-1] > min(mfi_values[:-1])
            return price_trend and mfi_trend
        else:
            # Bearish divergence: price makes higher high, MFI makes lower high
            price_trend = prices[-1] > max(prices[:-1])
            mfi_trend = mfi_values[-1] < max(mfi_values[:-1])
            return price_trend and mfi_trend

    def check_volume_spike(self):
        """Check for volume spike"""
        if pd.isna(self.volume_sma[-1]) or self.volume_sma[-1] <= 0:
            return False

        current_volume = self.data.Volume[-1]
        return current_volume > self.volume_sma[-1] * self.volume_multiplier

    def get_trade_confidence(self, mfi_value, is_long=True):
        """Calculate trade confidence based on MFI conditions"""
        if pd.isna(mfi_value):
            return 1.0

        confidence = 1.0

        if is_long:
            # Long trade confidence
            if mfi_value < self.mfi_oversold:
                confidence += 0.4  # Strong oversold
            elif mfi_value < 30:
                confidence += 0.2  # Moderate oversold

            # Check for bullish divergence
            if self.check_mfi_divergence(is_bullish=True):
                confidence += 0.3

            # Volume spike confirmation
            if self.check_volume_spike():
                confidence += 0.2

            # OBV confirmation
            if len(self.obv) > 1 and self.obv[-1] > self.obv_sma[-1]:
                confidence += 0.1

        else:
            # Short trade confidence
            if mfi_value > self.mfi_overbought:
                confidence += 0.4  # Strong overbought
            elif mfi_value > 70:
                confidence += 0.2  # Moderate overbought

            # Check for bearish divergence
            if self.check_mfi_divergence(is_bullish=False):
                confidence += 0.3

            # Volume spike confirmation
            if self.check_volume_spike():
                confidence += 0.2

            # OBV confirmation
            if len(self.obv) > 1 and self.obv[-1] < self.obv_sma[-1]:
                confidence += 0.1

        return confidence

    def next(self):
        """Execute trading logic with MFI confirmation"""
        # Skip if not enough data
        if len(self.data.Close) < max(self.pivot_lookback, self.mfi_period + 10):
            return

        price = self.data.Close[-1]
        high = self.data.High[-1]
        low = self.data.Low[-1]
        atr = self.atr[-1]
        mfi = self.mfi[-1]

        # Check for valid indicators
        if pd.isna(atr) or atr <= 0 or pd.isna(mfi):
            return

        # Get current pivot levels
        pivot_high = self.current_pivot_high[-1]
        pivot_low = self.current_pivot_low[-1]

        if pd.isna(pivot_high) or pd.isna(pivot_low):
            return

        # Calculate Fibonacci levels
        resistance_levels = self.calculate_fib_levels(pivot_high, atr, is_resistance=True)
        support_levels = self.calculate_fib_levels(pivot_low, atr, is_resistance=False)

        # Trading logic with MFI confirmation
        if not self.position:
            best_long_confidence = 0
            best_long_level = None
            best_short_confidence = 0
            best_short_level = None

            # Evaluate long opportunities at support levels
            if mfi < 50:  # Focus on longs when MFI is lower
                for i, support in enumerate(support_levels[:5]):
                    if self.check_level_touch(price, high, low, support):
                        # Calculate confidence score
                        confidence = self.get_trade_confidence(mfi, is_long=True)

                        # Bonus for lower Fibonacci numbers (stronger levels)
                        confidence += (5 - i) * 0.05

                        if confidence > best_long_confidence:
                            best_long_confidence = confidence
                            best_long_level = support

            # Evaluate short opportunities at resistance levels
            elif mfi > 50:  # Focus on shorts when MFI is higher
                for i, resistance in enumerate(resistance_levels[:5]):
                    if self.check_level_touch(price, high, low, resistance):
                        # Calculate confidence score
                        confidence = self.get_trade_confidence(mfi, is_long=False)

                        # Bonus for lower Fibonacci numbers (stronger levels)
                        confidence += (5 - i) * 0.05

                        if confidence > best_short_confidence:
                            best_short_confidence = confidence
                            best_short_level = resistance

            # Execute trade with highest confidence
            if best_long_confidence >= 1.4 and best_long_level is not None:
                # Confirm bounce with price action
                if price > best_long_level and self.data.Close[-1] > self.data.Close[-2]:
                    # Scale position based on MFI level
                    mfi_size_mult = 1.0
                    if mfi < self.mfi_oversold:
                        mfi_size_mult = 1.2  # Larger size in extreme oversold

                    size = min(self.position_size * mfi_size_mult, self.position_size)
                    self.buy(size=size)
                    self.entry_price = price
                    self.entry_atr = atr
                    self.entry_mfi = mfi
                    self.is_long = True

            elif best_short_confidence >= 1.4 and best_short_level is not None:
                # Confirm rejection with price action
                if price < best_short_level and self.data.Close[-1] < self.data.Close[-2]:
                    # Scale position based on MFI level
                    mfi_size_mult = 1.0
                    if mfi > self.mfi_overbought:
                        mfi_size_mult = 1.2  # Larger size in extreme overbought

                    size = min(self.position_size * mfi_size_mult, self.position_size)
                    self.sell(size=size)
                    self.entry_price = price
                    self.entry_atr = atr
                    self.entry_mfi = mfi
                    self.is_long = False

        # Exit logic for existing positions
        elif self.position:
            if self.is_long:
                # Long position exit conditions
                stop_loss = self.entry_price - (self.stop_loss_atr * self.entry_atr)
                take_profit = self.entry_price + (self.take_profit_atr * self.entry_atr)

                # MFI-based exits
                mfi_exit = False
                if mfi > self.mfi_overbought:
                    mfi_exit = True  # Exit when overbought

                # Check for bearish divergence
                divergence_exit = self.check_mfi_divergence(is_bullish=False)

                # Check for resistance hit
                hit_resistance = False
                for resistance in resistance_levels[:2]:
                    if price >= resistance * 0.995:
                        hit_resistance = True
                        break

                # Exit conditions
                if price <= stop_loss or price >= take_profit or mfi_exit or divergence_exit or hit_resistance:
                    self.position.close()
                    self.entry_price = 0
                    self.entry_atr = 0
                    self.entry_mfi = 0

                # Partial exit conditions
                elif mfi > 70 and self.entry_mfi < 30:  # Large MFI swing
                    if self.position.size > 0.5:
                        self.position.close(0.5)  # Take half profit

                elif mfi > self.mfi_upper[-1] and not pd.isna(self.mfi_upper[-1]):
                    if self.position.size > 0.7:
                        self.position.close(0.3)  # Take partial profit

            else:
                # Short position exit conditions
                stop_loss = self.entry_price + (self.stop_loss_atr * self.entry_atr)
                take_profit = self.entry_price - (self.take_profit_atr * self.entry_atr)

                # MFI-based exits
                mfi_exit = False
                if mfi < self.mfi_oversold:
                    mfi_exit = True  # Exit when oversold

                # Check for bullish divergence
                divergence_exit = self.check_mfi_divergence(is_bullish=True)

                # Check for support hit
                hit_support = False
                for support in support_levels[:2]:
                    if price <= support * 1.005:
                        hit_support = True
                        break

                # Exit conditions
                if price >= stop_loss or price <= take_profit or mfi_exit or divergence_exit or hit_support:
                    self.position.close()
                    self.entry_price = 0
                    self.entry_atr = 0
                    self.entry_mfi = 0

                # Partial exit conditions
                elif mfi < 30 and self.entry_mfi > 70:  # Large MFI swing
                    if abs(self.position.size) > 0.5:
                        self.position.close(0.5)  # Take half profit

                elif mfi < self.mfi_lower[-1] and not pd.isna(self.mfi_lower[-1]):
                    if abs(self.position.size) > 0.7:
                        self.position.close(0.3)  # Take partial profit

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING FIBONACCI CIRCLES MFI STRATEGY ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(FibonacciCirclesMFI, 'FibonacciCirclesMFI')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/FibonacciCirclesMFI.csv")