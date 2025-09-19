"""
Smart Money Breakout Channels - MACD + Kalman Filter Enhanced
Adds MACD for trend confirmation and Kalman filter for price smoothing
"""

from backtesting import Backtest, Strategy
import pandas as pd
import numpy as np
import pandas_ta as ta
from datetime import datetime
import os
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class SmartMoneyBreakoutMACD(Strategy):
    # Strategy parameters
    lookback = 20  # Lookback period for channel detection
    volatility_threshold = 0.5  # Threshold for volatility normalization
    channel_min_bars = 5  # Minimum bars for valid channel
    breakout_buffer = 0.001  # Buffer for breakout confirmation (0.1%)
    strong_close_pct = 0.5  # Percentage of candle body outside channel for strong breakout
    atr_period = 14
    stop_loss_atr = 2.0  # ATR multiplier for stop loss
    take_profit_atr = 3.0  # ATR multiplier for take profit
    position_size_pct = 0.95  # Position size as percentage of equity

    # Volume parameters
    volume_ma_period = 20
    volume_threshold = 1.2  # Volume must be X times average for valid breakout

    # MACD parameters
    macd_fast = 12
    macd_slow = 26
    macd_signal = 9

    # Kalman filter parameters
    kalman_gain = 0.01  # Kalman gain (lower = smoother)
    measurement_noise = 0.1  # Measurement noise estimate
    process_noise = 0.01  # Process noise estimate

    def init(self):
        # Price data
        self.high = self.data.High
        self.low = self.data.Low
        self.close = self.data.Close
        self.open = self.data.Open
        self.volume = self.data.Volume

        # Calculate ATR for position sizing and stops
        self.atr = self.I(ta.atr, pd.Series(self.data.High),
                         pd.Series(self.data.Low),
                         pd.Series(self.data.Close),
                         length=self.atr_period)

        # Calculate normalized volatility for channel detection
        self.hl_range = self.I(lambda: pd.Series(self.data.High - self.data.Low))
        self.volatility_ma = self.I(ta.sma, self.hl_range, length=self.lookback)
        self.normalized_volatility = self.I(lambda: self.hl_range / self.volatility_ma)

        # Volume analysis
        self.volume_ma = self.I(ta.sma, pd.Series(self.data.Volume), length=self.volume_ma_period)
        self.volume_ratio = self.I(lambda: pd.Series(self.data.Volume) / self.volume_ma)

        # Calculate MACD
        macd_result = ta.macd(pd.Series(self.data.Close),
                             fast=self.macd_fast,
                             slow=self.macd_slow,
                             signal=self.macd_signal)

        if macd_result is not None and len(macd_result.columns) >= 3:
            self.macd_line = self.I(lambda: macd_result.iloc[:, 0])
            self.macd_signal_line = self.I(lambda: macd_result.iloc[:, 1])
            self.macd_histogram = self.I(lambda: macd_result.iloc[:, 2])
        else:
            # Fallback if MACD calculation fails
            self.macd_line = self.I(lambda: pd.Series([0] * len(self.data)))
            self.macd_signal_line = self.I(lambda: pd.Series([0] * len(self.data)))
            self.macd_histogram = self.I(lambda: pd.Series([0] * len(self.data)))

        # Initialize Kalman filter for price smoothing
        self.kalman_price = self.I(self.apply_kalman_filter, pd.Series(self.data.Close))

        # Track channel state
        self.channel_top = np.nan
        self.channel_bottom = np.nan
        self.channel_start_idx = -1
        self.in_channel = False
        self.channel_volume_total = 0
        self.channel_up_volume = 0
        self.channel_down_volume = 0
        self.bars_in_channel = 0
        self.channel_macd_avg = 0

        # Trade management
        self.entry_price = 0
        self.stop_loss = 0
        self.take_profit = 0
        self.trade_type = None  # 'long' or 'short'

    def apply_kalman_filter(self, prices):
        """Apply Kalman filter to smooth price data"""
        filtered_prices = np.zeros_like(prices)

        # Initial state
        x = prices.iloc[0] if len(prices) > 0 else 0
        p = 1.0  # Initial error covariance

        for i in range(len(prices)):
            # Prediction step
            x_pred = x
            p_pred = p + self.process_noise

            # Update step
            k = p_pred / (p_pred + self.measurement_noise)  # Kalman gain
            x = x_pred + k * (prices.iloc[i] - x_pred)
            p = (1 - k) * p_pred

            filtered_prices[i] = x

        return pd.Series(filtered_prices, index=prices.index)

    def detect_channel_formation(self, idx):
        """Detect when a consolidation channel forms using Kalman-filtered prices"""
        if idx < self.lookback:
            return False

        # Check if volatility is below threshold (indicating consolidation)
        recent_volatility = self.normalized_volatility[idx]

        # Also check MACD histogram for low momentum (consolidation)
        recent_macd_hist = abs(self.macd_histogram[idx]) if idx < len(self.macd_histogram) else 0
        macd_threshold = np.std(self.macd_histogram[:idx]) * 0.5 if idx > 20 else 0.01

        if recent_volatility < self.volatility_threshold and recent_macd_hist < macd_threshold:
            if not self.in_channel:
                # Start new channel
                self.channel_start_idx = idx
                self.in_channel = True
                self.bars_in_channel = 0
                self.channel_volume_total = 0
                self.channel_up_volume = 0
                self.channel_down_volume = 0
                self.channel_macd_avg = self.macd_histogram[idx]

                # Calculate initial channel boundaries using Kalman-filtered prices
                lookback_start = max(0, idx - self.lookback)

                # Use both raw and filtered prices for channel bounds
                raw_high = max(self.data.High[lookback_start:idx+1])
                raw_low = min(self.data.Low[lookback_start:idx+1])
                kalman_high = max(self.kalman_price[lookback_start:idx+1])
                kalman_low = min(self.kalman_price[lookback_start:idx+1])

                # Blend raw and filtered bounds
                self.channel_top = 0.7 * raw_high + 0.3 * kalman_high
                self.channel_bottom = 0.7 * raw_low + 0.3 * kalman_low

                return True
        else:
            # Volatility increased or momentum picked up - end channel if it exists
            if self.in_channel and self.bars_in_channel >= self.channel_min_bars:
                self.in_channel = False
                return False

        return self.in_channel

    def update_channel_stats(self, idx):
        """Update channel statistics including volume and MACD"""
        if not self.in_channel:
            return

        self.bars_in_channel += 1

        # Update channel boundaries if needed
        if self.data.High[idx] <= self.channel_top and self.data.Low[idx] >= self.channel_bottom:
            # Price still within channel - update volume stats
            self.channel_volume_total += self.volume[idx]

            if self.close[idx] > self.open[idx]:
                self.channel_up_volume += self.volume[idx]
            else:
                self.channel_down_volume += self.volume[idx]

            # Update average MACD histogram
            self.channel_macd_avg = ((self.channel_macd_avg * (self.bars_in_channel - 1) +
                                     self.macd_histogram[idx]) / self.bars_in_channel)

    def check_macd_divergence(self, idx, lookback=15):
        """Check for MACD divergence patterns"""
        if idx < lookback:
            return None

        # Get recent price and MACD data
        recent_prices = self.kalman_price[idx-lookback:idx+1]
        recent_macd = self.macd_line[idx-lookback:idx+1]

        # Find local extremes
        price_max_idx = np.argmax(recent_prices)
        price_min_idx = np.argmin(recent_prices)
        macd_max_idx = np.argmax(recent_macd)
        macd_min_idx = np.argmin(recent_macd)

        # Bearish divergence: Price makes higher high, MACD makes lower high
        if price_max_idx > lookback // 2:  # Recent high
            if recent_prices.iloc[-1] > recent_prices.iloc[0] and recent_macd.iloc[-1] < recent_macd.iloc[macd_max_idx]:
                return 'bearish'

        # Bullish divergence: Price makes lower low, MACD makes higher low
        if price_min_idx > lookback // 2:  # Recent low
            if recent_prices.iloc[-1] < recent_prices.iloc[0] and recent_macd.iloc[-1] > recent_macd.iloc[macd_min_idx]:
                return 'bullish'

        return None

    def check_breakout(self, idx):
        """Check for channel breakout with MACD and Kalman filter confirmation"""
        if not self.in_channel or self.bars_in_channel < self.channel_min_bars:
            return None

        current_close = self.close[idx]
        current_high = self.high[idx]
        current_low = self.low[idx]
        current_open = self.open[idx]
        current_kalman = self.kalman_price[idx]
        current_macd = self.macd_line[idx]
        current_signal = self.macd_signal_line[idx]
        current_histogram = self.macd_histogram[idx]

        # Calculate candle body
        body_top = max(current_close, current_open)
        body_bottom = min(current_close, current_open)
        body_size = body_top - body_bottom

        # Calculate volume delta
        volume_delta = self.channel_up_volume - self.channel_down_volume
        volume_delta_ratio = volume_delta / max(self.channel_volume_total, 1)

        # Check for upward breakout
        if current_close > self.channel_top * (1 + self.breakout_buffer):
            # Check strong close requirement
            body_outside_top = max(0, body_bottom - self.channel_top)
            if body_size > 0:
                pct_outside = body_outside_top / body_size
                if pct_outside >= self.strong_close_pct:
                    # Enhanced confirmation with MACD and Kalman
                    volume_confirmed = self.volume_ratio[idx] >= self.volume_threshold

                    # MACD should be bullish
                    macd_bullish = (current_macd > current_signal and
                                  current_histogram > 0 and
                                  current_histogram > self.channel_macd_avg)

                    # Kalman price should confirm breakout
                    kalman_confirmed = current_kalman > self.channel_top

                    # Check for histogram momentum
                    histogram_momentum = (idx > 2 and
                                        self.macd_histogram[idx] > self.macd_histogram[idx-1] and
                                        self.macd_histogram[idx-1] > self.macd_histogram[idx-2])

                    delta_confirmed = volume_delta_ratio > 0.1  # Positive delta

                    # Check for divergence
                    divergence = self.check_macd_divergence(idx)
                    no_bearish_divergence = divergence != 'bearish'

                    if (volume_confirmed and macd_bullish and kalman_confirmed and
                        histogram_momentum and delta_confirmed and no_bearish_divergence):
                        self.in_channel = False
                        return 'long'

        # Check for downward breakout
        elif current_close < self.channel_bottom * (1 - self.breakout_buffer):
            # Check strong close requirement
            body_outside_bottom = max(0, self.channel_bottom - body_top)
            if body_size > 0:
                pct_outside = body_outside_bottom / body_size
                if pct_outside >= self.strong_close_pct:
                    # Enhanced confirmation with MACD and Kalman
                    volume_confirmed = self.volume_ratio[idx] >= self.volume_threshold

                    # MACD should be bearish
                    macd_bearish = (current_macd < current_signal and
                                  current_histogram < 0 and
                                  current_histogram < self.channel_macd_avg)

                    # Kalman price should confirm breakout
                    kalman_confirmed = current_kalman < self.channel_bottom

                    # Check for histogram momentum
                    histogram_momentum = (idx > 2 and
                                        self.macd_histogram[idx] < self.macd_histogram[idx-1] and
                                        self.macd_histogram[idx-1] < self.macd_histogram[idx-2])

                    delta_confirmed = volume_delta_ratio < -0.1  # Negative delta

                    # Check for divergence
                    divergence = self.check_macd_divergence(idx)
                    no_bullish_divergence = divergence != 'bullish'

                    if (volume_confirmed and macd_bearish and kalman_confirmed and
                        histogram_momentum and delta_confirmed and no_bullish_divergence):
                        self.in_channel = False
                        return 'short'

        return None

    def calculate_position_size(self):
        """Calculate position size based on MACD strength"""
        idx = len(self.data) - 1
        histogram_strength = abs(self.macd_histogram[idx]) if idx < len(self.macd_histogram) else 0

        # Get recent histogram average for comparison
        recent_avg = np.mean(np.abs(self.macd_histogram[max(0, idx-20):idx])) if idx > 20 else 0.01

        # Adjust position size based on MACD momentum strength
        if histogram_strength > recent_avg * 2:
            # Very strong momentum - full position
            return self.position_size_pct
        elif histogram_strength > recent_avg:
            # Moderate momentum - reduced position
            return self.position_size_pct * 0.75
        else:
            # Weak momentum - minimal position
            return self.position_size_pct * 0.5

    def next(self):
        idx = len(self.data) - 1
        if idx < max(self.lookback, self.macd_slow + self.macd_signal) + 1:
            return

        # Detect channel formation
        self.detect_channel_formation(idx)

        # Update channel statistics if in channel
        if self.in_channel:
            self.update_channel_stats(idx)

        # Check for existing position
        if self.position:
            # Manage existing trade with MACD-based exit conditions
            current_macd = self.macd_line[idx]
            current_signal = self.macd_signal_line[idx]
            current_histogram = self.macd_histogram[idx]

            if self.trade_type == 'long':
                # Check stop loss
                if self.close[idx] <= self.stop_loss:
                    self.position.close()
                    self.trade_type = None
                # Check take profit
                elif self.close[idx] >= self.take_profit:
                    self.position.close()
                    self.trade_type = None
                # Exit on MACD crossunder
                elif current_macd < current_signal and current_histogram < 0:
                    self.position.close()
                    self.trade_type = None
                # Check for bearish divergence exit
                elif self.check_macd_divergence(idx) == 'bearish':
                    self.position.close()
                    self.trade_type = None

            elif self.trade_type == 'short':
                # Check stop loss
                if self.close[idx] >= self.stop_loss:
                    self.position.close()
                    self.trade_type = None
                # Check take profit
                elif self.close[idx] <= self.take_profit:
                    self.position.close()
                    self.trade_type = None
                # Exit on MACD crossover
                elif current_macd > current_signal and current_histogram > 0:
                    self.position.close()
                    self.trade_type = None
                # Check for bullish divergence exit
                elif self.check_macd_divergence(idx) == 'bullish':
                    self.position.close()
                    self.trade_type = None

        else:
            # Look for new trade setup
            breakout_signal = self.check_breakout(idx)

            if breakout_signal == 'long':
                # Calculate position size and stops
                current_atr = self.atr[idx]
                if current_atr > 0:
                    size = self.calculate_position_size()
                    self.buy(size=size)

                    # Set trade parameters
                    self.entry_price = self.close[idx]
                    self.stop_loss = self.entry_price - (current_atr * self.stop_loss_atr)
                    self.take_profit = self.entry_price + (current_atr * self.take_profit_atr)
                    self.trade_type = 'long'

            elif breakout_signal == 'short':
                # Calculate position size and stops
                current_atr = self.atr[idx]
                if current_atr > 0:
                    size = self.calculate_position_size()
                    self.sell(size=size)

                    # Set trade parameters
                    self.entry_price = self.close[idx]
                    self.stop_loss = self.entry_price + (current_atr * self.stop_loss_atr)
                    self.take_profit = self.entry_price - (current_atr * self.take_profit_atr)
                    self.trade_type = 'short'


def run_backtest(data_path, cash=1000000, commission=0.001):
    """Run backtest on a single dataset"""
    try:
        # Load data
        df = pd.read_csv(data_path, parse_dates=['datetime'])
        df = df.set_index('datetime')

        # Ensure required columns exist
        required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        for col in required_columns:
            if col not in df.columns:
                print(f"Missing column {col} in {data_path}")
                return None

        # Clean data
        df = df.dropna()
        if len(df) < 100:
            print(f"Insufficient data in {data_path}")
            return None

        # Run backtest
        bt = Backtest(df, SmartMoneyBreakoutMACD, cash=cash, commission=commission)
        stats = bt.run()

        return stats

    except Exception as e:
        print(f"Error running backtest on {data_path}: {str(e)}")
        return None


def main():
    # Test with a single dataset first
    data_path = "/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv"

    if os.path.exists(data_path):
        print("Running Smart Money Breakout MACD+Kalman Strategy Backtest")
        print("=" * 50)

        stats = run_backtest(data_path)

        if stats is not None:
            print(f"\nResults for {os.path.basename(data_path)}:")
            print(stats)

            # Save results
            results_dir = "/Users/md/Dropbox/dev/github/moon-dev-trading-bots/backtests/smart_money_breakout/results"
            os.makedirs(results_dir, exist_ok=True)

            # Save summary stats
            summary = pd.DataFrame([{
                'Strategy': 'SmartMoneyBreakoutMACD',
                'Dataset': os.path.basename(data_path),
                'Return%': stats['Return [%]'],
                'Sharpe': stats['Sharpe Ratio'],
                'Max_Drawdown%': stats['Max. Drawdown [%]'],
                'Win_Rate%': stats['Win Rate [%]'] if 'Win Rate [%]' in stats else 0,
                'Trades': stats['# Trades'],
                'Exposure%': stats['Exposure Time [%]']
            }])

            summary.to_csv(f"{results_dir}/smart_money_macd_single_test.csv", index=False)
            print(f"\nResults saved to {results_dir}/smart_money_macd_single_test.csv")
    else:
        print(f"Data file not found: {data_path}")


if __name__ == "__main__":
    main()