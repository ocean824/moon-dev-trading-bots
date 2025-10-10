"""
MOMENTUM IGNITION Strategy - Catch Momentum at the Start
========================================================

Concept: Detect when momentum is just starting to build and ride
the initial thrust. Exit quickly before momentum fades.

Target: 4000+ trades on momentum bursts
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's MOMENTUM IGNITION Strategy 🚀")
print("=" * 70)

# Load data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1m-4wks-data.csv'
print(f"📊 Loading BTC 1-minute data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Momentum indicators
data['Momentum_1'] = data['Close'].diff(1)
data['Momentum_3'] = data['Close'].diff(3) / 3
data['Momentum_5'] = data['Close'].diff(5) / 5

# Acceleration
data['Acceleration'] = data['Momentum_1'].diff(1)
data['Jerk'] = data['Acceleration'].diff(1)  # Rate of acceleration change

# Momentum strength
data['Momentum_Strength'] = abs(data['Momentum_3']) / data['Close']
data['Is_Strong'] = data['Momentum_Strength'] > data['Momentum_Strength'].rolling(20).mean()

# Consecutive momentum bars
data['Up_Streak'] = (data['Momentum_1'] > 0).groupby((data['Momentum_1'] <= 0).cumsum()).cumsum()
data['Down_Streak'] = (data['Momentum_1'] < 0).groupby((data['Momentum_1'] >= 0).cumsum()).cumsum()

print(f"✅ Loaded {len(data):,} 1-minute bars")


class MomentumIgnitionStrategy(Strategy):
    """
    Catch momentum explosions early
    """
    
    # Parameters
    min_momentum = 0.0005     # Minimum momentum to enter (0.05%)
    acceleration_min = 0.0001 # Minimum acceleration
    streak_min = 2            # Minimum consecutive bars
    take_profit = 0.003       # 0.3%
    stop_loss = 0.0015        # 0.15%
    max_bars = 5              # Exit after 5 bars
    
    def init(self):
        self.momentum_1 = self.I(lambda: self.data.Momentum_1)
        self.momentum_3 = self.I(lambda: self.data.Momentum_3)
        self.acceleration = self.I(lambda: self.data.Acceleration)
        self.jerk = self.I(lambda: self.data.Jerk)
        self.is_strong = self.I(lambda: self.data.Is_Strong)
        self.up_streak = self.I(lambda: self.data.Up_Streak)
        self.down_streak = self.I(lambda: self.data.Down_Streak)
        
        self.entry_bar = 0
        
    def next(self):
        if len(self.data) < 30:
            return
            
        current_price = self.data.Close[-1]
        mom1 = self.momentum_1[-1] if self.momentum_1[-1] else 0
        mom3 = self.momentum_3[-1] if self.momentum_3[-1] else 0
        accel = self.acceleration[-1] if self.acceleration[-1] else 0
        jerk = self.jerk[-1] if self.jerk[-1] else 0
        up_streak = self.up_streak[-1] if self.up_streak[-1] else 0
        down_streak = self.down_streak[-1] if self.down_streak[-1] else 0
        
        # Exit logic
        if self.position:
            bars_held = len(self.data) - self.entry_bar
            
            # Time exit
            if bars_held >= self.max_bars:
                self.position.close()
                return
                
            # Exit on momentum reversal
            if self.position.is_long and mom1 < 0:
                self.position.close()
                return
            elif self.position.is_short and mom1 > 0:
                self.position.close()
                return
        
        # Entry logic - catch ignition
        if not self.position:
            
            # Bullish ignition
            if (mom3 > self.min_momentum and
                accel > self.acceleration_min and
                jerk > 0 and  # Acceleration increasing
                up_streak >= self.streak_min):
                
                tp = current_price * (1 + self.take_profit)
                sl = current_price * (1 - self.stop_loss)
                self.buy(tp=tp, sl=sl)
                self.entry_bar = len(self.data)
                
            # Bearish ignition
            elif (mom3 < -self.min_momentum and
                  accel < -self.acceleration_min and
                  jerk < 0 and  # Acceleration increasing (negative)
                  down_streak >= self.streak_min):
                
                tp = current_price * (1 - self.take_profit)
                sl = current_price * (1 + self.stop_loss)
                self.sell(tp=tp, sl=sl)
                self.entry_bar = len(self.data)


# Run backtest
print("\n" + "="*70)
print("RUNNING MOMENTUM IGNITION BACKTEST")
print("="*70)

bt = Backtest(
    data,
    MomentumIgnitionStrategy,
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
        min_momentum=[0.0003, 0.0005, 0.0007],
        acceleration_min=[0.00005, 0.0001, 0.00015],
        take_profit=[0.002, 0.003, 0.004],
        stop_loss=[0.001, 0.0015, 0.002],
        maximize='Return [%]',
        return_heatmap=False
    )
    
    print(f"\n✨ OPTIMIZED RESULTS:")
    print(optimization_results)
    
except Exception as e:
    print(f"Optimization failed: {str(e)}")

bt.plot()