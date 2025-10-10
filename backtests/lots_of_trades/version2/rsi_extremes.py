"""
RSI EXTREMES - Trade Oversold and Overbought Conditions
========================================================

Concept: Trade RSI extremes with divergence confirmation.
High win rate by only taking the best setups.

Focus: Quality over quantity for profitability
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

print("📈 Moon Dev's RSI EXTREMES V2 📈")
print("=" * 70)

# Load data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1m-4wks-data.csv'
print(f"📊 Loading BTC 1-minute data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# RSI calculations
data['RSI_6'] = ta.rsi(data['Close'], length=6)
data['RSI_14'] = ta.rsi(data['Close'], length=14)
data['RSI_28'] = ta.rsi(data['Close'], length=28)

# RSI divergence
data['Price_High'] = data['High'].rolling(10).max()
data['Price_Low'] = data['Low'].rolling(10).min()
data['RSI_High'] = data['RSI_14'].rolling(10).max()
data['RSI_Low'] = data['RSI_14'].rolling(10).min()

# Bullish divergence: price makes lower low, RSI makes higher low
data['Bullish_Div'] = ((data['Low'] < data['Price_Low'].shift(1)) & 
                       (data['RSI_14'] > data['RSI_Low'].shift(1)))

# Bearish divergence: price makes higher high, RSI makes lower high
data['Bearish_Div'] = ((data['High'] > data['Price_High'].shift(1)) & 
                       (data['RSI_14'] < data['RSI_High'].shift(1)))

# Support/Resistance
data['Support'] = data['Low'].rolling(20).min()
data['Resistance'] = data['High'].rolling(20).max()

print(f"✅ Loaded {len(data):,} 1-minute bars")


class RSIExtremesStrategy(Strategy):
    """
    Trade RSI extremes with divergence confirmation
    """
    
    rsi_oversold = 25
    rsi_overbought = 75
    rsi_exit = 50
    take_profit = 0.007   # 0.7%
    stop_loss = 0.003     # 0.3%
    use_divergence = True
    
    def init(self):
        self.rsi_6 = self.I(lambda: self.data.RSI_6)
        self.rsi_14 = self.I(lambda: self.data.RSI_14)
        self.bullish_div = self.I(lambda: self.data.Bullish_Div)
        self.bearish_div = self.I(lambda: self.data.Bearish_Div)
        self.support = self.I(lambda: self.data.Support)
        self.resistance = self.I(lambda: self.data.Resistance)
        
    def next(self):
        if len(self.data) < 30:
            return
            
        current_price = self.data.Close[-1]
        rsi6 = self.rsi_6[-1] if self.rsi_6[-1] else 50
        rsi14 = self.rsi_14[-1] if self.rsi_14[-1] else 50
        has_bull_div = self.bullish_div[-1] if self.use_divergence else False
        has_bear_div = self.bearish_div[-1] if self.use_divergence else False
        support = self.support[-1]
        resistance = self.resistance[-1]
        
        # Exit logic
        if self.position:
            if self.position.is_long:
                # Exit at RSI neutral or overbought
                if rsi6 > self.rsi_exit or rsi14 > self.rsi_overbought - 5:
                    self.position.close()
                    return
            else:
                # Exit at RSI neutral or oversold
                if rsi6 < self.rsi_exit or rsi14 < self.rsi_oversold + 5:
                    self.position.close()
                    return
        
        # Entry logic
        if not self.position:
            # BUY on oversold with confirmation
            if rsi14 < self.rsi_oversold:
                # Extra confirmation
                if (rsi6 < self.rsi_oversold + 5 or has_bull_div):
                    # Near support is bonus
                    if current_price <= support * 1.01 or rsi14 < self.rsi_oversold - 5:
                        tp = current_price * (1 + self.take_profit)
                        sl = current_price * (1 - self.stop_loss)
                        self.buy(tp=tp, sl=sl)
                        return
                        
            # SELL on overbought with confirmation
            if rsi14 > self.rsi_overbought:
                # Extra confirmation
                if (rsi6 > self.rsi_overbought - 5 or has_bear_div):
                    # Near resistance is bonus
                    if current_price >= resistance * 0.99 or rsi14 > self.rsi_overbought + 5:
                        tp = current_price * (1 - self.take_profit)
                        sl = current_price * (1 + self.stop_loss)
                        self.sell(tp=tp, sl=sl)
                        return


# Run backtest
print("\n" + "="*70)
print("RUNNING RSI EXTREMES BACKTEST")
print("="*70)

bt = Backtest(
    data,
    RSIExtremesStrategy,
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
        rsi_oversold=[20, 25, 30],
        rsi_overbought=[70, 75, 80],
        take_profit=[0.006, 0.007, 0.008],
        stop_loss=[0.002, 0.003, 0.004],
        maximize='Return [%]',
        return_heatmap=False
    )
    
    print(f"\n✨ OPTIMIZED RESULTS:")
    print(optimization_results)
    
except Exception as e:
    print(f"Optimization failed: {str(e)}")

bt.plot()