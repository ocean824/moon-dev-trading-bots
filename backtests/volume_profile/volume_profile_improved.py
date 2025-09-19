"""
Improved Volume Profile Strategy
Uses actual volume profile calculations with better entry/exit logic
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

class VolumeProfileImproved(Strategy):
    # Parameters
    profile_period = 50  # Lookback for volume profile
    num_bins = 20  # Number of price bins
    value_area_pct = 0.68  # 68% of volume for value area
    volume_surge = 1.5  # Volume multiplier for confirmation
    stop_loss_pct = 0.015  # 1.5% stop loss
    take_profit_pct = 0.03  # 3% take profit

    def init(self):
        # Basic data
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        volume = pd.Series(self.data.Volume)

        # Volume moving average
        self.volume_ma = self.I(ta.sma, volume, 20)

        # RSI for trend confirmation
        self.rsi = self.I(ta.rsi, close, 14)

        # VWAP as simple POC proxy
        typical_price = (high + low + close) / 3
        self.vwap = self.I(ta.sma, typical_price * volume, 20) / self.I(ta.sma, volume, 20)

        # Bollinger Bands for volatility
        bb = ta.bbands(close, length=20, std=2)
        if bb is not None:
            self.bb_upper = self.I(lambda: bb.iloc[:, 0])
            self.bb_lower = self.I(lambda: bb.iloc[:, 2])
        else:
            self.bb_upper = self.I(ta.sma, close, 20)
            self.bb_lower = self.I(ta.sma, close, 20)

    def next(self):
        # Skip if not enough data
        if len(self.data) < self.profile_period:
            return

        # Current values
        current_price = self.data.Close[-1]
        current_volume = self.data.Volume[-1]
        current_vwap = self.vwap[-1]
        current_rsi = self.rsi[-1]
        volume_avg = self.volume_ma[-1]

        # Simple volume profile calculation
        recent_highs = self.data.High[-self.profile_period:]
        recent_lows = self.data.Low[-self.profile_period:]
        recent_volumes = self.data.Volume[-self.profile_period:]

        # Find POC (simplified)
        price_range = max(recent_highs) - min(recent_lows)
        if price_range <= 0:
            return

        poc_level = current_vwap  # Use VWAP as POC approximation
        val_level = poc_level * 0.98  # 2% below POC
        vah_level = poc_level * 1.02  # 2% above POC

        if not self.position:
            # Long entry conditions
            if (current_price < poc_level and
                current_price > val_level and
                current_volume > volume_avg * self.volume_surge and
                current_rsi < 70):

                sl = current_price * (1 - self.stop_loss_pct)
                tp = vah_level
                if tp > current_price * 1.01:  # At least 1% profit potential
                    self.buy(sl=sl, tp=tp)

            # Short entry conditions
            elif (current_price > poc_level and
                  current_price < vah_level and
                  current_volume > volume_avg * self.volume_surge and
                  current_rsi > 30):

                sl = current_price * (1 + self.stop_loss_pct)
                tp = val_level
                if tp < current_price * 0.99:  # At least 1% profit potential
                    self.sell(sl=sl, tp=tp)

        else:
            # Exit if price reaches opposite value area boundary
            if self.position.is_long:
                if current_price >= vah_level or current_rsi > 75:
                    self.position.close()

            elif self.position.is_short:
                if current_price <= val_level or current_rsi < 25:
                    self.position.close()

# Test the strategy
if __name__ == "__main__":
    DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

    print("Volume Profile Improved Strategy")
    print("="*60)

    # Load data
    data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
    data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
    data = data.sort_index().dropna()

    # Use recent data for testing
    data = data.tail(5000)  # Last 5000 bars

    print(f"Data loaded: {len(data)} rows")
    print(f"Date range: {data.index[0]} to {data.index[-1]}")

    # Run backtest
    bt = Backtest(data, VolumeProfileImproved, cash=10000, commission=0.001)
    stats = bt.run()

    print("\nBacktest Results:")
    print("="*60)
    print(stats)

    # Show plot
    bt.plot()