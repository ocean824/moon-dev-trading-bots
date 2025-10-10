"""
VOLUME WEIGHTED ZONES - High Volume Support/Resistance
=======================================================

Concept: Trade zones created by high-volume price levels.
These zones act as stronger support/resistance than regular zones.

Focus: PROFITABILITY with high volume
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

print("🎯 Moon Dev's VOLUME WEIGHTED ZONES Strategy V3 🎯")
print("=" * 70)

# Load data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1m-4wks-data.csv'
print(f"📊 Loading BTC 1-minute data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Volume-weighted zones
data['VWAP'] = ta.vwap(data['High'], data['Low'], data['Close'], data['Volume'])
data['Volume_MA'] = data['Volume'].rolling(20).mean()
data['High_Volume'] = data['Volume'] > (data['Volume_MA'] * 1.5)

# Create zones at high-volume areas
data['HV_High'] = data['High'].where(data['High_Volume']).fillna(method='ffill')
data['HV_Low'] = data['Low'].where(data['High_Volume']).fillna(method='ffill')

# Rolling high-volume zones
data['Volume_Zone_High'] = data['HV_High'].rolling(30).max()
data['Volume_Zone_Low'] = data['HV_Low'].rolling(30).min()

# Distance from zones
data['Distance_High'] = (data['Volume_Zone_High'] - data['Close']) / data['Close']
data['Distance_Low'] = (data['Close'] - data['Volume_Zone_Low']) / data['Close']

# RSI for confirmation
data['RSI'] = ta.rsi(data['Close'], length=14)

# Volume profile strength
data['Volume_Strength'] = data['Volume'].rolling(10).sum() / data['Volume'].rolling(100).sum()

print(f"✅ Loaded {len(data):,} 1-minute bars")


class VolumeWeightedZones(Strategy):
    """
    Trade bounces from high-volume zones
    """

    zone_proximity = 0.002  # 0.2% from zone
    volume_multiplier = 1.5
    rsi_oversold = 35
    rsi_overbought = 65
    take_profit = 0.006
    stop_loss = 0.003

    def init(self):
        self.vwap = self.I(lambda: self.data.VWAP)
        self.volume_zone_high = self.I(lambda: self.data.Volume_Zone_High)
        self.volume_zone_low = self.I(lambda: self.data.Volume_Zone_Low)
        self.distance_high = self.I(lambda: self.data.Distance_High)
        self.distance_low = self.I(lambda: self.data.Distance_Low)
        self.rsi = self.I(lambda: self.data.RSI)
        self.volume_strength = self.I(lambda: self.data.Volume_Strength)

    def next(self):
        if len(self.data) < 100:
            return

        price = self.data.Close[-1]
        rsi = self.rsi[-1]

        if pd.isna(rsi) or pd.isna(self.vwap[-1]):
            return

        # Exit at VWAP
        if self.position:
            vwap = self.vwap[-1]
            if self.position.is_long and price >= vwap:
                self.position.close()
            elif self.position.is_short and price <= vwap:
                self.position.close()
            return

        # Entry logic
        if not self.position:
            # BUY: Near volume support zone + oversold
            if (self.distance_low[-1] < self.zone_proximity and
                rsi < self.rsi_oversold and
                self.volume_strength[-1] > 0.1):

                tp = price * (1 + self.take_profit)
                sl = price * (1 - self.stop_loss)
                self.buy(tp=tp, sl=sl)

            # SELL: Near volume resistance zone + overbought
            elif (self.distance_high[-1] < self.zone_proximity and
                  rsi > self.rsi_overbought and
                  self.volume_strength[-1] > 0.1):

                tp = price * (1 - self.take_profit)
                sl = price * (1 + self.stop_loss)
                self.sell(tp=tp, sl=sl)


# Run backtest
print("\n" + "="*70)
print("RUNNING VOLUME WEIGHTED ZONES BACKTEST")
print("="*70)

bt = Backtest(
    data,
    VolumeWeightedZones,
    cash=1000000,
    commission=0.001,
    exclusive_orders=True
)

baseline_stats = bt.run()
print(f"\n📊 BASELINE RESULTS:")
print(baseline_stats)

# Optimization
print("\n" + "="*70)
print("OPTIMIZING FOR MAXIMUM RETURN")
print("="*70)

try:
    optimization_results = bt.optimize(
        zone_proximity=[0.0015, 0.002, 0.0025],
        rsi_oversold=[30, 35, 40],
        rsi_overbought=[60, 65, 70],
        take_profit=[0.005, 0.006, 0.007],
        stop_loss=[0.002, 0.003, 0.004],
        maximize='Return [%]',
        return_heatmap=False
    )

    print(f"\n✨ OPTIMIZED RESULTS:")
    print(optimization_results)

    print(f"\n🎯 OPTIMAL PARAMETERS:")
    print(f"zone_proximity: {optimization_results._strategy.zone_proximity}")
    print(f"rsi_oversold: {optimization_results._strategy.rsi_oversold}")
    print(f"rsi_overbought: {optimization_results._strategy.rsi_overbought}")
    print(f"take_profit: {optimization_results._strategy.take_profit}")
    print(f"stop_loss: {optimization_results._strategy.stop_loss}")

except Exception as e:
    print(f"Optimization failed: {str(e)}")

bt.plot()