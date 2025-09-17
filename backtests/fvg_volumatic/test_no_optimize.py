#!/usr/bin/env python3
"""
Test FVG strategies without optimization - just run with default params
"""

import pandas as pd
import pandas_ta as ta
import numpy as np
from backtesting import Backtest, Strategy

class SimpleFVG(Strategy):
    """Simplified FVG strategy for testing"""

    # Parameters
    min_gap_pct = 0.5
    volume_threshold = 1.2
    take_profit_pct = 3.0
    stop_loss_pct = 2.0

    def init(self):
        # Volume SMA for comparison
        self.volume_sma = self.I(ta.sma, pd.Series(self.data.Volume), length=20)

        # Track gaps
        self.gaps = []

    def next(self):
        if len(self.data) < 3:
            return

        # Get current and previous values
        curr_high = self.data.High[-1]
        curr_low = self.data.Low[-1]
        prev_high = self.data.High[-2]
        prev_low = self.data.Low[-2]
        prev2_high = self.data.High[-3]
        prev2_low = self.data.Low[-3]
        curr_close = self.data.Close[-1]
        curr_volume = self.data.Volume[-1]

        # Check volume surge
        if self.volume_sma[-1] == 0:
            return

        volume_ratio = curr_volume / self.volume_sma[-1]

        # Detect Bullish FVG (gap up)
        if prev2_high < curr_low and volume_ratio > self.volume_threshold:
            gap_size = ((curr_low - prev2_high) / prev2_high) * 100

            if gap_size >= self.min_gap_pct and not self.position:
                # Enter long position
                self.buy()

        # Detect Bearish FVG (gap down)
        elif prev2_low > curr_high and volume_ratio > self.volume_threshold:
            gap_size = ((prev2_low - curr_high) / curr_high) * 100

            if gap_size >= self.min_gap_pct and not self.position:
                # Enter short position
                self.sell()

        # Exit logic - use simple percentage-based stops
        if self.position:
            # Use backtesting.py's built-in TP/SL functionality
            entry_price = self.position.entry_price if hasattr(self.position, 'entry_price') else self.data.Close[-2]

            if self.position.is_long:
                # Set take profit and stop loss for long
                take_profit_price = entry_price * (1 + self.take_profit_pct / 100)
                stop_loss_price = entry_price * (1 - self.stop_loss_pct / 100)

                if curr_close >= take_profit_price or curr_close <= stop_loss_price:
                    self.position.close()

            else:  # Short position
                # Set take profit and stop loss for short
                take_profit_price = entry_price * (1 - self.take_profit_pct / 100)
                stop_loss_price = entry_price * (1 + self.stop_loss_pct / 100)

                if curr_close <= take_profit_price or curr_close >= stop_loss_price:
                    self.position.close()


if __name__ == "__main__":
    print("\n🚀 Testing Simplified FVG Strategy")
    print("="*60)

    # Load data
    print("📊 Loading BTC hourly data...")
    data = pd.read_csv('/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv')
    data.columns = ['datetime', 'Open', 'High', 'Low', 'Close', 'Volume']
    data.set_index('datetime', inplace=True)
    data.index = pd.to_datetime(data.index)

    # Use last 2 years of data for faster testing
    data = data.tail(17520)  # ~2 years of hourly data
    print(f"✅ Using {len(data)} bars (last 2 years)")

    # Run backtest
    bt = Backtest(data, SimpleFVG, cash=1000000, commission=0.002)
    stats = bt.run()

    # Print all stats
    print("\n📊 BACKTEST RESULTS:")
    print("="*60)
    print(stats)

    # Key metrics
    print("\n🎯 KEY METRICS:")
    print(f"Total Return: {stats['Return [%]']:.2f}%")
    print(f"Buy & Hold: {stats['Buy & Hold Return [%]']:.2f}%")
    print(f"Sharpe Ratio: {stats['Sharpe Ratio']:.3f}")
    print(f"Max Drawdown: {stats['Max. Drawdown [%]']:.2f}%")
    print(f"Win Rate: {stats['Win Rate [%]']:.1f}%")
    print(f"Number of Trades: {stats['# Trades']}")
    print(f"Profit Factor: {stats['Profit Factor']:.3f}")
    print(f"Average Trade: {stats['Avg. Trade [%]']:.3f}%")

    # Show plot
    bt.plot(show_legend=False)