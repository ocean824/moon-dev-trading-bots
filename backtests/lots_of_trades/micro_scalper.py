"""
MICRO SCALPER Strategy - Ultra High Frequency Trading
=====================================================

Concept: Trade tiny price movements with extremely tight stops.
Enter on micro dips, exit on micro rallies. Pure scalping.

Target: 5000+ trades capturing 0.1-0.2% moves
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import warnings
warnings.filterwarnings('ignore')

print("⚡ Moon Dev's MICRO SCALPER Strategy ⚡")
print("=" * 70)

# Load data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1m-4wks-data.csv'
print(f"📊 Loading BTC 1-minute data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Calculate micro indicators
data['Micro_MA'] = data['Close'].rolling(3).mean()  # Ultra-fast MA
data['Price_Change'] = data['Close'].pct_change()
data['Micro_High'] = data['High'].rolling(5).max()  # 5-min high
data['Micro_Low'] = data['Low'].rolling(5).min()    # 5-min low
data['Range'] = data['Micro_High'] - data['Micro_Low']
data['Mid_Point'] = (data['Micro_High'] + data['Micro_Low']) / 2

# Micro momentum
data['Micro_Momentum'] = data['Close'].diff(2)

print(f"✅ Loaded {len(data):,} 1-minute bars")


class MicroScalperStrategy(Strategy):
    """
    Ultra high-frequency scalping strategy
    """
    
    # Parameters
    scalp_profit = 0.002   # 0.2% profit target
    scalp_loss = 0.001     # 0.1% stop loss
    min_range = 0.0005     # Minimum range to trade (0.05%)
    dip_threshold = 0.001  # Buy on 0.1% dips
    rally_threshold = 0.001 # Sell on 0.1% rallies
    max_hold_bars = 10     # Maximum bars to hold position
    
    def init(self):
        self.micro_ma = self.I(lambda: self.data.Micro_MA)
        self.micro_high = self.I(lambda: self.data.Micro_High)
        self.micro_low = self.I(lambda: self.data.Micro_Low)
        self.range = self.I(lambda: self.data.Range)
        self.mid_point = self.I(lambda: self.data.Mid_Point)
        self.micro_momentum = self.I(lambda: self.data.Micro_Momentum)
        
        # Track entry bar
        self.entry_bar = 0
        
    def next(self):
        if len(self.data) < 10:
            return
            
        current_price = self.data.Close[-1]
        current_range = self.range[-1] if self.range[-1] else 0
        
        # Exit logic
        if self.position:
            bars_held = len(self.data) - self.entry_bar
            
            # Time exit
            if bars_held >= self.max_hold_bars:
                self.position.close()
                return
                
            # Quick profit exit
            if self.position.pl_pct > self.scalp_profit * 0.5:
                self.position.close()
                return
        
        # Entry logic - only trade if range is sufficient
        if not self.position and current_range > self.min_range:
            micro_high = self.micro_high[-1]
            micro_low = self.micro_low[-1]
            mid = self.mid_point[-1]
            
            # BUY on micro dips
            if current_price < micro_low * (1 + self.dip_threshold):
                tp = current_price * (1 + self.scalp_profit)
                sl = current_price * (1 - self.scalp_loss)
                self.buy(tp=tp, sl=sl)
                self.entry_bar = len(self.data)
                
            # SELL on micro rallies
            elif current_price > micro_high * (1 - self.rally_threshold):
                tp = current_price * (1 - self.scalp_profit)
                sl = current_price * (1 + self.scalp_loss)
                self.sell(tp=tp, sl=sl)
                self.entry_bar = len(self.data)


# Run backtest
print("\n" + "="*70)
print("RUNNING MICRO SCALPER BACKTEST")
print("="*70)

bt = Backtest(
    data,
    MicroScalperStrategy,
    cash=1000000,
    commission=0.001,
    exclusive_orders=True
)

baseline_stats = bt.run()

print(f"\n📊 RESULTS:")
print(baseline_stats)

# Optimization
print("\n" + "="*70)
print("OPTIMIZING FOR MAXIMUM TRADES")
print("="*70)

try:
    optimization_results = bt.optimize(
        scalp_profit=[0.0015, 0.002, 0.0025],
        scalp_loss=[0.0008, 0.001, 0.0012],
        dip_threshold=[0.0008, 0.001, 0.0012],
        max_hold_bars=[8, 10, 12],
        maximize='# Trades',
        return_heatmap=False
    )
    
    print(f"\n✨ OPTIMIZED RESULTS:")
    print(optimization_results)
    print(f"\n🎯 OPTIMIZED PARAMETERS:")
    print(f"Scalp Profit: {optimization_results._strategy.scalp_profit*100:.2f}%")
    print(f"Scalp Loss: {optimization_results._strategy.scalp_loss*100:.3f}%")
    print(f"Max Hold: {optimization_results._strategy.max_hold_bars} bars")
    
except Exception as e:
    print(f"Optimization failed: {str(e)}")

bt.plot()