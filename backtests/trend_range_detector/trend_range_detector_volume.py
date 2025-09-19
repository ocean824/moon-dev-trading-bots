"""
Moon Dev's Trend Range Detector with Volume Confirmation Strategy
==================================================================
Enhanced version that requires volume confirmation for breakouts.
Uses volume surge detection to filter false breakouts and improve win rate.
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Trend Range Detector with Volume Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
WMA_PERIOD = 20
ATR_PERIOD = 14
ATR_MULTIPLIER = 1.5  # Reduced for more ranges
MIN_RANGE_LENGTH = 30  # Reduced for more signals
BREAKOUT_CONFIRM_BARS = 2
VOLUME_PERIOD = 20  # Period for volume moving average
VOLUME_MULTIPLIER = 1.5  # Volume must be 1.5x average for confirmation
VOLUME_LOOKBACK = 5  # Bars to check for volume surge
STOP_LOSS_PERCENT = 2.0
TAKE_PROFIT_PERCENT = 4.0

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class TrendRangeDetectorVolume(Strategy):
    """
    Trend Range Detector with Volume Confirmation
    - Identifies consolidation ranges using ATR boundaries
    - Requires volume surge for breakout confirmation
    - Uses relative volume to filter false signals
    - Tracks volume profile within ranges
    - Dynamic position sizing based on volume strength
    """

    # Core parameters
    wma_period = WMA_PERIOD
    atr_period = ATR_PERIOD
    atr_multiplier = ATR_MULTIPLIER
    min_range_length = MIN_RANGE_LENGTH
    breakout_confirm = BREAKOUT_CONFIRM_BARS

    # Volume parameters
    volume_period = VOLUME_PERIOD
    volume_multiplier = VOLUME_MULTIPLIER
    volume_lookback = VOLUME_LOOKBACK

    # Risk management
    stop_loss_pct = STOP_LOSS_PERCENT / 100
    take_profit_pct = TAKE_PROFIT_PERCENT / 100

    def calculate_weighted_ma(self, prices):
        """Calculate custom weighted moving average based on price deltas"""
        wma = np.zeros(len(prices))

        for i in range(self.wma_period, len(prices)):
            weights = np.arange(1, self.wma_period + 1)
            window = prices[i - self.wma_period + 1:i + 1]
            wma[i] = np.sum(window * weights) / np.sum(weights)

        return wma

    def calculate_volume_profile(self, volumes, start_idx, end_idx):
        """Calculate volume profile metrics for a range"""
        if end_idx <= start_idx:
            return 0, 0, 0

        range_volumes = volumes[start_idx:end_idx + 1]
        if len(range_volumes) == 0:
            return 0, 0, 0

        avg_volume = np.mean(range_volumes)
        max_volume = np.max(range_volumes)
        volume_concentration = max_volume / avg_volume if avg_volume > 0 else 0

        return avg_volume, max_volume, volume_concentration

    def detect_ranges_with_volume(self, prices, highs, lows, volumes, atr, vol_ma):
        """Detect ranges and track volume characteristics"""
        ranges = []
        in_range = False
        range_start = 0
        range_center = 0
        range_top = 0
        range_bottom = 0
        range_volume_sum = 0
        range_bar_count = 0

        wma = self.calculate_weighted_ma(prices)

        for i in range(max(self.atr_period + self.wma_period, self.volume_period), len(prices)):
            if atr[i] == 0 or np.isnan(atr[i]):
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
                range_volume_sum = volumes[i]
                range_bar_count = 1

            elif in_range:
                if price_in_range:
                    range_volume_sum += volumes[i]
                    range_bar_count += 1
                    # Smooth adjustment of range boundaries
                    range_center = (range_center * 0.9 + current_center * 0.1)
                    range_top = range_top * 0.98 + current_top * 0.02
                    range_bottom = range_bottom * 0.98 + current_bottom * 0.02

                    # Check if we have enough bars and potential breakout
                    if range_bar_count >= self.min_range_length:
                        if prices[i] > range_top * 0.98 or prices[i] < range_bottom * 1.02:
                            avg_range_volume = range_volume_sum / range_bar_count if range_bar_count > 0 else 0
                            ranges.append({
                                'start': range_start,
                                'end': i,
                                'center': range_center,
                                'top': range_top,
                                'bottom': range_bottom,
                                'length': range_bar_count,
                                'avg_volume': avg_range_volume
                            })
                            in_range = False
                else:
                    # Price broke out of range
                    if range_bar_count >= self.min_range_length:
                        avg_range_volume = range_volume_sum / range_bar_count if range_bar_count > 0 else 0
                        ranges.append({
                            'start': range_start,
                            'end': i,
                            'center': range_center,
                            'top': range_top,
                            'bottom': range_bottom,
                            'length': range_length,
                            'avg_volume': avg_range_volume
                        })
                    in_range = False

        return ranges

    def check_volume_confirmation(self, volumes, vol_ma, idx):
        """Check if volume confirms the breakout"""
        if idx < self.volume_lookback or idx >= len(volumes):
            return False

        # Check recent volume bars for surge
        recent_volumes = volumes[idx - self.volume_lookback:idx + 1]
        recent_vol_ma = vol_ma[idx - self.volume_lookback:idx + 1]

        # Count how many bars have elevated volume
        elevated_count = 0
        for j in range(len(recent_volumes)):
            if recent_vol_ma[j] > 0 and recent_volumes[j] > recent_vol_ma[j] * self.volume_multiplier:
                elevated_count += 1

        # Require at least 2 bars with elevated volume
        return elevated_count >= 2

    def init(self):
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        volume = pd.Series(self.data.Volume)

        # Calculate indicators
        atr = ta.atr(high, low, close, length=self.atr_period)
        vol_ma = ta.sma(volume, length=self.volume_period)

        # Convert to full arrays
        atr_full = np.full(len(close), np.nan)
        atr_full[-len(atr):] = atr.values

        vol_ma_full = np.full(len(close), np.nan)
        vol_ma_full[-len(vol_ma):] = vol_ma.values

        # Detect ranges with volume analysis
        ranges = self.detect_ranges_with_volume(
            close.values, high.values, low.values,
            volume.values, atr_full, vol_ma_full
        )

        # Create signals
        self.signal = np.zeros(len(close))
        self.volume_confirmed = np.zeros(len(close))
        self.range_top = np.full(len(close), np.nan)
        self.range_bottom = np.full(len(close), np.nan)
        self.range_center = np.full(len(close), np.nan)

        # Mark range boundaries and volume-confirmed breakouts
        for r in ranges:
            for j in range(r['start'], min(r['end'] + 1, len(close))):
                self.range_top[j] = r['top']
                self.range_bottom[j] = r['bottom']
                self.range_center[j] = r['center']

            if r['end'] < len(close):
                end_price = close.iloc[r['end']]

                # Simplified breakout detection with volume
                if end_price > r['top']:
                    # Confirm breakout
                    confirmed = True
                    for k in range(1, min(self.breakout_confirm, len(close) - r['end'])):
                        if close.iloc[r['end'] + k] < r['top'] * 0.995:
                            confirmed = False
                            break

                    if confirmed:
                        # Check volume confirmation
                        volume_ok = self.check_volume_confirmation(
                            volume.values, vol_ma_full, r['end']
                        )
                        if volume_ok:
                            self.signal[r['end']] = 1
                            self.volume_confirmed[r['end']] = 1

                elif end_price < r['bottom']:
                    # Confirm breakdown
                    confirmed = True
                    for k in range(1, min(self.breakout_confirm, len(close) - r['end'])):
                        if close.iloc[r['end'] + k] > r['bottom'] * 1.005:
                            confirmed = False
                            break

                    if confirmed:
                        volume_ok = self.check_volume_confirmation(
                            volume.values, vol_ma_full, r['end']
                        )
                        if volume_ok:
                            self.signal[r['end']] = -1
                            self.volume_confirmed[r['end']] = 1

        # Store indicators
        self.I(lambda: self.signal, name='Signal')
        self.I(lambda: self.volume_confirmed, name='VolumeConfirmed')
        self.I(lambda: self.range_top, name='RangeTop')
        self.I(lambda: self.range_bottom, name='RangeBottom')
        self.I(lambda: vol_ma_full, name='VolumeMA')

    def next(self):
        current_signal = self.signal[-1] if len(self.signal) > 0 else 0
        current_price = self.data.Close[-1]
        current_volume = self.data.Volume[-1]

        # Dynamic position sizing based on volume strength
        position_size = 1000000
        if self.volume_confirmed[-1] == 1 and len(self.data.Volume) > self.volume_period:
            # Get recent average volume
            recent_vol_avg = np.mean(list(self.data.Volume)[-self.volume_period:])
            if recent_vol_avg > 0:
                volume_ratio = current_volume / recent_vol_avg
                # Higher volume = larger position
                position_size = 1000000 * min(2.0, max(0.5, volume_ratio / self.volume_multiplier))

        if not np.isnan(self.range_top[-1]) and not np.isnan(self.range_bottom[-1]):
            range_width = (self.range_top[-1] - self.range_bottom[-1]) / self.range_bottom[-1]
            position_size *= max(0.5, min(2.0, 1.0 / (1 + range_width * 10)))

        # Entry logic with volume confirmation
        if not self.position:
            if current_signal == 1 and self.volume_confirmed[-1] == 1:
                # Long entry
                if not np.isnan(self.range_center[-1]):
                    sl_price = self.range_center[-1]
                    tp_price = current_price + (current_price - self.range_bottom[-1]) * 1.5
                else:
                    sl_price = current_price * (1 - self.stop_loss_pct)
                    tp_price = current_price * (1 + self.take_profit_pct)

                self.buy(size=position_size, sl=sl_price, tp=tp_price)

            elif current_signal == -1 and self.volume_confirmed[-1] == 1:
                # Short entry
                if not np.isnan(self.range_center[-1]):
                    sl_price = self.range_center[-1]
                    tp_price = current_price - (self.range_top[-1] - current_price) * 1.5
                else:
                    sl_price = current_price * (1 + self.stop_loss_pct)
                    tp_price = current_price * (1 - self.take_profit_pct)

                self.sell(size=position_size, sl=sl_price, tp=tp_price)

        # Exit on range re-entry or volume exhaustion
        elif self.position:
            # Check for volume exhaustion (volume dropping below average)
            volume_exhausted = False
            if len(list(self.data.Volume)) > self.volume_period:
                recent_vol_avg = np.mean(list(self.data.Volume)[-self.volume_period:])
                if current_volume < recent_vol_avg * 0.5:
                    volume_exhausted = True

            if self.position.is_long:
                if not np.isnan(self.range_top[-1]) and current_price < self.range_top[-1]:
                    self.position.close()
                elif volume_exhausted:
                    self.position.close()

            elif self.position.is_short:
                if not np.isnan(self.range_bottom[-1]) and current_price > self.range_bottom[-1]:
                    self.position.close()
                elif volume_exhausted:
                    self.position.close()

# Run single backtest
bt = Backtest(data, TrendRangeDetectorVolume, cash=10000000, commission=0.00045)

print("\n🌙 ===== TREND RANGE DETECTOR VOLUME - DEFAULT PARAMETERS ===== 🌙")
print(f"WMA Period: {WMA_PERIOD}")
print(f"ATR Multiplier: {ATR_MULTIPLIER}")
print(f"Volume Period: {VOLUME_PERIOD}")
print(f"Volume Multiplier: {VOLUME_MULTIPLIER}x")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")

stats_default = bt.run()
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING TREND RANGE DETECTOR VOLUME ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(TrendRangeDetectorVolume, 'TrendRangeDetectorVolume')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/TrendRangeDetectorVolume.csv")