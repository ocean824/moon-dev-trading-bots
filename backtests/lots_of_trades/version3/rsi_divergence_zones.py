"""
RSI DIVERGENCE ZONES - Hidden and Regular Divergences
======================================================

Concept: Trade RSI divergences at supply/demand zones.
Regular divergence for reversals, hidden divergence for continuations.

Focus: PROFITABILITY with high volume
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

print("🎯 Moon Dev's RSI DIVERGENCE ZONES Strategy V3 🎯")
print("=" * 70)

# Load data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1m-4wks-data.csv'
print(f"📊 Loading BTC 1-minute data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Calculate RSI
data['RSI'] = ta.rsi(data['Close'], length=14)

# Find local peaks and troughs
window = 5
data['Price_Peak'] = data['High'] == data['High'].rolling(window*2+1, center=True).max()
data['Price_Trough'] = data['Low'] == data['Low'].rolling(window*2+1, center=True).min()

data['RSI_Peak'] = data['RSI'] == data['RSI'].rolling(window*2+1, center=True).max()
data['RSI_Trough'] = data['RSI'] == data['RSI'].rolling(window*2+1, center=True).min()

# Track previous peaks and troughs
data['Prev_Price_Peak'] = data['High'].where(data['Price_Peak']).ffill()
data['Prev_Price_Trough'] = data['Low'].where(data['Price_Trough']).ffill()
data['Prev_RSI_Peak'] = data['RSI'].where(data['RSI_Peak']).ffill()
data['Prev_RSI_Trough'] = data['RSI'].where(data['RSI_Trough']).ffill()

# Detect divergences
# Bullish divergence: Price makes lower low, RSI makes higher low
data['Bullish_Div'] = ((data['Low'] < data['Prev_Price_Trough'] * 0.998) &
                       (data['RSI'] > data['Prev_RSI_Trough'] + 2) &
                       data['Price_Trough'])

# Bearish divergence: Price makes higher high, RSI makes lower high
data['Bearish_Div'] = ((data['High'] > data['Prev_Price_Peak'] * 1.002) &
                       (data['RSI'] < data['Prev_RSI_Peak'] - 2) &
                       data['Price_Peak'])

# Supply and demand zones
data['Demand_Zone'] = data['Close'].rolling(20).min()
data['Supply_Zone'] = data['Close'].rolling(20).max()

# Volume confirmation
data['Volume_MA'] = data['Volume'].rolling(20).mean()
data['Volume_Spike'] = data['Volume'] / data['Volume_MA']

print(f"✅ Loaded {len(data):,} 1-minute bars")


class RSIDivergenceZones(Strategy):
    """
    Trade RSI divergences at key zones
    """

    rsi_oversold = 35
    rsi_overbought = 65
    zone_buffer = 0.002
    divergence_lookback = 20
    take_profit = 0.008
    stop_loss = 0.003

    def init(self):
        self.rsi = self.I(lambda: self.data.RSI)
        self.bullish_div = self.I(lambda: self.data.Bullish_Div)
        self.bearish_div = self.I(lambda: self.data.Bearish_Div)
        self.demand_zone = self.I(lambda: self.data.Demand_Zone)
        self.supply_zone = self.I(lambda: self.data.Supply_Zone)
        self.volume_spike = self.I(lambda: self.data.Volume_Spike)

    def next(self):
        if len(self.data) < 50:
            return

        price = self.data.Close[-1]
        rsi = self.rsi[-1]

        if pd.isna(rsi):
            return

        # Exit on RSI normalization
        if self.position:
            if self.position.is_long and rsi > 60:
                self.position.close()
            elif self.position.is_short and rsi < 40:
                self.position.close()
            return

        # Entry logic
        if not self.position:
            # Check for recent divergences
            recent_bullish = any(self.bullish_div[-self.divergence_lookback:])
            recent_bearish = any(self.bearish_div[-self.divergence_lookback:])

            # BUY: Bullish divergence near demand zone
            if (recent_bullish and
                price <= self.demand_zone[-1] * (1 + self.zone_buffer) and
                rsi < self.rsi_oversold and
                self.volume_spike[-1] > 1.1):

                tp = price * (1 + self.take_profit)
                sl = price * (1 - self.stop_loss)
                self.buy(tp=tp, sl=sl)

            # SELL: Bearish divergence near supply zone
            elif (recent_bearish and
                  price >= self.supply_zone[-1] * (1 - self.zone_buffer) and
                  rsi > self.rsi_overbought and
                  self.volume_spike[-1] > 1.1):

                tp = price * (1 - self.take_profit)
                sl = price * (1 + self.stop_loss)
                self.sell(tp=tp, sl=sl)


# Run backtest
print("\n" + "="*70)
print("RUNNING RSI DIVERGENCE ZONES BACKTEST")
print("="*70)

bt = Backtest(
    data,
    RSIDivergenceZones,
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
        rsi_oversold=[30, 35, 40],
        rsi_overbought=[60, 65, 70],
        zone_buffer=[0.0015, 0.002, 0.0025],
        take_profit=[0.007, 0.008, 0.009],
        stop_loss=[0.002, 0.003, 0.004],
        maximize='Return [%]',
        return_heatmap=False
    )

    print(f"\n✨ OPTIMIZED RESULTS:")
    print(optimization_results)

    print(f"\n🎯 OPTIMAL PARAMETERS:")
    print(f"rsi_oversold: {optimization_results._strategy.rsi_oversold}")
    print(f"rsi_overbought: {optimization_results._strategy.rsi_overbought}")
    print(f"zone_buffer: {optimization_results._strategy.zone_buffer}")
    print(f"take_profit: {optimization_results._strategy.take_profit}")
    print(f"stop_loss: {optimization_results._strategy.stop_loss}")

except Exception as e:
    print(f"Optimization failed: {str(e)}")

bt.plot()