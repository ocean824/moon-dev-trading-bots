"""
Angled Market Structure Strategy - Base Implementation
Detects market structure breaks using angled pivot tracking with ATR-based decay
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
from typing import Optional

class AngledMarketStructureBase(Strategy):
    # Parameters
    pivot_length = 5  # Length for pivot detection
    atr_period = 14  # ATR period for volatility measurement
    angle_factor = 0.1  # Decay factor (percentage of ATR per bar)
    min_structure_breaks = 1  # Minimum structure breaks to enter
    deviation_multiplier = 1.5  # Multiplier for deviation levels

    # Risk management
    position_size_pct = 0.95  # Percentage of capital to use
    stop_loss_deviation = 2  # Stop loss at -2 deviation level
    take_profit_deviation = 3  # Take profit at +3 deviation level

    # Volume and volatility filters
    volume_ma_period = 20  # Volume MA period
    min_volume_ratio = 0.8  # Minimum volume ratio vs MA
    max_atr_percentile = 80  # Maximum ATR percentile for entry

    def init(self):
        # Calculate ATR for angle decay
        self.atr = self.I(ta.atr, pd.Series(self.data.High),
                         pd.Series(self.data.Low),
                         pd.Series(self.data.Close),
                         length=self.atr_period)

        # Calculate volume MA for filtering
        self.volume_ma = self.I(ta.sma, pd.Series(self.data.Volume), length=self.volume_ma_period)

        # Initialize pivot tracking arrays
        self.pivot_highs = self.I(self.calculate_pivot_highs)
        self.pivot_lows = self.I(self.calculate_pivot_lows)

        # Initialize angled lines
        self.angled_high_line = self.I(self.calculate_angled_high_line)
        self.angled_low_line = self.I(self.calculate_angled_low_line)

        # Track structure breaks
        self.bullish_breaks = self.I(self.detect_bullish_breaks)
        self.bearish_breaks = self.I(self.detect_bearish_breaks)

        # Calculate deviation levels
        self.upper_deviations = self.I(self.calculate_upper_deviations)
        self.lower_deviations = self.I(self.calculate_lower_deviations)

    def calculate_pivot_highs(self):
        """Detect pivot highs using specified length"""
        highs = pd.Series(self.data.High)
        pivot_highs = np.zeros(len(highs))

        for i in range(self.pivot_length, len(highs) - self.pivot_length):
            # Check if current high is highest in the window
            window_start = i - self.pivot_length
            window_end = i + self.pivot_length + 1

            if highs[i] == highs[window_start:window_end].max():
                pivot_highs[i] = highs[i]

        return pivot_highs

    def calculate_pivot_lows(self):
        """Detect pivot lows using specified length"""
        lows = pd.Series(self.data.Low)
        pivot_lows = np.zeros(len(lows))

        for i in range(self.pivot_length, len(lows) - self.pivot_length):
            # Check if current low is lowest in the window
            window_start = i - self.pivot_length
            window_end = i + self.pivot_length + 1

            if lows[i] == lows[window_start:window_end].min():
                pivot_lows[i] = lows[i]

        return pivot_lows

    def calculate_angled_high_line(self):
        """Calculate angled high line that decays by ATR * angle_factor each bar"""
        pivot_highs = self.pivot_highs
        atr = self.atr
        angled_line = np.zeros(len(pivot_highs))

        last_pivot_idx = -1
        last_pivot_value = 0

        for i in range(len(pivot_highs)):
            if pivot_highs[i] > 0:
                # New pivot found
                last_pivot_idx = i
                last_pivot_value = pivot_highs[i]
                angled_line[i] = last_pivot_value
            elif last_pivot_idx >= 0:
                # Decay the line by ATR * angle_factor
                bars_since_pivot = i - last_pivot_idx
                decay = atr[i] * self.angle_factor * bars_since_pivot
                angled_line[i] = last_pivot_value - decay

        return angled_line

    def calculate_angled_low_line(self):
        """Calculate angled low line that rises by ATR * angle_factor each bar"""
        pivot_lows = self.pivot_lows
        atr = self.atr
        angled_line = np.full(len(pivot_lows), np.inf)

        last_pivot_idx = -1
        last_pivot_value = np.inf

        for i in range(len(pivot_lows)):
            if pivot_lows[i] > 0:
                # New pivot found
                last_pivot_idx = i
                last_pivot_value = pivot_lows[i]
                angled_line[i] = last_pivot_value
            elif last_pivot_idx >= 0:
                # Rise the line by ATR * angle_factor
                bars_since_pivot = i - last_pivot_idx
                rise = atr[i] * self.angle_factor * bars_since_pivot
                angled_line[i] = last_pivot_value + rise

        return angled_line

    def detect_bullish_breaks(self):
        """Detect bullish structure breaks (price crosses above angled high line)"""
        closes = pd.Series(self.data.Close)
        angled_high = self.angled_high_line

        breaks = np.zeros(len(closes))
        consecutive_breaks = 0

        for i in range(1, len(closes)):
            if closes[i] > angled_high[i] and closes[i-1] <= angled_high[i-1]:
                consecutive_breaks += 1
                breaks[i] = consecutive_breaks
            elif closes[i] <= angled_high[i]:
                consecutive_breaks = 0

        return breaks

    def detect_bearish_breaks(self):
        """Detect bearish structure breaks (price crosses below angled low line)"""
        closes = pd.Series(self.data.Close)
        angled_low = self.angled_low_line

        breaks = np.zeros(len(closes))
        consecutive_breaks = 0

        for i in range(1, len(closes)):
            if closes[i] < angled_low[i] and closes[i-1] >= angled_low[i-1]:
                consecutive_breaks += 1
                breaks[i] = consecutive_breaks
            elif closes[i] >= angled_low[i]:
                consecutive_breaks = 0

        return breaks

    def calculate_upper_deviations(self):
        """Calculate upper deviation levels (+1, +2, +3)"""
        angled_high = self.angled_high_line
        atr = self.atr

        deviations = {}
        for level in [1, 2, 3]:
            deviations[f'level_{level}'] = angled_high + (atr * self.deviation_multiplier * level)

        return pd.DataFrame(deviations)

    def calculate_lower_deviations(self):
        """Calculate lower deviation levels (-1, -2, -3)"""
        angled_low = self.angled_low_line
        atr = self.atr

        deviations = {}
        for level in [1, 2, 3]:
            deviations[f'level_{level}'] = angled_low - (atr * self.deviation_multiplier * level)

        return pd.DataFrame(deviations)

    def check_volume_filter(self):
        """Check if volume conditions are met"""
        current_volume = self.data.Volume[-1]
        volume_ma = self.volume_ma[-1]

        if pd.isna(volume_ma) or volume_ma == 0:
            return False

        return current_volume >= volume_ma * self.min_volume_ratio

    def check_volatility_filter(self):
        """Check if volatility conditions are met"""
        current_atr = self.atr[-1]
        atr_series = pd.Series(self.atr)
        atr_percentile = (atr_series <= current_atr).mean() * 100

        return atr_percentile <= self.max_atr_percentile

    def next(self):
        # Skip if we don't have enough data
        if len(self.data) < self.pivot_length * 2 + self.atr_period:
            return

        # Get current values
        current_price = self.data.Close[-1]
        bullish_break = self.bullish_breaks[-1]
        bearish_break = self.bearish_breaks[-1]

        # Check filters
        volume_ok = self.check_volume_filter()
        volatility_ok = self.check_volatility_filter()

        # Long entry conditions
        if not self.position:
            # Bullish structure break with minimum breaks and filters
            if (bullish_break >= self.min_structure_breaks and
                volume_ok and volatility_ok):

                # Calculate position size
                size = self.position_size_pct * 1000000 / current_price

                # Set stop loss at lower deviation level
                stop_loss = self.lower_deviations.iloc[-1][f'level_{self.stop_loss_deviation}']

                # Set take profit at upper deviation level
                take_profit = self.upper_deviations.iloc[-1][f'level_{self.take_profit_deviation}']

                # Enter long position
                self.buy(size=size, sl=stop_loss, tp=take_profit)

            # Bearish structure break with minimum breaks and filters
            elif (bearish_break >= self.min_structure_breaks and
                  volume_ok and volatility_ok):

                # Calculate position size
                size = self.position_size_pct * 1000000 / current_price

                # Set stop loss at upper deviation level
                stop_loss = self.upper_deviations.iloc[-1][f'level_{self.stop_loss_deviation}']

                # Set take profit at lower deviation level
                take_profit = self.lower_deviations.iloc[-1][f'level_{self.take_profit_deviation}']

                # Enter short position
                self.sell(size=size, sl=stop_loss, tp=take_profit)

        # Exit on reversal structure break
        elif self.position.is_long and bearish_break >= 1:
            self.position.close()

        elif self.position.is_short and bullish_break >= 1:
            self.position.close()


if __name__ == "__main__":
    # Load sample data for testing
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

    # Test with BTC data
    data_path = "/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/BTC-USD-15m.csv"

    if os.path.exists(data_path):
        df = pd.read_csv(data_path)
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.set_index('Date')

        # Ensure we have required columns
        required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        if all(col in df.columns for col in required_columns):
            # Run backtest
            bt = Backtest(df, AngledMarketStructureBase,
                         cash=1000000,
                         commission=0.001,
                         trade_on_close=False)

            # Run with default parameters
            stats = bt.run()
            print("\n" + "="*50)
            print("ANGLED MARKET STRUCTURE - BASE STRATEGY")
            print("="*50)
            print(stats)
            print("="*50)

            # Show plot
            bt.plot()
        else:
            print(f"Data missing required columns. Found: {df.columns.tolist()}")
    else:
        print(f"Data file not found: {data_path}")