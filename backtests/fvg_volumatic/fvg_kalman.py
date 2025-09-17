import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
import sys
import os

print("🚀 Moon Dev's Fair Value Gap (FVG) + Kalman Filter Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
FVG_MIN_GAP_PERCENT = 0.5  # Minimum gap size as percentage (0.5%)
VOLUME_FILTER_PERIOD = 20  # Period for volume average
VOLUME_THRESHOLD = 1.2  # Volume must be 1.2x average
BULL_VOLUME_RATIO = 0.6  # 60% buy volume for bullish confirmation
BEAR_VOLUME_RATIO = 0.4  # 40% buy volume (60% sell) for bearish confirmation
KALMAN_PROCESS_NOISE = 0.01  # Process noise for Kalman filter
KALMAN_MEASUREMENT_NOISE = 0.1  # Measurement noise for Kalman filter
KALMAN_TREND_THRESHOLD = 0.001  # Minimum trend strength from Kalman
TAKE_PROFIT_PERCENT = 4.0
STOP_LOSS_PERCENT = 2.0
GAP_MITIGATION_PERCENT = 50  # Exit when gap is 50% filled

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class FVGKalman(Strategy):
    """
    Fair Value Gap (FVG) + Kalman Filter Strategy

    This strategy enhances the base FVG strategy with Kalman filtering for:
    - Noise reduction in price data for cleaner gap detection
    - Trend estimation and prediction
    - Adaptive entry/exit based on filtered trends
    - Enhanced gap validation using smoothed price action
    """

    # Strategy parameters
    min_gap_percent = FVG_MIN_GAP_PERCENT / 100
    volume_filter_period = VOLUME_FILTER_PERIOD
    volume_threshold = VOLUME_THRESHOLD
    bull_volume_ratio = BULL_VOLUME_RATIO
    bear_volume_ratio = BEAR_VOLUME_RATIO
    kalman_process_noise = KALMAN_PROCESS_NOISE
    kalman_measurement_noise = KALMAN_MEASUREMENT_NOISE
    kalman_trend_threshold = KALMAN_TREND_THRESHOLD
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100
    gap_mitigation_percent = GAP_MITIGATION_PERCENT / 100

    def init(self):
        # Volume moving average for filtering
        self.volume_ma = self.I(talib.SMA, self.data.Volume, timeperiod=self.volume_filter_period)

        # Kalman Filter implementation
        def kalman_filter(prices, process_noise=0.01, measurement_noise=0.1):
            """
            Apply Kalman filter to price series for noise reduction
            Returns: filtered prices, trend (velocity), and prediction confidence
            """
            n = len(prices)
            filtered = np.zeros(n)
            trend = np.zeros(n)
            confidence = np.zeros(n)

            # Initial state [position, velocity]
            x = np.array([prices[0], 0])
            # Initial covariance
            P = np.array([[1, 0], [0, 1]])

            # State transition matrix
            F = np.array([[1, 1], [0, 1]])
            # Measurement matrix
            H = np.array([[1, 0]])
            # Process noise covariance
            Q = np.array([[process_noise/4, process_noise/2],
                         [process_noise/2, process_noise]])
            # Measurement noise covariance
            R = measurement_noise

            for i in range(n):
                # Prediction step
                x = F @ x
                P = F @ P @ F.T + Q

                # Update step
                y = prices[i] - H @ x  # Innovation
                S = H @ P @ H.T + R  # Innovation covariance
                K = P @ H.T / S  # Kalman gain

                x = x + K * y
                P = (np.eye(2) - np.outer(K, H)) @ P

                # Store results
                filtered[i] = x[0]
                trend[i] = x[1]
                confidence[i] = 1 / (1 + abs(y))  # Confidence based on innovation

            return filtered, trend, confidence

        # Apply Kalman filter to prices
        kalman_close, kalman_trend, kalman_conf = kalman_filter(
            self.data.Close.values,
            self.kalman_process_noise,
            self.kalman_measurement_noise
        )

        self.kalman_price = self.I(lambda: kalman_close)
        self.kalman_trend = self.I(lambda: kalman_trend)
        self.kalman_confidence = self.I(lambda: kalman_conf)

        # Kalman filter on volume for volume trend detection
        kalman_volume, volume_trend, _ = kalman_filter(
            self.data.Volume.values,
            self.kalman_process_noise * 10,  # More noise tolerance for volume
            self.kalman_measurement_noise * 10
        )

        self.kalman_volume = self.I(lambda: kalman_volume)
        self.volume_trend = self.I(lambda: volume_trend)

        # ATR for dynamic gap validation
        self.atr = self.I(talib.ATR, self.data.High, self.data.Low, self.data.Close, timeperiod=14)

        # Calculate bull/bear volume ratio
        def calculate_volume_ratio(high, low, close, volume):
            """
            Calculate the ratio of bull vs bear volume for each candle
            """
            bull_ratio = np.zeros(len(high))

            for i in range(len(high)):
                if high[i] > low[i]:
                    # Calculate where close is within the candle's range
                    range_size = high[i] - low[i]
                    bull_portion = (close[i] - low[i]) / range_size
                    bull_ratio[i] = bull_portion
                else:
                    # If high equals low (doji), assume neutral (0.5)
                    bull_ratio[i] = 0.5

            return bull_ratio

        self.bull_volume_ratio = self.I(
            calculate_volume_ratio,
            self.data.High, self.data.Low, self.data.Close, self.data.Volume
        )

        # Track active FVGs
        self.bullish_fvg_high = None  # Top of bullish gap
        self.bullish_fvg_low = None   # Bottom of bullish gap
        self.bearish_fvg_high = None  # Top of bearish gap
        self.bearish_fvg_low = None   # Bottom of bearish gap

        # Track entry details
        self.entry_price = None
        self.entry_type = None  # 'bullish' or 'bearish'
        self.entry_kalman_trend = None  # Kalman trend at entry

    def detect_bullish_fvg(self, idx):
        """
        Detect Bullish Fair Value Gap with Kalman filter enhancement
        """
        if idx < 2:
            return False, None, None

        current_low = self.data.Low[idx]
        two_bars_ago_high = self.data.High[idx - 2]
        kalman_price = self.kalman_price[idx]
        kalman_trend = self.kalman_trend[idx]
        kalman_confidence = self.kalman_confidence[idx]
        volume_trend = self.volume_trend[idx]

        # Check for bullish gap
        if current_low > two_bars_ago_high:
            gap_size = current_low - two_bars_ago_high
            price_level = (current_low + two_bars_ago_high) / 2
            gap_percent = gap_size / price_level

            # Validate gap size
            if gap_percent >= self.min_gap_percent:
                # Check volume conditions
                current_volume = self.data.Volume[idx]
                avg_volume = self.volume_ma[idx]

                if current_volume >= avg_volume * self.volume_threshold:
                    # Check bull volume ratio
                    if self.bull_volume_ratio[idx] >= self.bull_volume_ratio:
                        # Kalman filter confirmation
                        # Best: Strong positive trend with high confidence
                        if (kalman_trend > self.kalman_trend_threshold and
                            kalman_confidence > 0.7):
                            return True, current_low, two_bars_ago_high
                        # Good: Price above Kalman with positive trend
                        elif (self.data.Close[idx] > kalman_price and
                              kalman_trend > 0):
                            return True, current_low, two_bars_ago_high
                        # Alternative: Volume trend increasing with gap
                        elif volume_trend > 0 and kalman_trend >= 0:
                            return True, current_low, two_bars_ago_high

        return False, None, None

    def detect_bearish_fvg(self, idx):
        """
        Detect Bearish Fair Value Gap with Kalman filter enhancement
        """
        if idx < 2:
            return False, None, None

        current_high = self.data.High[idx]
        two_bars_ago_low = self.data.Low[idx - 2]
        kalman_price = self.kalman_price[idx]
        kalman_trend = self.kalman_trend[idx]
        kalman_confidence = self.kalman_confidence[idx]
        volume_trend = self.volume_trend[idx]

        # Check for bearish gap
        if current_high < two_bars_ago_low:
            gap_size = two_bars_ago_low - current_high
            price_level = (current_high + two_bars_ago_low) / 2
            gap_percent = gap_size / price_level

            # Validate gap size
            if gap_percent >= self.min_gap_percent:
                # Check volume conditions
                current_volume = self.data.Volume[idx]
                avg_volume = self.volume_ma[idx]

                if current_volume >= avg_volume * self.volume_threshold:
                    # Check bear volume ratio
                    if self.bull_volume_ratio[idx] <= self.bear_volume_ratio:
                        # Kalman filter confirmation
                        # Best: Strong negative trend with high confidence
                        if (kalman_trend < -self.kalman_trend_threshold and
                            kalman_confidence > 0.7):
                            return True, two_bars_ago_low, current_high
                        # Good: Price below Kalman with negative trend
                        elif (self.data.Close[idx] < kalman_price and
                              kalman_trend < 0):
                            return True, two_bars_ago_low, current_high
                        # Alternative: Volume trend increasing with gap
                        elif volume_trend > 0 and kalman_trend <= 0:
                            return True, two_bars_ago_low, current_high

        return False, None, None

    def is_gap_mitigated(self, gap_high, gap_low, current_price, gap_type):
        """
        Check if a gap has been mitigated (filled)
        Enhanced with Kalman trend reversal detection
        """
        if gap_high is None or gap_low is None:
            return False

        gap_midpoint = (gap_high + gap_low) / 2
        current_kalman_trend = self.kalman_trend[-1]
        kalman_price = self.kalman_price[-1]

        if gap_type == 'bullish':
            # Bullish gap is mitigated when price goes below midpoint
            # OR when Kalman trend reverses negative
            price_mitigation = current_price <= gap_midpoint
            # Check for trend reversal
            trend_reversal = (current_kalman_trend < -self.kalman_trend_threshold and
                            self.entry_kalman_trend > 0 if self.entry_kalman_trend else False)
            # Check for price below Kalman filter
            below_kalman = current_price < kalman_price * 0.995
            return price_mitigation or trend_reversal or below_kalman
        else:
            # Bearish gap is mitigated when price goes above midpoint
            # OR when Kalman trend reverses positive
            price_mitigation = current_price >= gap_midpoint
            # Check for trend reversal
            trend_reversal = (current_kalman_trend > self.kalman_trend_threshold and
                            self.entry_kalman_trend < 0 if self.entry_kalman_trend else False)
            # Check for price above Kalman filter
            above_kalman = current_price > kalman_price * 1.005
            return price_mitigation or trend_reversal or above_kalman

    def calculate_adaptive_targets(self, kalman_trend, confidence):
        """
        Calculate adaptive take profit and stop loss based on Kalman metrics
        """
        # Stronger trends get wider targets
        trend_multiplier = 1 + min(abs(kalman_trend) * 100, 0.5)
        # Higher confidence gets tighter stops
        confidence_multiplier = 1 - (confidence - 0.5) * 0.5

        adaptive_tp = self.take_profit * trend_multiplier
        adaptive_sl = self.stop_loss * confidence_multiplier

        return adaptive_tp, adaptive_sl

    def next(self):
        # Skip if we don't have enough data
        if len(self.data) < self.volume_filter_period * 2:
            return

        # Get current index and values
        idx = len(self.data) - 1
        current_price = self.data.Close[-1]
        kalman_price = self.kalman_price[-1]
        kalman_trend = self.kalman_trend[-1]
        kalman_confidence = self.kalman_confidence[-1]

        # Check if we have a position
        if self.position:
            # Exit logic with Kalman enhancement
            if self.position.is_long:
                # Adaptive targets based on Kalman metrics
                adaptive_tp, adaptive_sl = self.calculate_adaptive_targets(
                    kalman_trend, kalman_confidence
                )

                # Check for take profit
                if current_price >= self.entry_price * (1 + adaptive_tp):
                    self.position.close()
                    self.entry_price = None
                    self.entry_type = None
                    self.entry_kalman_trend = None
                    self.bullish_fvg_high = None
                    self.bullish_fvg_low = None
                # Check for stop loss
                elif current_price <= self.entry_price * (1 - adaptive_sl):
                    self.position.close()
                    self.entry_price = None
                    self.entry_type = None
                    self.entry_kalman_trend = None
                    self.bullish_fvg_high = None
                    self.bullish_fvg_low = None
                # Check for gap mitigation or Kalman exit signals
                elif self.is_gap_mitigated(self.bullish_fvg_high, self.bullish_fvg_low,
                                          current_price, 'bullish'):
                    self.position.close()
                    self.entry_price = None
                    self.entry_type = None
                    self.entry_kalman_trend = None
                    self.bullish_fvg_high = None
                    self.bullish_fvg_low = None
                # Exit if confidence drops too low
                elif kalman_confidence < 0.3:
                    self.position.close()
                    self.entry_price = None
                    self.entry_type = None
                    self.entry_kalman_trend = None
                    self.bullish_fvg_high = None
                    self.bullish_fvg_low = None

            elif self.position.is_short:
                # Adaptive targets based on Kalman metrics
                adaptive_tp, adaptive_sl = self.calculate_adaptive_targets(
                    kalman_trend, kalman_confidence
                )

                # Check for take profit
                if current_price <= self.entry_price * (1 - adaptive_tp):
                    self.position.close()
                    self.entry_price = None
                    self.entry_type = None
                    self.entry_kalman_trend = None
                    self.bearish_fvg_high = None
                    self.bearish_fvg_low = None
                # Check for stop loss
                elif current_price >= self.entry_price * (1 + adaptive_sl):
                    self.position.close()
                    self.entry_price = None
                    self.entry_type = None
                    self.entry_kalman_trend = None
                    self.bearish_fvg_high = None
                    self.bearish_fvg_low = None
                # Check for gap mitigation or Kalman exit signals
                elif self.is_gap_mitigated(self.bearish_fvg_high, self.bearish_fvg_low,
                                          current_price, 'bearish'):
                    self.position.close()
                    self.entry_price = None
                    self.entry_type = None
                    self.entry_kalman_trend = None
                    self.bearish_fvg_high = None
                    self.bearish_fvg_low = None
                # Exit if confidence drops too low
                elif kalman_confidence < 0.3:
                    self.position.close()
                    self.entry_price = None
                    self.entry_type = None
                    self.entry_kalman_trend = None
                    self.bearish_fvg_high = None
                    self.bearish_fvg_low = None
        else:
            # Entry logic - Look for new FVGs with Kalman confirmation

            # Only consider entries when Kalman confidence is reasonable
            if kalman_confidence > 0.5:
                # Check for bullish FVG
                is_bullish_fvg, gap_high, gap_low = self.detect_bullish_fvg(idx)
                if is_bullish_fvg:
                    # Enter long position
                    self.buy()
                    self.entry_price = current_price
                    self.entry_type = 'bullish'
                    self.entry_kalman_trend = kalman_trend
                    self.bullish_fvg_high = gap_high
                    self.bullish_fvg_low = gap_low
                    return

                # Check for bearish FVG
                is_bearish_fvg, gap_high, gap_low = self.detect_bearish_fvg(idx)
                if is_bearish_fvg:
                    # Enter short position
                    self.sell()
                    self.entry_price = current_price
                    self.entry_type = 'bearish'
                    self.entry_kalman_trend = kalman_trend
                    self.bearish_fvg_high = gap_high
                    self.bearish_fvg_low = gap_low

# Run single backtest
bt = Backtest(data, FVGKalman, cash=1000000, commission=0.00045)

print("\n🌙 ===== FVG + KALMAN FILTER STRATEGY - DEFAULT PARAMETERS ===== 🌙")
print(f"Min Gap: {FVG_MIN_GAP_PERCENT}%")
print(f"Volume Threshold: {VOLUME_THRESHOLD}x average")
print(f"Kalman Process Noise: {KALMAN_PROCESS_NOISE}")
print(f"Kalman Measurement Noise: {KALMAN_MEASUREMENT_NOISE}")
print(f"Kalman Trend Threshold: {KALMAN_TREND_THRESHOLD}")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")

stats_default = bt.run()
print(stats_default)

# Optimization
print("\n🚀 Optimizing FVG + Kalman Strategy...")
optimization_results = bt.optimize(
    min_gap_percent=[i / 1000 for i in range(3, 11, 2)],  # 0.3% to 1.0%
    volume_threshold=[1.0, 1.2, 1.5],
    kalman_process_noise=[0.005, 0.01, 0.02],
    kalman_measurement_noise=[0.05, 0.1, 0.2],
    take_profit=[i / 1000 for i in range(30, 61, 10)],
    stop_loss=[i / 1000 for i in range(10, 26, 5)],
    maximize='Sortino Ratio',
    constraint=lambda p: p.take_profit > p.stop_loss
)

print("\n🚀 ===== OPTIMIZATION RESULTS ===== 🚀")
print(optimization_results)

print("\n🏆 BEST PARAMETERS:")
print(f"Min Gap: {optimization_results._strategy.min_gap_percent * 100:.1f}%")
print(f"Volume Threshold: {optimization_results._strategy.volume_threshold}x")
print(f"Kalman Process Noise: {optimization_results._strategy.kalman_process_noise}")
print(f"Kalman Measurement Noise: {optimization_results._strategy.kalman_measurement_noise}")
print(f"Take Profit: {optimization_results._strategy.take_profit * 100:.1f}%")
print(f"Stop Loss: {optimization_results._strategy.stop_loss * 100:.1f}%")

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING FVG + KALMAN FILTER STRATEGY ON ALL DATA SOURCES")
    print("="*80)

    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(FVGKalman, 'FVG_Kalman')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/FVG_Kalman_[timestamp].csv")