"""
MEAN REVERSION SCALPER - Quick Z-Score Reversions
==================================================

Concept: Trade extreme z-score deviations with high win rate.
Focus on quick mean reversion with favorable risk/reward.

Focus: High win rate and profitability
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import warnings
warnings.filterwarnings('ignore')

print("🌊 Moon Dev's MEAN REVERSION SCALPER V2 🌊")
print("=" * 70)

# Load data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1m-4wks-data.csv'
print(f"📊 Loading BTC 1-minute data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Z-score calculations
def calculate_zscore(series, period):
    mean = series.rolling(period).mean()
    std = series.rolling(period).std()
    return (series - mean) / std

data['ZScore_5'] = calculate_zscore(data['Close'], 5)
data['ZScore_10'] = calculate_zscore(data['Close'], 10)
data['ZScore_20'] = calculate_zscore(data['Close'], 20)

# Bollinger Bands for targets
data['BB_Middle'] = data['Close'].rolling(20).mean()
data['BB_Std'] = data['Close'].rolling(20).std()
data['BB_Upper'] = data['BB_Middle'] + (data['BB_Std'] * 2)
data['BB_Lower'] = data['BB_Middle'] - (data['BB_Std'] * 2)

# Volume confirmation
data['Volume_MA'] = data['Volume'].rolling(20).mean()
data['High_Volume'] = data['Volume'] > data['Volume_MA']

print(f"✅ Loaded {len(data):,} 1-minute bars")


class MeanReversionScalperStrategy(Strategy):
    """
    High win rate mean reversion scalping
    """
    
    zscore_entry = 2.0    # Entry threshold
    zscore_exit = 0.5     # Exit when normalized
    take_profit = 0.006   # 0.6%
    stop_loss = 0.003     # 0.3%
    use_volume = True     # Require volume confirmation
    
    def init(self):
        self.zscore_5 = self.I(lambda: self.data.ZScore_5)
        self.zscore_10 = self.I(lambda: self.data.ZScore_10)
        self.bb_middle = self.I(lambda: self.data.BB_Middle)
        self.bb_upper = self.I(lambda: self.data.BB_Upper)
        self.bb_lower = self.I(lambda: self.data.BB_Lower)
        self.high_volume = self.I(lambda: self.data.High_Volume)
        
    def next(self):
        if len(self.data) < 30:
            return
            
        current_price = self.data.Close[-1]
        z5 = self.zscore_5[-1] if self.zscore_5[-1] and not np.isnan(self.zscore_5[-1]) else 0
        z10 = self.zscore_10[-1] if self.zscore_10[-1] and not np.isnan(self.zscore_10[-1]) else 0
        bb_middle = self.bb_middle[-1] if self.bb_middle[-1] else current_price
        has_volume = self.high_volume[-1] if self.use_volume else True
        
        # Exit logic
        if self.position:
            if self.position.is_long:
                # Exit when mean reverts
                if z5 > -self.zscore_exit or current_price >= bb_middle:
                    self.position.close()
                    return
            else:
                # Exit when mean reverts
                if z5 < self.zscore_exit or current_price <= bb_middle:
                    self.position.close()
                    return
        
        # Entry logic
        if not self.position:
            # BUY on extreme oversold
            if z5 < -self.zscore_entry and z10 < -self.zscore_entry * 0.8:
                if has_volume or z5 < -self.zscore_entry * 1.5:
                    tp = min(bb_middle, current_price * (1 + self.take_profit))
                    sl = current_price * (1 - self.stop_loss)
                    self.buy(tp=tp, sl=sl)
                    
            # SELL on extreme overbought
            elif z5 > self.zscore_entry and z10 > self.zscore_entry * 0.8:
                if has_volume or z5 > self.zscore_entry * 1.5:
                    tp = max(bb_middle, current_price * (1 - self.take_profit))
                    sl = current_price * (1 + self.stop_loss)
                    self.sell(tp=tp, sl=sl)


# Run backtest
print("\n" + "="*70)
print("RUNNING MEAN REVERSION BACKTEST")
print("="*70)

bt = Backtest(
    data,
    MeanReversionScalperStrategy,
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
        zscore_entry=[1.5, 2.0, 2.5],
        zscore_exit=[0.3, 0.5, 0.7],
        take_profit=[0.005, 0.006, 0.007],
        stop_loss=[0.002, 0.003, 0.004],
        maximize='Return [%]',
        return_heatmap=False
    )
    
    print(f"\n✨ OPTIMIZED RESULTS:")
    print(optimization_results)
    
except Exception as e:
    print(f"Optimization failed: {str(e)}")

bt.plot()