"""
RANGE BREAKOUT Strategy - Trade Micro Range Breakouts
======================================================

Concept: Identify tight 5-10 minute ranges and trade breakouts.
Quick entries on breaks with momentum continuation.

Target: 3500+ trades on range expansions
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import warnings
warnings.filterwarnings('ignore')

print("💥 Moon Dev's RANGE BREAKOUT Strategy 💥")
print("=" * 70)

# Load data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1m-4wks-data.csv'
print(f"📊 Loading BTC 1-minute data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Range calculations
data['Range_5'] = data['High'].rolling(5).max() - data['Low'].rolling(5).min()
data['Range_10'] = data['High'].rolling(10).max() - data['Low'].rolling(10).min()
data['Range_Pct'] = data['Range_5'] / data['Close']

# Breakout levels
data['Resistance_5'] = data['High'].rolling(5).max()
data['Support_5'] = data['Low'].rolling(5).min()
data['Resistance_10'] = data['High'].rolling(10).max()
data['Support_10'] = data['Low'].rolling(10).min()

# Compression detection
data['Compression'] = data['Range_5'] / data['Range_10']
data['Is_Compressed'] = data['Compression'] < 0.5

# Breakout strength
data['Breakout_Up'] = (data['Close'] > data['Resistance_5'].shift(1)).astype(int)
data['Breakout_Down'] = (data['Close'] < data['Support_5'].shift(1)).astype(int)

print(f"✅ Loaded {len(data):,} 1-minute bars")


class RangeBreakoutStrategy(Strategy):
    """
    Trade breakouts from compressed ranges
    """
    
    # Parameters
    min_range = 0.001      # Minimum range (0.1%)
    max_range = 0.005      # Maximum range (0.5%)  
    breakout_buffer = 0.0002  # Buffer above/below range
    take_profit = 0.004    # 0.4%
    stop_loss = 0.002      # 0.2%
    momentum_bars = 2      # Bars to confirm momentum
    
    def init(self):
        self.resistance_5 = self.I(lambda: self.data.Resistance_5)
        self.support_5 = self.I(lambda: self.data.Support_5)
        self.range_pct = self.I(lambda: self.data.Range_Pct)
        self.is_compressed = self.I(lambda: self.data.Is_Compressed)
        self.breakout_up = self.I(lambda: self.data.Breakout_Up)
        self.breakout_down = self.I(lambda: self.data.Breakout_Down)
        
    def next(self):
        if len(self.data) < 20:
            return
            
        current_price = self.data.Close[-1]
        current_range = self.range_pct[-1] if self.range_pct[-1] else 0
        resistance = self.resistance_5[-1]
        support = self.support_5[-1]
        
        # Exit on opposite breakout
        if self.position:
            if self.position.is_long and self.breakout_down[-1]:
                self.position.close()
                return
            elif self.position.is_short and self.breakout_up[-1]:
                self.position.close()
                return
        
        # Entry logic - trade breakouts from tight ranges
        if not self.position:
            # Check for tradeable range
            range_ok = self.min_range < current_range < self.max_range
            
            if range_ok:
                # Upside breakout
                if current_price > resistance * (1 + self.breakout_buffer):
                    # Confirm momentum
                    momentum_up = all(self.data.Close[-i] > self.data.Close[-i-1] 
                                     for i in range(1, min(self.momentum_bars+1, len(self.data))))
                    
                    if momentum_up:
                        tp = current_price * (1 + self.take_profit)
                        sl = support  # Stop at range bottom
                        if sl >= current_price:
                            sl = current_price * (1 - self.stop_loss)
                        self.buy(tp=tp, sl=sl)
                
                # Downside breakout
                elif current_price < support * (1 - self.breakout_buffer):
                    # Confirm momentum
                    momentum_down = all(self.data.Close[-i] < self.data.Close[-i-1] 
                                       for i in range(1, min(self.momentum_bars+1, len(self.data))))
                    
                    if momentum_down:
                        tp = current_price * (1 - self.take_profit)
                        sl = resistance  # Stop at range top
                        if sl <= current_price:
                            sl = current_price * (1 + self.stop_loss)
                        self.sell(tp=tp, sl=sl)


# Run backtest
print("\n" + "="*70)
print("RUNNING RANGE BREAKOUT BACKTEST")
print("="*70)

bt = Backtest(
    data,
    RangeBreakoutStrategy,
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
        min_range=[0.0008, 0.001, 0.0012],
        max_range=[0.004, 0.005, 0.006],
        take_profit=[0.003, 0.004, 0.005],
        stop_loss=[0.0015, 0.002, 0.0025],
        maximize='Return [%]',
        return_heatmap=False
    )
    
    print(f"\n✨ OPTIMIZED RESULTS:")
    print(optimization_results)
    
except Exception as e:
    print(f"Optimization failed: {str(e)}")

bt.plot()