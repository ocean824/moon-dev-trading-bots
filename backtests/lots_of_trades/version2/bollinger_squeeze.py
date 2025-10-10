"""
BOLLINGER SQUEEZE - Volatility Compression Breakouts
====================================================

Concept: Trade breakouts from Bollinger Band squeezes.
When bands compress, volatility expansion follows.

Focus: Catch profitable volatility expansions
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import warnings
warnings.filterwarnings('ignore')

print("📊 Moon Dev's BOLLINGER SQUEEZE V2 📊")
print("=" * 70)

# Load data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1m-4wks-data.csv'
print(f"📊 Loading BTC 1-minute data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Bollinger Bands
data['BB_Middle'] = data['Close'].rolling(20).mean()
data['BB_Std'] = data['Close'].rolling(20).std()
data['BB_Upper'] = data['BB_Middle'] + (data['BB_Std'] * 2)
data['BB_Lower'] = data['BB_Middle'] - (data['BB_Std'] * 2)
data['BB_Width'] = data['BB_Upper'] - data['BB_Lower']
data['BB_Width_Pct'] = data['BB_Width'] / data['BB_Middle']

# Squeeze detection
data['BB_Width_MA'] = data['BB_Width_Pct'].rolling(50).mean()
data['Is_Squeezed'] = data['BB_Width_Pct'] < data['BB_Width_MA'] * 0.7

# Keltner Channels for comparison
data['TR'] = pd.concat([
    data['High'] - data['Low'],
    abs(data['High'] - data['Close'].shift()),
    abs(data['Low'] - data['Close'].shift())
], axis=1).max(axis=1)
data['ATR'] = data['TR'].rolling(20).mean()
data['KC_Upper'] = data['BB_Middle'] + (data['ATR'] * 2)
data['KC_Lower'] = data['BB_Middle'] - (data['ATR'] * 2)

# Squeeze: BB inside KC
data['TTM_Squeeze'] = (data['BB_Upper'] < data['KC_Upper']) & (data['BB_Lower'] > data['KC_Lower'])

print(f"✅ Loaded {len(data):,} 1-minute bars")


class BollingerSqueezeStrategy(Strategy):
    """
    Trade volatility expansion from squeezes
    """
    
    min_squeeze_bars = 3   # Minimum bars in squeeze
    breakout_buffer = 0.0002  # Buffer for breakout
    take_profit = 0.008    # 0.8% profit
    stop_loss = 0.003      # 0.3% stop
    use_ttm = False        # Use TTM squeeze
    
    def init(self):
        self.bb_upper = self.I(lambda: self.data.BB_Upper)
        self.bb_lower = self.I(lambda: self.data.BB_Lower)
        self.bb_middle = self.I(lambda: self.data.BB_Middle)
        self.is_squeezed = self.I(lambda: self.data.Is_Squeezed)
        self.ttm_squeeze = self.I(lambda: self.data.TTM_Squeeze)
        
        self.squeeze_count = 0
        
    def next(self):
        if len(self.data) < 50:
            return
            
        current_price = self.data.Close[-1]
        bb_upper = self.bb_upper[-1]
        bb_lower = self.bb_lower[-1]
        bb_middle = self.bb_middle[-1]
        
        # Track squeeze duration
        in_squeeze = self.ttm_squeeze[-1] if self.use_ttm else self.is_squeezed[-1]
        
        if in_squeeze:
            self.squeeze_count += 1
        else:
            # Check if exiting squeeze
            if self.squeeze_count >= self.min_squeeze_bars:
                # Breakout trade opportunity
                if not self.position:
                    # Upside breakout
                    if current_price > bb_upper * (1 + self.breakout_buffer):
                        tp = current_price * (1 + self.take_profit)
                        sl = bb_middle
                        if sl >= current_price:
                            sl = current_price * (1 - self.stop_loss)
                        self.buy(tp=tp, sl=sl)
                        
                    # Downside breakout
                    elif current_price < bb_lower * (1 - self.breakout_buffer):
                        tp = current_price * (1 - self.take_profit)
                        sl = bb_middle
                        if sl <= current_price:
                            sl = current_price * (1 + self.stop_loss)
                        self.sell(tp=tp, sl=sl)
                        
            self.squeeze_count = 0
        
        # Exit at opposite band
        if self.position:
            if self.position.is_long and current_price >= bb_upper:
                self.position.close()
            elif self.position.is_short and current_price <= bb_lower:
                self.position.close()


# Run backtest
print("\n" + "="*70)
print("RUNNING BOLLINGER SQUEEZE BACKTEST")
print("="*70)

bt = Backtest(
    data,
    BollingerSqueezeStrategy,
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
        min_squeeze_bars=[2, 3, 4],
        take_profit=[0.006, 0.008, 0.01],
        stop_loss=[0.002, 0.003, 0.004],
        maximize='Return [%]',
        return_heatmap=False
    )
    
    print(f"\n✨ OPTIMIZED RESULTS:")
    print(optimization_results)
    
except Exception as e:
    print(f"Optimization failed: {str(e)}")

bt.plot()