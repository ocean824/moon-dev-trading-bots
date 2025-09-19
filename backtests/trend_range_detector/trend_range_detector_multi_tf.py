"""
Moon Dev's Trend Range Detector Multi-Timeframe Strategy
=========================================================
Uses multiple timeframe analysis to confirm ranges and breakouts.
Higher timeframe ranges provide stronger support/resistance levels.
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Trend Range Detector Multi-TF Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
WMA_PERIOD = 20
ATR_PERIOD = 14
ATR_MULTIPLIER = 1.5  # Reduced for more ranges
MIN_RANGE_LENGTH = 30  # Reduced for more signals
BREAKOUT_CONFIRM_BARS = 2
HTF_MULTIPLIER = 4  # Higher timeframe multiplier (4h if base is 1h)
MTF_WEIGHT = 1.5  # Weight for multi-timeframe confirmation
ALIGNMENT_THRESHOLD = 0.8  # How aligned timeframes need to be
STOP_LOSS_PERCENT = 2.0
TAKE_PROFIT_PERCENT = 4.0

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class TrendRangeDetectorMultiTF(Strategy):
    """
    Trend Range Detector with Multi-Timeframe Analysis
    - Analyzes ranges on multiple timeframes simultaneously
    - Higher timeframe ranges act as major support/resistance
    - Requires alignment between timeframes for entries
    - Stronger signals when multiple timeframes agree
    - Dynamic sizing based on timeframe confluence
    """

    # Core parameters
    wma_period = WMA_PERIOD
    atr_period = ATR_PERIOD
    atr_multiplier = ATR_MULTIPLIER
    min_range_length = MIN_RANGE_LENGTH
    breakout_confirm = BREAKOUT_CONFIRM_BARS

    # Multi-timeframe parameters
    htf_multiplier = HTF_MULTIPLIER
    mtf_weight = MTF_WEIGHT
    alignment_threshold = ALIGNMENT_THRESHOLD

    # Risk management
    stop_loss_pct = STOP_LOSS_PERCENT / 100
    take_profit_pct = TAKE_PROFIT_PERCENT / 100

    def calculate_weighted_ma(self, prices):
        """Calculate custom weighted moving average"""
        wma = np.zeros(len(prices))

        for i in range(self.wma_period, len(prices)):
            weights = np.arange(1, self.wma_period + 1)
            window = prices[i - self.wma_period + 1:i + 1]
            wma[i] = np.sum(window * weights) / np.sum(weights)

        return wma

    def resample_to_higher_tf(self, prices, highs, lows, multiplier):
        """Resample data to higher timeframe"""
        if multiplier <= 1:
            return prices, highs, lows

        # Calculate new length
        new_length = len(prices) // multiplier

        htf_prices = np.zeros(new_length)
        htf_highs = np.zeros(new_length)
        htf_lows = np.zeros(new_length)

        for i in range(new_length):
            start_idx = i * multiplier
            end_idx = min(start_idx + multiplier, len(prices))

            # Get OHLC for the period
            period_prices = prices[start_idx:end_idx]
            period_highs = highs[start_idx:end_idx]
            period_lows = lows[start_idx:end_idx]

            if len(period_prices) > 0:
                htf_prices[i] = period_prices[-1]  # Close price
                htf_highs[i] = np.max(period_highs)
                htf_lows[i] = np.min(period_lows)

        return htf_prices, htf_highs, htf_lows

    def detect_ranges_multi_tf(self, prices, highs, lows, atr):
        """Detect ranges on multiple timeframes"""
        # Base timeframe ranges
        base_ranges = self.detect_single_tf_ranges(prices, highs, lows, atr)

        # Higher timeframe data
        htf_prices, htf_highs, htf_lows = self.resample_to_higher_tf(
            prices, highs, lows, self.htf_multiplier
        )

        # Calculate HTF ATR
        htf_atr = np.zeros(len(htf_prices))
        for i in range(self.atr_period, len(htf_prices)):
            htf_atr[i] = np.mean([
                htf_highs[j] - htf_lows[j]
                for j in range(i - self.atr_period, i)
            ])

        # HTF ranges
        htf_ranges = self.detect_single_tf_ranges(
            htf_prices, htf_highs, htf_lows, htf_atr
        )

        # Scale HTF ranges back to base timeframe indices
        scaled_htf_ranges = []
        for r in htf_ranges:
            scaled_htf_ranges.append({
                'start': r['start'] * self.htf_multiplier,
                'end': min(r['end'] * self.htf_multiplier, len(prices) - 1),
                'center': r['center'],
                'top': r['top'],
                'bottom': r['bottom'],
                'length': r['length'] * self.htf_multiplier,
                'timeframe': 'HTF'
            })

        return base_ranges, scaled_htf_ranges

    def detect_single_tf_ranges(self, prices, highs, lows, atr):
        """Detect ranges on a single timeframe"""
        ranges = []
        in_range = False
        range_start = 0
        range_center = 0
        range_top = 0
        range_bottom = 0

        wma = self.calculate_weighted_ma(prices)

        for i in range(max(self.atr_period + self.wma_period, len(wma) // 2), len(prices)):
            if i >= len(atr) or atr[i] == 0 or np.isnan(atr[i]):
                continue

            current_center = wma[i]
            current_range = atr[i] * self.atr_multiplier
            current_top = current_center + current_range / 2
            current_bottom = current_center - current_range / 2

            # More lenient range detection using close price
            price_in_range = current_bottom <= prices[i] <= current_top

            if not in_range and price_in_range:
                in_range = True
                range_start = i
                range_center = current_center
                range_top = current_top
                range_bottom = current_bottom
                range_count = 1

            elif in_range:
                if price_in_range:
                    range_count += 1
                    range_center = (range_center * 0.9 + current_center * 0.1)
                    range_top = range_top * 0.98 + current_top * 0.02
                    range_bottom = range_bottom * 0.98 + current_bottom * 0.02

                    # Check if we have enough bars and potential breakout
                    min_length = self.min_range_length // (self.htf_multiplier if len(prices) < 1000 else 1)
                    if range_count >= min_length:
                        if prices[i] > range_top * 0.98 or prices[i] < range_bottom * 1.02:
                            ranges.append({
                                'start': range_start,
                                'end': i,
                                'center': range_center,
                                'top': range_top,
                                'bottom': range_bottom,
                                'length': range_count
                            })
                            in_range = False
                else:
                    # Price broke out of range
                    min_length = self.min_range_length // (self.htf_multiplier if len(prices) < 1000 else 1)
                    if range_count >= min_length:
                        ranges.append({
                            'start': range_start,
                            'end': i,
                            'center': range_center,
                            'top': range_top,
                            'bottom': range_bottom,
                            'length': range_length,
                            'timeframe': 'Base'
                        })
                    in_range = False

        return ranges

    def check_timeframe_alignment(self, base_ranges, htf_ranges, idx):
        """Check if timeframes are aligned at given index"""
        base_in_range = False
        htf_in_range = False
        alignment_score = 0

        # Check if index is within any base range
        for r in base_ranges:
            if r['start'] <= idx <= r['end']:
                base_in_range = True
                base_range = r
                break

        # Check if index is within any HTF range
        for r in htf_ranges:
            if r['start'] <= idx <= r['end']:
                htf_in_range = True
                htf_range = r
                break

        # Calculate alignment score
        if base_in_range and htf_in_range:
            # Check if ranges overlap significantly
            price_at_idx = self.data.Close[idx] if idx < len(self.data.Close) else 0

            # Both ranges contain the current price
            if (base_range['bottom'] <= price_at_idx <= base_range['top'] and
                htf_range['bottom'] <= price_at_idx <= htf_range['top']):
                alignment_score = 1.0

                # Extra score if centers are close
                center_diff = abs(base_range['center'] - htf_range['center']) / base_range['center']
                if center_diff < 0.05:  # Within 5%
                    alignment_score *= 1.2

        elif base_in_range or htf_in_range:
            alignment_score = 0.5  # Partial alignment

        return alignment_score

    def init(self):
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)

        # Calculate ATR
        atr = ta.atr(high, low, close, length=self.atr_period)
        atr_full = np.full(len(close), np.nan)
        atr_full[-len(atr):] = atr.values

        # Detect ranges on multiple timeframes
        base_ranges, htf_ranges = self.detect_ranges_multi_tf(
            close.values, high.values, low.values, atr_full
        )

        # Create signals
        self.signal = np.zeros(len(close))
        self.alignment_score = np.zeros(len(close))
        self.range_top = np.full(len(close), np.nan)
        self.range_bottom = np.full(len(close), np.nan)
        self.htf_range_top = np.full(len(close), np.nan)
        self.htf_range_bottom = np.full(len(close), np.nan)

        # Mark base timeframe ranges
        for r in base_ranges:
            for j in range(r['start'], min(r['end'], len(close))):
                self.range_top[j] = r['top']
                self.range_bottom[j] = r['bottom']

        # Mark HTF ranges
        for r in htf_ranges:
            for j in range(r['start'], min(r['end'], len(close))):
                self.htf_range_top[j] = r['top']
                self.htf_range_bottom[j] = r['bottom']

        # Check for breakouts with multi-timeframe confirmation
        for r in base_ranges:
            if r['end'] < len(close):
                end_price = close.iloc[r['end']]
                # Calculate alignment at breakout point
                alignment = self.check_timeframe_alignment(base_ranges, htf_ranges, r['end'])
                self.alignment_score[r['end']] = alignment

                # Simplified breakout detection
                if end_price > r['top']:
                    # Confirm breakout
                    confirmed = True
                    for k in range(1, min(self.breakout_confirm, len(close) - r['end'])):
                        if close.iloc[r['end'] + k] < r['top'] * 0.995:
                            confirmed = False
                            break
                    breakout = confirmed
                else:
                    breakout = False

                if breakout and alignment >= self.alignment_threshold:
                    # Check if HTF also shows bullish structure
                    htf_bullish = True
                    for htf_r in htf_ranges:
                        if htf_r['start'] <= r['end'] <= htf_r['end']:
                            # We're still in HTF range, wait for HTF breakout
                            if close.iloc[r['end']] < htf_r['top'] * 0.98:
                                htf_bullish = False
                            break

                    if htf_bullish:
                        self.signal[r['end']] = 1 * (1 + alignment * 0.5)

                # Simplified breakdown detection
                if end_price < r['bottom']:
                    # Confirm breakdown
                    confirmed = True
                    for k in range(1, min(self.breakout_confirm, len(close) - r['end'])):
                        if close.iloc[r['end'] + k] > r['bottom'] * 1.005:
                            confirmed = False
                            break
                    breakdown = confirmed
                else:
                    breakdown = False

                if breakdown and alignment >= self.alignment_threshold:
                    # Check if HTF also shows bearish structure
                    htf_bearish = True
                    for htf_r in htf_ranges:
                        if htf_r['start'] <= r['end'] <= htf_r['end']:
                            if close.iloc[r['end']] > htf_r['bottom'] * 1.02:
                                htf_bearish = False
                            break

                    if htf_bearish:
                        self.signal[r['end']] = -1 * (1 + alignment * 0.5)

        # Store indicators
        self.I(lambda: self.signal, name='Signal')
        self.I(lambda: self.alignment_score, name='AlignmentScore')
        self.I(lambda: self.range_top, name='RangeTop')
        self.I(lambda: self.range_bottom, name='RangeBottom')
        self.I(lambda: self.htf_range_top, name='HTFRangeTop')
        self.I(lambda: self.htf_range_bottom, name='HTFRangeBottom')

    def next(self):
        current_signal = self.signal[-1] if len(self.signal) > 0 else 0
        current_price = self.data.Close[-1]
        alignment = self.alignment_score[-1] if len(self.alignment_score) > 0 else 0

        # Dynamic position sizing based on timeframe alignment
        position_size = 1000000

        # Increase size with better alignment
        if alignment > self.alignment_threshold:
            position_size *= (1 + (alignment - self.alignment_threshold) * self.mtf_weight)

        # Adjust for range width
        if not np.isnan(self.range_top[-1]) and not np.isnan(self.range_bottom[-1]):
            range_width = (self.range_top[-1] - self.range_bottom[-1]) / self.range_bottom[-1]
            position_size *= max(0.5, min(2.0, 1.0 / (1 + range_width * 10)))

        # Entry logic with multi-timeframe confirmation
        if not self.position:
            if current_signal > 0:
                # Long entry with MTF confirmation
                # Use HTF range for stops if available
                if not np.isnan(self.htf_range_bottom[-1]):
                    sl_price = self.htf_range_bottom[-1]
                    tp_price = current_price + (current_price - self.htf_range_bottom[-1]) * 2.5
                elif not np.isnan(self.range_center[-1]):
                    sl_price = self.range_bottom[-1]
                    tp_price = current_price + (current_price - self.range_bottom[-1]) * 2.0
                else:
                    sl_price = current_price * (1 - self.stop_loss_pct)
                    tp_price = current_price * (1 + self.take_profit_pct)

                self.buy(size=position_size, sl=sl_price, tp=tp_price)

            elif current_signal < 0:
                # Short entry with MTF confirmation
                if not np.isnan(self.htf_range_top[-1]):
                    sl_price = self.htf_range_top[-1]
                    tp_price = current_price - (self.htf_range_top[-1] - current_price) * 2.5
                elif not np.isnan(self.range_top[-1]):
                    sl_price = self.range_top[-1]
                    tp_price = current_price - (self.range_top[-1] - current_price) * 2.0
                else:
                    sl_price = current_price * (1 + self.stop_loss_pct)
                    tp_price = current_price * (1 - self.take_profit_pct)

                self.sell(size=position_size, sl=sl_price, tp=tp_price)

        # Exit on range re-entry or timeframe divergence
        elif self.position:
            # Check if timeframes are diverging
            current_alignment = 0
            if not np.isnan(self.range_top[-1]) and not np.isnan(self.htf_range_top[-1]):
                # If base and HTF ranges are moving apart, consider exit
                range_divergence = abs(self.range_top[-1] - self.htf_range_top[-1]) / self.range_top[-1]
                if range_divergence > 0.1:  # 10% divergence
                    current_alignment = -1

            if self.position.is_long:
                # Exit if price falls back into base range or timeframes diverge
                if not np.isnan(self.range_top[-1]) and current_price < self.range_top[-1]:
                    self.position.close()
                elif current_alignment < 0:
                    self.position.close()

            elif self.position.is_short:
                # Exit if price rises back into base range or timeframes diverge
                if not np.isnan(self.range_bottom[-1]) and current_price > self.range_bottom[-1]:
                    self.position.close()
                elif current_alignment < 0:
                    self.position.close()

# Run single backtest
bt = Backtest(data, TrendRangeDetectorMultiTF, cash=10000000, commission=0.00045)

print("\n🌙 ===== TREND RANGE DETECTOR MULTI-TF - DEFAULT PARAMETERS ===== 🌙")
print(f"WMA Period: {WMA_PERIOD}")
print(f"ATR Multiplier: {ATR_MULTIPLIER}")
print(f"HTF Multiplier: {HTF_MULTIPLIER}x")
print(f"Alignment Threshold: {ALIGNMENT_THRESHOLD}")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")

stats_default = bt.run()
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING TREND RANGE DETECTOR MULTI-TF ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(TrendRangeDetectorMultiTF, 'TrendRangeDetectorMultiTF')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/TrendRangeDetectorMultiTF.csv")