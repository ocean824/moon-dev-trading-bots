"""
Statistical Arbitrage with VELOCITY FILTER
===========================================

STRATEGY GOAL: Increase expectancy by filtering trades based on price velocity,
only entering when momentum confirms the reversal.

Key Improvements:
- Price velocity (rate of change) confirmation
- Acceleration/deceleration patterns
- Velocity divergence detection
- Speed-based position sizing

Target: 4000+ trades with >0.04% expectancy
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's STAT ARB + VELOCITY FILTER Strategy 🌙")
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

# Velocity calculations
data['Velocity_1'] = data['Close'].diff(1)  # 1-bar velocity
data['Velocity_3'] = data['Close'].diff(3) / 3  # 3-bar average velocity
data['Velocity_5'] = data['Close'].diff(5) / 5  # 5-bar average velocity

# Acceleration (change in velocity)
data['Acceleration'] = data['Velocity_3'].diff(1)

# Velocity momentum
data['Velocity_MA'] = data['Velocity_3'].rolling(10).mean()
data['Velocity_Std'] = data['Velocity_3'].rolling(10).std()
data['Velocity_ZScore'] = (data['Velocity_3'] - data['Velocity_MA']) / data['Velocity_Std']

# Velocity divergence
data['Price_Velocity_Divergence'] = 0
# Price falling but velocity slowing (bullish divergence)
data.loc[(data['Close'] < data['Close'].shift(5)) & 
         (data['Velocity_3'] > data['Velocity_3'].shift(3)), 'Price_Velocity_Divergence'] = 1
# Price rising but velocity slowing (bearish divergence)
data.loc[(data['Close'] > data['Close'].shift(5)) & 
         (data['Velocity_3'] < data['Velocity_3'].shift(3)), 'Price_Velocity_Divergence'] = -1

# Speed indicator (absolute velocity)
data['Speed'] = abs(data['Velocity_3'])
data['Speed_MA'] = data['Speed'].rolling(20).mean()
data['High_Speed'] = (data['Speed'] > data['Speed_MA'] * 1.5).astype(int)

# Bollinger Bands
data['BB_Middle'] = data['Close'].rolling(20).mean()
data['BB_Std'] = data['Close'].rolling(20).std()

print(f"✅ Loaded {len(data):,} 1-minute bars")


class StatArbVelocityStrategy(Strategy):
    """
    Velocity-Filtered Statistical Arbitrage
    
    Only enters when velocity confirms the reversal is starting
    """
    
    # Parameters
    lookback_period = 6
    zscore_entry = 1.5
    zscore_exit = 0.2
    
    # Velocity filters
    min_velocity_reversal = 0.0001  # Minimum velocity change for reversal
    max_velocity_against = -0.0003  # Max velocity against position
    use_acceleration = True  # Use acceleration for confirmation
    acceleration_threshold = 0.00005  # Minimum acceleration
    
    # Divergence trading
    trade_divergences = True
    divergence_zscore = 1.2  # Lower threshold for divergences
    
    # Risk management
    take_profit = 0.006
    stop_loss = 0.002
    high_speed_tp_mult = 1.5  # Larger TP in fast markets
    
    def init(self):
        # Zones
        self.support = self.I(lambda: pd.Series(self.data.Close).rolling(
            window=self.lookback_period, min_periods=1).min())
        self.resistance = self.I(lambda: pd.Series(self.data.Close).rolling(
            window=self.lookback_period, min_periods=1).max())
        
        # Indicators
        self.zscore_5 = self.I(lambda: self.data.ZScore_5)
        self.zscore_10 = self.I(lambda: self.data.ZScore_10)
        self.velocity_1 = self.I(lambda: self.data.Velocity_1)
        self.velocity_3 = self.I(lambda: self.data.Velocity_3)
        self.velocity_5 = self.I(lambda: self.data.Velocity_5)
        self.acceleration = self.I(lambda: self.data.Acceleration)
        self.velocity_zscore = self.I(lambda: self.data.Velocity_ZScore)
        self.divergence = self.I(lambda: self.data.Price_Velocity_Divergence)
        self.high_speed = self.I(lambda: self.data.High_Speed)
        self.bb_middle = self.I(lambda: self.data.BB_Middle)
        
    def check_velocity_reversal(self, is_long):
        """Check if velocity supports the reversal"""
        v1 = self.velocity_1[-1] if self.velocity_1[-1] else 0
        v3 = self.velocity_3[-1] if self.velocity_3[-1] else 0
        v5 = self.velocity_5[-1] if self.velocity_5[-1] else 0
        accel = self.acceleration[-1] if self.acceleration[-1] else 0
        
        if is_long:
            # For long: velocity turning positive or decelerating down
            velocity_turning = v1 > self.min_velocity_reversal or v3 > -abs(self.max_velocity_against)
            velocity_improving = v3 > self.velocity_3[-2] if self.velocity_3[-2] else False
            
            if self.use_acceleration:
                # Positive acceleration (slowing the fall)
                acceleration_good = accel > self.acceleration_threshold
                return velocity_turning and (velocity_improving or acceleration_good)
            else:
                return velocity_turning and velocity_improving
        else:
            # For short: velocity turning negative or decelerating up
            velocity_turning = v1 < -self.min_velocity_reversal or v3 < abs(self.max_velocity_against)
            velocity_improving = v3 < self.velocity_3[-2] if self.velocity_3[-2] else False
            
            if self.use_acceleration:
                # Negative acceleration (slowing the rise)
                acceleration_good = accel < -self.acceleration_threshold
                return velocity_turning and (velocity_improving or acceleration_good)
            else:
                return velocity_turning and velocity_improving
    
    def calculate_velocity_targets(self, current_price):
        """Adjust targets based on market speed"""
        is_high_speed = self.high_speed[-1] == 1 if self.high_speed[-1] else False
        
        if is_high_speed:
            # Larger targets in fast markets
            tp = self.take_profit * self.high_speed_tp_mult
            sl = self.stop_loss * 1.2  # Slightly wider stop
        else:
            tp = self.take_profit
            sl = self.stop_loss
            
        return tp, sl
    
    def next(self):
        # Skip if insufficient data
        if len(self.data) < 50:
            return
        
        # Get current values
        current_price = self.data.Close[-1]
        z5 = self.zscore_5[-1] if self.zscore_5[-1] and not np.isnan(self.zscore_5[-1]) else 0
        z10 = self.zscore_10[-1] if self.zscore_10[-1] and not np.isnan(self.zscore_10[-1]) else 0
        current_divergence = self.divergence[-1] if self.divergence[-1] else 0
        current_bb_middle = self.bb_middle[-1] if self.bb_middle[-1] and not np.isnan(self.bb_middle[-1]) else current_price
        velocity_z = self.velocity_zscore[-1] if self.velocity_zscore[-1] and not np.isnan(self.velocity_zscore[-1]) else 0
        
        # Get zones
        demand_zone = self.support[-1]
        supply_zone = self.resistance[-1]
        
        # Exit logic
        if self.position:
            current_velocity = self.velocity_3[-1] if self.velocity_3[-1] else 0
            
            if self.position.is_long:
                # Exit if velocity turns strongly negative
                if current_velocity < self.max_velocity_against:
                    self.position.close()
                    return
                # Normal exit
                if z5 > -self.zscore_exit and self.position.pl_pct > 0:
                    self.position.close()
                    return
            else:
                # Exit if velocity turns strongly positive
                if current_velocity > -self.max_velocity_against:
                    self.position.close()
                    return
                # Normal exit
                if z5 < self.zscore_exit and self.position.pl_pct > 0:
                    self.position.close()
                    return
        
        # Entry logic
        if not self.position:
            near_demand = abs(current_price - demand_zone) / demand_zone <= 0.005
            near_supply = abs(current_price - supply_zone) / supply_zone <= 0.005
            
            # Get dynamic targets
            tp_pct, sl_pct = self.calculate_velocity_targets(current_price)
            
            # BUY signals
            buy_signal = False
            
            # Standard oversold with velocity confirmation
            if z5 < -self.zscore_entry and z10 < -self.zscore_entry * 0.8:
                if near_demand and self.check_velocity_reversal(True):
                    buy_signal = True
            
            # Bullish divergence trade
            elif self.trade_divergences and current_divergence == 1:
                if z5 < -self.divergence_zscore and near_demand:
                    if velocity_z > -1:  # Velocity not extremely negative
                        buy_signal = True
            
            # Extreme velocity reversal
            elif velocity_z < -2 and self.acceleration[-1] > self.acceleration_threshold * 2:
                if near_demand:
                    buy_signal = True
            
            if buy_signal:
                sl_price = current_price * (1 - sl_pct)
                tp_price = max(current_bb_middle, current_price * (1 + tp_pct))
                if tp_price <= current_price * 1.002:
                    tp_price = current_price * (1 + tp_pct)
                
                self.buy(sl=sl_price, tp=tp_price)
            
            # SELL signals
            else:
                sell_signal = False
                
                # Standard overbought with velocity confirmation
                if z5 > self.zscore_entry and z10 > self.zscore_entry * 0.8:
                    if near_supply and self.check_velocity_reversal(False):
                        sell_signal = True
                
                # Bearish divergence trade
                elif self.trade_divergences and current_divergence == -1:
                    if z5 > self.divergence_zscore and near_supply:
                        if velocity_z < 1:  # Velocity not extremely positive
                            sell_signal = True
                
                # Extreme velocity reversal
                elif velocity_z > 2 and self.acceleration[-1] < -self.acceleration_threshold * 2:
                    if near_supply:
                        sell_signal = True
                
                if sell_signal:
                    sl_price = current_price * (1 + sl_pct)
                    tp_price = min(current_bb_middle, current_price * (1 - tp_pct))
                    if tp_price >= current_price * 0.998:
                        tp_price = current_price * (1 - tp_pct)
                    
                    self.sell(sl=sl_price, tp=tp_price)


# Run backtest
print("\n" + "="*70)
print("RUNNING VELOCITY FILTER BACKTEST")
print("="*70)

bt = Backtest(
    data,
    StatArbVelocityStrategy,
    cash=1000000,
    commission=0.001,
    exclusive_orders=True
)

# Run baseline
baseline_stats = bt.run()

print(f"\n📊 BASELINE RESULTS:")
print(f"Min Velocity Reversal: {StatArbVelocityStrategy.min_velocity_reversal*10000:.2f} bps")
print(f"Use Acceleration: {StatArbVelocityStrategy.use_acceleration}")
print(f"Take Profit: {StatArbVelocityStrategy.take_profit*100:.2f}%")
print(f"Stop Loss: {StatArbVelocityStrategy.stop_loss*100:.2f}%")
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
        min_velocity_reversal=[0.00008, 0.0001, 0.00012],
        acceleration_threshold=[0.00003, 0.00005, 0.00007],
        take_profit=[0.005, 0.006, 0.007],
        stop_loss=[0.0015, 0.002, 0.0025],
        maximize='Return [%]',
        return_heatmap=False
    )

    print(f"\n✨ OPTIMIZED RESULTS:")
    print(optimization_results)
    print(f"\n🎯 OPTIMIZED PARAMETERS:")
    print(f"Lookback Period: {optimization_results._strategy.lookback_period} bars")
    print(f"Z-Score Entry: {optimization_results._strategy.zscore_entry}")
    print(f"Min Velocity Reversal: {optimization_results._strategy.min_velocity_reversal*10000:.2f} bps")
    print(f"Acceleration Threshold: {optimization_results._strategy.acceleration_threshold*10000:.2f} bps")
    print(f"Take Profit: {optimization_results._strategy.take_profit*100:.2f}%")
    print(f"Stop Loss: {optimization_results._strategy.stop_loss*100:.2f}%")
    
except Exception as e:
    print(f"Optimization failed: {str(e)}")

bt.plot()