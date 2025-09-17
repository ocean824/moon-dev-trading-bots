"""
ATAI Volume Pressure Analyzer - MFI Strategy
Adds Money Flow Index for additional volume confirmation
"""

from backtesting import Backtest, Strategy
import pandas as pd
import numpy as np
import pandas_ta as ta
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

class ATAIVolumePressureMFI(Strategy):
    # Parameters
    period = 55  # Main period for volume analysis
    volume_spike_threshold = 1.5
    mfi_period = 14
    mfi_long_threshold = 50  # MFI > 50 for longs
    mfi_short_threshold = 50  # MFI < 50 for shorts
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

        # Volume ratio (up vs down pressure)
        total_up = self.up_volume.rolling(window=self.period).sum()
        total_down = self.down_volume.rolling(window=self.period).sum()
        self.volume_ratio = total_up / (total_down + 1)

        # Volume spike detection
        self.volume_spike = volume / (self.total_volume_ma + 1)

        # Money Flow Index (MFI)
        self.mfi = ta.mfi(high, low, close, volume, length=self.mfi_period)

        # Volume-weighted momentum
        typical_price = (high + low + close) / 3
        raw_money_flow = typical_price * volume
        self.money_flow_ratio = raw_money_flow.rolling(window=self.period).mean()

        # Track volume peaks
        self.volume_peaks = self._find_volume_peaks(volume, high, low, self.period)

        # Price structure
        self.higher_lows = self._detect_higher_lows(low, self.period)
        self.lower_highs = self._detect_lower_highs(high, self.period)

        # RSI for additional filtering
        self.rsi = ta.rsi(close, length=14)

        # ATR for stops
        self.atr = ta.atr(high, low, close, length=self.atr_period)

        # Convert to numpy arrays
        self.up_volume = self.I(lambda: self.up_volume.values)
        self.down_volume = self.I(lambda: self.down_volume.values)
        self.up_volume_ma = self.I(lambda: self.up_volume_ma.values)
        self.down_volume_ma = self.I(lambda: self.down_volume_ma.values)
        self.volume_ratio = self.I(lambda: self.volume_ratio.values)
        self.volume_spike = self.I(lambda: self.volume_spike.values)
        self.mfi = self.I(lambda: self.mfi.values)
        self.money_flow_ratio = self.I(lambda: self.money_flow_ratio.values)
        self.higher_lows = self.I(lambda: self.higher_lows.values)
        self.lower_highs = self.I(lambda: self.lower_highs.values)
        self.rsi = self.I(lambda: self.rsi.values)
        self.atr = self.I(lambda: self.atr.values)

    def _find_volume_peaks(self, volume, high, low, period):
        """Find volume peaks for support/resistance"""
        peaks = pd.Series(0.0, index=volume.index)

        for i in range(period, len(volume)):
            window = volume.iloc[i-period:i]
            if volume.iloc[i] == window.max() and volume.iloc[i] > volume.rolling(period).mean().iloc[i] * 1.5:
                peaks.iloc[i] = (high.iloc[i] + low.iloc[i]) / 2

        return peaks

    def _detect_higher_lows(self, low, period):
        """Detect higher lows pattern"""
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
        """Detect lower highs pattern"""
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
        # Skip if insufficient data
        if len(self.data) < self.period + 1:
            return

        # Get current values
        current_spike = self.volume_spike[-1]
        current_ratio = self.volume_ratio[-1]
        current_mfi = self.mfi[-1]
        current_rsi = self.rsi[-1]
        current_atr = self.atr[-1]

        # Check for NaN values
        if pd.isna(current_spike) or pd.isna(current_ratio) or pd.isna(current_mfi) or pd.isna(current_atr):
            return

        # MFI divergence detection
        mfi_bullish_div = current_mfi < 30 and self.higher_lows[-1]
        mfi_bearish_div = current_mfi > 70 and self.lower_highs[-1]

        # Long signals with MFI confirmation
        long_signal = (
            current_spike > self.volume_spike_threshold and
            self.up_volume[-1] > self.down_volume[-1] and
            current_ratio > 1.2 and
            current_mfi > self.mfi_long_threshold and  # MFI confirmation
            (self.higher_lows[-1] or mfi_bullish_div) and
            current_rsi < 70
        )

        # Enhanced long signal with strong MFI
        strong_long_signal = (
            long_signal and
            current_mfi > 60 and  # Strong money flow
            self.mfi[-1] > self.mfi[-2]  # MFI trending up
        )

        # Short signals with MFI confirmation
        short_signal = (
            current_spike > self.volume_spike_threshold and
            self.down_volume[-1] > self.up_volume[-1] and
            current_ratio < 0.8 and
            current_mfi < self.mfi_short_threshold and  # MFI confirmation
            (self.lower_highs[-1] or mfi_bearish_div) and
            current_rsi > 30
        )

        # Enhanced short signal with weak MFI
        strong_short_signal = (
            short_signal and
            current_mfi < 40 and  # Weak money flow
            self.mfi[-1] < self.mfi[-2]  # MFI trending down
        )

        # Position management
        if not self.position:
            # Prioritize stronger signals
            if strong_long_signal:
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
                current_price = self.data.Close[-1]

                sl_price = current_price * (1 + self.stop_loss_pct)

                tp_price = current_price * (1 - self.take_profit_pct)

                self.sell(sl=sl_price, tp=tp_price)

            elif short_signal:
                current_price = self.data.Close[-1]

                sl_price = current_price * (1 + self.stop_loss_pct)

                tp_price = current_price * (1 - self.take_profit_pct)

                self.sell(sl=sl_price, tp=tp_price)

        # Exit on MFI divergence or volume exhaustion
        elif self.position.is_long:
            # Exit if MFI shows selling pressure
            if (current_mfi < 45 and self.mfi[-1] < self.mfi[-2]) or \
               (self.down_volume[-1] > self.up_volume[-1] * 1.5 and current_ratio < 0.9):
                self.position.close()

        elif self.position.is_short:
            # Exit if MFI shows buying pressure
            if (current_mfi > 55 and self.mfi[-1] > self.mfi[-2]) or \
               (self.up_volume[-1] > self.down_volume[-1] * 1.5 and current_ratio > 1.1):
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
        bt = Backtest(df, ATAIVolumePressureMFI, cash=cash, commission=commission)
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

    print("\n🎯 Testing ATAI Volume Pressure MFI Strategy")
    print("=" * 80)

    # Test on all available data sources
    results = test_on_all_data(
        ATAIVolumePressureMFI,
        'ATAIVolumePressureMFI',
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

    print("\n🌙 ATAI Volume Pressure MFI Strategy Testing Complete! 🚀")
