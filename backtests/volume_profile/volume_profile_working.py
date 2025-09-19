"""
Working Volume Profile Strategy
Simplified approach focusing on VWAP and volume for reliable signals
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

class VolumeProfileWorking(Strategy):
    # Simpler parameters that work
    vwap_period = 20
    volume_period = 20
    volume_multiplier = 1.2  # Lower threshold for more trades
    rsi_period = 14
    stop_loss = 0.02  # 2% stop loss
    take_profit = 0.03  # 3% take profit

    def init(self):
        # Basic data
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        volume = pd.Series(self.data.Volume)

        # Calculate VWAP manually
        typical_price = (high + low + close) / 3
        tpv = typical_price * volume

        # Use SMA to calculate rolling VWAP
        self.vwap = self.I(lambda: ta.sma(tpv, self.vwap_period) / ta.sma(volume, self.vwap_period))

        # Volume indicators
        self.volume_sma = self.I(ta.sma, volume, self.volume_period)

        # RSI for momentum
        self.rsi = self.I(ta.rsi, close, self.rsi_period)

        # Price position relative to VWAP
        self.price_to_vwap = self.I(lambda: close / self.vwap)

    def next(self):
        # Need enough data
        if len(self.data) < 50:
            return

        # Current values
        price = self.data.Close[-1]
        volume = self.data.Volume[-1]
        vwap = self.vwap[-1]
        volume_avg = self.volume_sma[-1]
        rsi = self.rsi[-1]
        price_ratio = self.price_to_vwap[-1]

        # Skip if invalid values
        if pd.isna(vwap) or pd.isna(volume_avg) or volume_avg == 0:
            return

        # Volume ratio
        vol_ratio = volume / volume_avg if volume_avg > 0 else 0

        if not self.position:
            # Long signal: Price below VWAP with volume surge
            if (price < vwap * 0.995 and  # Price below VWAP
                vol_ratio > self.volume_multiplier and  # Volume surge
                rsi < 65 and  # Not overbought
                price_ratio < 0.995):  # Confirm below VWAP

                # Set stop loss and take profit
                sl = price * (1 - self.stop_loss)
                tp = price * (1 + self.take_profit)
                self.buy(sl=sl, tp=tp)

            # Short signal: Price above VWAP with volume surge
            elif (price > vwap * 1.005 and  # Price above VWAP
                  vol_ratio > self.volume_multiplier and  # Volume surge
                  rsi > 35 and  # Not oversold
                  price_ratio > 1.005):  # Confirm above VWAP

                # Set stop loss and take profit
                sl = price * (1 + self.stop_loss)
                tp = price * (1 - self.take_profit)
                self.sell(sl=sl, tp=tp)

# Test the strategy
if __name__ == "__main__":
    DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

    print("Volume Profile Working Strategy")
    print("="*60)

    # Load data
    data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
    data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
    data = data.sort_index().dropna()

    # Use last 10000 bars for testing
    data = data.tail(10000)

    print(f"Data loaded: {len(data)} rows")
    print(f"Date range: {data.index[0]} to {data.index[-1]}")

    # Run backtest with reasonable capital
    bt = Backtest(data, VolumeProfileWorking, cash=100000, commission=0.001)

    # Run with default parameters
    stats = bt.run()

    print("\nBacktest Results:")
    print("="*60)
    print(f"Return: {stats['Return [%]']:.2f}%")
    print(f"Buy & Hold Return: {stats['Buy & Hold Return [%]']:.2f}%")
    print(f"Number of Trades: {stats['# Trades']}")
    print(f"Win Rate: {stats['Win Rate [%]']:.2f}%")
    print(f"Sharpe Ratio: {stats['Sharpe Ratio']:.3f}")
    print(f"Max Drawdown: {stats['Max. Drawdown [%]']:.2f}%")

    if stats['# Trades'] > 0:
        print(f"\n✅ Strategy working! Generated {stats['# Trades']} trades")
        print(f"Average Trade: {stats['Avg. Trade [%]']:.2f}%")
        print(f"Best Trade: {stats['Best Trade [%]']:.2f}%")
        print(f"Worst Trade: {stats['Worst Trade [%]']:.2f}%")
    else:
        print("\n⚠️ No trades generated")

    # Print full stats
    print("\nFull Statistics:")
    print("="*60)
    print(stats)

    # Show plot
    bt.plot()