"""
Volume by Time with ADX Filter Strategy
Combines volume-by-time analysis with ADX trend strength confirmation.
Only takes trades when both volume spikes occur AND trend is strong (ADX > threshold).
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

class VolumeByTimeADX(Strategy):
    # Parameters
    lookback_days = 20  # Days to calculate historical volume average
    volume_threshold = 1.2  # Multiplier for volume spike detection - lowered for more signals
    use_median = False  # Use median instead of mean
    adx_period = 14  # ADX period
    adx_threshold = 25  # Minimum ADX for trend strength
    di_threshold = 5  # Minimum DI difference for direction confirmation
    stop_loss_pct = 0.02  # 2% stop loss
    take_profit_pct = 0.04  # 4% take profit

    def init(self):
        # Calculate ADX and directional indicators
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        close = pd.Series(self.data.Close)

        # Calculate ADX using pandas_ta
        adx_result = ta.adx(high, low, close, length=self.adx_period)
        if adx_result is not None and len(adx_result.columns) >= 3:
            self.adx = self.I(lambda: adx_result.iloc[:, 0].values)  # ADX
            self.plus_di = self.I(lambda: adx_result.iloc[:, 1].values)  # +DI
            self.minus_di = self.I(lambda: adx_result.iloc[:, 2].values)  # -DI
        else:
            # Fallback to manual calculation if pandas_ta fails
            self.adx = self.I(lambda: np.full(len(close), 25))
            self.plus_di = self.I(lambda: np.full(len(close), 50))
            self.minus_di = self.I(lambda: np.full(len(close), 50))

        # Calculate volume by time metrics
        self.volume_ratio = self.I(self.calculate_volume_ratio,
                                   self.data.Volume,
                                   self.data.Close,
                                   self.data.Open)

        # Calculate price direction
        close_prices = pd.Series(self.data.Close)
        open_prices = pd.Series(self.data.Open)
        self.price_direction = self.I(lambda: (close_prices > open_prices).astype(int) * 2 - 1)

        # Moving averages for trend context
        self.sma_20 = self.I(ta.sma, close, 20)
        self.sma_50 = self.I(ta.sma, close, 50)

        # Volume moving average
        self.volume_ma = self.I(ta.sma, pd.Series(self.data.Volume), 20)

        # ATR for dynamic stop loss
        self.atr = self.I(ta.atr, high, low, close, 14)

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
        if len(self.data) < self.lookback_days * 2:
            return

        # Get current values
        current_volume_ratio = self.volume_ratio[-1]
        price_dir = self.price_direction[-1]
        current_adx = self.adx[-1]
        current_plus_di = self.plus_di[-1]
        current_minus_di = self.minus_di[-1]

        # Check if we have a position
        if self.position:
            # Exit conditions based on trend change
            if self.position.is_long:
                # Exit if trend weakens or reverses
                if current_adx < 20 or current_minus_di > current_plus_di or self.data.Close[-1] < self.sma_20[-1] * 0.98:
                    self.position.close()

            elif self.position.is_short:
                # Exit if trend weakens or reverses
                if current_adx < 20 or current_plus_di > current_minus_di or self.data.Close[-1] > self.sma_20[-1] * 1.02:
                    self.position.close()
            return

        # Check ADX for trend strength
        strong_trend = current_adx > self.adx_threshold

        # Calculate DI difference for direction confirmation
        di_diff = current_plus_di - current_minus_di

        # Long signal: Volume spike + Bullish price + Strong uptrend (ADX + DI)
        if (current_volume_ratio > self.volume_threshold and
            price_dir > 0 and  # Bullish candle
            self.data.Close[-1] > self.sma_20[-1] and  # Above short-term trend
            strong_trend and  # ADX confirms strong trend
            di_diff > self.di_threshold):  # +DI > -DI confirms uptrend

            self.buy()

        # Short signal: Volume spike + Bearish price + Strong downtrend (ADX + DI)
        elif (current_volume_ratio > self.volume_threshold and
              price_dir < 0 and  # Bearish candle
              self.data.Close[-1] < self.sma_20[-1] and  # Below short-term trend
              strong_trend and  # ADX confirms strong trend
              di_diff < -self.di_threshold):  # -DI > +DI confirms downtrend

            self.sell()


def run_backtest(data, strategy_class=VolumeByTimeADX, cash=100000, commission=0.002):
    """Run backtest with the given data and strategy"""
    bt = Backtest(data, strategy_class, cash=cash, commission=commission)
    stats = bt.run()
    return stats, bt


if __name__ == "__main__":
    print("\n🎯 Testing Volume by Time + ADX Strategy")
    print("=" * 80)

    # Test on all available data sources
    results = test_on_all_data(
        VolumeByTimeADX,
        'VolumeByTimeADX',
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

    print("\n🌙 Volume by Time + ADX Strategy Testing Complete! 🚀")
    import sys; sys.exit()

# OLD CODE BELOW - REPLACED
    # Load sample data for testing
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

    # Try to load data
    try:
        # Try Coinbase data first
        data_path = "/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1d-100wks-data.csv"
        if os.path.exists(data_path):
            data = pd.read_csv(data_path, index_col=0, parse_dates=True)
            print(f"Loaded data from {data_path}")
            print(f"Data shape: {data.shape}")
            print(f"Date range: {data.index[0]} to {data.index[-1]}")
        else:
            # Try another Coinbase file
            data_path = "/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-100wks-data.csv"
            data = pd.read_csv(data_path, index_col=0, parse_dates=True)
            print(f"Loaded data from {data_path}")
    except Exception as e:
        print(f"Error loading data: {e}")
        print("Please ensure data files are available in the /data directory")
        sys.exit(1)

    # Ensure required columns and rename if needed
    if 'open' in data.columns:
        data = data.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low',
                                   'close': 'Close', 'volume': 'Volume'})

    required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
    for col in required_columns:
        if col not in data.columns:
            print(f"Missing required column: {col}")
            sys.exit(1)

    # Run backtest
    print("\nRunning Volume by Time with ADX Strategy backtest...")
    stats, bt = run_backtest(data)

    # Print results
    print("\n" + "="*60)
    print("BACKTEST RESULTS - Volume by Time with ADX Filter")
    print("="*60)
    print(stats)
    print("="*60)

    # Show plot
    bt.plot()