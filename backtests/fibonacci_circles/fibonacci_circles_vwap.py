"""
Moon Dev's Fibonacci Sequence Circles with VWAP Strategy
========================================================
Uses Fibonacci sequence-based circular levels with VWAP for price context
to identify high-probability reversal zones.
Tests across all datasets with comprehensive stats output.
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
import talib
import warnings
warnings.filterwarnings('ignore')

class FibonacciCirclesVWAP(Strategy):
    """
    Fibonacci Sequence Circles with VWAP Strategy

    - Identifies pivot highs and lows using local extrema
    - Projects Fibonacci sequence levels as support/resistance zones
    - Uses VWAP to confirm price value areas
    - Combines Fibonacci levels with VWAP bands for high-probability trades
    - Enhanced entries when Fib levels align with VWAP bands
    """

    # Fibonacci sequence for circle radii
    fib_sequence = [2, 3, 5, 8, 13, 21, 34, 55]

    # Pivot detection parameters
    pivot_lookback = 20
    pivot_threshold = 3

    # VWAP parameters
    vwap_period = 20  # Rolling VWAP period
    vwap_stdev_mult_1 = 1.0  # First standard deviation band
    vwap_stdev_mult_2 = 2.0  # Second standard deviation band
    vwap_stdev_mult_3 = 3.0  # Third standard deviation band

    # Trade parameters
    position_size = 0.95
    atr_period = 14
    stop_loss_atr = 2.0
    take_profit_atr = 4.5

    # Confirmation parameters
    level_tolerance = 0.003
    vwap_alignment_bonus = 0.2  # Extra confidence when Fib aligns with VWAP

    def init(self):
        """Initialize indicators including VWAP"""
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        volume = pd.Series(self.data.Volume)

        # Calculate ATR
        self.atr = self.I(talib.ATR, high, low, close, self.atr_period)

        # Calculate VWAP and bands
        # Using typical price (HLC/3)
        typical_price = (high + low + close) / 3

        # Rolling VWAP calculation
        vwap_values = []
        vwap_upper1 = []
        vwap_upper2 = []
        vwap_upper3 = []
        vwap_lower1 = []
        vwap_lower2 = []
        vwap_lower3 = []

        for i in range(len(close)):
            if i < self.vwap_period - 1:
                vwap_values.append(np.nan)
                vwap_upper1.append(np.nan)
                vwap_upper2.append(np.nan)
                vwap_upper3.append(np.nan)
                vwap_lower1.append(np.nan)
                vwap_lower2.append(np.nan)
                vwap_lower3.append(np.nan)
            else:
                # Calculate VWAP for rolling window
                window_tp = typical_price.iloc[i-self.vwap_period+1:i+1]
                window_vol = volume.iloc[i-self.vwap_period+1:i+1]

                if window_vol.sum() > 0:
                    vwap = (window_tp * window_vol).sum() / window_vol.sum()

                    # Calculate standard deviation
                    squared_diff = ((window_tp - vwap) ** 2 * window_vol).sum() / window_vol.sum()
                    stdev = np.sqrt(squared_diff)

                    vwap_values.append(vwap)
                    vwap_upper1.append(vwap + stdev * self.vwap_stdev_mult_1)
                    vwap_upper2.append(vwap + stdev * self.vwap_stdev_mult_2)
                    vwap_upper3.append(vwap + stdev * self.vwap_stdev_mult_3)
                    vwap_lower1.append(vwap - stdev * self.vwap_stdev_mult_1)
                    vwap_lower2.append(vwap - stdev * self.vwap_stdev_mult_2)
                    vwap_lower3.append(vwap - stdev * self.vwap_stdev_mult_3)
                else:
                    vwap_values.append(np.nan)
                    vwap_upper1.append(np.nan)
                    vwap_upper2.append(np.nan)
                    vwap_upper3.append(np.nan)
                    vwap_lower1.append(np.nan)
                    vwap_lower2.append(np.nan)
                    vwap_lower3.append(np.nan)

        # Store VWAP and bands
        self.vwap = self.I(lambda: vwap_values, name='VWAP')
        self.vwap_upper1 = self.I(lambda: vwap_upper1, name='VWAP_Upper1')
        self.vwap_upper2 = self.I(lambda: vwap_upper2, name='VWAP_Upper2')
        self.vwap_upper3 = self.I(lambda: vwap_upper3, name='VWAP_Upper3')
        self.vwap_lower1 = self.I(lambda: vwap_lower1, name='VWAP_Lower1')
        self.vwap_lower2 = self.I(lambda: vwap_lower2, name='VWAP_Lower2')
        self.vwap_lower3 = self.I(lambda: vwap_lower3, name='VWAP_Lower3')

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

        # Calculate RSI for additional confirmation
        self.rsi = self.I(talib.RSI, close, 14)

        # Track entry information
        self.entry_price = 0
        self.entry_atr = 0
        self.is_long = True

    def calculate_fib_levels(self, pivot_price, atr_value, is_resistance=True):
        """Calculate Fibonacci circle levels from a pivot point"""
        if pd.isna(pivot_price) or pd.isna(atr_value) or atr_value <= 0:
            return []

        levels = []
        for fib_num in self.fib_sequence:
            distance = fib_num * atr_value * 0.1

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

    def check_vwap_alignment(self, level, vwap_band, tolerance=0.005):
        """Check if Fibonacci level aligns with VWAP band"""
        if pd.isna(level) or pd.isna(vwap_band):
            return False

        return abs(level - vwap_band) / vwap_band <= tolerance

    def get_trade_confidence(self, fib_level, is_long=True):
        """Calculate trade confidence based on VWAP alignment"""
        confidence = 1.0

        # Check alignment with VWAP bands
        vwap = self.vwap[-1]

        if is_long:
            # For long trades, check support alignment with lower VWAP bands
            if self.check_vwap_alignment(fib_level, self.vwap_lower1[-1]):
                confidence += 0.2
            elif self.check_vwap_alignment(fib_level, self.vwap_lower2[-1]):
                confidence += 0.3
            elif self.check_vwap_alignment(fib_level, self.vwap_lower3[-1]):
                confidence += 0.4

            # Bonus if price is below VWAP (oversold)
            if not pd.isna(vwap) and self.data.Close[-1] < vwap:
                confidence += 0.1
        else:
            # For short trades, check resistance alignment with upper VWAP bands
            if self.check_vwap_alignment(fib_level, self.vwap_upper1[-1]):
                confidence += 0.2
            elif self.check_vwap_alignment(fib_level, self.vwap_upper2[-1]):
                confidence += 0.3
            elif self.check_vwap_alignment(fib_level, self.vwap_upper3[-1]):
                confidence += 0.4

            # Bonus if price is above VWAP (overbought)
            if not pd.isna(vwap) and self.data.Close[-1] > vwap:
                confidence += 0.1

        return confidence

    def next(self):
        """Execute trading logic with VWAP confirmation"""
        # Skip if not enough data
        if len(self.data.Close) < max(self.pivot_lookback, self.vwap_period + 10):
            return

        price = self.data.Close[-1]
        high = self.data.High[-1]
        low = self.data.Low[-1]
        atr = self.atr[-1]
        vwap = self.vwap[-1]
        rsi = self.rsi[-1]

        # Check for valid indicators
        if pd.isna(atr) or atr <= 0 or pd.isna(vwap):
            return

        # Get current pivot levels
        pivot_high = self.current_pivot_high[-1]
        pivot_low = self.current_pivot_low[-1]

        if pd.isna(pivot_high) or pd.isna(pivot_low):
            return

        # Calculate Fibonacci levels
        resistance_levels = self.calculate_fib_levels(pivot_high, atr, is_resistance=True)
        support_levels = self.calculate_fib_levels(pivot_low, atr, is_resistance=False)

        # Trading logic with VWAP confirmation
        if not self.position:
            best_long_confidence = 0
            best_long_level = None
            best_short_confidence = 0
            best_short_level = None

            # Evaluate long opportunities at support levels
            if price < vwap:  # Below VWAP, look for longs
                for i, support in enumerate(support_levels[:5]):
                    if self.check_level_touch(price, high, low, support):
                        # Calculate confidence score
                        confidence = self.get_trade_confidence(support, is_long=True)

                        # Add RSI oversold bonus
                        if not pd.isna(rsi) and rsi < 30:
                            confidence += 0.2

                        if confidence > best_long_confidence:
                            best_long_confidence = confidence
                            best_long_level = support

            # Evaluate short opportunities at resistance levels
            elif price > vwap:  # Above VWAP, look for shorts
                for i, resistance in enumerate(resistance_levels[:5]):
                    if self.check_level_touch(price, high, low, resistance):
                        # Calculate confidence score
                        confidence = self.get_trade_confidence(resistance, is_long=False)

                        # Add RSI overbought bonus
                        if not pd.isna(rsi) and rsi > 70:
                            confidence += 0.2

                        if confidence > best_short_confidence:
                            best_short_confidence = confidence
                            best_short_level = resistance

            # Execute trade with highest confidence
            if best_long_confidence >= 1.3 and best_long_level is not None:
                # Confirm bounce
                if price > best_long_level and self.data.Close[-1] > self.data.Close[-2]:
                    # Scale position based on confidence
                    size = min(self.position_size * (best_long_confidence / 1.5), self.position_size)
                    self.buy(size=size)
                    self.entry_price = price
                    self.entry_atr = atr
                    self.is_long = True

            elif best_short_confidence >= 1.3 and best_short_level is not None:
                # Confirm rejection
                if price < best_short_level and self.data.Close[-1] < self.data.Close[-2]:
                    # Scale position based on confidence
                    size = min(self.position_size * (best_short_confidence / 1.5), self.position_size)
                    self.sell(size=size)
                    self.entry_price = price
                    self.entry_atr = atr
                    self.is_long = False

        # Exit logic for existing positions
        elif self.position:
            if self.is_long:
                # Long position exit conditions
                stop_loss = self.entry_price - (self.stop_loss_atr * self.entry_atr)
                take_profit = self.entry_price + (self.take_profit_atr * self.entry_atr)

                # VWAP-based exits
                vwap_exit = False
                if price > self.vwap_upper2[-1] and not pd.isna(self.vwap_upper2[-1]):
                    vwap_exit = True  # Take profit at upper band 2

                # Check for resistance hit
                hit_resistance = False
                for resistance in resistance_levels[:2]:
                    if price >= resistance * 0.995:
                        hit_resistance = True
                        break

                # Exit conditions
                if price <= stop_loss or price >= take_profit or vwap_exit or hit_resistance:
                    self.position.close()
                    self.entry_price = 0
                    self.entry_atr = 0

                # Partial exit at VWAP upper band 1
                elif price > self.vwap_upper1[-1] and not pd.isna(self.vwap_upper1[-1]):
                    if self.position.size > 0.5:
                        self.position.close(0.3)  # Take 30% profit

            else:
                # Short position exit conditions
                stop_loss = self.entry_price + (self.stop_loss_atr * self.entry_atr)
                take_profit = self.entry_price - (self.take_profit_atr * self.entry_atr)

                # VWAP-based exits
                vwap_exit = False
                if price < self.vwap_lower2[-1] and not pd.isna(self.vwap_lower2[-1]):
                    vwap_exit = True  # Take profit at lower band 2

                # Check for support hit
                hit_support = False
                for support in support_levels[:2]:
                    if price <= support * 1.005:
                        hit_support = True
                        break

                # Exit conditions
                if price >= stop_loss or price <= take_profit or vwap_exit or hit_support:
                    self.position.close()
                    self.entry_price = 0
                    self.entry_atr = 0

                # Partial exit at VWAP lower band 1
                elif price < self.vwap_lower1[-1] and not pd.isna(self.vwap_lower1[-1]):
                    if abs(self.position.size) > 0.5:
                        self.position.close(0.3)  # Take 30% profit

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING FIBONACCI CIRCLES VWAP STRATEGY ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(FibonacciCirclesVWAP, 'FibonacciCirclesVWAP')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/FibonacciCirclesVWAP.csv")