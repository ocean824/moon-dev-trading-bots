"""
SUPPORT RESISTANCE FLIP - Trade S/R Role Reversals
===================================================

Concept: When resistance breaks, it becomes support (and vice versa).
Trade the retest of these flipped levels.

Focus: High probability retests of key levels
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import warnings
warnings.filterwarnings('ignore')

print("🔄 Moon Dev's SUPPORT RESISTANCE FLIP V2 🔄")
print("=" * 70)

# Load data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1m-4wks-data.csv'
print(f"📊 Loading BTC 1-minute data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Find swing highs and lows
data['Swing_High'] = data['High'][
    (data['High'] > data['High'].shift(1)) & 
    (data['High'] > data['High'].shift(-1))
]
data['Swing_Low'] = data['Low'][
    (data['Low'] < data['Low'].shift(1)) & 
    (data['Low'] < data['Low'].shift(-1))
]

# Recent levels
data['Resistance'] = data['Swing_High'].rolling(50, min_periods=1).max()
data['Support'] = data['Swing_Low'].rolling(50, min_periods=1).min()

# Track breakouts
data['Break_Above'] = (data['Close'] > data['Resistance'].shift(1)) & (data['Close'].shift(1) <= data['Resistance'].shift(1))
data['Break_Below'] = (data['Close'] < data['Support'].shift(1)) & (data['Close'].shift(1) >= data['Support'].shift(1))

# Store broken levels for retest
data['Broken_Resistance'] = np.where(data['Break_Above'], data['Resistance'].shift(1), np.nan)
data['Broken_Support'] = np.where(data['Break_Below'], data['Support'].shift(1), np.nan)

# Forward fill broken levels for 20 bars
data['Broken_Resistance'] = data['Broken_Resistance'].fillna(method='ffill', limit=20)
data['Broken_Support'] = data['Broken_Support'].fillna(method='ffill', limit=20)

# Volume for confirmation
data['Volume_MA'] = data['Volume'].rolling(20).mean()

print(f"✅ Loaded {len(data):,} 1-minute bars")


class SupportResistanceFlipStrategy(Strategy):
    """
    Trade retests of flipped support/resistance
    """
    
    retest_buffer = 0.001   # 0.1% buffer for retest
    take_profit = 0.007     # 0.7%
    stop_loss = 0.003       # 0.3%
    min_distance = 0.002    # Min distance for valid level
    require_volume = True   # Need volume on retest
    
    def init(self):
        self.resistance = self.I(lambda: self.data.Resistance)
        self.support = self.I(lambda: self.data.Support)
        self.broken_resistance = self.I(lambda: self.data.Broken_Resistance)
        self.broken_support = self.I(lambda: self.data.Broken_Support)
        self.volume_ma = self.I(lambda: self.data.Volume_MA)
        
    def next(self):
        if len(self.data) < 50:
            return
            
        current_price = self.data.Close[-1]
        current_volume = self.data.Volume[-1]
        volume_ma = self.volume_ma[-1] if self.volume_ma[-1] else 0
        
        # Get current levels
        resistance = self.resistance[-1] if self.resistance[-1] else current_price * 1.01
        support = self.support[-1] if self.support[-1] else current_price * 0.99
        broken_res = self.broken_resistance[-1] if not np.isnan(self.broken_resistance[-1]) else None
        broken_sup = self.broken_support[-1] if not np.isnan(self.broken_support[-1]) else None
        
        # Volume check
        has_volume = current_volume > volume_ma if self.require_volume else True
        
        # Exit at opposite level
        if self.position:
            if self.position.is_long and current_price >= resistance:
                self.position.close()
                return
            elif self.position.is_short and current_price <= support:
                self.position.close()
                return
        
        # Entry logic - trade retests
        if not self.position:
            
            # BUY on retest of broken resistance (now support)
            if broken_res and abs(current_price - broken_res) / broken_res < self.retest_buffer:
                # Check it's a valid retest from above
                if (current_price > broken_res and
                    self.data.Low[-1] <= broken_res * (1 + self.retest_buffer) and
                    has_volume):

                    # Ensure sufficient distance from current resistance
                    if (resistance - current_price) / current_price > self.min_distance:
                        # For longs: TP must be above current price
                        # Simple percentage-based approach to avoid complex logic
                        tp = current_price * (1 + self.take_profit)
                        sl = current_price * (1 - self.stop_loss)

                        # Validate TP > current > SL
                        if tp > current_price and sl < current_price:
                            self.buy(tp=tp, sl=sl)
                        return

            # SELL on retest of broken support (now resistance)
            if broken_sup and abs(current_price - broken_sup) / broken_sup < self.retest_buffer:
                # Check it's a valid retest from below
                if (current_price < broken_sup and
                    self.data.High[-1] >= broken_sup * (1 - self.retest_buffer) and
                    has_volume):

                    # Ensure sufficient distance from current support
                    if (current_price - support) / current_price > self.min_distance:
                        # For shorts: TP must be below current price
                        # Simple percentage-based approach to avoid complex logic
                        tp = current_price * (1 - self.take_profit)
                        sl = current_price * (1 + self.stop_loss)

                        # Validate TP < current < SL
                        if tp < current_price and sl > current_price:
                            self.sell(tp=tp, sl=sl)
                        return


# Run backtest
print("\n" + "="*70)
print("RUNNING SUPPORT RESISTANCE FLIP BACKTEST")
print("="*70)

bt = Backtest(
    data,
    SupportResistanceFlipStrategy,
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
        retest_buffer=[0.0008, 0.001, 0.0012],
        take_profit=[0.006, 0.007, 0.008],
        stop_loss=[0.002, 0.003, 0.004],
        min_distance=[0.0015, 0.002, 0.0025],
        maximize='Return [%]',
        return_heatmap=False
    )
    
    print(f"\n✨ OPTIMIZED RESULTS:")
    print(optimization_results)
    
except Exception as e:
    print(f"Optimization failed: {str(e)}")

bt.plot()