"""
Volume by Time with MFI Strategy
Combines volume-by-time analysis with Money Flow Index for volume/price confirmation.
MFI helps confirm whether volume spikes are accompanied by smart money flow.
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

class VolumeByTimeMFI(Strategy):
    # Parameters
    lookback_days = 20  # Days to calculate historical volume average
    volume_threshold = 1.2  # Multiplier for volume spike detection - lowered for more signals
    use_median = False  # Use median instead of mean
    mfi_period = 14  # Money Flow Index period
    mfi_oversold = 30  # MFI oversold level
    mfi_overbought = 70  # MFI overbought level
    mfi_divergence_lookback = 10  # Bars to check for divergence
    stop_loss_pct = 0.02  # 2% stop loss
    take_profit_pct = 0.04  # 4% take profit

    def init(self):
        # Calculate MFI (Money Flow Index)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        close = pd.Series(self.data.Close)
        volume = pd.Series(self.data.Volume)

        # Calculate MFI using pandas_ta
        self.mfi = self.I(ta.mfi, high, low, close, volume, self.mfi_period)

        # Calculate volume by time metrics
        self.volume_ratio = self.I(self.calculate_volume_ratio,
                                   self.data.Volume,
                                   self.data.Close,
                                   self.data.Open)

        # Calculate price direction
        open_prices = pd.Series(self.data.Open)
        self.price_direction = self.I(lambda: (close > open_prices).astype(int) * 2 - 1)

        # Moving averages for trend context
        self.sma_20 = self.I(ta.sma, close, 20)
        self.sma_50 = self.I(ta.sma, close, 50)

        # Volume moving average
        self.volume_ma = self.I(ta.sma, volume, 20)

        # ATR for dynamic stops
        self.atr = self.I(ta.atr, high, low, close, 14)

        # RSI for additional confirmation
        self.rsi = self.I(ta.rsi, close, 14)

        # Calculate money flow ratio components
        self.money_flow = self.I(self.calculate_money_flow, high, low, close, volume)

        # Bollinger Bands for volatility context
        bb_result = ta.bbands(close, length=20, std=2)
        if bb_result is not None and len(bb_result.columns) >= 3:
            self.bb_upper = self.I(lambda: bb_result.iloc[:, 0].values)
            self.bb_middle = self.I(lambda: bb_result.iloc[:, 1].values)
            self.bb_lower = self.I(lambda: bb_result.iloc[:, 2].values)
        else:
            self.bb_upper = self.I(lambda: self.sma_20 * 1.02)
            self.bb_middle = self.I(lambda: self.sma_20)
            self.bb_lower = self.I(lambda: self.sma_20 * 0.98)

    def calculate_money_flow(self, high, low, close, volume):
        """Calculate raw money flow for additional analysis"""
        typical_price = (high + low + close) / 3
        money_flow = typical_price * volume

        # Calculate directional money flow
        close_series = pd.Series(close)
        prev_close = close_series.shift(1)
        direction = np.where(close_series > prev_close, 1, -1)
        directional_money_flow = money_flow * direction

        return directional_money_flow.fillna(0).values

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

    def check_mfi_divergence(self, lookback=10):
        """Check for MFI divergence with price"""
        if len(self.data) < lookback + 1:
            return False, False

        # Get recent price and MFI data
        recent_prices = self.data.Close[-lookback:]
        recent_mfi = self.mfi[-lookback:]

        # Find local extremes
        price_high_idx = np.argmax(recent_prices)
        price_low_idx = np.argmin(recent_prices)
        mfi_high_idx = np.argmax(recent_mfi)
        mfi_low_idx = np.argmin(recent_mfi)

        # Bullish divergence: Price makes lower low, MFI makes higher low
        bullish_div = (price_low_idx > lookback/2 and
                      recent_prices[-1] < recent_prices[price_low_idx] and
                      recent_mfi[-1] > recent_mfi[mfi_low_idx])

        # Bearish divergence: Price makes higher high, MFI makes lower high
        bearish_div = (price_high_idx > lookback/2 and
                      recent_prices[-1] > recent_prices[price_high_idx] and
                      recent_mfi[-1] < recent_mfi[mfi_high_idx])

        return bullish_div, bearish_div

    def next(self):
        # Skip if not enough data
        if len(self.data) < max(self.lookback_days * 2, self.mfi_period + 10):
            return

        # Get current values
        current_volume_ratio = self.volume_ratio[-1]
        price_dir = self.price_direction[-1]
        current_mfi = self.mfi[-1]
        current_rsi = self.rsi[-1]
        current_money_flow = self.money_flow[-1]
        current_price = self.data.Close[-1]

        # Check for MFI divergences
        bullish_div, bearish_div = self.check_mfi_divergence(self.mfi_divergence_lookback)

        # Check if we have a position
        if self.position:
            # Dynamic exit based on MFI
            if self.position.is_long:
                # Exit long if MFI becomes overbought or bearish divergence
                if current_mfi > 80 or bearish_div:
                    self.position.close()
                    return

                # Trailing stop
                trailing_stop = self.data.Close[-1] - (2 * self.atr[-1])
                if hasattr(self.position, 'sl'):
                    self.position.sl = max(self.position.sl, trailing_stop)

            elif self.position.is_short:
                # Exit short if MFI becomes oversold or bullish divergence
                if current_mfi < 20 or bullish_div:
                    self.position.close()
                    return

                # Trailing stop
                trailing_stop = self.data.Close[-1] + (2 * self.atr[-1])
                if hasattr(self.position, 'sl'):
                    self.position.sl = min(self.position.sl, trailing_stop)
            return

        # Long signal: Volume spike + MFI confirmation + Positive money flow
        long_conditions = [
            current_volume_ratio > self.volume_threshold,  # Volume spike at this time
            price_dir > 0,  # Bullish candle
            current_mfi < self.mfi_overbought,  # Not overbought
            current_mfi > self.mfi_oversold - 10,  # But recovering from oversold
            current_money_flow > 0,  # Positive money flow
            self.data.Close[-1] > self.sma_20[-1],  # Above short-term trend
            self.data.Volume[-1] > self.volume_ma[-1] * 1.2  # Above average volume
        ]

        # Alternative long: MFI oversold bounce with volume spike
        alt_long_conditions = [
            current_volume_ratio > self.volume_threshold * 0.8,  # Slightly lower threshold
            current_mfi < self.mfi_oversold,  # Oversold
            price_dir > 0,  # Bullish reversal
            bullish_div,  # Bullish divergence detected
            current_price > self.bb_lower[-1]  # Bouncing from lower band
        ]

        # Strong long: Multiple confirmations
        strong_long_conditions = [
            current_volume_ratio > self.volume_threshold * 1.5,  # Strong volume spike
            current_mfi > self.mfi_oversold and current_mfi < 50,  # Rising from oversold
            current_money_flow > self.money_flow[-2],  # Increasing money flow
            current_rsi < 60,  # Room to move up
            self.data.Close[-1] > self.data.Open[-1],  # Bullish candle
            self.data.Close[-1] > self.sma_20[-1]  # Above trend
        ]

        if all(long_conditions) or all(alt_long_conditions) or all(strong_long_conditions):
            # Dynamic stop loss and take profit
            atr_multiplier = 2.0 if all(strong_long_conditions) else 1.5
            stop_loss = current_price - (atr_multiplier * self.atr[-1])
            take_profit = current_price + (atr_multiplier * 2 * self.atr[-1])

            self.buy(sl=stop_loss, tp=take_profit)

        # Short signal: Volume spike + MFI confirmation + Negative money flow
        short_conditions = [
            current_volume_ratio > self.volume_threshold,  # Volume spike
            price_dir < 0,  # Bearish candle
            current_mfi > self.mfi_oversold,  # Not oversold
            current_mfi < self.mfi_overbought + 10,  # But falling from overbought
            current_money_flow < 0,  # Negative money flow
            self.data.Close[-1] < self.sma_20[-1],  # Below short-term trend
            self.data.Volume[-1] > self.volume_ma[-1] * 1.2  # Above average volume
        ]

        # Alternative short: MFI overbought rejection with volume spike
        alt_short_conditions = [
            current_volume_ratio > self.volume_threshold * 0.8,
            current_mfi > self.mfi_overbought,  # Overbought
            price_dir < 0,  # Bearish reversal
            bearish_div,  # Bearish divergence detected
            current_price < self.bb_upper[-1]  # Rejected from upper band
        ]

        # Strong short: Multiple confirmations
        strong_short_conditions = [
            current_volume_ratio > self.volume_threshold * 1.5,  # Strong volume spike
            current_mfi < self.mfi_overbought and current_mfi > 50,  # Falling from overbought
            current_money_flow < self.money_flow[-2],  # Decreasing money flow
            current_rsi > 40,  # Room to move down
            self.data.Close[-1] < self.data.Open[-1],  # Bearish candle
            self.data.Close[-1] < self.sma_20[-1]  # Below trend
        ]

        if all(short_conditions) or all(alt_short_conditions) or all(strong_short_conditions):
            # Dynamic stop loss and take profit
            atr_multiplier = 2.0 if all(strong_short_conditions) else 1.5
            stop_loss = current_price + (atr_multiplier * self.atr[-1])
            take_profit = current_price - (atr_multiplier * 2 * self.atr[-1])

            self.sell(sl=stop_loss, tp=take_profit)


def run_backtest(data, strategy_class=VolumeByTimeMFI, cash=100000, commission=0.002):
    """Run backtest with the given data and strategy"""
    bt = Backtest(data, strategy_class, cash=cash, commission=commission)
    stats = bt.run()
    return stats, bt


if __name__ == "__main__":
    print("\n🎯 Testing Volume by Time + MFI Strategy")
    print("=" * 80)

    # Test on all available data sources
    results = test_on_all_data(
        VolumeByTimeMFI,
        'VolumeByTimeMFI',
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

    print("\n🌙 Volume by Time + MFI Strategy Testing Complete! 🚀")
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
    print("\nRunning Volume by Time with MFI Strategy backtest...")
    stats, bt = run_backtest(data)

    # Print results
    print("\n" + "="*60)
    print("BACKTEST RESULTS - Volume by Time with MFI")
    print("="*60)
    print(stats)
    print("="*60)

    # Show plot
    bt.plot()