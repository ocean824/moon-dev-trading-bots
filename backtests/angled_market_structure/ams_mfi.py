"""
Angled Market Structure Strategy - MFI Enhanced
Combines angled pivot tracking with Money Flow Index for improved entries
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
from typing import Optional

class AngledMarketStructureMFI(Strategy):
    # Parameters
    pivot_length = 5  # Length for pivot detection
    atr_period = 14  # ATR period for volatility measurement
    angle_factor = 0.1  # Decay factor (percentage of ATR per bar)
    min_structure_breaks = 1  # Minimum structure breaks to enter
    deviation_multiplier = 1.5  # Multiplier for deviation levels

    # MFI parameters
    mfi_period = 14  # MFI calculation period
    mfi_overbought = 75  # MFI overbought level
    mfi_oversold = 25  # MFI oversold level
    mfi_neutral_low = 40  # MFI neutral zone lower bound
    mfi_neutral_high = 60  # MFI neutral zone upper bound

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

        # Calculate MFI
        self.mfi = self.I(ta.mfi, pd.Series(self.data.High),
                         pd.Series(self.data.Low),
                         pd.Series(self.data.Close),
                         pd.Series(self.data.Volume),
                         length=self.mfi_period)

        # Calculate MFI divergence
        self.mfi_divergence = self.I(self.calculate_mfi_divergence)

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

        # MFI-weighted angle adjustments
        self.mfi_angle_factor = self.I(self.calculate_mfi_angle_factor)

    def calculate_mfi_divergence(self):
        """Detect MFI divergences with price"""
        mfi = pd.Series(self.mfi)
        close = pd.Series(self.data.Close)
        divergence = np.zeros(len(mfi))

        lookback = 20
        for i in range(lookback, len(mfi)):
            # Bullish divergence: price makes lower low, MFI makes higher low
            price_window = close[i-lookback:i+1]
            mfi_window = mfi[i-lookback:i+1]

            if len(price_window) > 0 and len(mfi_window) > 0:
                price_min_idx = price_window.idxmin()
                mfi_min_idx = mfi_window.idxmin()

                if price_min_idx == i and mfi[i] > mfi[mfi_min_idx]:
                    divergence[i] = 1  # Bullish divergence

                # Bearish divergence: price makes higher high, MFI makes lower high
                price_max_idx = price_window.idxmax()
                mfi_max_idx = mfi_window.idxmax()

                if price_max_idx == i and mfi[i] < mfi[mfi_max_idx]:
                    divergence[i] = -1  # Bearish divergence

        return divergence

    def calculate_mfi_angle_factor(self):
        """Adjust angle factor based on MFI readings"""
        mfi = pd.Series(self.mfi)
        adjusted_factor = np.ones(len(mfi)) * self.angle_factor

        for i in range(len(mfi)):
            if pd.notna(mfi[i]):
                # Increase angle (steeper decay) when MFI is extreme
                if mfi[i] > self.mfi_overbought:
                    # Overbought - expect reversal down, increase high line decay
                    adjusted_factor[i] = self.angle_factor * 1.5
                elif mfi[i] < self.mfi_oversold:
                    # Oversold - expect reversal up, increase low line rise
                    adjusted_factor[i] = self.angle_factor * 1.5
                elif self.mfi_neutral_low <= mfi[i] <= self.mfi_neutral_high:
                    # Neutral zone - use normal angle
                    adjusted_factor[i] = self.angle_factor
                else:
                    # Transitional zones - slight adjustment
                    adjusted_factor[i] = self.angle_factor * 1.2

        return adjusted_factor

    def calculate_pivot_highs(self):
        """Detect pivot highs using specified length"""
        highs = pd.Series(self.data.High)
        pivot_highs = np.zeros(len(highs))

        for i in range(self.pivot_length, len(highs) - self.pivot_length):
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
            window_start = i - self.pivot_length
            window_end = i + self.pivot_length + 1

            if lows[i] == lows[window_start:window_end].min():
                pivot_lows[i] = lows[i]

        return pivot_lows

    def calculate_angled_high_line(self):
        """Calculate angled high line with MFI-adjusted decay"""
        pivot_highs = self.pivot_highs
        atr = self.atr
        mfi_factor = self.mfi_angle_factor
        angled_line = np.zeros(len(pivot_highs))

        last_pivot_idx = -1
        last_pivot_value = 0

        for i in range(len(pivot_highs)):
            if pivot_highs[i] > 0:
                last_pivot_idx = i
                last_pivot_value = pivot_highs[i]
                angled_line[i] = last_pivot_value
            elif last_pivot_idx >= 0:
                bars_since_pivot = i - last_pivot_idx
                decay = atr[i] * mfi_factor[i] * bars_since_pivot
                angled_line[i] = last_pivot_value - decay

        return angled_line

    def calculate_angled_low_line(self):
        """Calculate angled low line with MFI-adjusted rise"""
        pivot_lows = self.pivot_lows
        atr = self.atr
        mfi_factor = self.mfi_angle_factor
        angled_line = np.full(len(pivot_lows), np.inf)

        last_pivot_idx = -1
        last_pivot_value = np.inf

        for i in range(len(pivot_lows)):
            if pivot_lows[i] > 0:
                last_pivot_idx = i
                last_pivot_value = pivot_lows[i]
                angled_line[i] = last_pivot_value
            elif last_pivot_idx >= 0:
                bars_since_pivot = i - last_pivot_idx
                rise = atr[i] * mfi_factor[i] * bars_since_pivot
                angled_line[i] = last_pivot_value + rise

        return angled_line

    def detect_bullish_breaks(self):
        """Detect bullish structure breaks"""
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
        """Detect bearish structure breaks"""
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
        """Calculate upper deviation levels"""
        angled_high = self.angled_high_line
        atr = self.atr
        mfi = pd.Series(self.mfi)

        deviations = {}
        for level in [1, 2, 3]:
            # Adjust deviation size based on MFI
            mfi_adjustment = np.ones(len(atr))
            for i in range(len(mfi)):
                if pd.notna(mfi[i]):
                    if mfi[i] > self.mfi_overbought:
                        mfi_adjustment[i] = 1.2  # Wider deviations when overbought
                    elif mfi[i] < self.mfi_oversold:
                        mfi_adjustment[i] = 0.8  # Tighter deviations when oversold

            deviations[f'level_{level}'] = angled_high + (atr * self.deviation_multiplier * level * mfi_adjustment)

        return pd.DataFrame(deviations)

    def calculate_lower_deviations(self):
        """Calculate lower deviation levels"""
        angled_low = self.angled_low_line
        atr = self.atr
        mfi = pd.Series(self.mfi)

        deviations = {}
        for level in [1, 2, 3]:
            # Adjust deviation size based on MFI
            mfi_adjustment = np.ones(len(atr))
            for i in range(len(mfi)):
                if pd.notna(mfi[i]):
                    if mfi[i] > self.mfi_overbought:
                        mfi_adjustment[i] = 0.8  # Tighter deviations when overbought
                    elif mfi[i] < self.mfi_oversold:
                        mfi_adjustment[i] = 1.2  # Wider deviations when oversold

            deviations[f'level_{level}'] = angled_low - (atr * self.deviation_multiplier * level * mfi_adjustment)

        return pd.DataFrame(deviations)

    def check_mfi_conditions(self, is_long):
        """Check if MFI conditions support the trade"""
        current_mfi = self.mfi[-1]
        mfi_divergence = self.mfi_divergence[-1]

        if pd.isna(current_mfi):
            return False

        if is_long:
            # Long conditions: MFI not overbought, preferably oversold or rising
            if current_mfi > self.mfi_overbought:
                return False
            # Bonus for oversold or bullish divergence
            if current_mfi < self.mfi_oversold or mfi_divergence > 0:
                return True
            # Also allow if MFI is rising from low levels
            if len(self.mfi) > 5:
                mfi_trend = self.mfi[-1] - self.mfi[-5]
                if current_mfi < 50 and mfi_trend > 0:
                    return True
            return current_mfi < self.mfi_neutral_high
        else:
            # Short conditions: MFI not oversold, preferably overbought or falling
            if current_mfi < self.mfi_oversold:
                return False
            # Bonus for overbought or bearish divergence
            if current_mfi > self.mfi_overbought or mfi_divergence < 0:
                return True
            # Also allow if MFI is falling from high levels
            if len(self.mfi) > 5:
                mfi_trend = self.mfi[-1] - self.mfi[-5]
                if current_mfi > 50 and mfi_trend < 0:
                    return True
            return current_mfi > self.mfi_neutral_low

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
        if len(self.data) < max(self.pivot_length * 2 + self.atr_period, self.mfi_period + 5):
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
            # Bullish structure break with MFI confirmation
            if (bullish_break >= self.min_structure_breaks and
                self.check_mfi_conditions(is_long=True) and
                volume_ok and volatility_ok):

                # Calculate position size
                size = self.position_size_pct * 1000000 / current_price

                # Set stop loss at lower deviation level
                stop_loss = self.lower_deviations.iloc[-1][f'level_{self.stop_loss_deviation}']

                # Set take profit at upper deviation level (adjusted for MFI)
                current_mfi = self.mfi[-1]
                tp_level = self.take_profit_deviation
                if pd.notna(current_mfi) and current_mfi < self.mfi_oversold:
                    tp_level = min(tp_level + 1, 3)  # Extra profit potential from oversold

                take_profit = self.upper_deviations.iloc[-1][f'level_{tp_level}']

                # Enter long position
                self.buy(size=size, sl=stop_loss, tp=take_profit)

            # Bearish structure break with MFI confirmation
            elif (bearish_break >= self.min_structure_breaks and
                  self.check_mfi_conditions(is_long=False) and
                  volume_ok and volatility_ok):

                # Calculate position size
                size = self.position_size_pct * 1000000 / current_price

                # Set stop loss at upper deviation level
                stop_loss = self.upper_deviations.iloc[-1][f'level_{self.stop_loss_deviation}']

                # Set take profit at lower deviation level (adjusted for MFI)
                current_mfi = self.mfi[-1]
                tp_level = self.take_profit_deviation
                if pd.notna(current_mfi) and current_mfi > self.mfi_overbought:
                    tp_level = min(tp_level + 1, 3)  # Extra profit potential from overbought

                take_profit = self.lower_deviations.iloc[-1][f'level_{tp_level}']

                # Enter short position
                self.sell(size=size, sl=stop_loss, tp=take_profit)

        # Exit on reversal structure break or extreme MFI
        elif self.position.is_long:
            current_mfi = self.mfi[-1]
            if bearish_break >= 1 or (pd.notna(current_mfi) and current_mfi > self.mfi_overbought + 10):
                self.position.close()

        elif self.position.is_short:
            current_mfi = self.mfi[-1]
            if bullish_break >= 1 or (pd.notna(current_mfi) and current_mfi < self.mfi_oversold - 10):
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
            bt = Backtest(df, AngledMarketStructureMFI,
                         cash=1000000,
                         commission=0.001,
                         trade_on_close=False)

            # Run with default parameters
            stats = bt.run()
            print("\n" + "="*50)
            print("ANGLED MARKET STRUCTURE - MFI ENHANCED")
            print("="*50)
            print(stats)
            print("="*50)

            # Show plot
            bt.plot()
        else:
            print(f"Data missing required columns. Found: {df.columns.tolist()}")
    else:
        print(f"Data file not found: {data_path}")