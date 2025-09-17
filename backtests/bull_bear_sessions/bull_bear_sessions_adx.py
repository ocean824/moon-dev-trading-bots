import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
from datetime import time

print("🚀 Moon Dev's Bull vs Bear Sessions + ADX Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
SESSION_HOURS = [6, 12, 18, 24]  # Session boundaries (0-6, 6-12, 12-18, 18-24)
VOLUME_PERCENTILE = 70  # Percentile for Value Area calculation
MIN_SESSION_VOLUME = 50  # Minimum volume percentile for valid signals
DELTA_THRESHOLD = 0.55  # 55% bull volume for bullish bias
ADX_PERIOD = 14
ADX_THRESHOLD = 25  # Minimum ADX for trending market
DI_THRESHOLD = 5  # Minimum DI difference for direction confirmation
TAKE_PROFIT_PERCENT = 3.5
STOP_LOSS_PERCENT = 2.0

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class BullBearSessionsADX(Strategy):
    """
    Bull vs Bear Market Sessions + ADX Strategy

    This strategy combines session-based volume profile analysis with ADX
    to filter for trending markets. ADX ensures we only trade when there's
    sufficient directional movement, avoiding choppy/ranging conditions.
    """

    # Strategy parameters
    session_hours = SESSION_HOURS
    volume_percentile = VOLUME_PERCENTILE
    min_session_volume = MIN_SESSION_VOLUME
    delta_threshold = DELTA_THRESHOLD
    adx_period = ADX_PERIOD
    adx_threshold = ADX_THRESHOLD
    di_threshold = DI_THRESHOLD
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100

    def init(self):
        # Calculate session-based indicators
        def calculate_session_profile(high, low, close, open_, volume):
            """
            Calculate volume profiles for each trading session
            Returns arrays of POC, bull percentage, and session strength
            """
            n = len(high)
            poc_levels = np.zeros(n)
            bull_percentages = np.zeros(n)
            session_strengths = np.zeros(n)
            value_area_highs = np.zeros(n)
            value_area_lows = np.zeros(n)
            session_momentum = np.zeros(n)  # Session-to-session momentum

            for i in range(24, n):  # Need at least 24 hours (1 day) of data
                # Determine current session (0-3 based on hour)
                current_hour = i % 24
                current_session = min(current_hour // 6, 3)

                # Get session data (last 6 hours for current session)
                session_start = i - (current_hour % 6) - 6
                session_end = i

                if session_start < 0:
                    continue

                # Extract session data
                session_high = high[session_start:session_end+1]
                session_low = low[session_start:session_end+1]
                session_close = close[session_start:session_end+1]
                session_open = open_[session_start:session_end+1]
                session_volume = volume[session_start:session_end+1]

                if len(session_high) == 0:
                    continue

                # Calculate session momentum (close vs open)
                session_return = (session_close[-1] - session_open[0]) / session_open[0] if session_open[0] > 0 else 0
                session_momentum[i] = session_return

                # Create volume profile with 10 price bins
                price_range_high = np.max(session_high)
                price_range_low = np.min(session_low)

                if price_range_high == price_range_low:
                    poc_levels[i] = price_range_high
                    bull_percentages[i] = 0.5
                    continue

                # Create price bins
                bins = np.linspace(price_range_low, price_range_high, 11)
                bin_volumes = np.zeros(10)
                bin_bull_volumes = np.zeros(10)

                # Distribute volume across bins with directional weighting
                for j in range(len(session_high)):
                    # Determine if this candle was bullish or bearish
                    is_bullish = session_close[j] >= session_open[j]
                    candle_volume = session_volume[j]

                    # Add directional weighting based on candle strength
                    candle_range = session_high[j] - session_low[j]
                    if candle_range > 0:
                        if is_bullish:
                            candle_strength = (session_close[j] - session_low[j]) / candle_range
                        else:
                            candle_strength = (session_high[j] - session_close[j]) / candle_range
                        candle_volume *= (1 + candle_strength * 0.2)  # Up to 20% volume boost for strong candles

                    # Find which bins this candle touched
                    candle_low = session_low[j]
                    candle_high = session_high[j]

                    for k in range(10):
                        bin_low = bins[k]
                        bin_high = bins[k + 1]

                        # Check if candle overlaps with this bin
                        if candle_high >= bin_low and candle_low <= bin_high:
                            # Calculate overlap percentage
                            overlap_low = max(candle_low, bin_low)
                            overlap_high = min(candle_high, bin_high)
                            overlap_range = overlap_high - overlap_low
                            candle_range = candle_high - candle_low if candle_high > candle_low else 0.0001

                            # Distribute volume proportionally
                            volume_portion = candle_volume * (overlap_range / candle_range)
                            bin_volumes[k] += volume_portion

                            if is_bullish:
                                bin_bull_volumes[k] += volume_portion

                # Find Point of Control (bin with highest volume)
                if np.sum(bin_volumes) > 0:
                    poc_bin = np.argmax(bin_volumes)
                    poc_price = (bins[poc_bin] + bins[poc_bin + 1]) / 2
                    poc_levels[i] = poc_price

                    # Calculate bull percentage at POC
                    if bin_volumes[poc_bin] > 0:
                        bull_percentages[i] = bin_bull_volumes[poc_bin] / bin_volumes[poc_bin]
                    else:
                        bull_percentages[i] = 0.5

                    # Calculate Value Area (70% of volume)
                    total_volume = np.sum(bin_volumes)
                    target_volume = total_volume * self.volume_percentile / 100

                    # Expand from POC until we reach target volume
                    va_bins = [poc_bin]
                    va_volume = bin_volumes[poc_bin]

                    left_idx = poc_bin - 1
                    right_idx = poc_bin + 1

                    while va_volume < target_volume and (left_idx >= 0 or right_idx < 10):
                        left_vol = bin_volumes[left_idx] if left_idx >= 0 else 0
                        right_vol = bin_volumes[right_idx] if right_idx < 10 else 0

                        if left_vol > right_vol and left_idx >= 0:
                            va_bins.append(left_idx)
                            va_volume += left_vol
                            left_idx -= 1
                        elif right_idx < 10:
                            va_bins.append(right_idx)
                            va_volume += right_vol
                            right_idx += 1
                        else:
                            break

                    # Set Value Area boundaries
                    va_bin_min = min(va_bins)
                    va_bin_max = max(va_bins)
                    value_area_lows[i] = bins[va_bin_min]
                    value_area_highs[i] = bins[va_bin_max + 1] if va_bin_max < 9 else bins[10]

                    # Calculate session strength (volume relative to average)
                    avg_volume = np.mean(volume[max(0, i-96):i])  # 96 hours = 4 days
                    if avg_volume > 0:
                        session_strengths[i] = total_volume / (avg_volume * 6)  # Normalized by session length
                    else:
                        session_strengths[i] = 1.0
                else:
                    poc_levels[i] = close[i]
                    bull_percentages[i] = 0.5
                    value_area_highs[i] = high[i]
                    value_area_lows[i] = low[i]
                    session_strengths[i] = 1.0

            return poc_levels, bull_percentages, session_strengths, value_area_highs, value_area_lows, session_momentum

        # Calculate session profiles
        poc, bull_pct, strength, va_high, va_low, momentum = calculate_session_profile(
            self.data.High,
            self.data.Low,
            self.data.Close,
            self.data.Open,
            self.data.Volume
        )

        self.poc_levels = self.I(lambda: poc, name="POC")
        self.bull_percentages = self.I(lambda: bull_pct, name="Bull%")
        self.session_strengths = self.I(lambda: strength, name="Strength")
        self.value_area_highs = self.I(lambda: va_high, name="VA_High")
        self.value_area_lows = self.I(lambda: va_low, name="VA_Low")
        self.session_momentum = self.I(lambda: momentum, name="Momentum")

        # Calculate ADX and Directional Indicators
        self.adx = self.I(talib.ADX,
                          self.data.High,
                          self.data.Low,
                          self.data.Close,
                          timeperiod=self.adx_period)

        self.plus_di = self.I(talib.PLUS_DI,
                              self.data.High,
                              self.data.Low,
                              self.data.Close,
                              timeperiod=self.adx_period)

        self.minus_di = self.I(talib.MINUS_DI,
                               self.data.High,
                               self.data.Low,
                               self.data.Close,
                               timeperiod=self.adx_period)

        # Volume filter
        self.volume_ma = self.I(talib.SMA, self.data.Volume, timeperiod=24)

        # Calculate trending session transitions
        def detect_trending_transitions(bull_pct, adx, plus_di, minus_di, threshold, adx_min, di_diff):
            """Detect session transitions in trending markets"""
            transitions = np.zeros(len(bull_pct))

            for i in range(6, len(bull_pct)):
                if np.isnan(adx[i]) or np.isnan(plus_di[i]) or np.isnan(minus_di[i]):
                    continue

                prev_bull = bull_pct[i-6] > threshold
                curr_bull = bull_pct[i] > threshold
                is_trending = adx[i] > adx_min

                if is_trending:
                    # Check directional movement alignment
                    di_difference = plus_di[i] - minus_di[i]

                    if not prev_bull and curr_bull and di_difference > di_diff:
                        # Bear to Bull transition with uptrend confirmation
                        transitions[i] = 1
                    elif prev_bull and not curr_bull and di_difference < -di_diff:
                        # Bull to Bear transition with downtrend confirmation
                        transitions[i] = -1

            return transitions

        self.trending_transitions = self.I(
            lambda: detect_trending_transitions(
                bull_pct, self.adx, self.plus_di, self.minus_di,
                self.delta_threshold, self.adx_threshold, self.di_threshold
            ),
            name="TrendingTransitions"
        )

    def next(self):
        # Skip if not enough data or ADX not calculated
        if len(self.data) < 96 or np.isnan(self.adx[-1]):
            return

        # Get current values
        current_price = self.data.Close[-1]
        current_poc = self.poc_levels[-1]
        current_bull_pct = self.bull_percentages[-1]
        current_strength = self.session_strengths[-1]
        current_transition = self.trending_transitions[-1]
        current_volume = self.data.Volume[-1]
        current_adx = self.adx[-1]
        current_plus_di = self.plus_di[-1]
        current_minus_di = self.minus_di[-1]
        current_momentum = self.session_momentum[-1]
        va_high = self.value_area_highs[-1]
        va_low = self.value_area_lows[-1]

        # Calculate DI difference for direction
        di_diff = current_plus_di - current_minus_di

        # Volume filter - only trade on significant volume
        if current_volume < self.volume_ma[-1] * (self.min_session_volume / 100):
            return

        # Position management
        if not self.position:
            # Only trade in trending markets
            if current_adx < self.adx_threshold:
                return

            # Entry logic with ADX confirmation

            # Long Entry: Bear to Bull transition in uptrend
            if current_transition == 1 and current_strength > 1.0:
                if current_price <= current_poc * 1.005 and di_diff > self.di_threshold:
                    # Strong bull session in uptrend
                    sl_price = current_price * (1 - self.stop_loss)
                    tp_price = current_price * (1 + self.take_profit)
                    self.buy(sl=sl_price, tp=tp_price)

            # Short Entry: Bull to Bear transition in downtrend
            elif current_transition == -1 and current_strength > 1.0:
                if current_price >= current_poc * 0.995 and di_diff < -self.di_threshold:
                    # Strong bear session in downtrend
                    sl_price = current_price * (1 + self.stop_loss)
                    tp_price = current_price * (1 - self.take_profit)
                    self.sell(sl=sl_price, tp=tp_price)

            # Strong trend continuation entries
            elif current_adx > self.adx_threshold + 10:  # Very strong trend
                if current_bull_pct > 0.65 and di_diff > self.di_threshold * 2:
                    # Strong uptrend with bullish session
                    if current_price < current_poc and current_momentum > 0:
                        sl_price = current_price * (1 - self.stop_loss)
                        tp_price = current_price * (1 + self.take_profit * 1.2)  # Extended target in strong trends
                        self.buy(sl=sl_price, tp=tp_price)

                elif current_bull_pct < 0.35 and di_diff < -self.di_threshold * 2:
                    # Strong downtrend with bearish session
                    if current_price > current_poc and current_momentum < 0:
                        sl_price = current_price * (1 + self.stop_loss)
                        tp_price = current_price * (1 - self.take_profit * 1.2)  # Extended target in strong trends
                        self.sell(sl=sl_price, tp=tp_price)

            # Trend exhaustion reversals
            elif current_adx > 40 and abs(current_momentum) < 0.005:  # Strong trend but momentum slowing
                if di_diff > self.di_threshold * 3 and current_bull_pct < 0.4:
                    # Potential trend exhaustion - bearish reversal
                    if current_price > va_high:
                        sl_price = current_price * (1 + self.stop_loss * 0.75)  # Tighter stop for reversals
                        tp_price = current_poc
                        self.sell(sl=sl_price, tp=tp_price)

                elif di_diff < -self.di_threshold * 3 and current_bull_pct > 0.6:
                    # Potential trend exhaustion - bullish reversal
                    if current_price < va_low:
                        sl_price = current_price * (1 - self.stop_loss * 0.75)  # Tighter stop for reversals
                        tp_price = current_poc
                        self.buy(sl=sl_price, tp=tp_price)

        else:
            # Dynamic exit based on ADX and trend changes
            if self.position.is_long:
                # Exit if trend weakens or reverses
                if current_adx < self.adx_threshold - 5 or di_diff < -self.di_threshold:
                    self.position.close()
                # Exit if session turns strongly bearish in weak trend
                elif current_bull_pct < 0.3 and current_transition == -1 and current_adx < 30:
                    self.position.close()

            else:  # Short position
                # Exit if trend weakens or reverses
                if current_adx < self.adx_threshold - 5 or di_diff > self.di_threshold:
                    self.position.close()
                # Exit if session turns strongly bullish in weak trend
                elif current_bull_pct > 0.7 and current_transition == 1 and current_adx < 30:
                    self.position.close()

# Run single backtest
bt = Backtest(data, BullBearSessionsADX, cash=1000000, commission=0.00045)

print("\n🌙 ===== BULL VS BEAR SESSIONS + ADX - DEFAULT PARAMETERS ===== 🌙")
print(f"Session Hours: {SESSION_HOURS}")
print(f"Volume Percentile: {VOLUME_PERCENTILE}%")
print(f"Delta Threshold: {DELTA_THRESHOLD}")
print(f"ADX Period: {ADX_PERIOD}")
print(f"ADX Threshold: {ADX_THRESHOLD}")
print(f"DI Threshold: {DI_THRESHOLD}")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")

stats_default = bt.run()
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING BULL VS BEAR SESSIONS + ADX ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(BullBearSessionsADX, 'BullBearSessionsADX')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/BullBearSessionsADX.csv")