"""
BE-Indicator Aggregator Toolkit - Trend Following Strategy
==========================================================

This strategy uses the BE-Indicator's condition builder to create a robust
trend-following system. It demonstrates complex ATLEAST conditions for
confirming trends across multiple timeframes and indicators.

Condition Examples:
- ATLEAST4: Requires 4 out of 6 trend indicators to agree
- Combines moving averages, momentum, and volume for confirmation
"""

from backtesting import Backtest, Strategy
import pandas as pd
import numpy as np
import pandas_ta as ta
import talib
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's BE-Indicator Trend Following Strategy Loading... 🌙")

# Data configuration
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
TAKE_PROFIT_PERCENT = 5.0  # Higher TP for trend following
STOP_LOSS_PERCENT = 2.0    # Wider stop for trends
TREND_THRESHOLD = 4        # Minimum trend indicators required

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")


class BEIndicatorTrendFollow(Strategy):
    """
    Trend Following implementation using BE-Indicator logic

    Strategy focuses on:
    1. Multiple timeframe trend confirmation
    2. ATLEAST conditions for robust signals
    3. Volume confirmation for trend strength
    4. Trailing stop logic based on trend strength
    """

    # Strategy parameters
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100
    trend_threshold = TREND_THRESHOLD

    # Multiple timeframe periods
    fast_ma = 10
    medium_ma = 20
    slow_ma = 50
    very_slow_ma = 200
    momentum_period = 14
    volume_period = 20

    def init(self):
        """Initialize trend-following indicators"""

        # Prepare data series
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        volume = pd.Series(self.data.Volume)

        # ES1: Fast MA trend (10 period)
        fast_sma = ta.sma(close, length=self.fast_ma)
        self.es1_fast_trend = ((close - fast_sma) / fast_sma * 100 + 50).clip(0, 100)

        # ES2: Medium MA trend (20 period)
        medium_ema = ta.ema(close, length=self.medium_ma)
        self.es2_medium_trend = ((close - medium_ema) / medium_ema * 100 + 50).clip(0, 100)

        # ES3: Slow MA trend (50 period)
        slow_sma = ta.sma(close, length=self.slow_ma)
        self.es3_slow_trend = ((close - slow_sma) / slow_sma * 100 + 50).clip(0, 100)

        # ES4: Very slow MA trend (200 period)
        very_slow_ema = ta.ema(close, length=self.very_slow_ma)
        self.es4_very_slow_trend = ((close - very_slow_ema) / very_slow_ema * 100 + 50).clip(0, 100)

        # ES5: MACD trend strength
        macd_result = ta.macd(close, fast=12, slow=26, signal=9)
        if macd_result is not None and len(macd_result.columns) >= 3:
            macd_line = macd_result.iloc[:, 0]
            macd_histogram = macd_result.iloc[:, 1]
            # Normalize histogram to 0-100
            hist_ma = macd_histogram.rolling(window=50).mean()
            hist_std = macd_histogram.rolling(window=50).std()
            self.es5_macd_trend = ((macd_histogram - hist_ma) / (hist_std + 0.0001) * 20 + 50).clip(0, 100)
        else:
            self.es5_macd_trend = pd.Series(50, index=close.index)

        # ES6: Price momentum (ROC)
        roc = ta.roc(close, length=self.momentum_period)
        self.es6_momentum = ((roc + 10) * 5).clip(0, 100)  # Normalize ROC to 0-100

        # ES7: Volume trend (increasing volume in trend direction)
        volume_ma = volume.rolling(window=self.volume_period).mean()
        price_change = close.pct_change()
        # Volume should increase with price movement
        volume_trend = pd.Series(np.where(
            (price_change > 0) & (volume > volume_ma), 75,  # Bullish volume
            np.where((price_change < 0) & (volume > volume_ma), 25,  # Bearish volume
            50)  # Neutral
        ), index=close.index)
        self.es7_volume_trend = ta.ema(volume_trend, length=5)

        # ES8: Directional Movement (using DMI)
        adx_result = ta.adx(high, low, close, length=14)
        if adx_result is not None and len(adx_result.columns) >= 3:
            plus_di = adx_result.iloc[:, 1]
            minus_di = adx_result.iloc[:, 2]
            # Normalize DI difference to 0-100
            di_diff = plus_di - minus_di
            self.es8_directional = ((di_diff + 50) * 1).clip(0, 100)
        else:
            self.es8_directional = pd.Series(50, index=close.index)

        # ES9: Ichimoku trend (simplified)
        # Using Tenkan (9) and Kijun (26) lines
        tenkan = (high.rolling(9).max() + low.rolling(9).min()) / 2
        kijun = (high.rolling(26).max() + low.rolling(26).min()) / 2
        self.es9_ichimoku = ((close - kijun) / kijun * 100 + 50).clip(0, 100)

        # ES10: Parabolic SAR trend
        sar = ta.psar(high, low, close)
        if sar is not None and len(sar.columns) >= 1:
            psar_long = sar.iloc[:, 0]  # Long SAR
            # If price above SAR = bullish (100), below = bearish (0)
            self.es10_psar = pd.Series(np.where(close > psar_long, 75, 25), index=close.index)
        else:
            self.es10_psar = pd.Series(50, index=close.index)

        # Calculate overall trend strength (how many indicators agree)
        self.trend_agreement = self._calculate_trend_agreement()

        # Moving average alignment (perfect trend when all MAs are aligned)
        self.ma_alignment = self._check_ma_alignment(fast_sma, medium_ema, slow_sma, very_slow_ema, close)

        # Convert to numpy arrays
        self.es1 = self.I(lambda: self.es1_fast_trend.values)
        self.es2 = self.I(lambda: self.es2_medium_trend.values)
        self.es3 = self.I(lambda: self.es3_slow_trend.values)
        self.es4 = self.I(lambda: self.es4_very_slow_trend.values)
        self.es5 = self.I(lambda: self.es5_macd_trend.values)
        self.es6 = self.I(lambda: self.es6_momentum.values)
        self.es7 = self.I(lambda: self.es7_volume_trend.values)
        self.es8 = self.I(lambda: self.es8_directional.values)
        self.es9 = self.I(lambda: self.es9_ichimoku.values)
        self.es10 = self.I(lambda: self.es10_psar.values)

        self.trend_score = self.I(lambda: self.trend_agreement.values)
        self.ma_align = self.I(lambda: self.ma_alignment.values)

    def _calculate_trend_agreement(self):
        """Calculate how many indicators show the same trend"""
        agreement = pd.Series(0, index=self.es1_fast_trend.index)

        for i in range(len(agreement)):
            bullish_count = 0
            bearish_count = 0

            # Count bullish indicators (> 60)
            if not pd.isna(self.es1_fast_trend.iloc[i]) and self.es1_fast_trend.iloc[i] > 60:
                bullish_count += 1
            if not pd.isna(self.es2_medium_trend.iloc[i]) and self.es2_medium_trend.iloc[i] > 60:
                bullish_count += 1
            if not pd.isna(self.es3_slow_trend.iloc[i]) and self.es3_slow_trend.iloc[i] > 60:
                bullish_count += 1
            if not pd.isna(self.es4_very_slow_trend.iloc[i]) and self.es4_very_slow_trend.iloc[i] > 60:
                bullish_count += 1
            if not pd.isna(self.es5_macd_trend.iloc[i]) and self.es5_macd_trend.iloc[i] > 60:
                bullish_count += 1
            if not pd.isna(self.es6_momentum.iloc[i]) and self.es6_momentum.iloc[i] > 60:
                bullish_count += 1

            # Count bearish indicators (< 40)
            if not pd.isna(self.es1_fast_trend.iloc[i]) and self.es1_fast_trend.iloc[i] < 40:
                bearish_count += 1
            if not pd.isna(self.es2_medium_trend.iloc[i]) and self.es2_medium_trend.iloc[i] < 40:
                bearish_count += 1
            if not pd.isna(self.es3_slow_trend.iloc[i]) and self.es3_slow_trend.iloc[i] < 40:
                bearish_count += 1
            if not pd.isna(self.es4_very_slow_trend.iloc[i]) and self.es4_very_slow_trend.iloc[i] < 40:
                bearish_count += 1
            if not pd.isna(self.es5_macd_trend.iloc[i]) and self.es5_macd_trend.iloc[i] < 40:
                bearish_count += 1
            if not pd.isna(self.es6_momentum.iloc[i]) and self.es6_momentum.iloc[i] < 40:
                bearish_count += 1

            # Return normalized score (0-100)
            if bullish_count > bearish_count:
                agreement.iloc[i] = 50 + (bullish_count * 8)
            else:
                agreement.iloc[i] = 50 - (bearish_count * 8)

        return agreement

    def _check_ma_alignment(self, fast, medium, slow, very_slow, price):
        """Check if moving averages are perfectly aligned for trend"""
        alignment = pd.Series(50, index=price.index)

        for i in range(len(price)):
            if pd.isna([fast.iloc[i], medium.iloc[i], slow.iloc[i], very_slow.iloc[i], price.iloc[i]]).any():
                continue

            # Bullish alignment: price > fast > medium > slow > very_slow
            if (price.iloc[i] > fast.iloc[i] > medium.iloc[i] > slow.iloc[i] > very_slow.iloc[i]):
                alignment.iloc[i] = 100

            # Bearish alignment: price < fast < medium < slow < very_slow
            elif (price.iloc[i] < fast.iloc[i] < medium.iloc[i] < slow.iloc[i] < very_slow.iloc[i]):
                alignment.iloc[i] = 0

            # Partial alignment
            elif price.iloc[i] > fast.iloc[i] and fast.iloc[i] > medium.iloc[i]:
                alignment.iloc[i] = 75
            elif price.iloc[i] < fast.iloc[i] and fast.iloc[i] < medium.iloc[i]:
                alignment.iloc[i] = 25

        return alignment

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
        Trend following logic using ATLEAST conditions

        Strategy:
        - Require at least 4 out of 6 trend indicators to agree
        - Confirm with volume and momentum
        - Use MA alignment for high-confidence entries
        """

        if len(self.data) < 200:  # Need data for 200 MA
            return

        # Get current values
        current_fast = self.es1[-1]
        current_medium = self.es2[-1]
        current_slow = self.es3[-1]
        current_very_slow = self.es4[-1]
        current_macd = self.es5[-1]
        current_momentum = self.es6[-1]
        current_volume = self.es7[-1]
        current_directional = self.es8[-1]
        current_ichimoku = self.es9[-1]
        current_psar = self.es10[-1]

        current_trend_score = self.trend_score[-1]
        current_ma_align = self.ma_align[-1]

        # Skip if indicators invalid
        if any(pd.isna([current_fast, current_medium, current_slow, current_momentum])):
            return

        if not self.position:
            # LONG CONDITIONS - Strong uptrend required
            # Primary: ATLEAST 4 trend indicators bullish
            long_trend_indicators = [
                (current_fast, 'G', 60),        # Fast MA bullish
                (current_medium, 'G', 60),      # Medium MA bullish
                (current_slow, 'G', 55),        # Slow MA bullish
                (current_very_slow, 'G', 52),   # Very slow MA bullish
                (current_macd, 'G', 60),        # MACD bullish
                (current_momentum, 'G', 60),    # Momentum bullish
                (current_directional, 'G', 60), # DMI bullish
                (current_ichimoku, 'G', 55),    # Ichimoku bullish
                (current_psar, 'G', 60)         # SAR bullish
            ]

            # Check if at least 4 indicators are bullish
            long_signal = self.evaluate_conditions('ATLEAST4', long_trend_indicators)

            # Additional confirmation: Perfect MA alignment
            if not long_signal and current_ma_align > 90:
                # Perfect alignment with volume
                long_signal = self.evaluate_conditions('AND', [
                    (current_ma_align, 'G', 90),
                    (current_volume, 'G', 60),
                    (current_momentum, 'G', 55)
                ])

            # Alternative: Very strong trend score
            if not long_signal and current_trend_score > 75:
                long_signal = self.evaluate_conditions('AND', [
                    (current_trend_score, 'G', 75),
                    (current_volume, 'G', 50),
                    (current_directional, 'G', 55)
                ])

            # SHORT CONDITIONS - Strong downtrend required
            # Primary: ATLEAST 4 trend indicators bearish
            short_trend_indicators = [
                (current_fast, 'L', 40),        # Fast MA bearish
                (current_medium, 'L', 40),      # Medium MA bearish
                (current_slow, 'L', 45),        # Slow MA bearish
                (current_very_slow, 'L', 48),   # Very slow MA bearish
                (current_macd, 'L', 40),        # MACD bearish
                (current_momentum, 'L', 40),    # Momentum bearish
                (current_directional, 'L', 40), # DMI bearish
                (current_ichimoku, 'L', 45),    # Ichimoku bearish
                (current_psar, 'L', 40)         # SAR bearish
            ]

            # Check if at least 4 indicators are bearish
            short_signal = self.evaluate_conditions('ATLEAST4', short_trend_indicators)

            # Additional confirmation: Perfect MA alignment
            if not short_signal and current_ma_align < 10:
                # Perfect bearish alignment with volume
                short_signal = self.evaluate_conditions('AND', [
                    (current_ma_align, 'L', 10),
                    (current_volume, 'G', 60),
                    (current_momentum, 'L', 45)
                ])

            # Alternative: Very weak trend score
            if not short_signal and current_trend_score < 25:
                short_signal = self.evaluate_conditions('AND', [
                    (current_trend_score, 'L', 25),
                    (current_volume, 'G', 50),
                    (current_directional, 'L', 45)
                ])

            # Execute trades
            current_price = self.data.Close[-1]

            if long_signal:
                # Dynamic position sizing based on trend strength
                strength_multiplier = min(0.95, 0.5 + (current_trend_score / 200))
                position_size = strength_multiplier

                sl_price = current_price * (1 - self.stop_loss)
                tp_price = current_price * (1 + self.take_profit)
                self.buy(sl=sl_price, tp=tp_price, size=position_size)

            elif short_signal:
                # Dynamic position sizing based on trend strength
                strength_multiplier = min(0.95, 0.5 + ((100 - current_trend_score) / 200))
                position_size = strength_multiplier

                sl_price = current_price * (1 + self.stop_loss)
                tp_price = current_price * (1 - self.take_profit)
                self.sell(sl=sl_price, tp=tp_price, size=position_size)


# Run single backtest
bt = Backtest(data, BEIndicatorTrendFollow, cash=10000000, commission=0.00045)

print("\n🌙 ===== BE-INDICATOR TREND FOLLOWING STRATEGY ===== 🌙")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")
print(f"Trend Threshold: At least {TREND_THRESHOLD} indicators must agree")
print("Using ATLEAST conditions for robust trend confirmation")

stats = bt.run()
print("\n" + "="*80)
print("BACKTEST RESULTS:")
print("="*80)
print(stats)
print("="*80)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING BE-INDICATOR TREND FOLLOW ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(BEIndicatorTrendFollow, 'BEIndicatorTrendFollow')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/BEIndicatorTrendFollow.csv")