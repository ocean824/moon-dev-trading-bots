"""
SPEED TRADER Strategy - Ultra-Fast Price Velocity Trading
=========================================================

Concept: Trade based on price speed/velocity. When price moves
fast in one direction, jump on for a quick ride.

Target: 5000+ trades on rapid price movements
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import warnings
warnings.filterwarnings('ignore')

print("⚡ Moon Dev's SPEED TRADER Strategy ⚡")
print("=" * 70)

# Load data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1m-4wks-data.csv'
print(f"📊 Loading BTC 1-minute data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Speed calculations
data['Speed_1'] = abs(data['Close'].diff(1))  # 1-bar speed
data['Speed_3'] = abs(data['Close'].diff(3)) / 3  # 3-bar average speed
data['Direction'] = np.sign(data['Close'].diff(1))

# Velocity (directional speed)
data['Velocity_1'] = data['Close'].diff(1)
data['Velocity_3'] = data['Close'].diff(3) / 3

# Speed metrics
data['Speed_MA'] = data['Speed_1'].rolling(20).mean()
data['Speed_Ratio'] = data['Speed_1'] / (data['Speed_MA'] + 0.00001)
data['Is_Fast'] = data['Speed_Ratio'] > 2  # Moving 2x normal speed

# Acceleration
data['Speed_Accel'] = data['Speed_1'].diff(1)
data['Is_Accelerating'] = data['Speed_Accel'] > 0

# Quick move detection
data['Quick_Up'] = (data['Velocity_1'] > data['Speed_MA']) & (data['Direction'] > 0)
data['Quick_Down'] = (data['Velocity_1'] < -data['Speed_MA']) & (data['Direction'] < 0)

print(f"✅ Loaded {len(data):,} 1-minute bars")


class SpeedTraderStrategy(Strategy):
    """
    Trade ultra-fast price movements
    """
    
    # Parameters
    min_speed = 0.0005       # Minimum speed to enter (0.05%)
    speed_ratio_min = 1.5    # Minimum speed ratio
    take_profit = 0.002      # 0.2% quick profit
    stop_loss = 0.001        # 0.1% tight stop
    max_bars = 3             # Ultra-quick exit
    fade_extreme = True      # Fade extreme moves
    extreme_ratio = 3.0      # Extreme speed ratio
    
    def init(self):
        self.speed_1 = self.I(lambda: self.data.Speed_1)
        self.velocity_1 = self.I(lambda: self.data.Velocity_1)
        self.speed_ma = self.I(lambda: self.data.Speed_MA)
        self.speed_ratio = self.I(lambda: self.data.Speed_Ratio)
        self.is_fast = self.I(lambda: self.data.Is_Fast)
        self.is_accelerating = self.I(lambda: self.data.Is_Accelerating)
        self.quick_up = self.I(lambda: self.data.Quick_Up)
        self.quick_down = self.I(lambda: self.data.Quick_Down)
        self.direction = self.I(lambda: self.data.Direction)
        
        self.entry_bar = 0
        
    def next(self):
        if len(self.data) < 30:
            return
            
        current_price = self.data.Close[-1]
        speed = self.speed_1[-1] if self.speed_1[-1] else 0
        velocity = self.velocity_1[-1] if self.velocity_1[-1] else 0
        speed_ratio = self.speed_ratio[-1] if self.speed_ratio[-1] else 0
        is_fast = self.is_fast[-1] if self.is_fast[-1] else False
        is_accel = self.is_accelerating[-1] if self.is_accelerating[-1] else False
        direction = self.direction[-1] if self.direction[-1] else 0
        
        # Exit logic
        if self.position:
            bars_held = len(self.data) - self.entry_bar
            
            # Ultra-quick time exit
            if bars_held >= self.max_bars:
                self.position.close()
                return
                
            # Exit on speed reversal
            if self.position.is_long and velocity < 0:
                self.position.close()
                return
            elif self.position.is_short and velocity > 0:
                self.position.close()
                return
        
        # Entry logic
        if not self.position:
            
            # Momentum trades - go with speed
            if speed > self.min_speed and speed_ratio > self.speed_ratio_min:
                
                # BUY on upward speed
                if velocity > 0 and is_accel:
                    tp = current_price * (1 + self.take_profit)
                    sl = current_price * (1 - self.stop_loss)
                    self.buy(tp=tp, sl=sl)
                    self.entry_bar = len(self.data)
                    return
                    
                # SELL on downward speed
                elif velocity < 0 and is_accel:
                    tp = current_price * (1 - self.take_profit)
                    sl = current_price * (1 + self.stop_loss)
                    self.sell(tp=tp, sl=sl)
                    self.entry_bar = len(self.data)
                    return
            
            # Fade extreme moves
            if self.fade_extreme and speed_ratio > self.extreme_ratio:
                
                # Fade extreme up move
                if velocity > 0:
                    tp = current_price * (1 - self.take_profit)
                    sl = current_price * (1 + self.stop_loss)
                    self.sell(tp=tp, sl=sl)
                    self.entry_bar = len(self.data)
                    
                # Fade extreme down move
                elif velocity < 0:
                    tp = current_price * (1 + self.take_profit)
                    sl = current_price * (1 - self.stop_loss)
                    self.buy(tp=tp, sl=sl)
                    self.entry_bar = len(self.data)


# Run backtest
print("\n" + "="*70)
print("RUNNING SPEED TRADER BACKTEST")
print("="*70)

bt = Backtest(
    data,
    SpeedTraderStrategy,
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
        min_speed=[0.0003, 0.0005, 0.0007],
        speed_ratio_min=[1.2, 1.5, 1.8],
        take_profit=[0.0015, 0.002, 0.0025],
        stop_loss=[0.0008, 0.001, 0.0012],
        maximize='Return [%]',
        return_heatmap=False
    )
    
    print(f"\n✨ OPTIMIZED RESULTS:")
    print(optimization_results)
    print(f"\n🎯 PARAMETERS:")
    print(f"Min Speed: {optimization_results._strategy.min_speed*10000:.2f} bps")
    print(f"Speed Ratio: {optimization_results._strategy.speed_ratio_min}")
    print(f"Take Profit: {optimization_results._strategy.take_profit*100:.2f}%")
    print(f"Stop Loss: {optimization_results._strategy.stop_loss*100:.2f}%")
    
except Exception as e:
    print(f"Optimization failed: {str(e)}")

bt.plot()