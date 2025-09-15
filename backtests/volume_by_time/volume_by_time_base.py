"""
Volume by Time Base Strategy
Analyzes volume patterns at specific times of day, comparing current volume to historical averages.
Enters trades when volume significantly exceeds historical norms at that time.
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
from datetime import datetime, time
import warnings
warnings.filterwarnings('ignore')
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from multi_data_tester import test_on_all_data

class VolumeByTimeBase(Strategy):
    # Parameters
    lookback_days = 20  # Days to calculate historical volume average
    volume_threshold = 1.1  # Multiplier for volume spike detection (1.1x average) - lowered for more signals
    use_median = False  # Use median instead of mean for historical calculation
    stop_loss_pct = 0.03  # 3% stop loss
    take_profit_pct = 0.06  # 6% take profit

    def init(self):
        # Extract time from index for volume analysis
        self.df = pd.DataFrame(self.data.Close)
        self.df['Volume'] = self.data.Volume
        self.df['High'] = self.data.High
        self.df['Low'] = self.data.Low
        self.df['Open'] = self.data.Open

        # Calculate volume by time metrics
        self.volume_ratio = self.I(self.calculate_volume_ratio,
                                   self.data.Volume,
                                   self.data.Close,
                                   self.data.Open)

        # Calculate price direction for bi-directional volume
        close_prices = pd.Series(self.data.Close)
        open_prices = pd.Series(self.data.Open)
        self.price_direction = self.I(lambda: (close_prices > open_prices).astype(int) * 2 - 1)

        # Simple moving averages for trend context
        self.sma_20 = self.I(ta.sma, pd.Series(self.data.Close), 20)
        self.sma_50 = self.I(ta.sma, pd.Series(self.data.Close), 50)

        # Volume moving average for additional context
        self.volume_ma = self.I(ta.sma, pd.Series(self.data.Volume), 20)

    def calculate_volume_ratio(self, volume, close, open_price):
        """
        Calculate the ratio of current volume to historical average/median
        For daily data, we'll use a rolling window approach
        """
        volume_series = pd.Series(volume)

        # Calculate rolling volume average/median
        volume_ratios = []

        for i in range(len(volume_series)):
            if i < self.lookback_days:
                volume_ratios.append(1.0)
                continue

            # Get historical volumes for lookback period
            historical_volumes = volume_series[max(0, i-self.lookback_days):i]

            if len(historical_volumes) > 0:
                if self.use_median:
                    historical_avg = historical_volumes.median()
                else:
                    historical_avg = historical_volumes.mean()

                if historical_avg > 0:
                    ratio = volume_series.iloc[i] / historical_avg
                else:
                    ratio = 1.0
            else:
                ratio = 1.0

            volume_ratios.append(ratio)

        return np.array(volume_ratios)

    def next(self):
        # Skip if not enough data
        if len(self.data) < self.lookback_days + 20:  # Need lookback + SMA period
            return

        # Check that we have valid indicators
        if pd.isna(self.sma_20[-1]) or pd.isna(self.volume_ratio[-1]):
            return

        # Get current values
        current_volume_ratio = self.volume_ratio[-1]
        price_dir = self.price_direction[-1]

        # Check if we have a position
        if self.position:
            # Simple exit conditions without accessing sl/tp attributes
            if self.position.is_long:
                # Exit on bearish reversal or below SMA
                if price_dir < 0 or self.data.Close[-1] < self.sma_20[-1] * 0.98:
                    self.position.close()
            elif self.position.is_short:
                # Exit on bullish reversal or above SMA
                if price_dir > 0 or self.data.Close[-1] > self.sma_20[-1] * 1.02:
                    self.position.close()
            return

        # Trading signals based on volume spikes at specific times
        # Long signal: Volume spike with bullish price action
        if (current_volume_ratio > self.volume_threshold and
            price_dir > 0 and  # Bullish candle
            self.data.Close[-1] > self.sma_20[-1]):  # Above short-term trend

            self.buy()

        # Short signal: Volume spike with bearish price action
        elif (current_volume_ratio > self.volume_threshold and
              price_dir < 0 and  # Bearish candle
              self.data.Close[-1] < self.sma_20[-1]):  # Below short-term trend

            self.sell()


def run_backtest(data, strategy_class=VolumeByTimeBase, cash=100000, commission=0.002):
    """Run backtest with the given data and strategy"""
    bt = Backtest(data, strategy_class, cash=cash, commission=commission)
    stats = bt.run()
    return stats, bt


if __name__ == "__main__":
    print("\n🎯 Testing Volume by Time Base Strategy")
    print("=" * 80)

    # Test on all available data sources
    results = test_on_all_data(
        VolumeByTimeBase,
        'VolumeByTimeBase',
        cash=100000,
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

    print("\n🌙 Volume by Time Base Strategy Testing Complete! 🚀")