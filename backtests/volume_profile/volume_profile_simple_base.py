"""
Volume Profile Simple Base Strategy
Simplified version using basic VWAP and volume levels for faster execution.
Enters when price crosses above lower volume area, exits at upper volume area.
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from multi_data_tester import test_on_all_data

class VolumeProfileSimpleBase(Strategy):
    # Parameters
    vwap_period = 30  # Period for VWAP calculation
    volume_ma_period = 20  # Volume moving average
    entry_threshold = 0.98  # Enter when price is 2% below VWAP
    exit_threshold = 1.02  # Exit when price is 2% above VWAP
    volume_confirmation = 1.2  # Minimum volume ratio
    stop_loss_pct = 0.02  # 2% stop loss
    take_profit_pct = 0.04  # 4% take profit

    def init(self):
        # Basic price and volume data
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        volume = pd.Series(self.data.Volume)

        # Simple VWAP as our POC proxy
        typical_price = (high + low + close) / 3
        self.vwap = self.I(ta.sma, typical_price * volume, self.vwap_period) / self.I(ta.sma, volume, self.vwap_period)

        # Volume analysis
        self.volume_sma = self.I(ta.sma, volume, self.volume_ma_period)
        self.volume_ratio = self.I(lambda: volume / self.volume_sma)

        # Simple bands around VWAP as value area proxy
        self.upper_band = self.I(lambda: self.vwap * self.exit_threshold)
        self.lower_band = self.I(lambda: self.vwap * self.entry_threshold)

        # RSI for additional filtering
        self.rsi = self.I(ta.rsi, close, 14)

    def next(self):
        # Skip if not enough data
        if len(self.data) < 50:
            return

        # Current values
        current_price = self.data.Close[-1]
        current_vwap = self.vwap[-1]
        current_upper = self.upper_band[-1]
        current_lower = self.lower_band[-1]
        current_volume_ratio = self.volume_ratio[-1]
        current_rsi = self.rsi[-1]

        if not self.position:
            # Long entry: Price crosses above lower band with volume
            if current_price > current_lower and self.data.Close[-2] <= self.lower_band[-2]:
                if current_volume_ratio > self.volume_confirmation and current_rsi < 70:
                    sl_price = current_price * (1 - self.stop_loss_pct)
                    tp_price = current_upper  # Target the upper band
                    # Ensure tp_price is above current price for long
                    if tp_price > current_price * 1.01:  # At least 1% profit potential
                        self.buy(sl=sl_price, tp=tp_price)

            # Short entry: Price crosses below upper band with volume
            elif current_price < current_upper and self.data.Close[-2] >= self.upper_band[-2]:
                if current_volume_ratio > self.volume_confirmation and current_rsi > 30:
                    sl_price = current_price * (1 + self.stop_loss_pct)
                    tp_price = current_lower  # Target the lower band
                    # Ensure tp_price is below current price for short
                    if tp_price < current_price * 0.99:  # At least 1% profit potential
                        self.sell(sl=sl_price, tp=tp_price)

        else:
            # Exit management
            if self.position.is_long:
                if current_price >= current_upper or current_price < current_lower * 0.98:
                    self.position.close()

            elif self.position.is_short:
                if current_price <= current_lower or current_price > current_upper * 1.02:
                    self.position.close()

# Data configuration
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

print("Volume Profile Simple Base Strategy Loading...")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index().dropna()

print(f"Data loaded! {len(data)} rows")

# Run backtest
bt = Backtest(data, VolumeProfileSimpleBase, cash=1000000, commission=0.001)
stats = bt.run()
print(stats)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING VOLUME PROFILE SIMPLE BASE ON ALL DATA SOURCES")
    print("="*80)

    results = test_on_all_data(VolumeProfileSimpleBase, 'VolumeProfileSimpleBase')

    if results is not None:
        print("\nTesting complete! Results saved in: ./results/VolumeProfileSimpleBase.csv")