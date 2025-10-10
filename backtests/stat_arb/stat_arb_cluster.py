"""
Statistical Arbitrage with CLUSTER ENTRY
=========================================

STRATEGY GOAL: Increase expectancy by entering positions in clusters,
scaling into winners and avoiding single-point failures.

Key Improvements:
- Scale into positions over multiple bars
- Average entry prices for better risk/reward
- Pyramid into winning positions
- Reduce position size on losing clusters

Target: 4000+ trades with >0.05% expectancy
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's STAT ARB + CLUSTER ENTRY Strategy 🌙")
print("=" * 70)

# Load data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1m-4wks-data.csv'
print(f"📊 Loading BTC 1-minute data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Calculate indicators
def calculate_zscore(series, period):
    mean = series.rolling(period).mean()
    std = series.rolling(period).std()
    zscore = (series - mean) / std
    return zscore

# Z-scores
data['ZScore_5'] = calculate_zscore(data['Close'], 5)
data['ZScore_10'] = calculate_zscore(data['Close'], 10)
data['ZScore_15'] = calculate_zscore(data['Close'], 15)

# Cluster detection
data['Oversold_Cluster'] = ((data['ZScore_5'] < -1.5) & 
                            (data['ZScore_10'] < -1.2)).astype(int)
data['Overbought_Cluster'] = ((data['ZScore_5'] > 1.5) & 
                              (data['ZScore_10'] > 1.2)).astype(int)

# Cluster strength (consecutive bars)
data['Oversold_Streak'] = data['Oversold_Cluster'].groupby(
    (data['Oversold_Cluster'] != data['Oversold_Cluster'].shift()).cumsum()
).cumsum()
data['Overbought_Streak'] = data['Overbought_Cluster'].groupby(
    (data['Overbought_Cluster'] != data['Overbought_Cluster'].shift()).cumsum()
).cumsum()

# Price velocity for cluster quality
data['Price_Velocity'] = data['Close'].pct_change(3).rolling(3).mean()

# Bollinger Bands
data['BB_Middle'] = data['Close'].rolling(20).mean()
data['BB_Std'] = data['Close'].rolling(20).std()

# Volume clustering
data['Volume_MA'] = data['Volume'].rolling(20).mean()
data['Volume_Cluster'] = (data['Volume'] > data['Volume_MA'] * 1.2).astype(int)

print(f"✅ Loaded {len(data):,} 1-minute bars")


class StatArbClusterStrategy(Strategy):
    """
    Cluster Entry Statistical Arbitrage
    
    Scales into positions over multiple bars for better average entry
    """
    
    # Parameters
    lookback_period = 6
    zscore_initial = 1.5  # First entry threshold
    zscore_add = 1.8      # Add to position threshold
    zscore_max = 2.2      # Maximum z-score for entries
    
    # Cluster parameters
    max_cluster_size = 3  # Max positions in a cluster
    cluster_window = 5    # Bars to build cluster
    min_cluster_strength = 2  # Min consecutive oversold/bought bars
    
    # Risk management
    cluster_take_profit = 0.008  # Higher TP for full cluster
    single_take_profit = 0.005   # Lower TP for single entry
    stop_loss = 0.003
    
    # Position sizing
    position_scale = 0.33  # Each entry is 33% of full position
    
    def init(self):
        # Zones
        self.support = self.I(lambda: pd.Series(self.data.Close).rolling(
            window=self.lookback_period, min_periods=1).min())
        self.resistance = self.I(lambda: pd.Series(self.data.Close).rolling(
            window=self.lookback_period, min_periods=1).max())
        
        # Indicators
        self.zscore_5 = self.I(lambda: self.data.ZScore_5)
        self.zscore_10 = self.I(lambda: self.data.ZScore_10)
        self.zscore_15 = self.I(lambda: self.data.ZScore_15)
        self.oversold_streak = self.I(lambda: self.data.Oversold_Streak)
        self.overbought_streak = self.I(lambda: self.data.Overbought_Streak)
        self.price_velocity = self.I(lambda: self.data.Price_Velocity)
        self.bb_middle = self.I(lambda: self.data.BB_Middle)
        self.volume_cluster = self.I(lambda: self.data.Volume_Cluster)
        
        # Track cluster entries
        self.cluster_entries = []
        self.cluster_direction = 0  # 1 for long, -1 for short
        self.cluster_start_bar = 0
        self.average_entry_price = 0
        
    def calculate_cluster_quality(self):
        """Assess quality of current cluster opportunity"""
        quality_score = 0
        
        # Z-score alignment
        if abs(self.zscore_5[-1]) > 1.5 and abs(self.zscore_10[-1]) > 1.2:
            quality_score += 1
        if abs(self.zscore_15[-1]) > 1.0:
            quality_score += 1
            
        # Cluster strength
        if self.oversold_streak[-1] >= self.min_cluster_strength or \
           self.overbought_streak[-1] >= self.min_cluster_strength:
            quality_score += 1
            
        # Volume confirmation
        if self.volume_cluster[-1] == 1:
            quality_score += 1
            
        return quality_score
    
    def should_add_to_cluster(self, is_long):
        """Check if we should add to existing cluster"""
        if len(self.cluster_entries) >= self.max_cluster_size:
            return False
            
        bars_since_start = len(self.data) - self.cluster_start_bar
        if bars_since_start > self.cluster_window:
            return False
            
        # Check if z-score is more extreme
        if is_long:
            return self.zscore_10[-1] < -self.zscore_add and \
                   self.zscore_10[-1] > -self.zscore_max
        else:
            return self.zscore_10[-1] > self.zscore_add and \
                   self.zscore_10[-1] < self.zscore_max
    
    def calculate_cluster_targets(self):
        """Calculate TP/SL based on cluster size"""
        cluster_size = len(self.cluster_entries)
        
        # Scale TP based on cluster size
        if cluster_size >= 3:
            take_profit = self.cluster_take_profit
        elif cluster_size == 2:
            take_profit = (self.cluster_take_profit + self.single_take_profit) / 2
        else:
            take_profit = self.single_take_profit
            
        return take_profit
    
    def next(self):
        # Skip if insufficient data
        if len(self.data) < 50:
            return
        
        # Get current values
        current_price = self.data.Close[-1]
        z5 = self.zscore_5[-1] if self.zscore_5[-1] and not np.isnan(self.zscore_5[-1]) else 0
        z10 = self.zscore_10[-1] if self.zscore_10[-1] and not np.isnan(self.zscore_10[-1]) else 0
        current_bb_middle = self.bb_middle[-1] if self.bb_middle[-1] and not np.isnan(self.bb_middle[-1]) else current_price
        
        # Get zones
        demand_zone = self.support[-1]
        supply_zone = self.resistance[-1]
        
        # Exit logic
        if self.position:
            # Check if cluster period expired
            bars_since_start = len(self.data) - self.cluster_start_bar
            
            if self.position.is_long:
                # Exit on reversal or target
                if z5 > 0 and self.position.pl_pct > 0:
                    self.position.close()
                    self.cluster_entries = []
                    self.cluster_direction = 0
                    return
                # Exit if cluster window expired with profit
                elif bars_since_start > self.cluster_window * 2 and self.position.pl_pct > 0:
                    self.position.close()
                    self.cluster_entries = []
                    self.cluster_direction = 0
                    return
            else:
                # Exit on reversal or target
                if z5 < 0 and self.position.pl_pct > 0:
                    self.position.close()
                    self.cluster_entries = []
                    self.cluster_direction = 0
                    return
                # Exit if cluster window expired with profit
                elif bars_since_start > self.cluster_window * 2 and self.position.pl_pct > 0:
                    self.position.close()
                    self.cluster_entries = []
                    self.cluster_direction = 0
                    return
        
        # Entry logic
        near_demand = abs(current_price - demand_zone) / demand_zone <= 0.005
        near_supply = abs(current_price - supply_zone) / supply_zone <= 0.005
        
        # Check cluster quality
        cluster_quality = self.calculate_cluster_quality()
        
        # New cluster or add to existing
        if not self.position:
            # BUY cluster start
            if z10 < -self.zscore_initial and near_demand and cluster_quality >= 2:
                # Calculate dynamic targets
                take_profit = self.calculate_cluster_targets()
                sl_price = current_price * (1 - self.stop_loss)
                tp_price = max(current_bb_middle, current_price * (1 + take_profit))
                if tp_price <= current_price * 1.002:
                    tp_price = current_price * (1 + take_profit)
                
                # Start cluster
                self.buy(sl=sl_price, tp=tp_price, size=self.position_scale)
                self.cluster_entries.append(current_price)
                self.cluster_direction = 1
                self.cluster_start_bar = len(self.data)
                self.average_entry_price = current_price
            
            # SELL cluster start
            elif z10 > self.zscore_initial and near_supply and cluster_quality >= 2:
                # Calculate dynamic targets
                take_profit = self.calculate_cluster_targets()
                sl_price = current_price * (1 + self.stop_loss)
                tp_price = min(current_bb_middle, current_price * (1 - take_profit))
                if tp_price >= current_price * 0.998:
                    tp_price = current_price * (1 - take_profit)
                
                # Start cluster
                self.sell(sl=sl_price, tp=tp_price, size=self.position_scale)
                self.cluster_entries.append(current_price)
                self.cluster_direction = -1
                self.cluster_start_bar = len(self.data)
                self.average_entry_price = current_price
        
        # Add to existing cluster
        elif self.position and len(self.cluster_entries) < self.max_cluster_size:
            bars_since_start = len(self.data) - self.cluster_start_bar
            
            if self.position.is_long and self.should_add_to_cluster(True):
                # Add to long cluster if price is better
                if current_price < self.average_entry_price and near_demand:
                    # Recalculate targets for larger position
                    take_profit = self.calculate_cluster_targets()
                    sl_price = current_price * (1 - self.stop_loss)
                    tp_price = max(current_bb_middle, current_price * (1 + take_profit))
                    
                    self.buy(sl=sl_price, tp=tp_price, size=self.position_scale)
                    self.cluster_entries.append(current_price)
                    # Update average entry
                    self.average_entry_price = np.mean(self.cluster_entries)
            
            elif self.position.is_short and self.should_add_to_cluster(False):
                # Add to short cluster if price is better
                if current_price > self.average_entry_price and near_supply:
                    # Recalculate targets for larger position
                    take_profit = self.calculate_cluster_targets()
                    sl_price = current_price * (1 + self.stop_loss)
                    tp_price = min(current_bb_middle, current_price * (1 - take_profit))
                    
                    self.sell(sl=sl_price, tp=tp_price, size=self.position_scale)
                    self.cluster_entries.append(current_price)
                    # Update average entry
                    self.average_entry_price = np.mean(self.cluster_entries)


# Run backtest
print("\n" + "="*70)
print("RUNNING CLUSTER ENTRY BACKTEST")
print("="*70)

bt = Backtest(
    data,
    StatArbClusterStrategy,
    cash=1000000,
    commission=0.001,
    exclusive_orders=True
)

# Run baseline
baseline_stats = bt.run()

print(f"\n📊 BASELINE RESULTS:")
print(f"Max Cluster Size: {StatArbClusterStrategy.max_cluster_size}")
print(f"Cluster Window: {StatArbClusterStrategy.cluster_window} bars")
print(f"Cluster TP: {StatArbClusterStrategy.cluster_take_profit*100:.2f}%")
print(f"Single TP: {StatArbClusterStrategy.single_take_profit*100:.2f}%")
print("-" * 50)
print(baseline_stats)

# Optimization
print("\n" + "="*70)
print("OPTIMIZING FOR RETURN ON INVESTMENT")
print("="*70)

try:
    optimization_results = bt.optimize(
        lookback_period=[5, 6, 7],
        zscore_initial=[1.3, 1.5, 1.7],
        max_cluster_size=[2, 3, 4],
        cluster_take_profit=[0.007, 0.008, 0.009],
        single_take_profit=[0.004, 0.005, 0.006],
        stop_loss=[0.002, 0.003, 0.004],
        maximize='Return [%]',
        return_heatmap=False
    )

    print(f"\n✨ OPTIMIZED RESULTS:")
    print(optimization_results)
    print(f"\n🎯 OPTIMIZED PARAMETERS:")
    print(f"Lookback Period: {optimization_results._strategy.lookback_period} bars")
    print(f"Z-Score Initial: {optimization_results._strategy.zscore_initial}")
    print(f"Max Cluster Size: {optimization_results._strategy.max_cluster_size}")
    print(f"Cluster Take Profit: {optimization_results._strategy.cluster_take_profit*100:.2f}%")
    print(f"Single Take Profit: {optimization_results._strategy.single_take_profit*100:.2f}%")
    print(f"Stop Loss: {optimization_results._strategy.stop_loss*100:.2f}%")

except Exception as e:
    print(f"Optimization failed: {str(e)}")

bt.plot()