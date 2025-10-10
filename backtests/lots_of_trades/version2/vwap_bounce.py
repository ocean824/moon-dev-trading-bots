"""
VWAP BOUNCE - Volume Weighted Average Price Reversals
======================================================

Concept: Trade bounces from VWAP, a key institutional level.
VWAP acts as dynamic support/resistance.

Focus: High probability reversals at VWAP
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import warnings
warnings.filterwarnings('ignore')

print("💹 Moon Dev's VWAP BOUNCE V2 💹")
print("=" * 70)

# Load data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1m-4wks-data.csv'
print(f"📊 Loading BTC 1-minute data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# VWAP calculation (resets daily)
data['Typical_Price'] = (data['High'] + data['Low'] + data['Close']) / 3
data['TPV'] = data['Typical_Price'] * data['Volume']

# Create daily groups
data['Date'] = data.index.date

# Calculate VWAP for each day
data['Cumulative_TPV'] = data.groupby('Date')['TPV'].cumsum()
data['Cumulative_Volume'] = data.groupby('Date')['Volume'].cumsum()
data['VWAP'] = data['Cumulative_TPV'] / data['Cumulative_Volume']

# VWAP bands
data['Squared_Diff'] = (data['Typical_Price'] - data['VWAP']) ** 2
# Fix the expanding calculation - reset index after groupby
data['Variance'] = data.groupby('Date')['Squared_Diff'].expanding().mean().reset_index(level=0, drop=True)
data['StdDev'] = np.sqrt(data['Variance'])

data['VWAP_Upper'] = data['VWAP'] + (data['StdDev'] * 2)
data['VWAP_Lower'] = data['VWAP'] - (data['StdDev'] * 2)

# Distance from VWAP
data['VWAP_Distance'] = (data['Close'] - data['VWAP']) / data['VWAP']

print(f"✅ Loaded {len(data):,} 1-minute bars")


class VWAPBounceStrategy(Strategy):
    """
    Trade bounces from VWAP levels
    """
    
    vwap_buffer = 0.001    # 0.1% buffer zone
    take_profit = 0.006    # 0.6%
    stop_loss = 0.003      # 0.3%
    min_distance = 0.003   # Min distance from VWAP for reversal
    use_bands = True       # Trade band bounces too
    
    def init(self):
        self.vwap = self.I(lambda: self.data.VWAP)
        self.vwap_upper = self.I(lambda: self.data.VWAP_Upper)
        self.vwap_lower = self.I(lambda: self.data.VWAP_Lower)
        self.vwap_distance = self.I(lambda: self.data.VWAP_Distance)
        
    def next(self):
        if len(self.data) < 50:
            return
            
        current_price = self.data.Close[-1]
        vwap = self.vwap[-1] if self.vwap[-1] else current_price
        vwap_upper = self.vwap_upper[-1] if self.vwap_upper[-1] else vwap * 1.01
        vwap_lower = self.vwap_lower[-1] if self.vwap_lower[-1] else vwap * 0.99
        distance = self.vwap_distance[-1] if self.vwap_distance[-1] else 0
        
        # Skip if VWAP not properly calculated
        if np.isnan(vwap) or vwap == 0:
            return
            
        # Exit at VWAP
        if self.position:
            if self.position.is_long and current_price >= vwap:
                self.position.close()
                return
            elif self.position.is_short and current_price <= vwap:
                self.position.close()
                return
        
        # Entry logic
        if not self.position:
            # BUY setups
            # Bounce from VWAP from below
            if abs(current_price - vwap) / vwap < self.vwap_buffer:
                if self.data.Close[-2] < vwap and current_price > self.data.Close[-2]:
                    tp = current_price * (1 + self.take_profit)
                    sl = current_price * (1 - self.stop_loss)
                    self.buy(tp=tp, sl=sl)
                    return
                    
            # Bounce from lower band
            if self.use_bands and current_price <= vwap_lower * (1 + self.vwap_buffer):
                if distance < -self.min_distance:
                    tp = min(vwap, current_price * (1 + self.take_profit))
                    sl = current_price * (1 - self.stop_loss)
                    self.buy(tp=tp, sl=sl)
                    return
                    
            # SELL setups
            # Bounce from VWAP from above
            if abs(current_price - vwap) / vwap < self.vwap_buffer:
                if self.data.Close[-2] > vwap and current_price < self.data.Close[-2]:
                    tp = current_price * (1 - self.take_profit)
                    sl = current_price * (1 + self.stop_loss)
                    self.sell(tp=tp, sl=sl)
                    return
                    
            # Bounce from upper band
            if self.use_bands and current_price >= vwap_upper * (1 - self.vwap_buffer):
                if distance > self.min_distance:
                    tp = max(vwap, current_price * (1 - self.take_profit))
                    sl = current_price * (1 + self.stop_loss)
                    self.sell(tp=tp, sl=sl)
                    return


# Run backtest
print("\n" + "="*70)
print("RUNNING VWAP BOUNCE BACKTEST")
print("="*70)

bt = Backtest(
    data,
    VWAPBounceStrategy,
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
        vwap_buffer=[0.0008, 0.001, 0.0012],
        take_profit=[0.005, 0.006, 0.007],
        stop_loss=[0.002, 0.003, 0.004],
        min_distance=[0.002, 0.003, 0.004],
        maximize='Return [%]',
        return_heatmap=False
    )
    
    print(f"\n✨ OPTIMIZED RESULTS:")
    print(optimization_results)
    
except Exception as e:
    print(f"Optimization failed: {str(e)}")

bt.plot()