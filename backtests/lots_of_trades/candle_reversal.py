"""
CANDLE PATTERN REVERSAL Strategy - 1-Minute Reversal Patterns
==============================================================

Concept: Trade classic reversal patterns on 1-minute charts.
Hammers, shooting stars, engulfing patterns for quick reversals.

Target: 3000+ trades on candlestick patterns
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import warnings
warnings.filterwarnings('ignore')

print("🕯️ Moon Dev's CANDLE REVERSAL Strategy 🕯️")
print("=" * 70)

# Load data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1m-4wks-data.csv'
print(f"📊 Loading BTC 1-minute data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Candle calculations
data['Body'] = abs(data['Close'] - data['Open'])
data['Upper_Wick'] = data['High'] - data[['Close', 'Open']].max(axis=1)
data['Lower_Wick'] = data[['Close', 'Open']].min(axis=1) - data['Low']
data['Range'] = data['High'] - data['Low']
data['Body_Pct'] = data['Body'] / (data['Range'] + 0.00001)

# Pattern detection
# Hammer: Small body at top, long lower wick
data['Is_Hammer'] = ((data['Lower_Wick'] > data['Body'] * 2) & 
                     (data['Upper_Wick'] < data['Body'] * 0.5) &
                     (data['Body_Pct'] < 0.35))

# Shooting Star: Small body at bottom, long upper wick
data['Is_Shooting_Star'] = ((data['Upper_Wick'] > data['Body'] * 2) & 
                            (data['Lower_Wick'] < data['Body'] * 0.5) &
                            (data['Body_Pct'] < 0.35))

# Bullish Engulfing
data['Is_Bullish_Engulfing'] = ((data['Close'] > data['Open']) &
                                (data['Open'] < data['Close'].shift(1)) &
                                (data['Close'] > data['Open'].shift(1)) &
                                (data['Body'] > data['Body'].shift(1)))

# Bearish Engulfing  
data['Is_Bearish_Engulfing'] = ((data['Close'] < data['Open']) &
                                (data['Open'] > data['Close'].shift(1)) &
                                (data['Close'] < data['Open'].shift(1)) &
                                (data['Body'] > data['Body'].shift(1)))

# Doji
data['Is_Doji'] = data['Body_Pct'] < 0.1

# Recent high/low for context
data['Recent_High'] = data['High'].rolling(10).max()
data['Recent_Low'] = data['Low'].rolling(10).min()

print(f"✅ Loaded {len(data):,} 1-minute bars")


class CandleReversalStrategy(Strategy):
    """
    Trade 1-minute candlestick reversal patterns
    """
    
    # Parameters
    min_body_size = 0.0001   # Minimum body size to avoid noise
    take_profit = 0.003      # 0.3%
    stop_loss = 0.002        # 0.2%
    near_extreme_pct = 0.002 # Must be within 0.2% of recent high/low
    hold_bars = 5            # Max hold time
    
    def init(self):
        self.is_hammer = self.I(lambda: self.data.Is_Hammer)
        self.is_shooting_star = self.I(lambda: self.data.Is_Shooting_Star)
        self.is_bullish_engulfing = self.I(lambda: self.data.Is_Bullish_Engulfing)
        self.is_bearish_engulfing = self.I(lambda: self.data.Is_Bearish_Engulfing)
        self.is_doji = self.I(lambda: self.data.Is_Doji)
        self.recent_high = self.I(lambda: self.data.Recent_High)
        self.recent_low = self.I(lambda: self.data.Recent_Low)
        self.body = self.I(lambda: self.data.Body)
        
        self.entry_bar = 0
        
    def next(self):
        if len(self.data) < 20:
            return
            
        current_price = self.data.Close[-1]
        current_body = self.body[-1] if self.body[-1] else 0
        recent_high = self.recent_high[-1]
        recent_low = self.recent_low[-1]
        
        # Exit logic
        if self.position:
            bars_held = len(self.data) - self.entry_bar
            
            # Time exit
            if bars_held >= self.hold_bars:
                self.position.close()
                return
        
        # Entry logic - trade reversal patterns
        if not self.position and current_body > self.min_body_size:
            
            # Check if near extremes
            near_low = abs(current_price - recent_low) / recent_low < self.near_extreme_pct
            near_high = abs(current_price - recent_high) / recent_high < self.near_extreme_pct
            
            # Bullish patterns at lows
            if near_low:
                if self.is_hammer[-1] or self.is_bullish_engulfing[-1]:
                    tp = current_price * (1 + self.take_profit)
                    sl = recent_low * 0.998  # Just below recent low
                    if sl >= current_price:
                        sl = current_price * (1 - self.stop_loss)
                    self.buy(tp=tp, sl=sl)
                    self.entry_bar = len(self.data)
                    return
                    
            # Bearish patterns at highs
            if near_high:
                if self.is_shooting_star[-1] or self.is_bearish_engulfing[-1]:
                    tp = current_price * (1 - self.take_profit)
                    sl = recent_high * 1.002  # Just above recent high
                    if sl <= current_price:
                        sl = current_price * (1 + self.stop_loss)
                    self.sell(tp=tp, sl=sl)
                    self.entry_bar = len(self.data)
                    return
            
            # Doji reversals (uncertainty)
            if self.is_doji[-1]:
                # Buy if at support
                if near_low and self.data.Close[-1] > self.data.Open[-1]:
                    tp = current_price * (1 + self.take_profit)
                    sl = current_price * (1 - self.stop_loss)
                    self.buy(tp=tp, sl=sl)
                    self.entry_bar = len(self.data)
                    
                # Sell if at resistance
                elif near_high and self.data.Close[-1] < self.data.Open[-1]:
                    tp = current_price * (1 - self.take_profit)
                    sl = current_price * (1 + self.stop_loss)
                    self.sell(tp=tp, sl=sl)
                    self.entry_bar = len(self.data)


# Run backtest
print("\n" + "="*70)
print("RUNNING CANDLE REVERSAL BACKTEST")
print("="*70)

bt = Backtest(
    data,
    CandleReversalStrategy,
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
        take_profit=[0.002, 0.003, 0.004],
        stop_loss=[0.0015, 0.002, 0.0025],
        near_extreme_pct=[0.0015, 0.002, 0.0025],
        hold_bars=[4, 5, 6],
        maximize='Return [%]',
        return_heatmap=False
    )
    
    print(f"\n✨ OPTIMIZED RESULTS:")
    print(optimization_results)
    
except Exception as e:
    print(f"Optimization failed: {str(e)}")

bt.plot()