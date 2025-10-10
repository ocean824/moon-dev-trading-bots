"""
MULTI-TIMEFRAME RSI - Multiple RSI Confirmations
=================================================

Concept: Use RSI from multiple timeframes for stronger signals.
Only trade when 1m, 5m, and 15m RSI all agree on direction.

Focus: PROFITABILITY with high volume


======================================================================
RUNNING MULTI-TIMEFRAME RSI BACKTEST
======================================================================

📊 BASELINE RESULTS:
Start                     2025-08-26 15:41:00
End                       2025-09-23 15:40:00
Duration                     27 days 23:59:00
Exposure Time [%]                    6.349206
Equity Final [$]                1133138.22565
Equity Peak [$]                 1133200.95565
Return [%]                          13.313823
Buy & Hold Return [%]                2.958633
Return (Ann.) [%]                  362.924255
Volatility (Ann.) [%]               36.819138
Sharpe Ratio                         9.856946
Sortino Ratio                      134.101529
Calmar Ratio                       396.529949
Max. Drawdown [%]                   -0.915251
Avg. Drawdown [%]                    -0.07409
Max. Drawdown Duration        3 days 03:18:00
Avg. Drawdown Duration        0 days 02:21:00
# Trades                                   76
Win Rate [%]                        76.315789
Best Trade [%]                       0.716524
Worst Trade [%]                     -0.408499
Avg. Trade [%]                       0.173258
Max. Trade Duration           0 days 01:19:00
Avg. Trade Duration           0 days 00:33:00
Profit Factor                         6.80216
Expectancy [%]                       0.173548
SQN                                  6.304555
_strategy                   MultiTimeframeRSI
_equity_curve                             ...
_trades                       Size  EntryB...
dtype: object

======================================================================
OPTIMIZING FOR MAXIMUM RETURN
======================================================================
                                                                                                                                                         
✨ OPTIMIZED RESULTS:
Start                     2025-08-26 15:41:00
End                       2025-09-23 15:40:00
Duration                     27 days 23:59:00
Exposure Time [%]                    10.14881
Equity Final [$]                1219937.17783
Equity Peak [$]                 1220006.87783
Return [%]                          21.993718
Buy & Hold Return [%]                2.958633
Return (Ann.) [%]                 1052.842907
Volatility (Ann.) [%]              104.396102
Sharpe Ratio                        10.085079
Sortino Ratio                             inf
Calmar Ratio                      1581.370421
Max. Drawdown [%]                   -0.665779
Avg. Drawdown [%]                   -0.075574
Max. Drawdown Duration        1 days 05:55:00
Avg. Drawdown Duration        0 days 01:04:00
# Trades                                  110
Win Rate [%]                        83.636364
Best Trade [%]                        0.80301
Worst Trade [%]                      -0.50839
Avg. Trade [%]                       0.192071
Max. Trade Duration           0 days 02:08:00
Avg. Trade Duration           0 days 00:37:00
Profit Factor                       12.331163
Expectancy [%]                       0.192288
SQN                                  9.754091
_strategy                 MultiTimeframeRS...
_equity_curve                             ...
_trades                        Size  Entry...
dtype: object

🎯 OPTIMAL PARAMETERS:
rsi_1m_oversold: 35
rsi_1m_overbought: 65
take_profit: 0.009
stop_loss: 0.004
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

print("🎯 Moon Dev's MULTI-TIMEFRAME RSI Strategy V3 🎯")
print("=" * 70)

# Load data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1m-4wks-data.csv'
print(f"📊 Loading BTC 1-minute data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Calculate RSI for different timeframes
data['RSI_1m'] = ta.rsi(data['Close'], length=14)

# Resample for 5-minute RSI
data_5m = data['Close'].resample('5T').last()
rsi_5m = ta.rsi(data_5m, length=14)
data['RSI_5m'] = rsi_5m.reindex(data.index, method='ffill')

# Resample for 15-minute RSI
data_15m = data['Close'].resample('15T').last()
rsi_15m = ta.rsi(data_15m, length=14)
data['RSI_15m'] = rsi_15m.reindex(data.index, method='ffill')

# Combined RSI score
data['RSI_Combined'] = (data['RSI_1m'] + data['RSI_5m'] + data['RSI_15m']) / 3

# RSI alignment
data['All_Oversold'] = ((data['RSI_1m'] < 35) &
                        (data['RSI_5m'] < 40) &
                        (data['RSI_15m'] < 45)).astype(int)

data['All_Overbought'] = ((data['RSI_1m'] > 65) &
                          (data['RSI_5m'] > 60) &
                          (data['RSI_15m'] > 55)).astype(int)

# Volume confirmation
data['Volume_MA'] = data['Volume'].rolling(20).mean()
data['Volume_Ratio'] = data['Volume'] / data['Volume_MA']

print(f"✅ Loaded {len(data):,} 1-minute bars")


class MultiTimeframeRSI(Strategy):
    """
    Trade when multiple RSI timeframes align
    """

    rsi_1m_oversold = 30
    rsi_1m_overbought = 70
    rsi_5m_oversold = 35
    rsi_5m_overbought = 65
    rsi_15m_oversold = 40
    rsi_15m_overbought = 60
    take_profit = 0.008
    stop_loss = 0.003

    def init(self):
        self.rsi_1m = self.I(lambda: self.data.RSI_1m)
        self.rsi_5m = self.I(lambda: self.data.RSI_5m)
        self.rsi_15m = self.I(lambda: self.data.RSI_15m)
        self.rsi_combined = self.I(lambda: self.data.RSI_Combined)
        self.volume_ratio = self.I(lambda: self.data.Volume_Ratio)

    def next(self):
        if len(self.data) < 50:
            return

        price = self.data.Close[-1]
        rsi_1m = self.rsi_1m[-1]
        rsi_5m = self.rsi_5m[-1]
        rsi_15m = self.rsi_15m[-1]

        if pd.isna(rsi_1m) or pd.isna(rsi_5m) or pd.isna(rsi_15m):
            return

        # Exit when RSI neutralizes on any timeframe
        if self.position:
            if self.position.is_long and (rsi_1m > 60 or rsi_5m > 55):
                self.position.close()
            elif self.position.is_short and (rsi_1m < 40 or rsi_5m < 45):
                self.position.close()
            return

        # Entry logic - all timeframes must agree
        if not self.position:
            # BUY: All timeframes oversold
            if (rsi_1m < self.rsi_1m_oversold and
                rsi_5m < self.rsi_5m_oversold and
                rsi_15m < self.rsi_15m_oversold and
                self.volume_ratio[-1] > 0.8):

                tp = price * (1 + self.take_profit)
                sl = price * (1 - self.stop_loss)
                self.buy(tp=tp, sl=sl)

            # SELL: All timeframes overbought
            elif (rsi_1m > self.rsi_1m_overbought and
                  rsi_5m > self.rsi_5m_overbought and
                  rsi_15m > self.rsi_15m_overbought and
                  self.volume_ratio[-1] > 0.8):

                tp = price * (1 - self.take_profit)
                sl = price * (1 + self.stop_loss)
                self.sell(tp=tp, sl=sl)


# Run backtest
print("\n" + "="*70)
print("RUNNING MULTI-TIMEFRAME RSI BACKTEST")
print("="*70)

bt = Backtest(
    data,
    MultiTimeframeRSI,
    cash=1000000,
    commission=0.001,
    exclusive_orders=True
)

baseline_stats = bt.run()
print(f"\n📊 BASELINE RESULTS:")
print(baseline_stats)

# Optimization
print("\n" + "="*70)
print("OPTIMIZING FOR MAXIMUM RETURN")
print("="*70)

try:
    optimization_results = bt.optimize(
        rsi_1m_oversold=[25, 30, 35],
        rsi_1m_overbought=[65, 70, 75],
        take_profit=[0.007, 0.008, 0.009],
        stop_loss=[0.002, 0.003, 0.004],
        maximize='Return [%]',
        return_heatmap=False
    )

    print(f"\n✨ OPTIMIZED RESULTS:")
    print(optimization_results)

    print(f"\n🎯 OPTIMAL PARAMETERS:")
    print(f"rsi_1m_oversold: {optimization_results._strategy.rsi_1m_oversold}")
    print(f"rsi_1m_overbought: {optimization_results._strategy.rsi_1m_overbought}")
    print(f"take_profit: {optimization_results._strategy.take_profit}")
    print(f"stop_loss: {optimization_results._strategy.stop_loss}")

except Exception as e:
    print(f"Optimization failed: {str(e)}")

bt.plot()