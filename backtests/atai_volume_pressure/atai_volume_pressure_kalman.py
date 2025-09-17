"""
ATAI Volume Pressure Analyzer - Kalman Strategy
Adds Kalman filter for smoothing volume signals
"""

from backtesting import Backtest, Strategy
import pandas as pd
import numpy as np
import pandas_ta as ta
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

class KalmanFilter:
    """Simple Kalman filter implementation for smoothing"""
    def __init__(self, process_variance=1e-5, measurement_variance=1e-1, initial_value=0):
        self.process_variance = process_variance
        self.measurement_variance = measurement_variance
        self.posteri_estimate = initial_value
        self.posteri_error_estimate = 1.0

    def update(self, measurement):
        priori_estimate = self.posteri_estimate
        priori_error_estimate = self.posteri_error_estimate + self.process_variance

        blending_factor = priori_error_estimate / (priori_error_estimate + self.measurement_variance)
        self.posteri_estimate = priori_estimate + blending_factor * (measurement - priori_estimate)
        self.posteri_error_estimate = (1 - blending_factor) * priori_error_estimate

        return self.posteri_estimate


class ATAIVolumePressureKalman(Strategy):
    # Parameters
    period = 55  # Main period for volume analysis
    volume_spike_threshold = 1.5
    kalman_process_var = 1e-5  # Process variance for Kalman filter
    kalman_measure_var = 1e-1  # Measurement variance for Kalman filter
    atr_period = 14
    sl_multiplier = 2
    tp_multiplier = 3
    stop_loss_pct = 0.03  # 3% stop loss
    take_profit_pct = 0.06  # 6% take profit

    def init(self):
        # Calculate directional volumes
        close = pd.Series(self.data.Close)
        open_price = pd.Series(self.data.Open)
        volume = pd.Series(self.data.Volume)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)

        # Directional volume calculation
        up_condition = close > open_price
        self.up_volume = pd.Series(np.where(up_condition, volume, 0), index=close.index)
        self.down_volume = pd.Series(np.where(~up_condition, volume, 0), index=close.index)

        # Volume moving averages
        self.up_volume_ma = self.up_volume.rolling(window=self.period).mean()
        self.down_volume_ma = self.down_volume.rolling(window=self.period).mean()
        self.total_volume_ma = volume.rolling(window=self.period).mean()

        # Volume ratio
        total_up = self.up_volume.rolling(window=self.period).sum()
        total_down = self.down_volume.rolling(window=self.period).sum()
        self.volume_ratio = total_up / (total_down + 1)

        # Apply Kalman filter to smooth volume ratio
        self.volume_ratio_kalman = self._apply_kalman_filter(
            self.volume_ratio,
            self.kalman_process_var,
            self.kalman_measure_var
        )

        # Volume spike detection
        self.volume_spike = volume / (self.total_volume_ma + 1)

        # Apply Kalman filter to smooth volume spikes
        self.volume_spike_kalman = self._apply_kalman_filter(
            self.volume_spike,
            self.kalman_process_var * 0.5,  # Less smoothing for spikes
            self.kalman_measure_var * 0.5
        )

        # Kalman filtered price for trend detection
        self.price_kalman = self._apply_kalman_filter(
            close,
            self.kalman_process_var * 10,
            self.kalman_measure_var * 10
        )

        # Calculate trend from Kalman filtered price
        self.kalman_trend = self.price_kalman.diff()
        self.kalman_momentum = self.kalman_trend.rolling(window=10).mean()

        # Volume-weighted Kalman price
        typical_price = (high + low + close) / 3
        vwap = (typical_price * volume).rolling(window=self.period).sum() / volume.rolling(window=self.period).sum()
        self.vwap_kalman = self._apply_kalman_filter(vwap, self.kalman_process_var, self.kalman_measure_var)

        # Track volume peaks
        self.volume_peaks = self._find_volume_peaks(volume, high, low, self.period)

        # Price structure with Kalman smoothed data
        self.higher_lows = self._detect_higher_lows_kalman(self.price_kalman, self.period)
        self.lower_highs = self._detect_lower_highs_kalman(self.price_kalman, self.period)

        # RSI for filtering
        self.rsi = ta.rsi(close, length=14)
        self.rsi_kalman = self._apply_kalman_filter(self.rsi, self.kalman_process_var, self.kalman_measure_var)

        # ATR for stops
        self.atr = ta.atr(high, low, close, length=self.atr_period)

        # Convert to numpy arrays
        self.up_volume = self.I(lambda: self.up_volume.values)
        self.down_volume = self.I(lambda: self.down_volume.values)
        self.up_volume_ma = self.I(lambda: self.up_volume_ma.values)
        self.down_volume_ma = self.I(lambda: self.down_volume_ma.values)
        self.volume_ratio = self.I(lambda: self.volume_ratio.values)
        self.volume_ratio_kalman = self.I(lambda: self.volume_ratio_kalman.values)
        self.volume_spike = self.I(lambda: self.volume_spike.values)
        self.volume_spike_kalman = self.I(lambda: self.volume_spike_kalman.values)
        self.price_kalman = self.I(lambda: self.price_kalman.values)
        self.kalman_trend = self.I(lambda: self.kalman_trend.values)
        self.kalman_momentum = self.I(lambda: self.kalman_momentum.values)
        self.vwap_kalman = self.I(lambda: self.vwap_kalman.values)
        self.higher_lows = self.I(lambda: self.higher_lows.values)
        self.lower_highs = self.I(lambda: self.lower_highs.values)
        self.rsi = self.I(lambda: self.rsi.values)
        self.rsi_kalman = self.I(lambda: self.rsi_kalman.values)
        self.atr = self.I(lambda: self.atr.values)

    def _apply_kalman_filter(self, series, process_var, measure_var):
        """Apply Kalman filter to a pandas Series"""
        filtered_values = []
        kf = KalmanFilter(process_variance=process_var, measurement_variance=measure_var)

        for value in series:
            if pd.isna(value):
                filtered_values.append(np.nan)
            else:
                filtered_values.append(kf.update(value))

        return pd.Series(filtered_values, index=series.index)

    def _find_volume_peaks(self, volume, high, low, period):
        """Find volume peaks for support/resistance"""
        peaks = pd.Series(0.0, index=volume.index)

        for i in range(period, len(volume)):
            window = volume.iloc[i-period:i]
            if volume.iloc[i] == window.max() and volume.iloc[i] > volume.rolling(period).mean().iloc[i] * 1.5:
                peaks.iloc[i] = (high.iloc[i] + low.iloc[i]) / 2

        return peaks

    def _detect_higher_lows_kalman(self, price_kalman, period):
        """Detect higher lows using Kalman filtered price"""
        higher_lows = pd.Series(False, index=price_kalman.index)

        for i in range(period, len(price_kalman)):
            recent_prices = price_kalman.iloc[i-period:i]
            if len(recent_prices) >= period:
                # Find local minima
                minima_indices = []
                for j in range(1, len(recent_prices) - 1):
                    if recent_prices.iloc[j] < recent_prices.iloc[j-1] and recent_prices.iloc[j] < recent_prices.iloc[j+1]:
                        minima_indices.append(j)

                if len(minima_indices) >= 2:
                    # Check if last minimum is higher than previous
                    higher_lows.iloc[i] = recent_prices.iloc[minima_indices[-1]] > recent_prices.iloc[minima_indices[-2]]

        return higher_lows

    def _detect_lower_highs_kalman(self, price_kalman, period):
        """Detect lower highs using Kalman filtered price"""
        lower_highs = pd.Series(False, index=price_kalman.index)

        for i in range(period, len(price_kalman)):
            recent_prices = price_kalman.iloc[i-period:i]
            if len(recent_prices) >= period:
                # Find local maxima
                maxima_indices = []
                for j in range(1, len(recent_prices) - 1):
                    if recent_prices.iloc[j] > recent_prices.iloc[j-1] and recent_prices.iloc[j] > recent_prices.iloc[j+1]:
                        maxima_indices.append(j)

                if len(maxima_indices) >= 2:
                    # Check if last maximum is lower than previous
                    lower_highs.iloc[i] = recent_prices.iloc[maxima_indices[-1]] < recent_prices.iloc[maxima_indices[-2]]

        return lower_highs

    def next(self):
        # Skip if insufficient data
        if len(self.data) < self.period + 1:
            return

        # Get current values (use Kalman filtered versions)
        current_spike = self.volume_spike_kalman[-1]
        current_ratio = self.volume_ratio_kalman[-1]
        current_trend = self.kalman_trend[-1]
        current_momentum = self.kalman_momentum[-1]
        current_rsi = self.rsi_kalman[-1]
        current_atr = self.atr[-1]

        # Check for NaN values
        if pd.isna(current_spike) or pd.isna(current_ratio) or pd.isna(current_trend) or pd.isna(current_atr):
            return

        # Price position relative to Kalman VWAP
        price_vs_vwap = self.data.Close[-1] / self.vwap_kalman[-1] if self.vwap_kalman[-1] != 0 else 1

        # Long signals with Kalman smoothing
        long_signal = (
            current_spike > self.volume_spike_threshold and
            self.up_volume[-1] > self.down_volume[-1] and
            current_ratio > 1.2 and
            current_trend > 0 and  # Kalman price trending up
            current_momentum > 0 and  # Momentum positive
            (self.higher_lows[-1] or price_vs_vwap > 1.005) and  # Price above VWAP or higher lows
            current_rsi < 70
        )

        # Strong long with Kalman confirmation
        strong_long_signal = (
            long_signal and
            self.kalman_trend[-1] > self.kalman_trend[-2] and  # Accelerating uptrend
            current_ratio > self.volume_ratio_kalman[-2] and  # Increasing volume pressure
            price_vs_vwap > 1.01  # Clearly above VWAP
        )

        # Short signals with Kalman smoothing
        short_signal = (
            current_spike > self.volume_spike_threshold and
            self.down_volume[-1] > self.up_volume[-1] and
            current_ratio < 0.8 and
            current_trend < 0 and  # Kalman price trending down
            current_momentum < 0 and  # Momentum negative
            (self.lower_highs[-1] or price_vs_vwap < 0.995) and  # Price below VWAP or lower highs
            current_rsi > 30
        )

        # Strong short with Kalman confirmation
        strong_short_signal = (
            short_signal and
            self.kalman_trend[-1] < self.kalman_trend[-2] and  # Accelerating downtrend
            current_ratio < self.volume_ratio_kalman[-2] and  # Decreasing volume pressure
            price_vs_vwap < 0.99  # Clearly below VWAP
        )

        # Position management
        if not self.position:
            if strong_long_signal:
                # Tighter stop for strong signals
                current_price = self.data.Close[-1]

                sl_price = current_price * (1 - self.stop_loss_pct)

                tp_price = current_price * (1 + self.take_profit_pct)

                self.buy(sl=sl_price, tp=tp_price)

            elif long_signal:
                current_price = self.data.Close[-1]

                sl_price = current_price * (1 - self.stop_loss_pct)

                tp_price = current_price * (1 + self.take_profit_pct)

                self.buy(sl=sl_price, tp=tp_price)

            elif strong_short_signal:
                # Tighter stop for strong signals
                current_price = self.data.Close[-1]

                sl_price = current_price * (1 + self.stop_loss_pct)

                tp_price = current_price * (1 - self.take_profit_pct)

                self.sell(sl=sl_price, tp=tp_price)

            elif short_signal:
                current_price = self.data.Close[-1]

                sl_price = current_price * (1 + self.stop_loss_pct)

                tp_price = current_price * (1 - self.take_profit_pct)

                self.sell(sl=sl_price, tp=tp_price)

        # Exit on Kalman trend reversal or volume exhaustion
        elif self.position.is_long:
            # Exit if Kalman shows reversal
            if (current_trend < 0 and current_momentum < 0) or \
               (self.down_volume[-1] > self.up_volume[-1] * 1.5 and current_ratio < 0.9) or \
               (price_vs_vwap < 0.99):  # Price fell below VWAP
                self.position.close()

        elif self.position.is_short:
            # Exit if Kalman shows reversal
            if (current_trend > 0 and current_momentum > 0) or \
               (self.up_volume[-1] > self.down_volume[-1] * 1.5 and current_ratio > 1.1) or \
               (price_vs_vwap > 1.01):  # Price rose above VWAP
                self.position.close()


def run_backtest(data_path, cash=10000, commission=0.002):
    """Run backtest on a single data file"""

    try:
        # Load data
        df = pd.read_csv(data_path)

        # Ensure required columns
        required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        if not all(col in df.columns for col in required_columns):
            print(f"Missing required columns in {data_path}")
            return None

        # Clean data
        df = df.dropna()
        if len(df) < 100:
            print(f"Not enough data in {data_path}")
            return None

        # Run backtest
        bt = Backtest(df, ATAIVolumePressureKalman, cash=cash, commission=commission)
        stats = bt.run()

        return stats

    except Exception as e:
        print(f"Error processing {data_path}: {e}")
        return None


if __name__ == "__main__":
    # Use multi_data_tester to test on all 25 data sources
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    print("\n🎯 Testing ATAI Volume Pressure Kalman Strategy")
    print("=" * 80)

    # Test on all available data sources
    results = test_on_all_data(
        ATAIVolumePressureKalman,
        'ATAIVolumePressureKalman',
        cash=10000,
        commission=0.002,
        verbose=True
    )

    if results is not None:
        print("\n📊 Strategy Summary:")
        print(f"✅ Tested on {len(results)} data sources")
        print(f"📈 Average Return: {results['Return_%'].mean():.2f}%")
        print(f"📊 Average Sharpe Ratio: {results['Sharpe'].mean():.3f}")
        print(f"📉 Average Max Drawdown: {results['Max_DD_%'].mean():.2f}%")
        print(f"🎯 Average Win Rate: {results['Win_Rate_%'].mean():.2f}%")

    print("\n🌙 ATAI Volume Pressure Kalman Strategy Testing Complete! 🚀")
