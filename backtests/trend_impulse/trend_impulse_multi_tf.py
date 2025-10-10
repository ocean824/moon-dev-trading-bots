"""
Moon Dev's Trend Impulse Channels Multi-Timeframe Strategy
===========================================================
Multiple timeframe confirmation for higher probability trades.
Uses higher timeframe trend direction and lower timeframe entries.
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Trend Impulse Channels Multi-TF Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Multi-timeframe parameters
HTF_MULTIPLIER = 4  # Higher timeframe multiplier (4h if base is 1h)
MTF_MULTIPLIER = 2  # Medium timeframe multiplier

# Trend Impulse parameters for each timeframe
ATR_PERIOD_HTF = 50  # Higher TF - longer period
ATR_PERIOD_MTF = 100  # Medium TF
ATR_PERIOD_LTF = 200  # Lower TF - base timeframe

TRIGGER_THRESHOLD = 2.86
MAX_STEP_SIZE = 0.034
BAND_MULTIPLIER = 2.02

# Risk management
TAKE_PROFIT_PERCENT = 3.5  # Higher targets with MTF confirmation
STOP_LOSS_PERCENT = 1.5  # Tighter stops with better entries

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class TrendImpulseMultiTF(Strategy):
    """
    Trend Impulse Channels with Multi-Timeframe Analysis

    Features:
    - Higher timeframe (HTF) for overall trend direction
    - Medium timeframe (MTF) for momentum confirmation
    - Lower timeframe (LTF) for precise entries
    - Alignment scoring system for trade quality
    - Divergence detection across timeframes
    """

    # Timeframe parameters
    htf_multiplier = HTF_MULTIPLIER
    mtf_multiplier = MTF_MULTIPLIER

    # ATR periods for each timeframe
    atr_period_htf = ATR_PERIOD_HTF
    atr_period_mtf = ATR_PERIOD_MTF
    atr_period_ltf = ATR_PERIOD_LTF

    # Core parameters (same for all timeframes)
    trigger_threshold = TRIGGER_THRESHOLD
    max_step_size = MAX_STEP_SIZE
    band_multiplier = BAND_MULTIPLIER

    # Risk management
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100

    # Multi-timeframe parameters
    alignment_threshold = 2  # Minimum TFs aligned for trade
    divergence_penalty = 0.5  # Reduce signal strength on divergence

    def resample_data(self, close, high, low, multiplier):
        """Resample data to higher timeframe"""
        n = len(close)
        resampled_close = np.full(n, np.nan)
        resampled_high = np.full(n, np.nan)
        resampled_low = np.full(n, np.nan)

        for i in range(multiplier - 1, n, multiplier):
            # Get the window
            window_close = close[i-multiplier+1:i+1]
            window_high = high[i-multiplier+1:i+1]
            window_low = low[i-multiplier+1:i+1]

            # Calculate OHLC for the period
            period_close = window_close[-1]
            period_high = np.max(window_high)
            period_low = np.min(window_low)

            # Fill the values for this period
            for j in range(i-multiplier+1, i+1):
                if j >= 0 and j < n:
                    resampled_close[j] = period_close
                    resampled_high[j] = period_high
                    resampled_low[j] = period_low

        return resampled_close, resampled_high, resampled_low

    def calculate_trend_impulse_tf(self, close, high, low, atr_period):
        """Calculate trend impulse for a specific timeframe"""
        n = len(close)

        # Calculate ATR for this timeframe
        atr = np.full(n, np.nan)
        for i in range(atr_period, n):
            if not np.isnan(high[i]) and not np.isnan(low[i]):
                # Simple ATR calculation
                tr_values = []
                for j in range(i-atr_period+1, i+1):
                    if j > 0:
                        tr = max(high[j] - low[j],
                               abs(high[j] - close[j-1]),
                               abs(low[j] - close[j-1]))
                        tr_values.append(tr)
                if tr_values:
                    atr[i] = np.mean(tr_values)

        # Calculate trend impulse
        trend = np.full(n, np.nan)
        direction = np.zeros(n)

        # Find first valid index
        first_valid = 0
        for i in range(n):
            if not np.isnan(close[i]):
                trend[i] = close[i]
                direction[i] = 1
                first_valid = i
                break

        for i in range(first_valid + 1, n):
            if np.isnan(atr[i]) or np.isnan(close[i]):
                trend[i] = trend[i-1] if i > 0 else close[i]
                direction[i] = direction[i-1] if i > 0 else 1
                continue

            trigger = atr[i] * self.trigger_threshold
            step_size = min(atr[i] * self.max_step_size, abs(close[i] - trend[i-1]) * 0.1)

            flip_up = close[i] > trend[i-1] + trigger and direction[i-1] <= 0
            flip_down = close[i] < trend[i-1] - trigger and direction[i-1] >= 0

            if flip_up:
                direction[i] = 1
                trend[i] = close[i] - atr[i] * 0.5
            elif flip_down:
                direction[i] = -1
                trend[i] = close[i] + atr[i] * 0.5
            else:
                direction[i] = direction[i-1]
                if direction[i] > 0:
                    if close[i] > trend[i-1]:
                        trend[i] = trend[i-1] + step_size
                    else:
                        trend[i] = trend[i-1]
                else:
                    if close[i] < trend[i-1]:
                        trend[i] = trend[i-1] - step_size
                    else:
                        trend[i] = trend[i-1]

        # Calculate bands
        upper_band = trend + atr * self.band_multiplier
        lower_band = trend - atr * self.band_multiplier

        return trend, upper_band, lower_band, direction, atr

    def calculate_alignment_score(self, htf_dir, mtf_dir, ltf_dir, htf_trend, mtf_trend, ltf_trend, close):
        """Calculate alignment score across timeframes"""
        n = len(close)
        alignment_score = np.zeros(n)
        trend_agreement = np.zeros(n)

        for i in range(n):
            if np.isnan(htf_dir[i]) or np.isnan(mtf_dir[i]) or np.isnan(ltf_dir[i]):
                continue

            # Count aligned timeframes
            aligned_count = 0
            if htf_dir[i] > 0:
                aligned_count += 1
            if mtf_dir[i] > 0:
                aligned_count += 1
            if ltf_dir[i] > 0:
                aligned_count += 1

            # All bullish or all bearish
            if aligned_count == 3 or aligned_count == 0:
                alignment_score[i] = 3
                trend_agreement[i] = 1
            # Two aligned
            elif aligned_count == 2 or aligned_count == 1:
                alignment_score[i] = 2
                trend_agreement[i] = 0.5
            # Mixed (divergence)
            else:
                alignment_score[i] = 1
                trend_agreement[i] = -1

            # Bonus for price position relative to trends
            if not np.isnan(htf_trend[i]) and not np.isnan(close[i]):
                if htf_dir[i] > 0 and close[i] > htf_trend[i]:
                    alignment_score[i] += 0.5
                elif htf_dir[i] < 0 and close[i] < htf_trend[i]:
                    alignment_score[i] += 0.5

        return alignment_score, trend_agreement

    def generate_mtf_signals(self, close, high, low, htf_dir, mtf_dir, ltf_dir,
                            htf_upper, htf_lower, mtf_upper, mtf_lower,
                            ltf_upper, ltf_lower, alignment_score):
        """Generate signals based on multi-timeframe analysis"""
        n = len(close)
        long_signals = np.zeros(n)
        short_signals = np.zeros(n)

        for i in range(3, n):
            if np.isnan(htf_dir[i]) or np.isnan(alignment_score[i]):
                continue

            # Skip if alignment is poor
            if alignment_score[i] < self.alignment_threshold:
                continue

            # LONG SIGNALS
            # Perfect alignment - all TFs bullish
            if htf_dir[i] > 0 and mtf_dir[i] > 0 and ltf_dir[i] > 0:
                # LTF trend flip with HTF support
                if ltf_dir[i] != ltf_dir[i-1] and ltf_dir[i] > 0:
                    long_signals[i] = 3 * (alignment_score[i] / 3)

                # Bounce from MTF lower band with HTF uptrend
                elif low[i] <= mtf_lower[i] and close[i] > mtf_lower[i]:
                    long_signals[i] = max(long_signals[i], 2.5)

                # LTF lower band bounce with alignment
                elif low[i] <= ltf_lower[i] and close[i] > ltf_lower[i]:
                    long_signals[i] = max(long_signals[i], 2)

            # Partial alignment - HTF up, waiting for LTF confirmation
            elif htf_dir[i] > 0 and mtf_dir[i] > 0:
                # Early entry on LTF turn
                if ltf_dir[i] > ltf_dir[i-1] and close[i] > ltf_lower[i]:
                    long_signals[i] = max(long_signals[i], 1.5)

            # HTF support only
            elif htf_dir[i] > 0:
                # Conservative entry at HTF lower band
                if low[i] <= htf_lower[i] and close[i] > htf_lower[i]:
                    long_signals[i] = max(long_signals[i], 1)

            # SHORT SIGNALS
            # Perfect alignment - all TFs bearish
            if htf_dir[i] < 0 and mtf_dir[i] < 0 and ltf_dir[i] < 0:
                # LTF trend flip with HTF resistance
                if ltf_dir[i] != ltf_dir[i-1] and ltf_dir[i] < 0:
                    short_signals[i] = 3 * (alignment_score[i] / 3)

                # Rejection from MTF upper band with HTF downtrend
                elif high[i] >= mtf_upper[i] and close[i] < mtf_upper[i]:
                    short_signals[i] = max(short_signals[i], 2.5)

                # LTF upper band rejection with alignment
                elif high[i] >= ltf_upper[i] and close[i] < ltf_upper[i]:
                    short_signals[i] = max(short_signals[i], 2)

            # Partial alignment - HTF down, waiting for LTF confirmation
            elif htf_dir[i] < 0 and mtf_dir[i] < 0:
                # Early entry on LTF turn
                if ltf_dir[i] < ltf_dir[i-1] and close[i] < ltf_upper[i]:
                    short_signals[i] = max(short_signals[i], 1.5)

            # HTF resistance only
            elif htf_dir[i] < 0:
                # Conservative entry at HTF upper band
                if high[i] >= htf_upper[i] and close[i] < htf_upper[i]:
                    short_signals[i] = max(short_signals[i], 1)

            # Apply divergence penalty
            if alignment_score[i] < 3:
                long_signals[i] *= (1 - self.divergence_penalty * (3 - alignment_score[i]) / 3)
                short_signals[i] *= (1 - self.divergence_penalty * (3 - alignment_score[i]) / 3)

        return long_signals, short_signals

    def init(self):
        """Initialize multi-timeframe indicators"""
        close = pd.Series(self.data.Close).values
        high = pd.Series(self.data.High).values
        low = pd.Series(self.data.Low).values

        # Resample to higher timeframes
        htf_close, htf_high, htf_low = self.resample_data(close, high, low, self.htf_multiplier)
        mtf_close, mtf_high, mtf_low = self.resample_data(close, high, low, self.mtf_multiplier)

        # Calculate trend impulse for each timeframe
        htf_trend, htf_upper, htf_lower, htf_dir, htf_atr = self.calculate_trend_impulse_tf(
            htf_close, htf_high, htf_low, self.atr_period_htf
        )

        mtf_trend, mtf_upper, mtf_lower, mtf_dir, mtf_atr = self.calculate_trend_impulse_tf(
            mtf_close, mtf_high, mtf_low, self.atr_period_mtf
        )

        ltf_trend, ltf_upper, ltf_lower, ltf_dir, ltf_atr = self.calculate_trend_impulse_tf(
            close, high, low, self.atr_period_ltf
        )

        # Calculate alignment score
        alignment_score, trend_agreement = self.calculate_alignment_score(
            htf_dir, mtf_dir, ltf_dir,
            htf_trend, mtf_trend, ltf_trend,
            close
        )

        # Generate multi-timeframe signals
        long_signals, short_signals = self.generate_mtf_signals(
            close, high, low,
            htf_dir, mtf_dir, ltf_dir,
            htf_upper, htf_lower,
            mtf_upper, mtf_lower,
            ltf_upper, ltf_lower,
            alignment_score
        )

        # Store as indicators
        self.htf_trend = self.I(lambda: htf_trend)
        self.htf_upper = self.I(lambda: htf_upper)
        self.htf_lower = self.I(lambda: htf_lower)
        self.htf_dir = self.I(lambda: htf_dir)

        self.mtf_trend = self.I(lambda: mtf_trend)
        self.mtf_upper = self.I(lambda: mtf_upper)
        self.mtf_lower = self.I(lambda: mtf_lower)
        self.mtf_dir = self.I(lambda: mtf_dir)

        self.ltf_trend = self.I(lambda: ltf_trend)
        self.ltf_upper = self.I(lambda: ltf_upper)
        self.ltf_lower = self.I(lambda: ltf_lower)
        self.ltf_dir = self.I(lambda: ltf_dir)

        self.alignment_score = self.I(lambda: alignment_score)
        self.trend_agreement = self.I(lambda: trend_agreement)
        self.long_signals = self.I(lambda: long_signals)
        self.short_signals = self.I(lambda: short_signals)

    def next(self):
        """Execute multi-timeframe trading logic"""
        # Skip if indicators not ready
        if np.isnan(self.htf_trend[-1]) or np.isnan(self.ltf_trend[-1]):
            return

        current_price = self.data.Close[-1]

        # Position management
        if self.position:
            # Exit on HTF trend reversal (strongest signal)
            if self.position.is_long and self.htf_dir[-1] < 0:
                self.position.close()
            elif self.position.is_short and self.htf_dir[-1] > 0:
                self.position.close()

            # Exit on alignment breakdown
            if self.alignment_score[-1] < 2:
                if self.position.is_long and self.ltf_dir[-1] < 0:
                    self.position.close()
                elif self.position.is_short and self.ltf_dir[-1] > 0:
                    self.position.close()

            # Multi-timeframe trailing stops
            if self.position.is_long:
                # Use MTF lower band as primary stop
                if current_price < self.mtf_lower[-1]:
                    self.position.close()
                # Use LTF lower band as tight stop if in profit
                elif self.position.pl_pct > 0.01 and current_price < self.ltf_lower[-1]:
                    self.position.close()

            elif self.position.is_short:
                # Use MTF upper band as primary stop
                if current_price > self.mtf_upper[-1]:
                    self.position.close()
                # Use LTF upper band as tight stop if in profit
                elif self.position.pl_pct > 0.01 and current_price > self.ltf_upper[-1]:
                    self.position.close()

        else:
            # Entry signals with multi-timeframe confirmation
            if self.long_signals[-1] > 0 and self.alignment_score[-1] >= self.alignment_threshold:
                signal_strength = self.long_signals[-1]
                alignment_bonus = self.alignment_score[-1] / 3

                # Dynamic stops based on timeframe alignment
                if self.alignment_score[-1] == 3:  # Perfect alignment
                    # Use LTF lower band for tight stop
                    sl_price = self.ltf_lower[-1]
                else:
                    # Use wider stop with partial alignment
                    sl_price = current_price * (1 - self.stop_loss * (2 - alignment_bonus))

                # Ensure stop is below MTF lower band
                sl_price = min(sl_price, self.mtf_lower[-1] * 0.99)

                # Scale targets based on alignment and signal strength
                tp_multiplier = self.take_profit * signal_strength * alignment_bonus
                tp_price = current_price * (1 + tp_multiplier)

                self.buy(sl=sl_price, tp=tp_price, size=1000000)

            elif self.short_signals[-1] > 0 and self.alignment_score[-1] >= self.alignment_threshold:
                signal_strength = self.short_signals[-1]
                alignment_bonus = self.alignment_score[-1] / 3

                # Dynamic stops based on timeframe alignment
                if self.alignment_score[-1] == 3:  # Perfect alignment
                    # Use LTF upper band for tight stop
                    sl_price = self.ltf_upper[-1]
                else:
                    # Use wider stop with partial alignment
                    sl_price = current_price * (1 + self.stop_loss * (2 - alignment_bonus))

                # Ensure stop is above MTF upper band
                sl_price = max(sl_price, self.mtf_upper[-1] * 1.01)

                # Scale targets based on alignment and signal strength
                tp_multiplier = self.take_profit * signal_strength * alignment_bonus
                tp_price = current_price * (1 - tp_multiplier)

                self.sell(sl=sl_price, tp=tp_price, size=1000000)

# Run single backtest
bt = Backtest(data, TrendImpulseMultiTF, cash=10000000, commission=0.00045)

print("\n🌙 ===== TREND IMPULSE MULTI-TIMEFRAME ===== 🌙")
print(f"Timeframes: HTF={HTF_MULTIPLIER}x, MTF={MTF_MULTIPLIER}x, LTF=1x")
print(f"ATR Periods: HTF={ATR_PERIOD_HTF}, MTF={ATR_PERIOD_MTF}, LTF={ATR_PERIOD_LTF}")
print(f"Trigger Threshold: {TRIGGER_THRESHOLD}")
print(f"Band Multiplier: {BAND_MULTIPLIER}")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")

stats_default = bt.run()
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING TREND IMPULSE MULTI-TF ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(TrendImpulseMultiTF, 'TrendImpulseMultiTF')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/TrendImpulseMultiTF.csv")