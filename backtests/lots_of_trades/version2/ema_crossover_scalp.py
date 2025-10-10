"""
EMA CROSSOVER SCALP - Fast Exponential Moving Average Crosses
==============================================================

Concept: Trade fast EMA crossovers with momentum confirmation.
Quick entries and exits on trend changes.

Focus: Catch micro trends early
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import warnings
warnings.filterwarnings('ignore')

print("📊 Moon Dev's EMA CROSSOVER SCALP V2 📊")
print("=" * 70)

# Load data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1m-4wks-data.csv'
print(f"📊 Loading BTC 1-minute data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# EMA calculations
data['EMA_3'] = data['Close'].ewm(span=3, adjust=False).mean()
data['EMA_8'] = data['Close'].ewm(span=8, adjust=False).mean()
data['EMA_21'] = data['Close'].ewm(span=21, adjust=False).mean()

# Crossover signals
data['Fast_Above'] = data['EMA_3'] > data['EMA_8']
data['Bullish_Cross'] = (data['Fast_Above']) & (~data['Fast_Above'].shift(1).fillna(False))
data['Bearish_Cross'] = (~data['Fast_Above']) & (data['Fast_Above'].shift(1).fillna(False))

# Trend filter
data['Trend_Up'] = data['Close'] > data['EMA_21']
data['Trend_Down'] = data['Close'] < data['EMA_21']

# Momentum
data['Momentum'] = data['Close'].pct_change(5)
data['Volume_Surge'] = data['Volume'] > data['Volume'].rolling(20).mean() * 1.5

print(f"✅ Loaded {len(data):,} 1-minute bars")


class EMACrossoverScalpStrategy(Strategy):
    """
    Trade fast EMA crossovers
    """
    
    take_profit = 0.005    # 0.5%
    stop_loss = 0.003      # 0.3%
    use_trend_filter = True
    use_momentum = True
    min_ema_gap = 0.0001   # Minimum gap between EMAs
    
    def init(self):
        self.ema_3 = self.I(lambda: self.data.EMA_3)
        self.ema_8 = self.I(lambda: self.data.EMA_8)
        self.ema_21 = self.I(lambda: self.data.EMA_21)
        self.bullish_cross = self.I(lambda: self.data.Bullish_Cross)
        self.bearish_cross = self.I(lambda: self.data.Bearish_Cross)
        self.trend_up = self.I(lambda: self.data.Trend_Up)
        self.trend_down = self.I(lambda: self.data.Trend_Down)
        self.momentum = self.I(lambda: self.data.Momentum)
        self.volume_surge = self.I(lambda: self.data.Volume_Surge)
        
    def next(self):
        if len(self.data) < 30:
            return
            
        current_price = self.data.Close[-1]
        ema3 = self.ema_3[-1]
        ema8 = self.ema_8[-1]
        ema21 = self.ema_21[-1]
        ema_gap = abs(ema3 - ema8) / ema8
        
        # Trend and momentum filters
        in_uptrend = self.trend_up[-1] if self.use_trend_filter else True
        in_downtrend = self.trend_down[-1] if self.use_trend_filter else True
        momentum = self.momentum[-1] if self.momentum[-1] else 0
        has_volume = self.volume_surge[-1]
        
        # Exit on opposite cross or target
        if self.position:
            if self.position.is_long:
                # Exit on bearish cross or trend change
                if self.bearish_cross[-1] or not in_uptrend:
                    self.position.close()
                    return
            else:
                # Exit on bullish cross or trend change
                if self.bullish_cross[-1] or not in_downtrend:
                    self.position.close()
                    return
        
        # Entry logic
        if not self.position and ema_gap > self.min_ema_gap:
            
            # BUY on bullish crossover
            if self.bullish_cross[-1]:
                # Apply filters
                if in_uptrend:
                    momentum_ok = momentum > -0.001 if self.use_momentum else True
                    
                    if momentum_ok:
                        # Better entry with volume
                        tp_mult = 1.2 if has_volume else 1.0
                        tp = current_price * (1 + self.take_profit * tp_mult)
                        # Use percentage-based stop loss, not EMA
                        sl = current_price * (1 - self.stop_loss)

                        self.buy(tp=tp, sl=sl)
                        return
                            
            # SELL on bearish crossover
            elif self.bearish_cross[-1]:
                # Apply filters
                if in_downtrend:
                    momentum_ok = momentum < 0.001 if self.use_momentum else True
                    
                    if momentum_ok:
                        # Better entry with volume
                        tp_mult = 1.2 if has_volume else 1.0
                        tp = current_price * (1 - self.take_profit * tp_mult)
                        # Use percentage-based stop loss, not EMA
                        sl = current_price * (1 + self.stop_loss)

                        self.sell(tp=tp, sl=sl)
                        return


# Run backtest
print("\n" + "="*70)
print("RUNNING EMA CROSSOVER BACKTEST")
print("="*70)

bt = Backtest(
    data,
    EMACrossoverScalpStrategy,
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
        take_profit=[0.004, 0.005, 0.006],
        stop_loss=[0.002, 0.003, 0.004],
        min_ema_gap=[0.00008, 0.0001, 0.00012],
        maximize='Return [%]',
        return_heatmap=False
    )
    
    print(f"\n✨ OPTIMIZED RESULTS:")
    print(optimization_results)
    
except Exception as e:
    print(f"Optimization failed: {str(e)}")

bt.plot()