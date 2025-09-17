"""
Moon Dev's Fibonacci Sequence Circles with ADX Strategy
=======================================================
Uses Fibonacci sequence-based circular levels with ADX trend strength filter
to improve entry quality and reduce false signals.
Tests across all datasets with comprehensive stats output.
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
import talib
import warnings
warnings.filterwarnings('ignore')

class FibonacciCirclesADX(Strategy):
    """
    Fibonacci Sequence Circles with ADX Filter Strategy

    - Identifies pivot highs and lows using local extrema
    - Projects Fibonacci sequence levels as support/resistance zones
    - Uses ADX to confirm trend strength before entries
    - Only trades when ADX confirms trending conditions
    - Enhanced risk management with trend-based position sizing
    """

    # Fibonacci sequence for circle radii (in ATR multiples)
    fib_sequence = [2, 3, 5, 8, 13, 21, 34, 55]

    # Pivot detection parameters
    pivot_lookback = 20
    pivot_threshold = 3

    # ADX parameters
    adx_period = 14
    adx_trend_threshold = 25  # ADX above this indicates trending market
    adx_strong_trend = 40  # Strong trend for larger positions

    # Trade parameters
    position_size_base = 0.5  # Base position size
    position_size_trending = 0.95  # Size in strong trends
    atr_period = 14
    stop_loss_atr = 1.5  # Tighter stops with ADX confirmation
    take_profit_atr = 5.0  # Larger targets in trends

    # Confirmation parameters
    level_tolerance = 0.003  # 0.3% tolerance for level touches

    def init(self):
        """Initialize indicators including ADX"""
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)

        # Calculate ATR for dynamic sizing
        self.atr = self.I(talib.ATR, high, low, close, self.atr_period)

        # Calculate ADX for trend strength
        self.adx = self.I(talib.ADX, high, low, close, self.adx_period)

        # Calculate +DI and -DI for trend direction
        self.plus_di = self.I(talib.PLUS_DI, high, low, close, self.adx_period)
        self.minus_di = self.I(talib.MINUS_DI, high, low, close, self.adx_period)

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
        self.pivot_highs = self.I(lambda: pivot_highs, name='PivotHighs')
        self.pivot_lows = self.I(lambda: pivot_lows, name='PivotLows')

        # Calculate rolling pivot values
        pivot_high_series = pd.Series(pivot_highs).fillna(method='ffill')
        pivot_low_series = pd.Series(pivot_lows).fillna(method='ffill')

        self.current_pivot_high = self.I(lambda: pivot_high_series.values, name='CurrentPivotHigh')
        self.current_pivot_low = self.I(lambda: pivot_low_series.values, name='CurrentPivotLow')

        # Calculate EMAs for trend direction
        self.ema_fast = self.I(talib.EMA, close, 12)
        self.ema_slow = self.I(talib.EMA, close, 26)

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
            # Adjust distance based on ADX (wider circles in strong trends)
            adx_mult = 1.0
            if not pd.isna(self.adx[-1]) and self.adx[-1] > self.adx_strong_trend:
                adx_mult = 1.2  # Wider circles in strong trends

            distance = fib_num * atr_value * 0.1 * adx_mult

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

    def get_position_size(self, adx_value):
        """Dynamic position sizing based on ADX strength"""
        if pd.isna(adx_value):
            return self.position_size_base

        if adx_value >= self.adx_strong_trend:
            return self.position_size_trending
        elif adx_value >= self.adx_trend_threshold:
            # Scale between base and trending
            ratio = (adx_value - self.adx_trend_threshold) / (self.adx_strong_trend - self.adx_trend_threshold)
            return self.position_size_base + (self.position_size_trending - self.position_size_base) * ratio
        else:
            return self.position_size_base * 0.5  # Reduced size in ranging markets

    def next(self):
        """Execute trading logic with ADX filtering"""
        # Skip if not enough data
        if len(self.data.Close) < max(self.pivot_lookback, self.adx_period + 10):
            return

        price = self.data.Close[-1]
        high = self.data.High[-1]
        low = self.data.Low[-1]
        atr = self.atr[-1]
        adx = self.adx[-1]
        plus_di = self.plus_di[-1]
        minus_di = self.minus_di[-1]

        # Check for valid indicators
        if pd.isna(atr) or atr <= 0 or pd.isna(adx):
            return

        # Get current pivot levels
        pivot_high = self.current_pivot_high[-1]
        pivot_low = self.current_pivot_low[-1]

        if pd.isna(pivot_high) or pd.isna(pivot_low):
            return

        # Calculate Fibonacci levels
        resistance_levels = self.calculate_fib_levels(pivot_high, atr, is_resistance=True)
        support_levels = self.calculate_fib_levels(pivot_low, atr, is_resistance=False)

        # Get trend direction from EMAs
        ema_fast = self.ema_fast[-1]
        ema_slow = self.ema_slow[-1]
        uptrend = ema_fast > ema_slow if not pd.isna(ema_fast) and not pd.isna(ema_slow) else False
        downtrend = ema_fast < ema_slow if not pd.isna(ema_fast) and not pd.isna(ema_slow) else False

        # Trading logic with ADX filter
        if not self.position:
            # Only trade when ADX indicates trending market
            if adx < self.adx_trend_threshold:
                return  # Skip trading in ranging markets

            # Look for long entry at support levels
            if plus_di > minus_di and uptrend:  # Bullish bias confirmed
                for i, support in enumerate(support_levels[:4]):
                    if self.check_level_touch(price, high, low, support):
                        # Confirm bounce with ADX trend strength
                        if price > support and self.data.Close[-1] > self.data.Close[-2]:
                            # Stronger ADX = larger position
                            size = self.get_position_size(adx)
                            self.buy(size=size)
                            self.entry_price = price
                            self.entry_atr = atr
                            self.is_long = True
                            break

            # Look for short entry at resistance levels
            elif minus_di > plus_di and downtrend:  # Bearish bias confirmed
                for i, resistance in enumerate(resistance_levels[:4]):
                    if self.check_level_touch(price, high, low, resistance):
                        # Confirm rejection with ADX trend strength
                        if price < resistance and self.data.Close[-1] < self.data.Close[-2]:
                            # Stronger ADX = larger position
                            size = self.get_position_size(adx)
                            self.sell(size=size)
                            self.entry_price = price
                            self.entry_atr = atr
                            self.is_long = False
                            break

        # Exit logic for existing positions
        elif self.position:
            # Adjust stops based on ADX strength
            stop_multiplier = self.stop_loss_atr
            if adx < 20:  # Weak trend, tighter stops
                stop_multiplier *= 0.75

            if self.is_long:
                # Long position exit conditions
                stop_loss = self.entry_price - (stop_multiplier * self.entry_atr)
                take_profit = self.entry_price + (self.take_profit_atr * self.entry_atr)

                # Exit if trend weakens significantly
                trend_weakened = adx < 20 or minus_di > plus_di

                # Check for resistance level hit
                hit_resistance = False
                for resistance in resistance_levels[:2]:
                    if price >= resistance * 0.995:
                        hit_resistance = True
                        break

                # Exit conditions
                if price <= stop_loss or price >= take_profit or hit_resistance or trend_weakened:
                    self.position.close()
                    self.entry_price = 0
                    self.entry_atr = 0

                # Partial exit if ADX drops but still above threshold
                elif adx < self.adx_trend_threshold and self.position.size > self.position_size_base:
                    self.position.close(0.5)  # Reduce to base position

            else:
                # Short position exit conditions
                stop_loss = self.entry_price + (stop_multiplier * self.entry_atr)
                take_profit = self.entry_price - (self.take_profit_atr * self.entry_atr)

                # Exit if trend weakens significantly
                trend_weakened = adx < 20 or plus_di > minus_di

                # Check for support level hit
                hit_support = False
                for support in support_levels[:2]:
                    if price <= support * 1.005:
                        hit_support = True
                        break

                # Exit conditions
                if price >= stop_loss or price <= take_profit or hit_support or trend_weakened:
                    self.position.close()
                    self.entry_price = 0
                    self.entry_atr = 0

                # Partial exit if ADX drops
                elif adx < self.adx_trend_threshold and abs(self.position.size) > self.position_size_base:
                    self.position.close(0.5)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING FIBONACCI CIRCLES ADX STRATEGY ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(FibonacciCirclesADX, 'FibonacciCirclesADX')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/FibonacciCirclesADX.csv")