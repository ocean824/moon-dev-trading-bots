#!/usr/bin/env python3
"""
Simplified Smart Money Breakout Strategy for Testing
Dr. Data Dawg's Smart Money Breakout 🌙
"""

from backtesting import Backtest, Strategy
import pandas as pd
import numpy as np
import pandas_ta as ta
import os

class SmartMoneySimple(Strategy):
    # Parameters
    channel_lookback = 20
    min_channel_bars = 10
    volume_threshold = 1.2
    take_profit_pct = 3.0
    stop_loss_pct = 2.0
    strong_breakout_pct = 0.5

    def init(self):
        # Calculate ATR for volatility
        self.atr = self.I(ta.atr, pd.Series(self.data.High),
                         pd.Series(self.data.Low),
                         pd.Series(self.data.Close), length=14)

        # Volume moving average
        self.volume_ma = self.I(ta.sma, pd.Series(self.data.Volume), length=20)

        # Track channels
        self.channel_high = 0
        self.channel_low = 0
        self.in_channel = False
        self.channel_bars = 0

    def next(self):
        idx = len(self.data) - 1
        if idx < self.channel_lookback + 1:
            return

        # Get current values
        current_close = self.data.Close[-1]
        current_high = self.data.High[-1]
        current_low = self.data.Low[-1]
        current_volume = self.data.Volume[-1]
        current_atr = self.atr[-1] if self.atr[-1] else 0.001

        # Calculate recent high/low for channel
        recent_highs = self.data.High[-self.channel_lookback:]
        recent_lows = self.data.Low[-self.channel_lookback:]
        recent_high = max(recent_highs)
        recent_low = min(recent_lows)

        # Channel width relative to ATR
        channel_width = recent_high - recent_low
        if current_atr > 0:
            width_in_atr = channel_width / current_atr
        else:
            width_in_atr = 10

        # Detect consolidation (narrow range)
        if width_in_atr < 3:  # Channel is less than 3 ATRs wide
            if not self.in_channel:
                # New channel formed
                self.in_channel = True
                self.channel_high = recent_high
                self.channel_low = recent_low
                self.channel_bars = 0
            else:
                # Update channel
                self.channel_bars += 1
                # Adjust channel boundaries if needed
                if current_high <= self.channel_high and current_low >= self.channel_low:
                    # Still in channel
                    pass
                else:
                    # Channel broken
                    self.in_channel = False

        # Check for breakouts if we have a valid channel
        if self.in_channel and self.channel_bars >= self.min_channel_bars:
            # Volume check
            volume_ratio = current_volume / self.volume_ma[-1] if self.volume_ma[-1] > 0 else 1

            # Check for bullish breakout
            if current_close > self.channel_high and volume_ratio > self.volume_threshold:
                # Check strong close requirement
                candle_body = abs(current_close - self.data.Open[-1])
                above_channel = current_close - self.channel_high
                if candle_body > 0:
                    pct_above = above_channel / candle_body
                    if pct_above >= self.strong_breakout_pct:
                        if not self.position:
                            self.buy()
                            self.in_channel = False

            # Check for bearish breakout
            elif current_close < self.channel_low and volume_ratio > self.volume_threshold:
                # Check strong close requirement
                candle_body = abs(current_close - self.data.Open[-1])
                below_channel = self.channel_low - current_close
                if candle_body > 0:
                    pct_below = below_channel / candle_body
                    if pct_below >= self.strong_breakout_pct:
                        if not self.position:
                            self.sell()
                            self.in_channel = False

        # Exit management
        if self.position:
            if self.position.is_long:
                # Calculate P&L percentage
                entry_price = self.position.entry_price if hasattr(self.position, 'entry_price') else self.data.Close[-2]
                pnl_pct = ((current_close - entry_price) / entry_price) * 100

                # Check exits
                if pnl_pct >= self.take_profit_pct or pnl_pct <= -self.stop_loss_pct:
                    self.position.close()

            else:  # Short position
                # Calculate P&L percentage
                entry_price = self.position.entry_price if hasattr(self.position, 'entry_price') else self.data.Close[-2]
                pnl_pct = ((entry_price - current_close) / entry_price) * 100

                # Check exits
                if pnl_pct >= self.take_profit_pct or pnl_pct <= -self.stop_loss_pct:
                    self.position.close()


def main():
    # Test data path
    data_path = "/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv"

    if os.path.exists(data_path):
        print("🌙 Moon Dev's Smart Money Breakout (Simplified) 🌙")
        print("=" * 50)

        # Load data
        df = pd.read_csv(data_path)
        df['datetime'] = pd.to_datetime(df['datetime'])
        df = df.set_index('datetime')
        df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        df = df.sort_index()

        # Use last 2 years for faster testing
        df = df.tail(17520)
        print(f"Testing on {len(df)} bars (last 2 years)")

        # Run backtest
        bt = Backtest(df, SmartMoneySimple, cash=1000000, commission=0.002)
        stats = bt.run()

        # Print results
        print("\n📊 RESULTS:")
        print(f"Return: {stats['Return [%]']:.2f}%")
        print(f"Buy & Hold: {stats['Buy & Hold Return [%]']:.2f}%")
        print(f"Sharpe Ratio: {stats['Sharpe Ratio']:.3f}")
        print(f"Max Drawdown: {stats['Max. Drawdown [%]']:.2f}%")
        print(f"Win Rate: {stats.get('Win Rate [%]', 0):.1f}%")
        print(f"Number of Trades: {stats['# Trades']}")
        print(f"Average Trade: {stats.get('Avg. Trade [%]', 0):.3f}%")

        # Full stats
        print("\n📈 FULL STATISTICS:")
        print(stats)

    else:
        print(f"❌ Data file not found: {data_path}")


if __name__ == "__main__":
    main()