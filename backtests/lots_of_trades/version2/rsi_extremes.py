"""
RSI EXTREMES - Trade Oversold and Overbought Conditions
========================================================

Concept: Trade RSI extremes with divergence confirmation.
High win rate by only taking the best setups.

Focus: Quality over quantity for profitability


======================================================================
RUNNING RSI EXTREMES BACKTEST
======================================================================

📊 RESULTS:
Start                     2025-08-26 15:41:00
End                       2025-09-23 15:40:00
Duration                     27 days 23:59:00
Exposure Time [%]                    16.56994
Equity Final [$]                1918278.77135
Equity Peak [$]                 1918278.77135
Return [%]                          91.827877
Buy & Hold Return [%]                2.958633
Return (Ann.) [%]               267913.890322
Volatility (Ann.) [%]            61016.509898
Sharpe Ratio                         4.390843
Sortino Ratio                             inf
Calmar Ratio                    316101.068346
Max. Drawdown [%]                   -0.847558
Avg. Drawdown [%]                   -0.053552
Max. Drawdown Duration        0 days 13:04:00
Avg. Drawdown Duration        0 days 00:25:00
# Trades                                  379
Win Rate [%]                        84.432718
Best Trade [%]                       0.624312
Worst Trade [%]                     -0.410059
Avg. Trade [%]                       0.178768
Max. Trade Duration           0 days 01:00:00
Avg. Trade Duration           0 days 00:17:00
Profit Factor                       16.412048
Expectancy [%]                       0.178972
SQN                                  17.40523
_strategy                 RSIExtremesStrategy
_equity_curve                             ...
_trades                        Size  Entry...
dtype: object

======================================================================
OPTIMIZING FOR RETURN ON INVESTMENT
======================================================================
                                                                                                                                                                 
✨ OPTIMIZED RESULTS:
Start                     2025-08-26 15:41:00
End                       2025-09-23 15:40:00
Duration                     27 days 23:59:00
Exposure Time [%]                   30.687004
Equity Final [$]                2959239.19279
Equity Peak [$]                 2962900.58689
Return [%]                         195.923919
Buy & Hold Return [%]                2.958633
Return (Ann.) [%]             55958999.422938
Volatility (Ann.) [%]         21306222.634198
Sharpe Ratio                         2.626416
Sortino Ratio                             inf
Calmar Ratio                 109190592.689681
Max. Drawdown [%]                   -0.512489
Avg. Drawdown [%]                   -0.059401
Max. Drawdown Duration        0 days 12:39:00
Avg. Drawdown Duration        0 days 00:17:00
# Trades                                  762
Win Rate [%]                        82.283465
Best Trade [%]                       0.716524
Worst Trade [%]                     -0.496249
Avg. Trade [%]                       0.147837
Max. Trade Duration           0 days 01:01:00
Avg. Trade Duration           0 days 00:16:00
Profit Factor                       16.689837
Expectancy [%]                       0.148008
SQN                                 21.562725
_strategy                 RSIExtremesStrat...
_equity_curve                             ...
_trades                        Size  Entry...
dtype: object
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