import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
from datetime import time

print("🚀 Moon Dev's Bull vs Bear Sessions + Kalman Filter Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
SESSION_HOURS = [6, 12, 18, 24]  # Session boundaries (0-6, 6-12, 12-18, 18-24)
VOLUME_PERCENTILE = 70  # Percentile for Value Area calculation
MIN_SESSION_VOLUME = 50  # Minimum volume percentile for valid signals
DELTA_THRESHOLD = 0.55  # 55% bull volume for bullish bias
KALMAN_GAIN = 0.01  # Kalman filter gain (lower = smoother)
KALMAN_COVARIANCE = 1.0  # Initial covariance
TREND_THRESHOLD = 0.002  # Minimum Kalman trend strength
TAKE_PROFIT_PERCENT = 3.0
STOP_LOSS_PERCENT = 1.8

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class BullBearSessionsKalman(Strategy):
    """
    Bull vs Bear Market Sessions + Kalman Filter Strategy

    This strategy combines session-based volume profile analysis with Kalman filtering
    for smoothed price action confirmation. The Kalman filter helps identify the true
    trend direction while filtering out market noise.
    """

    # Strategy parameters
    session_hours = SESSION_HOURS
    volume_percentile = VOLUME_PERCENTILE
    min_session_volume = MIN_SESSION_VOLUME
    delta_threshold = DELTA_THRESHOLD
    kalman_gain = KALMAN_GAIN
    kalman_covariance = KALMAN_COVARIANCE
    trend_threshold = TREND_THRESHOLD
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100

    def init(self):
        # Calculate session-based indicators
        def calculate_session_profile(high, low, close, open_, volume):
            """
            Calculate volume profiles for each trading session with advanced metrics
            """
            n = len(high)
            poc_levels = np.zeros(n)
            bull_percentages = np.zeros(n)
            session_strengths = np.zeros(n)
            value_area_highs = np.zeros(n)
            value_area_lows = np.zeros(n)
            cumulative_delta = np.zeros(n)  # Cumulative volume delta
            delta_divergence = np.zeros(n)  # Price vs Delta divergence

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

                # Calculate session price change and volume delta
                price_change = (session_close[-1] - session_open[0]) / session_open[0] if session_open[0] > 0 else 0

                # Create volume profile with 10 price bins
                price_range_high = np.max(session_high)
                price_range_low = np.min(session_low)

                if price_range_high == price_range_low:
                    poc_levels[i] = price_range_high
                    bull_percentages[i] = 0.5
                    cumulative_delta[i] = cumulative_delta[i-1] if i > 0 else 0
                    continue

                # Create price bins
                bins = np.linspace(price_range_low, price_range_high, 11)
                bin_volumes = np.zeros(10)
                bin_bull_volumes = np.zeros(10)
                bin_bear_volumes = np.zeros(10)

                # Calculate session delta
                session_bull_vol = 0
                session_bear_vol = 0

                # Distribute volume across bins
                for j in range(len(session_high)):
                    # Determine if this candle was bullish or bearish
                    is_bullish = session_close[j] >= session_open[j]
                    candle_volume = session_volume[j]

                    if is_bullish:
                        session_bull_vol += candle_volume
                    else:
                        session_bear_vol += candle_volume

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
                            else:
                                bin_bear_volumes[k] += volume_portion

                # Calculate cumulative delta
                session_delta = session_bull_vol - session_bear_vol
                cumulative_delta[i] = cumulative_delta[i-1] + session_delta if i > 0 else session_delta

                # Calculate delta divergence (normalized)
                if session_bull_vol + session_bear_vol > 0:
                    delta_ratio = session_delta / (session_bull_vol + session_bear_vol)
                    # Divergence: price up but delta down, or vice versa
                    delta_divergence[i] = abs(price_change - delta_ratio) if (price_change * delta_ratio) < 0 else 0
                else:
                    delta_divergence[i] = 0

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

            return poc_levels, bull_percentages, session_strengths, value_area_highs, value_area_lows, cumulative_delta, delta_divergence

        # Calculate session profiles
        poc, bull_pct, strength, va_high, va_low, cum_delta, divergence = calculate_session_profile(
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
        self.cumulative_delta = self.I(lambda: cum_delta, name="CumDelta")
        self.delta_divergence = self.I(lambda: divergence, name="Divergence")

        # Implement Kalman Filter
        def kalman_filter(prices, gain, initial_covariance):
            """
            Apply Kalman filter to price series
            Returns: filtered prices, trend (velocity), and prediction confidence
            """
            n = len(prices)
            filtered = np.zeros(n)
            velocity = np.zeros(n)  # Rate of change (trend)
            confidence = np.zeros(n)  # Prediction confidence

            # Initialize
            x_est = prices[0] if n > 0 else 0  # Initial estimate
            p_est = initial_covariance  # Initial error covariance
            v_est = 0  # Initial velocity

            # Process noise covariance
            q = gain

            # Measurement noise covariance
            r = gain * 10

            for i in range(n):
                # Prediction step
                x_pred = x_est + v_est  # Predict next value using velocity
                p_pred = p_est + q

                # Update step
                k = p_pred / (p_pred + r)  # Kalman gain
                x_est = x_pred + k * (prices[i] - x_pred)  # Update estimate
                p_est = (1 - k) * p_pred

                # Update velocity (trend)
                if i > 0:
                    v_est = v_est + k * ((prices[i] - prices[i-1]) - v_est)
                    velocity[i] = v_est

                filtered[i] = x_est
                confidence[i] = 1 / (1 + p_est)  # Higher when estimate is more certain

            return filtered, velocity, confidence

        # Apply Kalman filter to price
        kalman_price, kalman_trend, kalman_confidence = kalman_filter(
            self.data.Close,
            self.kalman_gain,
            self.kalman_covariance
        )

        self.kalman_price = self.I(lambda: kalman_price, name="KalmanPrice")
        self.kalman_trend = self.I(lambda: kalman_trend, name="KalmanTrend")
        self.kalman_confidence = self.I(lambda: kalman_confidence, name="KalmanConf")

        # Volume filter
        self.volume_ma = self.I(talib.SMA, self.data.Volume, timeperiod=24)

        # Detect session transitions with Kalman confirmation
        def detect_kalman_transitions(bull_pct, kalman_trend, threshold, trend_min):
            """Detect session transitions confirmed by Kalman trend"""
            transitions = np.zeros(len(bull_pct))

            for i in range(6, len(bull_pct)):
                prev_bull = bull_pct[i-6] > threshold
                curr_bull = bull_pct[i] > threshold
                trend = kalman_trend[i]

                if not prev_bull and curr_bull and trend > trend_min:
                    # Bear to Bull transition with upward Kalman trend
                    transitions[i] = 1
                elif prev_bull and not curr_bull and trend < -trend_min:
                    # Bull to Bear transition with downward Kalman trend
                    transitions[i] = -1

            return transitions

        self.kalman_transitions = self.I(
            lambda: detect_kalman_transitions(
                bull_pct, kalman_trend, self.delta_threshold, self.trend_threshold
            ),
            name="KalmanTransitions"
        )

    def next(self):
        # Skip if not enough data
        if len(self.data) < 96:
            return

        # Get current values
        current_price = self.data.Close[-1]
        current_poc = self.poc_levels[-1]
        current_bull_pct = self.bull_percentages[-1]
        current_strength = self.session_strengths[-1]
        current_transition = self.kalman_transitions[-1]
        current_volume = self.data.Volume[-1]
        current_kalman = self.kalman_price[-1]
        current_trend = self.kalman_trend[-1]
        current_confidence = self.kalman_confidence[-1]
        current_cum_delta = self.cumulative_delta[-1]
        current_divergence = self.delta_divergence[-1]
        va_high = self.value_area_highs[-1]
        va_low = self.value_area_lows[-1]

        # Calculate price position relative to Kalman
        price_vs_kalman = (current_price - current_kalman) / current_kalman if current_kalman > 0 else 0

        # Volume filter - only trade on significant volume
        if current_volume < self.volume_ma[-1] * (self.min_session_volume / 100):
            return

        # Position management
        if not self.position:
            # Entry logic with Kalman confirmation

            # Long Entry: Bear to Bull transition with Kalman uptrend
            if current_transition == 1 and current_strength > 1.0:
                if current_price <= current_poc * 1.005 and price_vs_kalman < 0.005:
                    # Price near/below Kalman with upward trend
                    sl_price = current_price * (1 - self.stop_loss)
                    tp_price = current_price * (1 + self.take_profit)
                    self.buy(sl=sl_price, tp=tp_price)

            # Short Entry: Bull to Bear transition with Kalman downtrend
            elif current_transition == -1 and current_strength > 1.0:
                if current_price >= current_poc * 0.995 and price_vs_kalman > -0.005:
                    # Price near/above Kalman with downward trend
                    sl_price = current_price * (1 + self.stop_loss)
                    tp_price = current_price * (1 - self.take_profit)
                    self.sell(sl=sl_price, tp=tp_price)

            # Kalman trend acceleration entries
            elif abs(current_trend) > self.trend_threshold * 2 and current_confidence > 0.7:
                if current_trend > self.trend_threshold * 2 and current_bull_pct > 0.6:
                    # Strong upward Kalman trend with bullish session
                    if current_price < current_kalman * 1.002:  # Price below or near Kalman
                        sl_price = current_kalman * 0.98
                        tp_price = current_price * (1 + self.take_profit)
                        self.buy(sl=sl_price, tp=tp_price)

                elif current_trend < -self.trend_threshold * 2 and current_bull_pct < 0.4:
                    # Strong downward Kalman trend with bearish session
                    if current_price > current_kalman * 0.998:  # Price above or near Kalman
                        sl_price = current_kalman * 1.02
                        tp_price = current_price * (1 - self.take_profit)
                        self.sell(sl=sl_price, tp=tp_price)

            # Delta divergence entries (contrarian with Kalman support)
            elif current_divergence > 0.3 and current_confidence > 0.6:
                # Significant price/delta divergence - potential reversal
                if current_trend > 0 and price_vs_kalman < -0.01:
                    # Kalman trending up but price below - buy opportunity
                    if current_bull_pct > 0.45:
                        sl_price = current_price * (1 - self.stop_loss * 0.8)
                        tp_price = current_kalman * 1.01
                        self.buy(sl=sl_price, tp=tp_price)

                elif current_trend < 0 and price_vs_kalman > 0.01:
                    # Kalman trending down but price above - sell opportunity
                    if current_bull_pct < 0.55:
                        sl_price = current_price * (1 + self.stop_loss * 0.8)
                        tp_price = current_kalman * 0.99
                        self.sell(sl=sl_price, tp=tp_price)

            # Cumulative delta extreme entries
            elif current_strength > 1.3:
                # Check cumulative delta vs recent average
                recent_delta_avg = np.mean(self.cumulative_delta[-24:])

                if current_cum_delta > recent_delta_avg * 1.5 and current_bull_pct > 0.65:
                    # Strong positive delta accumulation
                    if current_price < current_poc and current_trend >= 0:
                        sl_price = current_price * (1 - self.stop_loss)
                        tp_price = current_price * (1 + self.take_profit)
                        self.buy(sl=sl_price, tp=tp_price)

                elif current_cum_delta < recent_delta_avg * 0.5 and current_bull_pct < 0.35:
                    # Strong negative delta accumulation
                    if current_price > current_poc and current_trend <= 0:
                        sl_price = current_price * (1 + self.stop_loss)
                        tp_price = current_price * (1 - self.take_profit)
                        self.sell(sl=sl_price, tp=tp_price)

        else:
            # Dynamic exit based on Kalman filter
            if self.position.is_long:
                # Exit if Kalman trend reverses or price diverges too much
                if current_trend < -self.trend_threshold or price_vs_kalman > 0.02:
                    self.position.close()
                # Exit if session turns strongly bearish
                elif current_bull_pct < 0.3 and current_transition == -1:
                    self.position.close()

            else:  # Short position
                # Exit if Kalman trend reverses or price diverges too much
                if current_trend > self.trend_threshold or price_vs_kalman < -0.02:
                    self.position.close()
                # Exit if session turns strongly bullish
                elif current_bull_pct > 0.7 and current_transition == 1:
                    self.position.close()

# Run single backtest
bt = Backtest(data, BullBearSessionsKalman, cash=1000000, commission=0.00045)

print("\n🌙 ===== BULL VS BEAR SESSIONS + KALMAN - DEFAULT PARAMETERS ===== 🌙")
print(f"Session Hours: {SESSION_HOURS}")
print(f"Volume Percentile: {VOLUME_PERCENTILE}%")
print(f"Delta Threshold: {DELTA_THRESHOLD}")
print(f"Kalman Gain: {KALMAN_GAIN}")
print(f"Trend Threshold: {TREND_THRESHOLD}")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")

stats_default = bt.run()
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING BULL VS BEAR SESSIONS + KALMAN ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(BullBearSessionsKalman, 'BullBearSessionsKalman')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/BullBearSessionsKalman.csv")