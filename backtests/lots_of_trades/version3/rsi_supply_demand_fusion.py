"""
RSI SUPPLY DEMAND FUSION - Combining Best of Both Worlds
=========================================================

Concept: Merge RSI extremes with supply/demand zones for high-probability trades.
Buy at demand zones with oversold RSI, sell at supply zones with overbought RSI.

Focus: PROFITABILITY with high volume
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

print("🎯 Moon Dev's RSI SUPPLY DEMAND FUSION Strategy V3 🎯")
print("=" * 70)

# Load data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1m-4wks-data.csv'
print(f"📊 Loading BTC 1-minute data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Calculate RSI
data['RSI'] = ta.rsi(data['Close'], length=14)

# Calculate supply and demand zones
data['Demand_Zone'] = data['Close'].rolling(15).min()
data['Supply_Zone'] = data['Close'].rolling(15).max()
data['Zone_Width'] = (data['Supply_Zone'] - data['Demand_Zone']) / data['Demand_Zone']

# Zone proximity
data['Near_Demand'] = (data['Close'] - data['Demand_Zone']) / data['Demand_Zone']
data['Near_Supply'] = (data['Supply_Zone'] - data['Close']) / data['Close']

# Volume analysis
data['Volume_MA'] = data['Volume'].rolling(20).mean()
data['Volume_Spike'] = data['Volume'] / data['Volume_MA']

print(f"✅ Loaded {len(data):,} 1-minute bars")


class RSISupplyDemandFusion(Strategy):
    """
    Combine RSI extremes with supply/demand zones
    """

    rsi_oversold = 25
    rsi_overbought = 75
    zone_proximity = 0.002  # 0.2% from zone
    volume_threshold = 1.2
    take_profit = 0.006
    stop_loss = 0.003

    def init(self):
        self.rsi = self.I(lambda: self.data.RSI)
        self.demand_zone = self.I(lambda: self.data.Demand_Zone)
        self.supply_zone = self.I(lambda: self.data.Supply_Zone)
        self.near_demand = self.I(lambda: self.data.Near_Demand)
        self.near_supply = self.I(lambda: self.data.Near_Supply)
        self.volume_spike = self.I(lambda: self.data.Volume_Spike)

    def next(self):
        if len(self.data) < 30:
            return

        price = self.data.Close[-1]
        rsi = self.rsi[-1]

        if pd.isna(rsi):
            return

        # Exit logic
        if self.position:
            if self.position.is_long and rsi > 70:
                self.position.close()
            elif self.position.is_short and rsi < 30:
                self.position.close()
            return

        # Entry logic - combine both signals
        if not self.position:
            # BUY: Near demand + oversold RSI + volume confirmation
            if (self.near_demand[-1] < self.zone_proximity and
                rsi < self.rsi_oversold and
                self.volume_spike[-1] > self.volume_threshold):

                tp = price * (1 + self.take_profit)
                sl = price * (1 - self.stop_loss)
                self.buy(tp=tp, sl=sl)

            # SELL: Near supply + overbought RSI + volume confirmation
            elif (self.near_supply[-1] < self.zone_proximity and
                  rsi > self.rsi_overbought and
                  self.volume_spike[-1] > self.volume_threshold):

                tp = price * (1 - self.take_profit)
                sl = price * (1 + self.stop_loss)
                self.sell(tp=tp, sl=sl)


# Run backtest
print("\n" + "="*70)
print("RUNNING RSI SUPPLY DEMAND FUSION BACKTEST")
print("="*70)

bt = Backtest(
    data,
    RSISupplyDemandFusion,
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
        rsi_oversold=[20, 25, 30],
        rsi_overbought=[70, 75, 80],
        zone_proximity=[0.0015, 0.002, 0.0025],
        take_profit=[0.005, 0.006, 0.007],
        stop_loss=[0.002, 0.003, 0.004],
        maximize='Return [%]',
        return_heatmap=False
    )

    print(f"\n✨ OPTIMIZED RESULTS:")
    print(optimization_results)

    print(f"\n🎯 OPTIMAL PARAMETERS:")
    print(f"rsi_oversold: {optimization_results._strategy.rsi_oversold}")
    print(f"rsi_overbought: {optimization_results._strategy.rsi_overbought}")
    print(f"zone_proximity: {optimization_results._strategy.zone_proximity}")
    print(f"take_profit: {optimization_results._strategy.take_profit}")
    print(f"stop_loss: {optimization_results._strategy.stop_loss}")

except Exception as e:
    print(f"Optimization failed: {str(e)}")

bt.plot()