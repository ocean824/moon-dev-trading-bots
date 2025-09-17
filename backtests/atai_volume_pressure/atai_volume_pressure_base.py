"""
ATAI Volume Pressure Analyzer - Base Strategy
Based on directional volume analysis and volume spike detection
"""

from backtesting import Backtest, Strategy
import pandas as pd
import numpy as np
import pandas_ta as ta
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

class ATAIVolumePressureBase(Strategy):
    # Parameters
    period = 55  # Main period for volume analysis (P in Pine Script)
    volume_spike_threshold = 1.5  # Threshold for volume spike detection
    atr_period = 14
    sl_multiplier = 2
    tp_multiplier = 3
    stop_loss_pct = 0.03  # 3% stop loss
    take_profit_pct = 0.06  # 6% take profit

    def init(self):
        # Calculate directional volumes
        # Up Volume = Volume when Close > Open (green candles)
        # Down Volume = Volume when Close <= Open (red candles)
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

        # Volume ratio (up vs down pressure)
        total_up = self.up_volume.rolling(window=self.period).sum()
        total_down = self.down_volume.rolling(window=self.period).sum()
        self.volume_ratio = total_up / (total_down + 1)  # Avoid division by zero

        # Volume spike detection
        self.volume_spike = volume / (self.total_volume_ma + 1)

        # Track top 3 volume peaks for support/resistance
        self.volume_peaks = self._find_volume_peaks(volume, high, low, self.period)

        # Price structure
        self.higher_lows = self._detect_higher_lows(low, self.period)
        self.lower_highs = self._detect_lower_highs(high, self.period)

        # RSI for overbought/oversold filtering
        self.rsi = ta.rsi(close, length=14)

        # ATR for stop loss and take profit
        self.atr = ta.atr(high, low, close, length=self.atr_period)

        # Convert to numpy arrays for indexing
        self.up_volume = self.I(lambda: self.up_volume.values)
        self.down_volume = self.I(lambda: self.down_volume.values)
        self.up_volume_ma = self.I(lambda: self.up_volume_ma.values)
        self.down_volume_ma = self.I(lambda: self.down_volume_ma.values)
        self.volume_ratio = self.I(lambda: self.volume_ratio.values)
        self.volume_spike = self.I(lambda: self.volume_spike.values)
        self.higher_lows = self.I(lambda: self.higher_lows.values)
        self.lower_highs = self.I(lambda: self.lower_highs.values)
        self.rsi = self.I(lambda: self.rsi.values)
        self.atr = self.I(lambda: self.atr.values)

    def _find_volume_peaks(self, volume, high, low, period):
        """Find top 3 volume peaks for potential support/resistance levels"""
        peaks = pd.Series(0.0, index=volume.index)

        # Rolling window to find local maxima
        for i in range(period, len(volume)):
            window = volume.iloc[i-period:i]
            if volume.iloc[i] == window.max() and volume.iloc[i] > volume.rolling(period).mean().iloc[i] * 1.5:
                # This is a significant volume peak
                peaks.iloc[i] = (high.iloc[i] + low.iloc[i]) / 2

        return peaks

    def _detect_higher_lows(self, low, period):
        """Detect if price is making higher lows"""
        higher_lows = pd.Series(False, index=low.index)

        for i in range(period, len(low)):
            recent_lows = []
            for j in range(i - period, i):
                if j > 0 and j < len(low) - 1:
                    if low.iloc[j] < low.iloc[j-1] and low.iloc[j] < low.iloc[j+1]:
                        recent_lows.append(low.iloc[j])

            if len(recent_lows) >= 2:
                higher_lows.iloc[i] = recent_lows[-1] > recent_lows[-2]

        return higher_lows

    def _detect_lower_highs(self, high, period):
        """Detect if price is making lower highs"""
        lower_highs = pd.Series(False, index=high.index)

        for i in range(period, len(high)):
            recent_highs = []
            for j in range(i - period, i):
                if j > 0 and j < len(high) - 1:
                    if high.iloc[j] > high.iloc[j-1] and high.iloc[j] > high.iloc[j+1]:
                        recent_highs.append(high.iloc[j])

            if len(recent_highs) >= 2:
                lower_highs.iloc[i] = recent_highs[-1] < recent_highs[-2]

        return lower_highs

    def next(self):
        # Skip if we don't have enough data
        if len(self.data) < self.period + 1:
            return

        # Get current values
        current_spike = self.volume_spike[-1]
        current_ratio = self.volume_ratio[-1]
        current_rsi = self.rsi[-1]
        current_atr = self.atr[-1]

        # Check for NaN values
        if pd.isna(current_spike) or pd.isna(current_ratio) or pd.isna(current_rsi) or pd.isna(current_atr):
            return

        # Long signals
        long_signal = (
            current_spike > self.volume_spike_threshold and  # Volume spike
            self.up_volume[-1] > self.down_volume[-1] and  # More up volume
            current_ratio > 1.2 and  # Strong up pressure
            self.higher_lows[-1] and  # Making higher lows
            current_rsi < 70  # Not overbought
        )

        # Short signals
        short_signal = (
            current_spike > self.volume_spike_threshold and  # Volume spike
            self.down_volume[-1] > self.up_volume[-1] and  # More down volume
            current_ratio < 0.8 and  # Strong down pressure
            self.lower_highs[-1] and  # Making lower highs
            current_rsi > 30  # Not oversold
        )

        # Position management
        if not self.position:
            if long_signal:
                # Enter long position with proper SL/TP placement
                current_price = self.data.Close[-1]
                # Use percentage-based stops as primary, ATR as fallback
                sl_price = current_price * (1 - self.stop_loss_pct)
                tp_price = current_price * (1 + self.take_profit_pct)
                self.buy(sl=sl_price, tp=tp_price)

            elif short_signal:
                # Enter short position with proper SL/TP placement
                current_price = self.data.Close[-1]
                # Use percentage-based stops as primary, ATR as fallback
                sl_price = current_price * (1 + self.stop_loss_pct)
                tp_price = current_price * (1 - self.take_profit_pct)
                self.sell(sl=sl_price, tp=tp_price)

        # Exit on volume exhaustion
        elif self.position.is_long:
            # Exit long if down volume dominates
            if self.down_volume[-1] > self.up_volume[-1] * 1.5 and current_ratio < 0.9:
                self.position.close()

        elif self.position.is_short:
            # Exit short if up volume dominates
            if self.up_volume[-1] > self.down_volume[-1] * 1.5 and current_ratio > 1.1:
                self.position.close()


def run_backtest(data_path, cash=10000, commission=0.002):
    """Run backtest on a single data file"""

    try:
        # Load data
        df = pd.read_csv(data_path)

        # Ensure required columns exist
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
        bt = Backtest(df, ATAIVolumePressureBase, cash=cash, commission=commission)
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

    print("\n🎯 Testing ATAI Volume Pressure Base Strategy")
    print("=" * 80)

    # Test on all available data sources
    results = test_on_all_data(
        ATAIVolumePressureBase,
        'ATAIVolumePressureBase',
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

    print("\n🌙 ATAI Volume Pressure Base Strategy Testing Complete! 🚀")
