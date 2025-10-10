"""
VOLUME SPIKE TRADER Strategy - Trade on Volume Explosions
=========================================================

Concept: Enter positions when volume suddenly spikes, indicating
strong interest. Volume precedes price movement.

Target: 4000+ trades on volume anomalies
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import warnings
warnings.filterwarnings('ignore')

print("📣 Moon Dev's VOLUME SPIKE TRADER Strategy 📣")
print("=" * 70)

# Load data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1m-4wks-data.csv'
print(f"📊 Loading BTC 1-minute data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Volume analysis
data['Volume_MA'] = data['Volume'].rolling(20).mean()
data['Volume_Std'] = data['Volume'].rolling(20).std()
data['Volume_ZScore'] = (data['Volume'] - data['Volume_MA']) / data['Volume_Std']
data['Volume_Spike'] = data['Volume'] / data['Volume_MA']

# Price direction during volume
data['Price_Direction'] = np.sign(data['Close'] - data['Open'])
data['Volume_Direction'] = data['Volume'] * data['Price_Direction']

# Cumulative volume delta
data['CVD'] = data['Volume_Direction'].rolling(10).sum()

print(f"✅ Loaded {len(data):,} 1-minute bars")


class VolumeSpikeTradingStrategy(Strategy):
    """
    Trade on sudden volume increases
    """
    
    # Parameters
    volume_spike_mult = 2.0    # Volume must be 2x average
    volume_zscore_min = 2.0    # Minimum z-score for entry
    take_profit = 0.003        # 0.3%
    stop_loss = 0.002          # 0.2%
    cvd_threshold = 1000       # Cumulative volume delta threshold
    hold_bars = 5              # Max bars to hold
    
    def init(self):
        self.volume_ma = self.I(lambda: self.data.Volume_MA)
        self.volume_zscore = self.I(lambda: self.data.Volume_ZScore)
        self.volume_spike = self.I(lambda: self.data.Volume_Spike)
        self.price_direction = self.I(lambda: self.data.Price_Direction)
        self.cvd = self.I(lambda: self.data.CVD)
        
        self.entry_bar = 0
        
    def next(self):
        if len(self.data) < 30:
            return
            
        current_price = self.data.Close[-1]
        current_volume = self.data.Volume[-1]
        vol_spike = self.volume_spike[-1] if self.volume_spike[-1] else 0
        vol_z = self.volume_zscore[-1] if self.volume_zscore[-1] and not np.isnan(self.volume_zscore[-1]) else 0
        current_cvd = self.cvd[-1] if self.cvd[-1] else 0
        price_dir = self.price_direction[-1]
        
        # Exit logic
        if self.position:
            bars_held = len(self.data) - self.entry_bar
            
            # Time exit
            if bars_held >= self.hold_bars:
                self.position.close()
                return
                
            # Exit on volume exhaustion
            if self.data.Volume[-1] < self.volume_ma[-1] * 0.5:
                self.position.close()
                return
        
        # Entry logic - trade volume spikes
        if not self.position:
            # Volume spike detected
            if vol_spike > self.volume_spike_mult and vol_z > self.volume_zscore_min:
                
                # BUY on bullish volume
                if price_dir > 0 and current_cvd > self.cvd_threshold:
                    tp = current_price * (1 + self.take_profit)
                    sl = current_price * (1 - self.stop_loss)
                    self.buy(tp=tp, sl=sl)
                    self.entry_bar = len(self.data)
                    
                # SELL on bearish volume
                elif price_dir < 0 and current_cvd < -self.cvd_threshold:
                    tp = current_price * (1 - self.take_profit)
                    sl = current_price * (1 + self.stop_loss)
                    self.sell(tp=tp, sl=sl)
                    self.entry_bar = len(self.data)


# Run backtest
print("\n" + "="*70)
print("RUNNING VOLUME SPIKE BACKTEST")
print("="*70)

bt = Backtest(
    data,
    VolumeSpikeTradingStrategy,
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
        volume_spike_mult=[1.5, 2.0, 2.5],
        volume_zscore_min=[1.5, 2.0, 2.5],
        take_profit=[0.002, 0.003, 0.004],
        stop_loss=[0.0015, 0.002, 0.0025],
        maximize='Return [%]',
        return_heatmap=False
    )
    
    print(f"\n✨ OPTIMIZED RESULTS:")
    print(optimization_results)
    print(f"\n🎯 PARAMETERS:")
    print(f"Volume Spike: {optimization_results._strategy.volume_spike_mult}x")
    print(f"Take Profit: {optimization_results._strategy.take_profit*100:.2f}%")
    
except Exception as e:
    print(f"Optimization failed: {str(e)}")

bt.plot()