"""
Angled Market Structure Strategy - ADX Enhanced
Combines angled pivot tracking with ADX for trend strength confirmation
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
from typing import Optional

class AngledMarketStructureADX(Strategy):
    # Parameters
    pivot_length = 5  # Length for pivot detection
    atr_period = 14  # ATR period for volatility measurement
    angle_factor = 0.1  # Decay factor (percentage of ATR per bar)
    min_structure_breaks = 1  # Minimum structure breaks to enter
    deviation_multiplier = 1.5  # Multiplier for deviation levels

    # ADX parameters
    adx_period = 14  # ADX calculation period
    adx_threshold = 25  # Minimum ADX for trend strength
    adx_strong = 40  # Strong trend ADX level
    adx_extreme = 60  # Extreme trend ADX level
    di_diff_threshold = 5  # Minimum DI+/- difference

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

        # Calculate ADX and directional indicators
        adx_result = ta.adx(pd.Series(self.data.High),
                            pd.Series(self.data.Low),
                            pd.Series(self.data.Close),
                            length=self.adx_period)

        if adx_result is not None and len(adx_result.columns) >= 3:
            self.adx = self.I(lambda: adx_result.iloc[:, 0].values)  # ADX
            self.di_plus = self.I(lambda: adx_result.iloc[:, 1].values)  # DI+
            self.di_minus = self.I(lambda: adx_result.iloc[:, 2].values)  # DI-
        else:
            # Fallback if ADX calculation fails
            self.adx = self.I(lambda: np.full(len(self.data.Close), 25))
            self.di_plus = self.I(lambda: np.zeros(len(self.data.Close)))
            self.di_minus = self.I(lambda: np.zeros(len(self.data.Close)))

        # Calculate ADX slope for trend acceleration
        self.adx_slope = self.I(self.calculate_adx_slope)

        # Calculate volume MA for filtering
        self.volume_ma = self.I(ta.sma, pd.Series(self.data.Volume), length=self.volume_ma_period)

        # Initialize pivot tracking arrays
        self.pivot_highs = self.I(self.calculate_pivot_highs)
        self.pivot_lows = self.I(self.calculate_pivot_lows)

        # Initialize angled lines with ADX adjustment
        self.angled_high_line = self.I(self.calculate_angled_high_line)
        self.angled_low_line = self.I(self.calculate_angled_low_line)

        # Track structure breaks
        self.bullish_breaks = self.I(self.detect_bullish_breaks)
        self.bearish_breaks = self.I(self.detect_bearish_breaks)

        # Calculate deviation levels
        self.upper_deviations = self.I(self.calculate_upper_deviations)
        self.lower_deviations = self.I(self.calculate_lower_deviations)

        # ADX-based angle adjustments
        self.adx_angle_factor = self.I(self.calculate_adx_angle_factor)

    def calculate_adx_slope(self):
        """Calculate ADX slope to detect trend acceleration"""
        adx = pd.Series(self.adx)
        slope = np.zeros(len(adx))

        lookback = 5
        for i in range(lookback, len(adx)):
            if pd.notna(adx[i]) and pd.notna(adx[i-lookback]):
                slope[i] = (adx[i] - adx[i-lookback]) / lookback

        return slope

    def calculate_adx_angle_factor(self):
        """Adjust angle factor based on ADX strength"""
        adx = pd.Series(self.adx)
        adjusted_factor = np.ones(len(adx)) * self.angle_factor

        for i in range(len(adx)):
            if pd.notna(adx[i]):
                if adx[i] < self.adx_threshold:
                    # Weak trend - reduce angle (flatter lines)
                    adjusted_factor[i] = self.angle_factor * 0.5
                elif adx[i] < self.adx_strong:
                    # Moderate trend - normal angle
                    adjusted_factor[i] = self.angle_factor
                elif adx[i] < self.adx_extreme:
                    # Strong trend - increase angle
                    adjusted_factor[i] = self.angle_factor * 1.5
                else:
                    # Extreme trend - maximum angle
                    adjusted_factor[i] = self.angle_factor * 2.0

        return adjusted_factor

    def calculate_pivot_highs(self):
        """Detect pivot highs with ADX filtering"""
        highs = pd.Series(self.data.High)
        adx = pd.Series(self.adx)
        pivot_highs = np.zeros(len(highs))

        for i in range(self.pivot_length, len(highs) - self.pivot_length):
            window_start = i - self.pivot_length
            window_end = i + self.pivot_length + 1

            # Only mark pivots when trend is not too strong (allows for reversals)
            if highs[i] == highs[window_start:window_end].max():
                if pd.isna(adx[i]) or adx[i] < self.adx_extreme:
                    pivot_highs[i] = highs[i]

        return pivot_highs

    def calculate_pivot_lows(self):
        """Detect pivot lows with ADX filtering"""
        lows = pd.Series(self.data.Low)
        adx = pd.Series(self.adx)
        pivot_lows = np.zeros(len(lows))

        for i in range(self.pivot_length, len(lows) - self.pivot_length):
            window_start = i - self.pivot_length
            window_end = i + self.pivot_length + 1

            # Only mark pivots when trend is not too strong
            if lows[i] == lows[window_start:window_end].min():
                if pd.isna(adx[i]) or adx[i] < self.adx_extreme:
                    pivot_lows[i] = lows[i]

        return pivot_lows

    def calculate_angled_high_line(self):
        """Calculate angled high line with ADX-adjusted decay"""
        pivot_highs = self.pivot_highs
        atr = self.atr
        adx_factor = self.adx_angle_factor
        di_plus = pd.Series(self.di_plus)
        di_minus = pd.Series(self.di_minus)
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

                # Adjust decay based on directional movement
                decay_multiplier = adx_factor[i]
                if pd.notna(di_plus[i]) and pd.notna(di_minus[i]):
                    if di_minus[i] > di_plus[i]:  # Bearish pressure
                        decay_multiplier *= 1.2

                decay = atr[i] * decay_multiplier * bars_since_pivot
                angled_line[i] = last_pivot_value - decay

        return angled_line

    def calculate_angled_low_line(self):
        """Calculate angled low line with ADX-adjusted rise"""
        pivot_lows = self.pivot_lows
        atr = self.atr
        adx_factor = self.adx_angle_factor
        di_plus = pd.Series(self.di_plus)
        di_minus = pd.Series(self.di_minus)
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

                # Adjust rise based on directional movement
                rise_multiplier = adx_factor[i]
                if pd.notna(di_plus[i]) and pd.notna(di_minus[i]):
                    if di_plus[i] > di_minus[i]:  # Bullish pressure
                        rise_multiplier *= 1.2

                rise = atr[i] * rise_multiplier * bars_since_pivot
                angled_line[i] = last_pivot_value + rise

        return angled_line

    def detect_bullish_breaks(self):
        """Detect bullish structure breaks with trend confirmation"""
        closes = pd.Series(self.data.Close)
        angled_high = self.angled_high_line
        adx = pd.Series(self.adx)
        di_plus = pd.Series(self.di_plus)
        di_minus = pd.Series(self.di_minus)

        breaks = np.zeros(len(closes))
        consecutive_breaks = 0

        for i in range(1, len(closes)):
            if closes[i] > angled_high[i] and closes[i-1] <= angled_high[i-1]:
                # Confirm with ADX and DI
                trend_confirmed = (pd.notna(adx[i]) and adx[i] >= self.adx_threshold and
                                 pd.notna(di_plus[i]) and pd.notna(di_minus[i]) and
                                 di_plus[i] > di_minus[i])

                if trend_confirmed or consecutive_breaks > 0:
                    consecutive_breaks += 1
                    breaks[i] = consecutive_breaks
            elif closes[i] <= angled_high[i]:
                consecutive_breaks = 0

        return breaks

    def detect_bearish_breaks(self):
        """Detect bearish structure breaks with trend confirmation"""
        closes = pd.Series(self.data.Close)
        angled_low = self.angled_low_line
        adx = pd.Series(self.adx)
        di_plus = pd.Series(self.di_plus)
        di_minus = pd.Series(self.di_minus)

        breaks = np.zeros(len(closes))
        consecutive_breaks = 0

        for i in range(1, len(closes)):
            if closes[i] < angled_low[i] and closes[i-1] >= angled_low[i-1]:
                # Confirm with ADX and DI
                trend_confirmed = (pd.notna(adx[i]) and adx[i] >= self.adx_threshold and
                                 pd.notna(di_plus[i]) and pd.notna(di_minus[i]) and
                                 di_minus[i] > di_plus[i])

                if trend_confirmed or consecutive_breaks > 0:
                    consecutive_breaks += 1
                    breaks[i] = consecutive_breaks
            elif closes[i] >= angled_low[i]:
                consecutive_breaks = 0

        return breaks

    def calculate_upper_deviations(self):
        """Calculate upper deviation levels with ADX adjustment"""
        angled_high = self.angled_high_line
        atr = self.atr
        adx = pd.Series(self.adx)

        deviations = {}
        for level in [1, 2, 3]:
            # Wider deviations in strong trends
            adx_adjustment = np.ones(len(atr))
            for i in range(len(adx)):
                if pd.notna(adx[i]):
                    if adx[i] > self.adx_strong:
                        adx_adjustment[i] = 1.2 + (adx[i] - self.adx_strong) / 100
                    elif adx[i] < self.adx_threshold:
                        adx_adjustment[i] = 0.8

            deviations[f'level_{level}'] = angled_high + (atr * self.deviation_multiplier * level * adx_adjustment)

        return pd.DataFrame(deviations)

    def calculate_lower_deviations(self):
        """Calculate lower deviation levels with ADX adjustment"""
        angled_low = self.angled_low_line
        atr = self.atr
        adx = pd.Series(self.adx)

        deviations = {}
        for level in [1, 2, 3]:
            # Wider deviations in strong trends
            adx_adjustment = np.ones(len(atr))
            for i in range(len(adx)):
                if pd.notna(adx[i]):
                    if adx[i] > self.adx_strong:
                        adx_adjustment[i] = 1.2 + (adx[i] - self.adx_strong) / 100
                    elif adx[i] < self.adx_threshold:
                        adx_adjustment[i] = 0.8

            deviations[f'level_{level}'] = angled_low - (atr * self.deviation_multiplier * level * adx_adjustment)

        return pd.DataFrame(deviations)

    def check_adx_conditions(self, is_long):
        """Check if ADX conditions support the trade"""
        current_adx = self.adx[-1]
        current_di_plus = self.di_plus[-1]
        current_di_minus = self.di_minus[-1]
        adx_slope = self.adx_slope[-1]

        # Need minimum ADX for trend
        if pd.isna(current_adx) or current_adx < self.adx_threshold:
            return False

        # Check directional indicators
        if pd.isna(current_di_plus) or pd.isna(current_di_minus):
            return False

        if is_long:
            # Long: DI+ > DI- with sufficient difference
            di_diff = current_di_plus - current_di_minus
            if di_diff < self.di_diff_threshold:
                return False

            # Bonus for rising ADX (trend strengthening)
            if adx_slope > 0:
                return True

            # Allow if strong trend
            return current_adx >= self.adx_strong or di_diff > self.di_diff_threshold * 2

        else:
            # Short: DI- > DI+ with sufficient difference
            di_diff = current_di_minus - current_di_plus
            if di_diff < self.di_diff_threshold:
                return False

            # Bonus for rising ADX (trend strengthening)
            if adx_slope > 0:
                return True

            # Allow if strong trend
            return current_adx >= self.adx_strong or di_diff > self.di_diff_threshold * 2

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
        if len(self.data) < max(self.pivot_length * 2 + self.atr_period, self.adx_period + 5):
            return

        # Get current values
        current_price = self.data.Close[-1]
        bullish_break = self.bullish_breaks[-1]
        bearish_break = self.bearish_breaks[-1]
        current_adx = self.adx[-1]

        # Check filters
        volume_ok = self.check_volume_filter()
        volatility_ok = self.check_volatility_filter()

        # Long entry conditions
        if not self.position:
            # Bullish structure break with ADX confirmation
            if (bullish_break >= self.min_structure_breaks and
                self.check_adx_conditions(is_long=True) and
                volume_ok and volatility_ok):

                # Calculate position size
                size = self.position_size_pct * 1000000 / current_price

                # Adjust stop loss based on trend strength
                sl_level = self.stop_loss_deviation
                if pd.notna(current_adx) and current_adx > self.adx_strong:
                    sl_level = max(sl_level - 1, 1)  # Tighter stop in strong trends

                stop_loss = self.lower_deviations.iloc[-1][f'level_{sl_level}']

                # Adjust take profit based on trend strength
                tp_level = self.take_profit_deviation
                if pd.notna(current_adx) and current_adx > self.adx_strong:
                    tp_level = min(tp_level + 1, 3)  # Larger targets in strong trends

                take_profit = self.upper_deviations.iloc[-1][f'level_{tp_level}']

                # Enter long position
                self.buy(size=size, sl=stop_loss, tp=take_profit)

            # Bearish structure break with ADX confirmation
            elif (bearish_break >= self.min_structure_breaks and
                  self.check_adx_conditions(is_long=False) and
                  volume_ok and volatility_ok):

                # Calculate position size
                size = self.position_size_pct * 1000000 / current_price

                # Adjust stop loss based on trend strength
                sl_level = self.stop_loss_deviation
                if pd.notna(current_adx) and current_adx > self.adx_strong:
                    sl_level = max(sl_level - 1, 1)

                stop_loss = self.upper_deviations.iloc[-1][f'level_{sl_level}']

                # Adjust take profit based on trend strength
                tp_level = self.take_profit_deviation
                if pd.notna(current_adx) and current_adx > self.adx_strong:
                    tp_level = min(tp_level + 1, 3)

                take_profit = self.lower_deviations.iloc[-1][f'level_{tp_level}']

                # Enter short position
                self.sell(size=size, sl=stop_loss, tp=take_profit)

        # Exit on reversal structure break or trend weakness
        elif self.position.is_long:
            # Exit if bearish break or trend weakening significantly
            if bearish_break >= 1 or (pd.notna(current_adx) and current_adx < self.adx_threshold * 0.7):
                self.position.close()

        elif self.position.is_short:
            # Exit if bullish break or trend weakening significantly
            if bullish_break >= 1 or (pd.notna(current_adx) and current_adx < self.adx_threshold * 0.7):
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
            bt = Backtest(df, AngledMarketStructureADX,
                         cash=1000000,
                         commission=0.001,
                         trade_on_close=False)

            # Run with default parameters
            stats = bt.run()
            print("\n" + "="*50)
            print("ANGLED MARKET STRUCTURE - ADX ENHANCED")
            print("="*50)
            print(stats)
            print("="*50)

            # Show plot
            bt.plot()
        else:
            print(f"Data missing required columns. Found: {df.columns.tolist()}")
    else:
        print(f"Data file not found: {data_path}")