"""
BE-Indicator Aggregator Toolkit - ADX Trend Strength Strategy
=============================================================

This strategy enhances the BE-Indicator with ADX (Average Directional Index)
for trend strength filtering. ADX helps avoid false signals in ranging markets
and confirms strong trends for better entry timing.

Key Enhancements:
- ADX trend strength filter (only trade in trending markets)
- Directional movement (+DI/-DI) for trend direction
- Trend persistence requirements
"""

from backtesting import Backtest, Strategy
import pandas as pd
import numpy as np
import pandas_ta as ta
import talib
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's BE-Indicator ADX Trend Strategy Loading... 🌙")

# Data configuration
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
TAKE_PROFIT_PERCENT = 4.0  # Higher TP in trending markets
STOP_LOSS_PERCENT = 1.8    # Slightly wider stop for trends
ADX_PERIOD = 14            # ADX period
ADX_THRESHOLD = 25         # Minimum ADX for trend

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")


class BEIndicatorADX(Strategy):
    """
    ADX-enhanced implementation of BE-Indicator Aggregator

    Key features:
    1. ADX trend strength filter (avoid ranging markets)
    2. +DI/-DI for trend direction confirmation
    3. Trend persistence checks
    4. Dynamic position sizing based on trend strength
    """

    # Strategy parameters
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100
    adx_threshold = ADX_THRESHOLD
    adx_period = ADX_PERIOD

    # Indicator periods
    es1_period = 14  # RSI
    es2_period = 20  # SMA
    es3_period = 50  # EMA
    es4_period = 12  # MACD fast
    es5_period = 26  # MACD slow
    es6_period = 9   # MACD signal
    es7_period = 20  # BB period
    es8_period = 14  # Stochastic
    es9_period = 10  # CCI
    es10_period = 20 # Volume MA

    def init(self):
        """Initialize indicators with ADX for trend filtering"""

        # Prepare data series
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        volume = pd.Series(self.data.Volume)

        # PRIMARY: ADX, +DI, -DI for trend analysis
        adx_result = ta.adx(high, low, close, length=self.adx_period)
        if adx_result is not None and len(adx_result.columns) >= 3:
            self.adx = adx_result.iloc[:, 0]  # ADX
            self.plus_di = adx_result.iloc[:, 1]  # +DI
            self.minus_di = adx_result.iloc[:, 2]  # -DI
        else:
            # Fallback calculation using talib
            self.adx = talib.ADX(high.values, low.values, close.values, timeperiod=self.adx_period)
            self.plus_di = talib.PLUS_DI(high.values, low.values, close.values, timeperiod=self.adx_period)
            self.minus_di = talib.MINUS_DI(high.values, low.values, close.values, timeperiod=self.adx_period)
            self.adx = pd.Series(self.adx, index=close.index)
            self.plus_di = pd.Series(self.plus_di, index=close.index)
            self.minus_di = pd.Series(self.minus_di, index=close.index)

        # Calculate trend strength score (0-100)
        self.trend_strength = (self.adx / 50 * 100).clip(0, 100)

        # Determine trend direction
        self.trend_direction = pd.Series(np.where(
            self.plus_di > self.minus_di, 1,  # Bullish
            np.where(self.plus_di < self.minus_di, -1, 0)  # Bearish or neutral
        ), index=close.index)

        # ES1: RSI
        self.es1_rsi = ta.rsi(close, length=self.es1_period)
        self.es1_rsi = self.es1_rsi.fillna(50).reindex(close.index, fill_value=50)

        # ES2: SMA difference (trend alignment)
        sma = ta.sma(close, length=self.es2_period)
        self.es2_sma_diff = ((close - sma) / sma * 100)
        self.es2_sma_diff = self.es2_sma_diff.fillna(0).reindex(close.index, fill_value=0)

        # ES3: EMA difference (faster trend)
        ema = ta.ema(close, length=self.es3_period)
        self.es3_ema_diff = ((close - ema) / ema * 100)
        self.es3_ema_diff = self.es3_ema_diff.fillna(0).reindex(close.index, fill_value=0)

        # ES4-ES5: MACD
        macd_result = ta.macd(close, fast=self.es4_period, slow=self.es5_period, signal=self.es6_period)
        if macd_result is not None and len(macd_result.columns) >= 3:
            macd_line = macd_result.iloc[:, 0]
            macd_signal = macd_result.iloc[:, 2]
            self.es4_macd = ((macd_line - macd_line.min()) / (macd_line.max() - macd_line.min() + 0.0001) * 100)
            self.es5_macd_signal = ((macd_signal - macd_signal.min()) / (macd_signal.max() - macd_signal.min() + 0.0001) * 100)
        else:
            self.es4_macd = pd.Series(50, index=close.index)
            self.es5_macd_signal = pd.Series(50, index=close.index)

        # ES6: Bollinger Bands (standard deviation fixed)
        bb_result = ta.bbands(close, length=self.es7_period, std=2.0)
        if bb_result is not None and len(bb_result.columns) >= 3:
            bb_lower = bb_result.iloc[:, 0]
            bb_upper = bb_result.iloc[:, 2]
            bb_width = bb_upper - bb_lower
            self.es6_bb_position = ((close - bb_lower) / (bb_width + 0.0001) * 100).clip(0, 100)
            self.es6_bb_position = self.es6_bb_position.fillna(50).reindex(close.index, fill_value=50)
        else:
            self.es6_bb_position = pd.Series(50, index=close.index)

        # ES7: Trend strength normalized (using ADX directly)
        self.es7_trend = self.trend_strength

        # ES8: Stochastic
        stoch_result = ta.stoch(high, low, close, k=self.es8_period, d=3)
        if stoch_result is not None and len(stoch_result.columns) >= 1:
            self.es8_stoch = stoch_result.iloc[:, 0]
            self.es8_stoch = self.es8_stoch.fillna(50).reindex(close.index, fill_value=50)
        else:
            self.es8_stoch = pd.Series(50, index=close.index)

        # ES9: CCI
        cci = ta.cci(high, low, close, length=self.es9_period)
        self.es9_cci = ((cci + 200) / 4).clip(0, 100)
        self.es9_cci = self.es9_cci.fillna(50).reindex(close.index, fill_value=50)

        # ES10: Volume trend indicator
        volume_ma = volume.rolling(window=self.es10_period).mean()
        volume_ratio = volume / (volume_ma + 1)
        # Smooth volume ratio with EMA
        self.es10_volume_trend = ta.ema(volume_ratio * 50, length=5).clip(0, 100)
        self.es10_volume_trend = self.es10_volume_trend.fillna(50).reindex(close.index, fill_value=50)

        # Trend persistence check (how long has trend been active)
        self.trend_persistence = self._calculate_trend_persistence(self.adx, self.trend_direction)

        # Convert to numpy arrays
        self.es1 = self.I(lambda: self.es1_rsi.values)
        self.es2 = self.I(lambda: self.es2_sma_diff.values)
        self.es3 = self.I(lambda: self.es3_ema_diff.values)
        self.es4 = self.I(lambda: self.es4_macd.values)
        self.es5 = self.I(lambda: self.es5_macd_signal.values)
        self.es6 = self.I(lambda: self.es6_bb_position.values)
        self.es7 = self.I(lambda: self.es7_trend.values)
        self.es8 = self.I(lambda: self.es8_stoch.values)
        self.es9 = self.I(lambda: self.es9_cci.values)
        self.es10 = self.I(lambda: self.es10_volume_trend.values)

        # ADX components
        self.adx_values = self.I(lambda: self.adx.values)
        self.plus_di_values = self.I(lambda: self.plus_di.values)
        self.minus_di_values = self.I(lambda: self.minus_di.values)
        self.trend_dir = self.I(lambda: self.trend_direction.values)
        self.trend_persist = self.I(lambda: self.trend_persistence.values)

    def _calculate_trend_persistence(self, adx, trend_direction):
        """Calculate how many bars the trend has been active"""
        persistence = pd.Series(0, index=adx.index)
        counter = 0
        prev_direction = 0

        for i in range(len(adx)):
            if pd.isna(adx.iloc[i]) or pd.isna(trend_direction.iloc[i]):
                persistence.iloc[i] = 0
                continue

            current_direction = trend_direction.iloc[i]

            # Check if trend is strong enough
            if adx.iloc[i] >= self.adx_threshold:
                if current_direction == prev_direction and current_direction != 0:
                    counter += 1
                else:
                    counter = 1 if current_direction != 0 else 0
            else:
                counter = 0

            persistence.iloc[i] = counter
            prev_direction = current_direction

        return persistence

    def check_condition(self, source, operator, threshold):
        """Check a single condition"""
        if operator == 'G':
            return source > threshold
        elif operator == 'L':
            return source < threshold
        elif operator == 'E':
            return abs(source - threshold) < 1
        return False

    def evaluate_conditions(self, condition_type, conditions):
        """Evaluate complex condition logic"""
        results = [self.check_condition(src, op, thresh) for src, op, thresh in conditions]

        if condition_type == 'OR':
            return any(results)
        elif condition_type == 'AND':
            return all(results)
        elif condition_type.startswith('ATLEAST'):
            required = int(condition_type.replace('ATLEAST', ''))
            return sum(results) >= required
        return False

    def next(self):
        """
        ADX-enhanced trading logic

        Rules:
        1. Only trade when ADX > threshold (trending market)
        2. Use +DI/-DI for trend direction confirmation
        3. Require trend persistence for higher confidence
        4. Adjust conditions based on trend strength
        """

        if len(self.data) < 50:
            return

        # Get current values
        current_rsi = self.es1[-1]
        current_sma_diff = self.es2[-1]
        current_ema_diff = self.es3[-1]
        current_macd = self.es4[-1]
        current_macd_signal = self.es5[-1]
        current_bb = self.es6[-1]
        current_trend_strength = self.es7[-1]
        current_stoch = self.es8[-1]
        current_cci = self.es9[-1]
        current_volume = self.es10[-1]

        # ADX components
        current_adx = self.adx_values[-1]
        current_plus_di = self.plus_di_values[-1]
        current_minus_di = self.minus_di_values[-1]
        current_trend_dir = self.trend_dir[-1]
        current_persist = self.trend_persist[-1]

        # Skip if indicators invalid
        if any(pd.isna([current_adx, current_rsi, current_macd])):
            return

        # PRIMARY FILTER: Only trade in trending markets
        if current_adx < self.adx_threshold:
            return  # Market is ranging, skip trading

        if not self.position:
            # LONG CONDITIONS - Strong uptrend required
            long_conditions = [
                # Primary: Strong uptrend with momentum
                [(current_adx, 'G', self.adx_threshold),
                 (current_plus_di, 'G', current_minus_di),
                 (current_trend_dir, 'E', 1),
                 (current_rsi, 'G', 40), (current_rsi, 'L', 70)],

                # Trend persistence with pullback entry
                [(current_persist, 'G', 3),
                 (current_rsi, 'L', 45),
                 (current_bb, 'L', 40),
                 (current_trend_strength, 'G', 30)],

                # Strong trend with MACD confirmation
                [(current_adx, 'G', 30),
                 (current_macd, 'G', current_macd_signal),
                 (current_sma_diff, 'G', 0),
                 (current_volume, 'G', 50)],

                # Very strong trend, less strict conditions
                [(current_adx, 'G', 40),
                 (current_plus_di, 'G', 25),
                 (current_trend_dir, 'E', 1)]
            ]

            long_signal = False
            for condition_group in long_conditions:
                if self.evaluate_conditions('AND', condition_group):
                    long_signal = True
                    break

            # Alternative: Multiple trend confirmations
            trend_bullish = [
                (current_adx, 'G', 25),
                (current_plus_di, 'G', current_minus_di),
                (current_sma_diff, 'G', 0),
                (current_ema_diff, 'G', 0),
                (current_macd, 'G', current_macd_signal),
                (current_persist, 'G', 2)
            ]

            if not long_signal:
                long_signal = self.evaluate_conditions('ATLEAST4', trend_bullish)

            # SHORT CONDITIONS - Strong downtrend required
            short_conditions = [
                # Primary: Strong downtrend with momentum
                [(current_adx, 'G', self.adx_threshold),
                 (current_minus_di, 'G', current_plus_di),
                 (current_trend_dir, 'E', -1),
                 (current_rsi, 'L', 60), (current_rsi, 'G', 30)],

                # Trend persistence with pullback entry
                [(current_persist, 'G', 3),
                 (current_rsi, 'G', 55),
                 (current_bb, 'G', 60),
                 (current_trend_strength, 'G', 30)],

                # Strong trend with MACD confirmation
                [(current_adx, 'G', 30),
                 (current_macd, 'L', current_macd_signal),
                 (current_sma_diff, 'L', 0),
                 (current_volume, 'G', 50)],

                # Very strong trend, less strict conditions
                [(current_adx, 'G', 40),
                 (current_minus_di, 'G', 25),
                 (current_trend_dir, 'E', -1)]
            ]

            short_signal = False
            for condition_group in short_conditions:
                if self.evaluate_conditions('AND', condition_group):
                    short_signal = True
                    break

            # Alternative: Multiple trend confirmations
            trend_bearish = [
                (current_adx, 'G', 25),
                (current_minus_di, 'G', current_plus_di),
                (current_sma_diff, 'L', 0),
                (current_ema_diff, 'L', 0),
                (current_macd, 'L', current_macd_signal),
                (current_persist, 'G', 2)
            ]

            if not short_signal:
                short_signal = self.evaluate_conditions('ATLEAST4', trend_bearish)

            # Execute trades with dynamic sizing based on trend strength
            current_price = self.data.Close[-1]

            # Adjust position size based on ADX strength (stronger trend = larger position)
            position_multiplier = min(0.95, 0.5 + (current_adx / 100))
            position_size = position_multiplier

            if long_signal:
                # Wider stops in strong trends
                sl_multiplier = 1 + (current_adx / 100)
                tp_multiplier = 1 + (current_adx / 50)

                sl_price = current_price * (1 - self.stop_loss * sl_multiplier)
                tp_price = current_price * (1 + self.take_profit * tp_multiplier)
                self.buy(sl=sl_price, tp=tp_price, size=position_size)

            elif short_signal:
                # Wider stops in strong trends
                sl_multiplier = 1 + (current_adx / 100)
                tp_multiplier = 1 + (current_adx / 50)

                sl_price = current_price * (1 + self.stop_loss * sl_multiplier)
                tp_price = current_price * (1 - self.take_profit * tp_multiplier)
                self.sell(sl=sl_price, tp=tp_price, size=position_size)


# Run single backtest
bt = Backtest(data, BEIndicatorADX, cash=10000000, commission=0.00045)

print("\n🌙 ===== BE-INDICATOR ADX TREND STRATEGY ===== 🌙")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")
print(f"ADX Threshold: {ADX_THRESHOLD}")
print("Trend strength filtering with ADX, +DI/-DI directional analysis")

stats = bt.run()
print("\n" + "="*80)
print("BACKTEST RESULTS:")
print("="*80)
print(stats)
print("="*80)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING BE-INDICATOR ADX ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(BEIndicatorADX, 'BEIndicatorADX')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/BEIndicatorADX.csv")