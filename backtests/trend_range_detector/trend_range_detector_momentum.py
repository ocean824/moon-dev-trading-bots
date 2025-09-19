"""
Moon Dev's Trend Range Detector with Momentum Strategy
=======================================================
Enhanced version using RSI divergence confirmation for better timing.
Identifies momentum shifts at range boundaries for higher probability trades.
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Trend Range Detector with Momentum Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
WMA_PERIOD = 20
ATR_PERIOD = 14
ATR_MULTIPLIER = 1.5  # Reduced for more ranges
MIN_RANGE_LENGTH = 30  # Reduced for more signals
BREAKOUT_CONFIRM_BARS = 2
RSI_PERIOD = 14  # RSI period for momentum
RSI_OVERSOLD = 30  # Oversold level
RSI_OVERBOUGHT = 70  # Overbought level
DIVERGENCE_LOOKBACK = 20  # Bars to look for divergence
STOP_LOSS_PERCENT = 2.0
TAKE_PROFIT_PERCENT = 4.0

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class TrendRangeDetectorMomentum(Strategy):
    """
    Trend Range Detector with RSI Momentum & Divergence
    - Uses RSI to confirm momentum at range boundaries
    - Detects bullish/bearish divergences for better entries
    - Filters breakouts based on momentum strength
    - Tracks RSI behavior within ranges
    - Enhanced exit using momentum exhaustion
    """

    # Core parameters
    wma_period = WMA_PERIOD
    atr_period = ATR_PERIOD
    atr_multiplier = ATR_MULTIPLIER
    min_range_length = MIN_RANGE_LENGTH
    breakout_confirm = BREAKOUT_CONFIRM_BARS

    # RSI parameters
    rsi_period = RSI_PERIOD
    rsi_oversold = RSI_OVERSOLD
    rsi_overbought = RSI_OVERBOUGHT
    divergence_lookback = DIVERGENCE_LOOKBACK

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

    def detect_rsi_divergence(self, prices, rsi_values, start_idx, end_idx):
        """
        Detect RSI divergences within a range
        Returns: bullish_divergence, bearish_divergence, divergence_strength
        """
        if end_idx - start_idx < self.divergence_lookback:
            return False, False, 0

        # Get data for the range
        price_segment = prices[max(0, start_idx):end_idx]
        rsi_segment = rsi_values[max(0, start_idx):end_idx]

        if len(price_segment) < 10 or len(rsi_segment) < 10:
            return False, False, 0

        # Find price and RSI peaks and troughs
        price_peaks = []
        price_troughs = []
        rsi_peaks = []
        rsi_troughs = []

        for i in range(2, len(price_segment) - 2):
            # Price peaks
            if price_segment[i] > price_segment[i-1] and price_segment[i] > price_segment[i+1]:
                if price_segment[i] > price_segment[i-2] and price_segment[i] > price_segment[i+2]:
                    price_peaks.append((i, price_segment[i]))

            # Price troughs
            if price_segment[i] < price_segment[i-1] and price_segment[i] < price_segment[i+1]:
                if price_segment[i] < price_segment[i-2] and price_segment[i] < price_segment[i+2]:
                    price_troughs.append((i, price_segment[i]))

            # RSI peaks
            if not np.isnan(rsi_segment[i]):
                if rsi_segment[i] > rsi_segment[i-1] and rsi_segment[i] > rsi_segment[i+1]:
                    rsi_peaks.append((i, rsi_segment[i]))

                # RSI troughs
                if rsi_segment[i] < rsi_segment[i-1] and rsi_segment[i] < rsi_segment[i+1]:
                    rsi_troughs.append((i, rsi_segment[i]))

        bullish_div = False
        bearish_div = False
        div_strength = 0

        # Check for bullish divergence (price lower low, RSI higher low)
        if len(price_troughs) >= 2 and len(rsi_troughs) >= 2:
            last_price_trough = price_troughs[-1]
            prev_price_trough = price_troughs[-2]

            # Find corresponding RSI troughs
            last_rsi = None
            prev_rsi = None
            for idx, val in rsi_troughs:
                if abs(idx - last_price_trough[0]) < 3:
                    last_rsi = val
                if abs(idx - prev_price_trough[0]) < 3:
                    prev_rsi = val

            if last_rsi and prev_rsi:
                if last_price_trough[1] < prev_price_trough[1] and last_rsi > prev_rsi:
                    bullish_div = True
                    div_strength = abs(last_rsi - prev_rsi) / 100

        # Check for bearish divergence (price higher high, RSI lower high)
        if len(price_peaks) >= 2 and len(rsi_peaks) >= 2:
            last_price_peak = price_peaks[-1]
            prev_price_peak = price_peaks[-2]

            # Find corresponding RSI peaks
            last_rsi = None
            prev_rsi = None
            for idx, val in rsi_peaks:
                if abs(idx - last_price_peak[0]) < 3:
                    last_rsi = val
                if abs(idx - prev_price_peak[0]) < 3:
                    prev_rsi = val

            if last_rsi and prev_rsi:
                if last_price_peak[1] > prev_price_peak[1] and last_rsi < prev_rsi:
                    bearish_div = True
                    div_strength = abs(last_rsi - prev_rsi) / 100

        return bullish_div, bearish_div, div_strength

    def detect_ranges_with_momentum(self, prices, highs, lows, atr, rsi):
        """Detect ranges and analyze momentum characteristics"""
        ranges = []
        in_range = False
        range_start = 0
        range_center = 0
        range_top = 0
        range_bottom = 0

        wma = self.calculate_weighted_ma(prices)

        for i in range(max(self.atr_period + self.wma_period, self.rsi_period), len(prices)):
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
                range_count = 1

            elif in_range:
                if price_in_range:
                    range_count += 1
                    range_center = (range_center * 0.9 + current_center * 0.1)
                    range_top = range_top * 0.98 + current_top * 0.02
                    range_bottom = range_bottom * 0.98 + current_bottom * 0.02

                    # Check if we have enough bars and potential breakout
                    if range_count >= self.min_range_length:
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
                    if range_count >= self.min_range_length:
                        # Analyze momentum within range
                        bullish_div, bearish_div, div_strength = self.detect_rsi_divergence(
                            prices, rsi, range_start, i
                        )

                        # Get RSI at range end
                        end_rsi = rsi[i] if not np.isnan(rsi[i]) else 50

                        ranges.append({
                            'start': range_start,
                            'end': i,
                            'center': range_center,
                            'top': range_top,
                            'bottom': range_bottom,
                            'length': range_length,
                            'bullish_div': bullish_div,
                            'bearish_div': bearish_div,
                            'div_strength': div_strength,
                            'end_rsi': end_rsi
                        })
                    in_range = False

        return ranges

    def init(self):
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)

        # Calculate indicators
        atr = ta.atr(high, low, close, length=self.atr_period)
        rsi = ta.rsi(close, length=self.rsi_period)

        # Convert to full arrays
        atr_full = np.full(len(close), np.nan)
        atr_full[-len(atr):] = atr.values

        rsi_full = np.full(len(close), np.nan)
        rsi_full[-len(rsi):] = rsi.values

        # Detect ranges with momentum analysis
        ranges = self.detect_ranges_with_momentum(
            close.values, high.values, low.values, atr_full, rsi_full
        )

        # Create signals
        self.signal = np.zeros(len(close))
        self.momentum_confirmed = np.zeros(len(close))
        self.divergence = np.zeros(len(close))
        self.range_top = np.full(len(close), np.nan)
        self.range_bottom = np.full(len(close), np.nan)
        self.range_center = np.full(len(close), np.nan)

        # Mark range boundaries and momentum-confirmed breakouts
        for r in ranges:
            for j in range(r['start'], min(r['end'] + 1, len(close))):
                self.range_top[j] = r['top']
                self.range_bottom[j] = r['bottom']
                self.range_center[j] = r['center']

                # Mark divergences
                if r['bullish_div']:
                    self.divergence[j] = 1
                elif r['bearish_div']:
                    self.divergence[j] = -1

            if r['end'] < len(close):
                end_price = close.iloc[r['end']]

                # Simplified breakout detection
                if end_price > r['top']:
                    # Confirm breakout
                    confirmed = True
                    for k in range(1, min(self.breakout_confirm, len(close) - r['end'])):
                        if close.iloc[r['end'] + k] < r['top'] * 0.995:
                            confirmed = False
                            break

                if breakout:
                    # Confirm with RSI momentum
                    current_rsi = rsi_full[r['end']]
                    if not np.isnan(current_rsi):
                        # Better breakout if RSI is not overbought and we had bullish divergence
                        if current_rsi < self.rsi_overbought and (r['bullish_div'] or current_rsi > 50):
                            self.signal[r['end']] = 1
                            self.momentum_confirmed[r['end']] = 1

                elif end_price < r['bottom']:
                    # Confirm breakdown
                    confirmed = True
                    for k in range(1, min(self.breakout_confirm, len(close) - r['end'])):
                        if close.iloc[r['end'] + k] > r['bottom'] * 1.005:
                            confirmed = False
                            break

                    if confirmed:
                        current_rsi = rsi_full[r['end']]
                        if not np.isnan(current_rsi):
                            # Better breakdown if RSI is not oversold and we had bearish divergence
                            if current_rsi > self.rsi_oversold and (r['bearish_div'] or current_rsi < 50):
                                self.signal[r['end']] = -1
                                self.momentum_confirmed[r['end']] = 1

        # Store indicators
        self.rsi_values = rsi_full
        self.I(lambda: self.signal, name='Signal')
        self.I(lambda: self.momentum_confirmed, name='MomentumConfirmed')
        self.I(lambda: self.divergence, name='Divergence')
        self.I(lambda: self.range_top, name='RangeTop')
        self.I(lambda: self.range_bottom, name='RangeBottom')
        self.I(lambda: rsi_full, name='RSI')

    def next(self):
        current_signal = self.signal[-1] if len(self.signal) > 0 else 0
        current_price = self.data.Close[-1]
        current_rsi = self.rsi_values[-1] if len(self.rsi_values) > 0 else 50

        # Dynamic position sizing based on momentum strength
        position_size = 1000000

        # Adjust size based on RSI extremes
        if not np.isnan(current_rsi):
            if current_rsi < self.rsi_oversold:
                position_size *= 1.5  # Increase size when oversold
            elif current_rsi > self.rsi_overbought:
                position_size *= 0.75  # Decrease size when overbought

        # Adjust for divergence strength
        if self.divergence[-1] != 0:
            position_size *= 1.25  # Increase size when divergence present

        # Adjust for range width
        if not np.isnan(self.range_top[-1]) and not np.isnan(self.range_bottom[-1]):
            range_width = (self.range_top[-1] - self.range_bottom[-1]) / self.range_bottom[-1]
            position_size *= max(0.5, min(2.0, 1.0 / (1 + range_width * 10)))

        # Entry logic with momentum confirmation
        if not self.position:
            if current_signal == 1 and self.momentum_confirmed[-1] == 1:
                # Long entry with momentum confirmation
                if not np.isnan(self.range_center[-1]):
                    # Tighter stop if we have divergence
                    stop_distance = 0.5 if self.divergence[-1] == 1 else 1.0
                    sl_price = self.range_center[-1] - (self.range_center[-1] - self.range_bottom[-1]) * stop_distance
                    tp_price = current_price + (current_price - self.range_bottom[-1]) * 2.0
                else:
                    sl_price = current_price * (1 - self.stop_loss_pct)
                    tp_price = current_price * (1 + self.take_profit_pct)

                self.buy(size=position_size, sl=sl_price, tp=tp_price)

            elif current_signal == -1 and self.momentum_confirmed[-1] == 1:
                # Short entry with momentum confirmation
                if not np.isnan(self.range_center[-1]):
                    stop_distance = 0.5 if self.divergence[-1] == -1 else 1.0
                    sl_price = self.range_center[-1] + (self.range_top[-1] - self.range_center[-1]) * stop_distance
                    tp_price = current_price - (self.range_top[-1] - current_price) * 2.0
                else:
                    sl_price = current_price * (1 + self.stop_loss_pct)
                    tp_price = current_price * (1 - self.take_profit_pct)

                self.sell(size=position_size, sl=sl_price, tp=tp_price)

        # Exit on momentum exhaustion or range re-entry
        elif self.position:
            momentum_exhausted = False

            if self.position.is_long:
                # Exit if RSI becomes overbought or price re-enters range
                if not np.isnan(current_rsi) and current_rsi > self.rsi_overbought + 5:
                    momentum_exhausted = True
                elif not np.isnan(self.range_top[-1]) and current_price < self.range_top[-1]:
                    self.position.close()
                elif momentum_exhausted:
                    self.position.close()

            elif self.position.is_short:
                # Exit if RSI becomes oversold or price re-enters range
                if not np.isnan(current_rsi) and current_rsi < self.rsi_oversold - 5:
                    momentum_exhausted = True
                elif not np.isnan(self.range_bottom[-1]) and current_price > self.range_bottom[-1]:
                    self.position.close()
                elif momentum_exhausted:
                    self.position.close()

# Run single backtest
bt = Backtest(data, TrendRangeDetectorMomentum, cash=10000000, commission=0.00045)

print("\n🌙 ===== TREND RANGE DETECTOR MOMENTUM - DEFAULT PARAMETERS ===== 🌙")
print(f"WMA Period: {WMA_PERIOD}")
print(f"ATR Multiplier: {ATR_MULTIPLIER}")
print(f"RSI Period: {RSI_PERIOD}")
print(f"RSI Oversold/Overbought: {RSI_OVERSOLD}/{RSI_OVERBOUGHT}")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")

stats_default = bt.run()
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING TREND RANGE DETECTOR MOMENTUM ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(TrendRangeDetectorMomentum, 'TrendRangeDetectorMomentum')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/TrendRangeDetectorMomentum.csv")