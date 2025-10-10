"""
BE-Indicator Aggregator Toolkit - Mean Reversion Strategy
=========================================================

This strategy uses the BE-Indicator's condition builder for mean reversion
trading. It demonstrates how to use OR conditions for catching extreme
oversold/overbought conditions across different indicators.

Condition Examples:
- OR conditions for any extreme reading
- AND conditions for confirmation
- Combines oscillators, bands, and volume for reversal signals
"""

from backtesting import Backtest, Strategy
import pandas as pd
import numpy as np
import pandas_ta as ta
import talib
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's BE-Indicator Mean Reversion Strategy Loading... 🌙")

# Data configuration
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
TAKE_PROFIT_PERCENT = 2.0  # Quick profit taking for mean reversion
STOP_LOSS_PERCENT = 1.0    # Tight stop for mean reversion
EXTREME_THRESHOLD = 2.0    # Standard deviations for extreme levels

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")


class BEIndicatorMeanReversion(Strategy):
    """
    Mean Reversion implementation using BE-Indicator logic

    Strategy focuses on:
    1. Extreme oversold/overbought conditions
    2. OR conditions for multiple reversal signals
    3. Statistical deviation measurements
    4. Quick profit taking at mean reversion
    """

    # Strategy parameters
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100
    extreme_threshold = EXTREME_THRESHOLD

    # Indicator periods
    bb_period = 20
    bb_std = 2.0
    rsi_period = 14
    cci_period = 20
    stoch_period = 14
    williams_period = 14
    zscore_period = 20
    atr_period = 14
    volume_period = 20

    def init(self):
        """Initialize mean reversion indicators"""

        # Prepare data series
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        volume = pd.Series(self.data.Volume)

        # ES1: RSI extreme levels (0-100)
        rsi = ta.rsi(close, length=self.rsi_period)
        self.es1_rsi_extreme = rsi.fillna(50).reindex(close.index, fill_value=50)

        # ES2: Bollinger Band position (0-100)
        bb_result = ta.bbands(close, length=self.bb_period, std=self.bb_std)
        if bb_result is not None and len(bb_result.columns) >= 3:
            bb_lower = bb_result.iloc[:, 0]
            bb_middle = bb_result.iloc[:, 1]
            bb_upper = bb_result.iloc[:, 2]
            bb_width = bb_upper - bb_lower
            self.es2_bb_position = ((close - bb_lower) / (bb_width + 0.0001) * 100).clip(0, 100)
            self.es2_bb_position = self.es2_bb_position.fillna(50).reindex(close.index, fill_value=50)

            # Calculate BB %B for extreme detection
            self.bb_pct_b = (close - bb_lower) / (bb_width + 0.0001)
        else:
            self.es2_bb_position = pd.Series(50, index=close.index)
            self.bb_pct_b = pd.Series(0.5, index=close.index)

        # ES3: Z-Score (standard deviations from mean)
        zscore_ma = close.rolling(window=self.zscore_period).mean()
        zscore_std = close.rolling(window=self.zscore_period).std()
        zscore = (close - zscore_ma) / (zscore_std + 0.0001)
        # Normalize to 0-100
        self.es3_zscore = ((zscore + 3) / 6 * 100).clip(0, 100)
        self.es3_zscore = self.es3_zscore.fillna(50).reindex(close.index, fill_value=50)

        # ES4: CCI extreme levels
        cci = ta.cci(high, low, close, length=self.cci_period)
        # CCI typically ranges from -200 to +200
        self.es4_cci_extreme = ((cci + 200) / 4).clip(0, 100)
        self.es4_cci_extreme = self.es4_cci_extreme.fillna(50).reindex(close.index, fill_value=50)

        # ES5: Stochastic extreme levels
        stoch_result = ta.stoch(high, low, close, k=self.stoch_period, d=3)
        if stoch_result is not None and len(stoch_result.columns) >= 2:
            self.es5_stoch_k = stoch_result.iloc[:, 0].fillna(50).reindex(close.index, fill_value=50)  # %K
            self.es5_stoch_d = stoch_result.iloc[:, 1].fillna(50).reindex(close.index, fill_value=50)  # %D
        else:
            self.es5_stoch_k = pd.Series(50, index=close.index)
            self.es5_stoch_d = pd.Series(50, index=close.index)

        # ES6: Williams %R extreme levels
        williams = ta.willr(high, low, close, length=self.williams_period)
        # Williams %R ranges from -100 to 0, normalize to 0-100
        self.es6_williams = ((williams + 100)).clip(0, 100)
        self.es6_williams = self.es6_williams.fillna(50).reindex(close.index, fill_value=50)

        # ES7: Price distance from moving average (mean reversion)
        ma50 = ta.sma(close, length=50)
        price_deviation = ((close - ma50) / ma50 * 100)
        # Normalize large deviations
        self.es7_ma_deviation = ((price_deviation + 10) * 5).clip(0, 100)
        self.es7_ma_deviation = self.es7_ma_deviation.fillna(50).reindex(close.index, fill_value=50)

        # ES8: Volume spike indicator (reversals often have volume)
        volume_ma = volume.rolling(window=self.volume_period).mean()
        volume_std = volume.rolling(window=self.volume_period).std()
        volume_zscore = (volume - volume_ma) / (volume_std + 0.0001)
        self.es8_volume_spike = ((volume_zscore + 3) / 6 * 100).clip(0, 100)
        self.es8_volume_spike = self.es8_volume_spike.fillna(50).reindex(close.index, fill_value=50)

        # ES9: Keltner Channel position
        kc_result = ta.kc(high, low, close, length=20, scalar=2)
        if kc_result is not None and len(kc_result.columns) >= 3:
            kc_lower = kc_result.iloc[:, 0]
            kc_upper = kc_result.iloc[:, 2]
            kc_width = kc_upper - kc_lower
            self.es9_keltner = ((close - kc_lower) / (kc_width + 0.0001) * 100).clip(0, 100)
            self.es9_keltner = self.es9_keltner.fillna(50).reindex(close.index, fill_value=50)
        else:
            self.es9_keltner = pd.Series(50, index=close.index)

        # ES10: Combined extreme score
        # Average of all oscillator extremes
        extreme_scores = []
        for indicator in [self.es1_rsi_extreme, self.es2_bb_position, self.es3_zscore,
                         self.es4_cci_extreme, self.es5_stoch_k, self.es6_williams]:
            if indicator is not None:
                # Check if oversold (< 20) or overbought (> 80)
                # Ensure indicator is reindexed first
                indicator_reindexed = indicator.reindex(close.index, fill_value=50)
                oversold = pd.Series(np.where(indicator_reindexed < 20, 100 - indicator_reindexed, 50), index=close.index)
                overbought = pd.Series(np.where(indicator_reindexed > 80, indicator_reindexed, 50), index=close.index)
                extreme_scores.append(pd.concat([oversold, overbought], axis=1).max(axis=1))

        if extreme_scores:
            self.es10_extreme_composite = pd.concat(extreme_scores, axis=1).mean(axis=1)
        else:
            self.es10_extreme_composite = pd.Series(50, index=close.index)

        # Calculate reversal probability based on multiple extremes
        self.reversal_probability = self._calculate_reversal_probability()

        # Detect divergences for high-probability reversals
        self.divergence_signal = self._detect_oscillator_divergence(close, rsi)

        # Convert to numpy arrays
        self.es1 = self.I(lambda: self.es1_rsi_extreme.values)
        self.es2 = self.I(lambda: self.es2_bb_position.values)
        self.es3 = self.I(lambda: self.es3_zscore.values)
        self.es4 = self.I(lambda: self.es4_cci_extreme.values)
        self.es5 = self.I(lambda: self.es5_stoch_k.values)
        self.es6 = self.I(lambda: self.es6_williams.values)
        self.es7 = self.I(lambda: self.es7_ma_deviation.values)
        self.es8 = self.I(lambda: self.es8_volume_spike.values)
        self.es9 = self.I(lambda: self.es9_keltner.values)
        self.es10 = self.I(lambda: self.es10_extreme_composite.values)

        self.reversal_prob = self.I(lambda: self.reversal_probability.values)
        self.divergence = self.I(lambda: self.divergence_signal.values)

    def _calculate_reversal_probability(self):
        """Calculate probability of reversal based on extreme readings - OPTIMIZED"""
        # Vectorized calculation of oversold/overbought conditions
        oversold_count = (
            (self.es1_rsi_extreme < 25).astype(int).fillna(0) +
            (self.es2_bb_position < 10).astype(int).fillna(0) +
            (self.es3_zscore < 20).astype(int).fillna(0) +
            (self.es5_stoch_k < 20).astype(int).fillna(0) +
            (self.es6_williams < 20).astype(int).fillna(0)
        )

        overbought_count = (
            (self.es1_rsi_extreme > 75).astype(int).fillna(0) +
            (self.es2_bb_position > 90).astype(int).fillna(0) +
            (self.es3_zscore > 80).astype(int).fillna(0) +
            (self.es5_stoch_k > 80).astype(int).fillna(0) +
            (self.es6_williams > 80).astype(int).fillna(0)
        )

        # Initialize probability series
        prob = pd.Series(50, index=self.es1_rsi_extreme.index)

        # Apply oversold conditions (bullish reversal)
        oversold_mask = oversold_count >= 2
        prob[oversold_mask] = np.minimum(90, 50 + oversold_count[oversold_mask] * 15)

        # Apply overbought conditions (bearish reversal)
        overbought_mask = overbought_count >= 2
        prob[overbought_mask] = np.maximum(10, 50 - overbought_count[overbought_mask] * 15)

        return prob

    def _detect_oscillator_divergence(self, price, oscillator):
        """Detect divergences between price and oscillator - SIMPLIFIED"""
        # Simplified divergence detection using rolling comparisons
        lookback = 14

        # Calculate price and oscillator changes
        price_change = price.diff(lookback)
        osc_change = oscillator.diff(lookback)

        # Initialize divergence series
        divergence = pd.Series(0, index=price.index)

        # Bullish divergence: price down, oscillator up
        bullish_div = (price_change < -price.rolling(lookback).std() * 0.5) & (osc_change > 0)
        divergence[bullish_div] = 1

        # Bearish divergence: price up, oscillator down
        bearish_div = (price_change > price.rolling(lookback).std() * 0.5) & (osc_change < 0)
        divergence[bearish_div] = -1

        # Smooth the signal to reduce noise
        divergence = divergence.rolling(3).max().fillna(0)

        return divergence

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
        Mean reversion logic using OR conditions for extremes

        Strategy:
        - Use OR conditions to catch any extreme reading
        - Confirm with volume or divergence
        - Quick profit taking when price reverts to mean
        """

        if len(self.data) < 50:
            return

        # Get current values
        current_rsi = self.es1[-1]
        current_bb = self.es2[-1]
        current_zscore = self.es3[-1]
        current_cci = self.es4[-1]
        current_stoch = self.es5[-1]
        current_williams = self.es6[-1]
        current_ma_dev = self.es7[-1]
        current_volume = self.es8[-1]
        current_keltner = self.es9[-1]
        current_extreme = self.es10[-1]

        current_reversal_prob = self.reversal_prob[-1]
        current_divergence = self.divergence[-1]

        # Skip if indicators invalid
        if any(pd.isna([current_rsi, current_bb, current_stoch])):
            return

        if not self.position:
            # LONG CONDITIONS - Extreme oversold
            # Primary: Any extreme oversold condition (OR)
            oversold_extremes = [
                (current_rsi, 'L', 25),          # RSI extreme oversold
                (current_bb, 'L', 5),            # Below lower BB
                (current_zscore, 'L', 17),       # Z-score < -2
                (current_cci, 'L', 15),          # CCI extreme oversold
                (current_stoch, 'L', 15),        # Stoch extreme oversold
                (current_williams, 'L', 15),     # Williams extreme oversold
                (current_keltner, 'L', 10)       # Below Keltner lower
            ]

            # Check if ANY extreme is met (OR condition)
            long_signal = self.evaluate_conditions('OR', oversold_extremes)

            # Additional confirmation with multiple extremes
            if not long_signal:
                # ATLEAST 2 oversold with volume
                oversold_with_volume = [
                    (current_rsi, 'L', 30),
                    (current_bb, 'L', 15),
                    (current_stoch, 'L', 20),
                    (current_volume, 'G', 70)  # Volume spike
                ]
                long_signal = self.evaluate_conditions('ATLEAST2', oversold_with_volume)

            # High probability reversal
            if not long_signal:
                long_signal = self.evaluate_conditions('AND', [
                    (current_reversal_prob, 'G', 75),
                    (current_extreme, 'G', 70)
                ])

            # Bullish divergence signal
            if not long_signal and current_divergence == 1:
                long_signal = self.evaluate_conditions('AND', [
                    (current_divergence, 'E', 1),
                    (current_rsi, 'L', 40)
                ])

            # SHORT CONDITIONS - Extreme overbought
            # Primary: Any extreme overbought condition (OR)
            overbought_extremes = [
                (current_rsi, 'G', 75),          # RSI extreme overbought
                (current_bb, 'G', 95),           # Above upper BB
                (current_zscore, 'G', 83),       # Z-score > +2
                (current_cci, 'G', 85),          # CCI extreme overbought
                (current_stoch, 'G', 85),        # Stoch extreme overbought
                (current_williams, 'G', 85),     # Williams extreme overbought
                (current_keltner, 'G', 90)       # Above Keltner upper
            ]

            # Check if ANY extreme is met (OR condition)
            short_signal = self.evaluate_conditions('OR', overbought_extremes)

            # Additional confirmation with multiple extremes
            if not short_signal:
                # ATLEAST 2 overbought with volume
                overbought_with_volume = [
                    (current_rsi, 'G', 70),
                    (current_bb, 'G', 85),
                    (current_stoch, 'G', 80),
                    (current_volume, 'G', 70)  # Volume spike
                ]
                short_signal = self.evaluate_conditions('ATLEAST2', overbought_with_volume)

            # High probability reversal
            if not short_signal:
                short_signal = self.evaluate_conditions('AND', [
                    (current_reversal_prob, 'L', 25),
                    (current_extreme, 'G', 70)
                ])

            # Bearish divergence signal
            if not short_signal and current_divergence == -1:
                short_signal = self.evaluate_conditions('AND', [
                    (current_divergence, 'E', -1),
                    (current_rsi, 'G', 60)
                ])

            # Execute trades with tight stops for mean reversion
            current_price = self.data.Close[-1]

            if long_signal:
                # Tighter stop for mean reversion
                sl_price = current_price * (1 - self.stop_loss)
                tp_price = current_price * (1 + self.take_profit)

                # Larger position for high probability reversals
                if current_reversal_prob > 80:
                    position_size = 0.95
                else:
                    position_size = 0.75

                self.buy(sl=sl_price, tp=tp_price, size=position_size)

            elif short_signal:
                # Tighter stop for mean reversion
                sl_price = current_price * (1 + self.stop_loss)
                tp_price = current_price * (1 - self.take_profit)

                # Larger position for high probability reversals
                if current_reversal_prob < 20:
                    position_size = 0.95
                else:
                    position_size = 0.75

                self.sell(sl=sl_price, tp=tp_price, size=position_size)


# Run single backtest
bt = Backtest(data, BEIndicatorMeanReversion, cash=10000000, commission=0.00045)

print("\n🌙 ===== BE-INDICATOR MEAN REVERSION STRATEGY ===== 🌙")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")
print(f"Extreme Threshold: {EXTREME_THRESHOLD} standard deviations")
print("Using OR conditions for extreme oversold/overbought detection")

stats = bt.run()
print("\n" + "="*80)
print("BACKTEST RESULTS:")
print("="*80)
print(stats)
print("="*80)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING BE-INDICATOR MEAN REVERSION ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(BEIndicatorMeanReversion, 'BEIndicatorMeanReversion')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/BEIndicatorMeanReversion.csv")