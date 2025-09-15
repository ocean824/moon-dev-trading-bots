"""
Volume by Time with VWAP Strategy
Combines volume-by-time analysis with VWAP for price action context.
Uses VWAP as dynamic support/resistance and for trade direction confirmation.
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

class VolumeByTimeVWAP(Strategy):
    # Parameters
    lookback_days = 20  # Days to calculate historical volume average
    volume_threshold = 1.2  # Multiplier for volume spike detection - lowered for more signals
    use_median = False  # Use median instead of mean
    vwap_period = 20  # Period for VWAP calculation
    vwap_bands_std = 2.0  # Standard deviations for VWAP bands
    price_vwap_threshold = 0.002  # Price distance from VWAP (0.2%)
    stop_loss_pct = 0.02  # 2% stop loss
    take_profit_pct = 0.04  # 4% take profit

    def init(self):
        # Calculate VWAP and bands
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        close = pd.Series(self.data.Close)
        volume = pd.Series(self.data.Volume)

        # Calculate VWAP
        self.vwap = self.I(self.calculate_vwap, close, volume, high, low)

        # Calculate VWAP bands (standard deviation bands)
        self.vwap_upper = self.I(self.calculate_vwap_band,
                                 self.vwap, close, self.vwap_bands_std)
        self.vwap_lower = self.I(self.calculate_vwap_band,
                                 self.vwap, close, -self.vwap_bands_std)

        # Calculate volume by time metrics
        self.volume_ratio = self.I(self.calculate_volume_ratio,
                                   self.data.Volume,
                                   self.data.Close,
                                   self.data.Open)

        # Calculate price direction
        open_prices = pd.Series(self.data.Open)
        self.price_direction = self.I(lambda: (close > open_prices).astype(int) * 2 - 1)

        # Moving averages for additional context
        self.sma_20 = self.I(ta.sma, close, 20)
        self.sma_50 = self.I(ta.sma, close, 50)

        # Volume moving average
        self.volume_ma = self.I(ta.sma, volume, 20)

        # ATR for dynamic stops
        self.atr = self.I(ta.atr, high, low, close, 14)

        # RSI for overbought/oversold conditions
        self.rsi = self.I(ta.rsi, close, 14)

    def calculate_vwap(self, close, volume, high, low):
        """Calculate Volume Weighted Average Price"""
        typical_price = (high + low + close) / 3
        cumulative_tpv = (typical_price * volume).cumsum()
        cumulative_volume = volume.cumsum()

        # Reset VWAP daily (simple rolling window approach for daily data)
        vwap_values = []
        window = self.vwap_period

        for i in range(len(close)):
            if i < window:
                # Simple VWAP for initial period
                if cumulative_volume.iloc[i] > 0:
                    vwap_values.append(cumulative_tpv.iloc[i] / cumulative_volume.iloc[i])
                else:
                    vwap_values.append(close.iloc[i])
            else:
                # Rolling VWAP
                period_tpv = (typical_price.iloc[i-window+1:i+1] *
                             volume.iloc[i-window+1:i+1]).sum()
                period_volume = volume.iloc[i-window+1:i+1].sum()
                if period_volume > 0:
                    vwap_values.append(period_tpv / period_volume)
                else:
                    vwap_values.append(close.iloc[i])

        return np.array(vwap_values)

    def calculate_vwap_band(self, vwap, close, std_multiplier):
        """Calculate VWAP bands based on standard deviation"""
        close_series = pd.Series(close)
        vwap_series = pd.Series(vwap)

        # Calculate rolling standard deviation
        std_dev = close_series.rolling(window=self.vwap_period).std()
        band = vwap_series + (std_multiplier * std_dev)

        return band.fillna(method='bfill').values

    def calculate_volume_ratio(self, volume, close, open_price):
        """Calculate the ratio of current volume to historical average/median"""
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
        current_price = self.data.Close[-1]
        current_vwap = self.vwap[-1]
        current_vwap_upper = self.vwap_upper[-1]
        current_vwap_lower = self.vwap_lower[-1]
        current_rsi = self.rsi[-1]

        # Calculate price position relative to VWAP
        price_to_vwap_pct = (current_price - current_vwap) / current_vwap

        # Check if we have a position
        if self.position:
            # Dynamic trailing stop using VWAP bands
            if self.position.is_long:
                # Use VWAP or lower band as trailing stop
                trailing_stop = max(current_vwap_lower,
                                   self.data.Close[-1] - (2 * self.atr[-1]))
                if hasattr(self.position, 'sl'):
                    self.position.sl = max(self.position.sl, trailing_stop)

                # Exit if price crosses below VWAP with volume
                if (current_price < current_vwap and
                    self.data.Volume[-1] > self.volume_ma[-1]):
                    self.position.close()

            elif self.position.is_short:
                # Use VWAP or upper band as trailing stop
                trailing_stop = min(current_vwap_upper,
                                   self.data.Close[-1] + (2 * self.atr[-1]))
                if hasattr(self.position, 'sl'):
                    self.position.sl = min(self.position.sl, trailing_stop)

                # Exit if price crosses above VWAP with volume
                if (current_price > current_vwap and
                    self.data.Volume[-1] > self.volume_ma[-1]):
                    self.position.close()
            return

        # Long signal: Volume spike + Price bouncing off VWAP/lower band
        long_conditions = [
            current_volume_ratio > self.volume_threshold,  # Volume spike
            price_dir > 0,  # Bullish candle
            current_price > current_vwap,  # Price above VWAP
            abs(price_to_vwap_pct) < 0.05,  # Price not too far from VWAP (5%)
            current_rsi < 70,  # Not overbought
            self.data.Close[-1] > self.sma_20[-1]  # Above short-term trend
        ]

        # Alternative long: Bounce from lower band with volume
        alt_long_conditions = [
            current_volume_ratio > self.volume_threshold * 0.8,  # Slightly lower volume threshold
            current_price > current_vwap_lower,  # Bounced from lower band
            current_price < current_vwap,  # Still below VWAP (room to move up)
            price_dir > 0,  # Bullish reversal candle
            current_rsi < 40  # Oversold bounce
        ]

        if all(long_conditions) or all(alt_long_conditions):
            # Dynamic stop loss and take profit for long positions
            stop_loss = min(current_vwap_lower,
                          current_price * (1 - self.stop_loss_pct))
            take_profit = max(current_price * (1 + self.take_profit_pct),
                            min(current_vwap_upper, current_price + (3 * self.atr[-1])))

            # Ensure stop loss is below current price
            stop_loss = min(stop_loss, current_price * 0.98)
            # Ensure take profit is above current price
            take_profit = max(take_profit, current_price * 1.02)

            self.buy(sl=stop_loss, tp=take_profit)

        # Short signal: Volume spike + Price rejected at VWAP/upper band
        short_conditions = [
            current_volume_ratio > self.volume_threshold,  # Volume spike
            price_dir < 0,  # Bearish candle
            current_price < current_vwap,  # Price below VWAP
            abs(price_to_vwap_pct) < 0.05,  # Price not too far from VWAP
            current_rsi > 30,  # Not oversold
            self.data.Close[-1] < self.sma_20[-1]  # Below short-term trend
        ]

        # Alternative short: Rejection from upper band with volume
        alt_short_conditions = [
            current_volume_ratio > self.volume_threshold * 0.8,  # Slightly lower volume threshold
            current_price < current_vwap_upper,  # Rejected from upper band
            current_price > current_vwap,  # Still above VWAP (room to move down)
            price_dir < 0,  # Bearish reversal candle
            current_rsi > 60  # Overbought rejection
        ]

        if all(short_conditions) or all(alt_short_conditions):
            # Dynamic stop loss and take profit for short positions
            stop_loss = max(current_vwap_upper,
                          current_price * (1 + self.stop_loss_pct))
            take_profit = min(current_price * (1 - self.take_profit_pct),
                            max(current_vwap_lower, current_price - (3 * self.atr[-1])))

            # Ensure stop loss is above current price for shorts
            stop_loss = max(stop_loss, current_price * 1.02)
            # Ensure take profit is below current price for shorts
            take_profit = min(take_profit, current_price * 0.98)

            self.sell(sl=stop_loss, tp=take_profit)


def run_backtest(data, strategy_class=VolumeByTimeVWAP, cash=100000, commission=0.002):
    """Run backtest with the given data and strategy"""
    bt = Backtest(data, strategy_class, cash=cash, commission=commission)
    stats = bt.run()
    return stats, bt


if __name__ == "__main__":
    print("\n🎯 Testing Volume by Time + VWAP Strategy")
    print("=" * 80)

    # Test on all available data sources
    results = test_on_all_data(
        VolumeByTimeVWAP,
        'VolumeByTimeVWAP',
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

    print("\n🌙 Volume by Time + VWAP Strategy Testing Complete! 🚀")
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
    print("\nRunning Volume by Time with VWAP Strategy backtest...")
    stats, bt = run_backtest(data)

    # Print results
    print("\n" + "="*60)
    print("BACKTEST RESULTS - Volume by Time with VWAP")
    print("="*60)
    print(stats)
    print("="*60)

    # Show plot
    bt.plot()