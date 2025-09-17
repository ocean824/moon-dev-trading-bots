"""
Moon Dev's Fibonacci Sequence Circles Base Strategy
===================================================
Uses Fibonacci sequence-based circular levels around pivot points to identify
support and resistance zones for trading opportunities.
Tests across all datasets with comprehensive stats output.

The strategy identifies pivot highs/lows and projects Fibonacci sequence distances
(2, 3, 5, 8, 13, 21, 34, 55, 89, 144) as circular zones around these pivots.
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
import talib
import warnings
warnings.filterwarnings('ignore')

class FibonacciCirclesBase(Strategy):
    """
    Fibonacci Sequence Circles Base Strategy

    - Identifies pivot highs and lows using local extrema
    - Projects Fibonacci sequence levels (2, 3, 5, 8, 13, 21, etc.) as circles
    - Each circle represents potential support/resistance zone
    - Trades bounces/rejections at these levels with confirmation
    - Uses ATR for dynamic position sizing and stop losses
    """

    # Fibonacci sequence for circle radii (in ATR multiples)
    fib_sequence = [2, 3, 5, 8, 13, 21, 34, 55]  # Using first 8 numbers

    # Pivot detection parameters
    pivot_lookback = 20  # Bars to look back for pivot detection
    pivot_threshold = 3  # Minimum bars on each side for pivot confirmation

    # Trade parameters
    position_size = 0.95  # 95% of equity
    atr_period = 14
    stop_loss_atr = 2.0  # Stop loss in ATR multiples
    take_profit_atr = 4.0  # Take profit in ATR multiples

    # Confirmation parameters
    confirmation_bars = 2  # Bars to confirm bounce/rejection
    level_tolerance = 0.002  # 0.2% tolerance for level touches

    def init(self):
        """Initialize indicators and calculate Fibonacci circle levels"""
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)

        # Calculate ATR for dynamic sizing
        self.atr = self.I(talib.ATR, high, low, close, self.atr_period)

        # Find pivot highs and lows
        # Pivot high: Higher than N bars before and after
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

        # Calculate rolling pivot values (forward fill to maintain levels)
        pivot_high_series = pd.Series(pivot_highs).fillna(method='ffill')
        pivot_low_series = pd.Series(pivot_lows).fillna(method='ffill')

        self.current_pivot_high = self.I(lambda: pivot_high_series.values, name='CurrentPivotHigh')
        self.current_pivot_low = self.I(lambda: pivot_low_series.values, name='CurrentPivotLow')

        # Calculate 20-period SMA for trend reference
        self.sma = self.I(talib.SMA, close, 20)

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
            # Calculate level based on Fibonacci sequence number * ATR
            distance = fib_num * atr_value * 0.1  # Scale down the multiplier

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

        # Check if candle wicks touch the level
        upper_bound = level * (1 + tolerance)
        lower_bound = level * (1 - tolerance)

        return (low <= upper_bound and high >= lower_bound)

    def next(self):
        """Execute trading logic"""
        # Skip if not enough data
        if len(self.data.Close) < self.pivot_lookback:
            return

        price = self.data.Close[-1]
        high = self.data.High[-1]
        low = self.data.Low[-1]
        atr = self.atr[-1]

        # Check for valid ATR
        if pd.isna(atr) or atr <= 0:
            return

        # Get current pivot levels
        pivot_high = self.current_pivot_high[-1]
        pivot_low = self.current_pivot_low[-1]

        if pd.isna(pivot_high) or pd.isna(pivot_low):
            return

        # Calculate Fibonacci resistance and support levels
        resistance_levels = self.calculate_fib_levels(pivot_high, atr, is_resistance=True)
        support_levels = self.calculate_fib_levels(pivot_low, atr, is_resistance=False)

        # Trading logic
        if not self.position:
            # Look for long entry at support levels
            for support in support_levels[:4]:  # Check first 4 Fib levels (2, 3, 5, 8)
                if self.check_level_touch(price, high, low, support):
                    # Confirm bounce: Current close above level and previous touched it
                    if price > support and len(self.data.Close) > 1:
                        # Additional confirmation: Price moving up from support
                        if self.data.Close[-1] > self.data.Close[-2]:
                            # Long entry
                            self.buy(size=self.position_size)
                            self.entry_price = price
                            self.entry_atr = atr
                            self.is_long = True
                            break

            # Look for short entry at resistance levels
            if not self.position:
                for resistance in resistance_levels[:4]:  # Check first 4 Fib levels
                    if self.check_level_touch(price, high, low, resistance):
                        # Confirm rejection: Current close below level and previous touched it
                        if price < resistance and len(self.data.Close) > 1:
                            # Additional confirmation: Price moving down from resistance
                            if self.data.Close[-1] < self.data.Close[-2]:
                                # Short entry
                                self.sell(size=self.position_size)
                                self.entry_price = price
                                self.entry_atr = atr
                                self.is_long = False
                                break

        # Exit logic for existing positions
        elif self.position:
            if self.is_long:
                # Long position exit conditions
                stop_loss = self.entry_price - (self.stop_loss_atr * self.entry_atr)
                take_profit = self.entry_price + (self.take_profit_atr * self.entry_atr)

                # Check for resistance level hit (exit signal)
                hit_resistance = False
                for resistance in resistance_levels[:2]:  # Check first 2 levels for exit
                    if price >= resistance * 0.995:  # Within 0.5% of resistance
                        hit_resistance = True
                        break

                # Exit conditions
                if price <= stop_loss or price >= take_profit or hit_resistance:
                    self.position.close()
                    self.entry_price = 0
                    self.entry_atr = 0

            else:
                # Short position exit conditions
                stop_loss = self.entry_price + (self.stop_loss_atr * self.entry_atr)
                take_profit = self.entry_price - (self.take_profit_atr * self.entry_atr)

                # Check for support level hit (exit signal)
                hit_support = False
                for support in support_levels[:2]:  # Check first 2 levels for exit
                    if price <= support * 1.005:  # Within 0.5% of support
                        hit_support = True
                        break

                # Exit conditions
                if price >= stop_loss or price <= take_profit or hit_support:
                    self.position.close()
                    self.entry_price = 0
                    self.entry_atr = 0

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING FIBONACCI CIRCLES BASE STRATEGY ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(FibonacciCirclesBase, 'FibonacciCirclesBase')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/FibonacciCirclesBase.csv")