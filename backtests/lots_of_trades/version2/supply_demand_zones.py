"""
SUPPLY DEMAND ZONES - 1-Minute Zone Trading
============================================

Concept: Trade bounces from 1-minute supply and demand zones.
Buy at demand, sell at supply with tight risk management.

Focus: PROFITABILITY with high volume
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import warnings
warnings.filterwarnings('ignore')

print("🎯 Moon Dev's SUPPLY DEMAND ZONES Strategy V2 🎯")
print("=" * 70)

# Load data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1m-4wks-data.csv'
print(f"📊 Loading BTC 1-minute data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Calculate supply and demand zones
data['Demand_Zone'] = data['Close'].rolling(10).min()
data['Supply_Zone'] = data['Close'].rolling(10).max()
data['Mid_Zone'] = (data['Demand_Zone'] + data['Supply_Zone']) / 2

# Zone strength (how many times tested)
data['At_Demand'] = (data['Low'] <= data['Demand_Zone'] * 1.001).astype(int)
data['At_Supply'] = (data['High'] >= data['Supply_Zone'] * 0.999).astype(int)
data['Demand_Strength'] = data['At_Demand'].rolling(20).sum()
data['Supply_Strength'] = data['At_Supply'].rolling(20).sum()

# Momentum for confirmation
data['Momentum'] = data['Close'].pct_change(3)

print(f"✅ Loaded {len(data):,} 1-minute bars")


class SupplyDemandZonesStrategy(Strategy):
    """
    Trade bounces from supply and demand zones
    """
    
    lookback = 10
    zone_buffer = 0.001   # 0.1% buffer
    take_profit = 0.005   # 0.5% profit
    stop_loss = 0.002     # 0.2% stop
    min_zone_width = 0.002  # Minimum zone width
    
    def init(self):
        self.demand_zone = self.I(lambda: self.data.Demand_Zone)
        self.supply_zone = self.I(lambda: self.data.Supply_Zone)
        self.mid_zone = self.I(lambda: self.data.Mid_Zone)
        self.demand_strength = self.I(lambda: self.data.Demand_Strength)
        self.supply_strength = self.I(lambda: self.data.Supply_Strength)
        self.momentum = self.I(lambda: self.data.Momentum)
        
    def next(self):
        if len(self.data) < 30:
            return
            
        current_price = self.data.Close[-1]
        demand = self.demand_zone[-1]
        supply = self.supply_zone[-1]
        zone_width = (supply - demand) / demand
        
        # Only trade if zone is wide enough and valid
        if zone_width < self.min_zone_width:
            return

        # Ensure supply is above demand (valid zones)
        if supply <= demand:
            return

        # Exit at mid zone
        if self.position:
            mid = self.mid_zone[-1]
            if self.position.is_long and current_price >= mid:
                self.position.close()
                return
            elif self.position.is_short and current_price <= mid:
                self.position.close()
                return

        # Entry logic
        if not self.position:
            # BUY at demand zone
            if current_price <= demand * (1 + self.zone_buffer):
                # Momentum confirmation
                if self.momentum[-1] > -0.002:  # Not falling too hard
                    # Simple TP calculation - always use percentage
                    # Mid zone often too close when at demand
                    tp = current_price * (1 + self.take_profit)
                    sl = current_price * (1 - self.stop_loss)

                    # Only buy if TP is reasonably above current price
                    if tp > current_price * 1.001:  # At least 0.1% profit potential
                        self.buy(tp=tp, sl=sl)

            # SELL at supply zone
            elif current_price >= supply * (1 - self.zone_buffer):
                # Momentum confirmation
                if self.momentum[-1] < 0.002:  # Not rising too hard
                    # Simple TP calculation - always use percentage
                    # Mid zone often too close when at supply
                    tp = current_price * (1 - self.take_profit)
                    sl = current_price * (1 + self.stop_loss)

                    # Only sell if TP is reasonably below current price
                    if tp < current_price * 0.999:  # At least 0.1% profit potential
                        self.sell(tp=tp, sl=sl)


# Run backtest
print("\n" + "="*70)
print("RUNNING SUPPLY DEMAND ZONES BACKTEST")
print("="*70)

bt = Backtest(
    data,
    SupplyDemandZonesStrategy,
    cash=1000000,
    commission=0.001,
    exclusive_orders=True
)

baseline_stats = bt.run()
print(f"\n📊 RESULTS:")
print(baseline_stats)

# Optimization
print("\n" + "="*70)
print("OPTIMIZING FOR RETURN ON INVESTMENT")
print("="*70)

try:
    optimization_results = bt.optimize(
        lookback=[8, 10, 12],
        zone_buffer=[0.0008, 0.001, 0.0012],
        take_profit=[0.004, 0.005, 0.006],
        stop_loss=[0.0015, 0.002, 0.0025],
        maximize='Return [%]',
        return_heatmap=False
    )
    
    print(f"\n✨ OPTIMIZED RESULTS:")
    print(optimization_results)

    print(f"\n🎯 OPTIMAL PARAMETERS:")
    print(f"lookback: {optimization_results._strategy.lookback}")
    print(f"zone_buffer: {optimization_results._strategy.zone_buffer}")
    print(f"take_profit: {optimization_results._strategy.take_profit}")
    print(f"stop_loss: {optimization_results._strategy.stop_loss}")

except Exception as e:
    print(f"Optimization failed: {str(e)}")

bt.plot()