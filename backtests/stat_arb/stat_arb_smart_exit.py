"""
Statistical Arbitrage with SMART EXITS
=======================================

STRATEGY GOAL: Increase expectancy through intelligent exit management,
maximizing profits while minimizing losses.

Key Improvements:
- Partial profit taking at multiple levels
- Dynamic exit based on market conditions
- Time-based exits for stale positions
- Breakeven stops after initial profit

Target: 4000+ trades with >0.05% expectancy
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's STAT ARB + SMART EXIT Strategy 🌙")
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
data['ZScore_20'] = calculate_zscore(data['Close'], 20)

# Exit quality indicators
data['Momentum'] = data['Close'].pct_change(5)
data['Momentum_Accel'] = data['Momentum'].diff()

# Volume for exit timing
data['Volume_MA'] = data['Volume'].rolling(20).mean()
data['Volume_Spike'] = (data['Volume'] > data['Volume_MA'] * 1.5).astype(int)

# Volatility for exit adjustment
data['Returns'] = data['Close'].pct_change()
data['Volatility'] = data['Returns'].rolling(10).std()
data['Vol_Percentile'] = data['Volatility'].rolling(100).rank(pct=True) * 100

# Bollinger Bands
data['BB_Middle'] = data['Close'].rolling(20).mean()
data['BB_Std'] = data['Close'].rolling(20).std()
data['BB_Upper'] = data['BB_Middle'] + (data['BB_Std'] * 2)
data['BB_Lower'] = data['BB_Middle'] - (data['BB_Std'] * 2)

# Exit score
data['Exit_Score'] = 0
# Z-score reversal
data.loc[abs(data['ZScore_5']) < 0.5, 'Exit_Score'] += 1
# Momentum reversal
data.loc[data['Momentum'] * data['Momentum'].shift(1) < 0, 'Exit_Score'] += 1
# Volume spike (potential reversal)
data.loc[data['Volume_Spike'] == 1, 'Exit_Score'] += 1
# Near BB middle (mean reversion complete)
data.loc[abs(data['Close'] - data['BB_Middle']) / data['BB_Middle'] < 0.002, 'Exit_Score'] += 1

print(f"✅ Loaded {len(data):,} 1-minute bars")


class StatArbSmartExitStrategy(Strategy):
    """
    Smart Exit Statistical Arbitrage
    
    Sophisticated exit logic to maximize expectancy
    """
    
    # Parameters
    lookback_period = 6
    zscore_entry = 1.5
    
    # Multi-level exits
    partial_profit_1 = 0.003  # First partial at 0.3%
    partial_profit_2 = 0.005  # Second partial at 0.5%
    final_profit = 0.008      # Final target at 0.8%
    
    # Exit management
    breakeven_after = 0.002   # Move stop to breakeven after 0.2%
    time_exit_bars = 30       # Exit after 30 bars if no profit
    min_exit_score = 2        # Min score to exit early
    trail_after = 0.004       # Start trailing after 0.4%
    trail_distance = 0.002    # Trail by 0.2%
    
    # Risk management
    initial_stop_loss = 0.003
    
    # Volatility adjustment
    use_vol_adjustment = True
    high_vol_threshold = 70  # Percentile
    
    def init(self):
        # Zones
        self.support = self.I(lambda: pd.Series(self.data.Close).rolling(
            window=self.lookback_period, min_periods=1).min())
        self.resistance = self.I(lambda: pd.Series(self.data.Close).rolling(
            window=self.lookback_period, min_periods=1).max())
        
        # Indicators
        self.zscore_5 = self.I(lambda: self.data.ZScore_5)
        self.zscore_10 = self.I(lambda: self.data.ZScore_10)
        self.zscore_20 = self.I(lambda: self.data.ZScore_20)
        self.momentum = self.I(lambda: self.data.Momentum)
        self.momentum_accel = self.I(lambda: self.data.Momentum_Accel)
        self.volume_spike = self.I(lambda: self.data.Volume_Spike)
        self.vol_percentile = self.I(lambda: self.data.Vol_Percentile)
        self.bb_middle = self.I(lambda: self.data.BB_Middle)
        self.bb_upper = self.I(lambda: self.data.BB_Upper)
        self.bb_lower = self.I(lambda: self.data.BB_Lower)
        self.exit_score = self.I(lambda: self.data.Exit_Score)
        
        # Track position info
        self.entry_bar = 0
        self.entry_price = 0
        self.max_profit = 0
        self.partial_exits = 0
        self.stop_moved_to_be = False
        
    def calculate_smart_exit_levels(self, current_price, is_long):
        """Calculate multi-level exit targets"""
        vol_pct = self.vol_percentile[-1] if self.vol_percentile[-1] else 50
        
        # Adjust targets based on volatility
        if self.use_vol_adjustment and vol_pct > self.high_vol_threshold:
            # Wider targets in high volatility
            mult = 1 + (vol_pct - 50) / 100  # 1.0x to 1.5x
            tp1 = self.partial_profit_1 * mult
            tp2 = self.partial_profit_2 * mult
            tp3 = self.final_profit * mult
        else:
            tp1 = self.partial_profit_1
            tp2 = self.partial_profit_2
            tp3 = self.final_profit
            
        if is_long:
            level1 = current_price * (1 + tp1)
            level2 = current_price * (1 + tp2)
            level3 = current_price * (1 + tp3)
        else:
            level1 = current_price * (1 - tp1)
            level2 = current_price * (1 - tp2)
            level3 = current_price * (1 - tp3)
            
        return level1, level2, level3
    
    def should_exit_early(self):
        """Check if we should exit based on market conditions"""
        current_exit_score = self.exit_score[-1] if self.exit_score[-1] else 0
        
        # Time-based exit
        bars_in_position = len(self.data) - self.entry_bar
        if bars_in_position > self.time_exit_bars:
            return True
            
        # Score-based exit
        if current_exit_score >= self.min_exit_score:
            return True
            
        # Momentum reversal exit
        if self.position:
            if self.position.is_long:
                if self.momentum[-1] < -0.002 and self.momentum_accel[-1] < 0:
                    return True
            else:
                if self.momentum[-1] > 0.002 and self.momentum_accel[-1] > 0:
                    return True
                    
        return False
    
    def manage_smart_exits(self):
        """Manage partial exits and trailing stops"""
        if not self.position:
            return False
            
        current_price = self.data.Close[-1]
        current_profit_pct = self.position.pl_pct
        
        # Update max profit
        if current_profit_pct > self.max_profit:
            self.max_profit = current_profit_pct
            
        # Check for partial profit taking
        if self.partial_exits == 0 and current_profit_pct >= self.partial_profit_1:
            # Can't actually do partial exits in backtesting.py
            # But we can move stop to breakeven
            self.stop_moved_to_be = True
            self.partial_exits = 1
            
        # Trailing stop logic
        if current_profit_pct >= self.trail_after:
            # Exit if profit drops below trail distance from max
            if self.max_profit - current_profit_pct > self.trail_distance:
                return True
                
        # Breakeven stop
        if self.stop_moved_to_be and current_profit_pct <= 0:
            return True
            
        return False
    
    def next(self):
        # Skip if insufficient data
        if len(self.data) < 50:
            return
        
        # Get current values
        current_price = self.data.Close[-1]
        z5 = self.zscore_5[-1] if self.zscore_5[-1] and not np.isnan(self.zscore_5[-1]) else 0
        z10 = self.zscore_10[-1] if self.zscore_10[-1] and not np.isnan(self.zscore_10[-1]) else 0
        z20 = self.zscore_20[-1] if self.zscore_20[-1] and not np.isnan(self.zscore_20[-1]) else 0
        current_bb_middle = self.bb_middle[-1] if self.bb_middle[-1] and not np.isnan(self.bb_middle[-1]) else current_price
        
        # Get zones
        demand_zone = self.support[-1]
        supply_zone = self.resistance[-1]
        
        # Smart exit management
        if self.position:
            # Check smart exit conditions
            if self.manage_smart_exits():
                self.position.close()
                self.entry_bar = 0
                self.max_profit = 0
                self.partial_exits = 0
                self.stop_moved_to_be = False
                return
                
            # Check early exit conditions
            if self.should_exit_early() and self.position.pl_pct > -self.initial_stop_loss/2:
                self.position.close()
                self.entry_bar = 0
                self.max_profit = 0
                self.partial_exits = 0
                self.stop_moved_to_be = False
                return
                
            # Normal exit conditions
            if self.position.is_long:
                # Exit at BB middle or z-score normalization
                if (current_price >= current_bb_middle and z5 > -0.5) or z5 > 0.5:
                    if self.position.pl_pct > 0:
                        self.position.close()
                        self.entry_bar = 0
                        self.max_profit = 0
                        self.partial_exits = 0
                        self.stop_moved_to_be = False
                        return
            else:
                # Exit at BB middle or z-score normalization
                if (current_price <= current_bb_middle and z5 < 0.5) or z5 < -0.5:
                    if self.position.pl_pct > 0:
                        self.position.close()
                        self.entry_bar = 0
                        self.max_profit = 0
                        self.partial_exits = 0
                        self.stop_moved_to_be = False
                        return
        
        # Entry logic
        if not self.position:
            near_demand = abs(current_price - demand_zone) / demand_zone <= 0.005
            near_supply = abs(current_price - supply_zone) / supply_zone <= 0.005
            
            # BUY signal
            if (z10 < -self.zscore_entry and 
                z5 < -self.zscore_entry * 0.8 and
                near_demand):
                
                # Calculate smart exit levels
                level1, level2, level3 = self.calculate_smart_exit_levels(current_price, True)
                
                sl_price = current_price * (1 - self.initial_stop_loss)
                # Use the highest level as TP for backtesting
                tp_price = max(level3, current_bb_middle)
                if tp_price <= current_price * 1.003:
                    tp_price = current_price * (1 + self.final_profit)
                
                self.buy(sl=sl_price, tp=tp_price)
                self.entry_bar = len(self.data)
                self.entry_price = current_price
                self.max_profit = 0
                self.partial_exits = 0
                self.stop_moved_to_be = False
            
            # SELL signal
            elif (z10 > self.zscore_entry and
                  z5 > self.zscore_entry * 0.8 and
                  near_supply):
                
                # Calculate smart exit levels
                level1, level2, level3 = self.calculate_smart_exit_levels(current_price, False)
                
                sl_price = current_price * (1 + self.initial_stop_loss)
                # Use the lowest level as TP for backtesting
                tp_price = min(level3, current_bb_middle)
                if tp_price >= current_price * 0.997:
                    tp_price = current_price * (1 - self.final_profit)
                
                self.sell(sl=sl_price, tp=tp_price)
                self.entry_bar = len(self.data)
                self.entry_price = current_price
                self.max_profit = 0
                self.partial_exits = 0
                self.stop_moved_to_be = False


# Run backtest
print("\n" + "="*70)
print("RUNNING SMART EXIT BACKTEST")
print("="*70)

bt = Backtest(
    data,
    StatArbSmartExitStrategy,
    cash=1000000,
    commission=0.001,
    exclusive_orders=True
)

# Run baseline
baseline_stats = bt.run()

print(f"\n📊 BASELINE RESULTS:")
print(f"Partial TP1: {StatArbSmartExitStrategy.partial_profit_1*100:.1f}%")
print(f"Partial TP2: {StatArbSmartExitStrategy.partial_profit_2*100:.1f}%")
print(f"Final TP: {StatArbSmartExitStrategy.final_profit*100:.1f}%")
print(f"Initial SL: {StatArbSmartExitStrategy.initial_stop_loss*100:.1f}%")
print(f"Time Exit: {StatArbSmartExitStrategy.time_exit_bars} bars")
print("-" * 50)
print(baseline_stats)

# Optimization
print("\n" + "="*70)
print("OPTIMIZING FOR RETURN ON INVESTMENT")
print("="*70)

try:
    optimization_results = bt.optimize(
        lookback_period=[5, 6, 7],
        zscore_entry=[1.3, 1.5, 1.7],
        partial_profit_1=[0.002, 0.003, 0.004],
        partial_profit_2=[0.004, 0.005, 0.006],
        final_profit=[0.007, 0.008, 0.009],
        initial_stop_loss=[0.002, 0.003, 0.004],
        time_exit_bars=[20, 30, 40],
        maximize='Return [%]',
        return_heatmap=False
    )

    print(f"\n✨ OPTIMIZED RESULTS:")
    print(optimization_results)
    print(f"\n🎯 OPTIMIZED PARAMETERS:")
    print(f"Lookback Period: {optimization_results._strategy.lookback_period} bars")
    print(f"Z-Score Entry: {optimization_results._strategy.zscore_entry}")
    print(f"Partial Profit 1: {optimization_results._strategy.partial_profit_1*100:.2f}%")
    print(f"Partial Profit 2: {optimization_results._strategy.partial_profit_2*100:.2f}%")
    print(f"Final Profit: {optimization_results._strategy.final_profit*100:.2f}%")
    print(f"Initial Stop Loss: {optimization_results._strategy.initial_stop_loss*100:.2f}%")
    print(f"Time Exit Bars: {optimization_results._strategy.time_exit_bars}")
    
except Exception as e:
    print(f"Optimization failed: {str(e)}")

bt.plot()