"""
LIQUIDITY ZONES - Trade High-Liquidity Price Areas
===================================================

Concept: Identify and trade zones where liquidity accumulates.
These are areas with many stop losses and pending orders.

Focus: PROFITABILITY with high volum

UNNING LIQUIDITY ZONES BACKTEST
======================================================================

📊 BASELINE RESULTS:
Start                     2025-08-26 15:41:00
End                       2025-09-23 15:40:00
Duration                     27 days 23:59:00
Exposure Time [%]                   85.029762
Equity Final [$]                3826737.36488
Equity Peak [$]                 3829979.28488
Return [%]                         282.673736
Buy & Hold Return [%]                2.958633
Return (Ann.) [%]           1631938908.249007
Volatility (Ann.) [%]        551763054.804918
Sharpe Ratio                         2.957681
Sortino Ratio                             inf
Calmar Ratio                2665531506.964723
Max. Drawdown [%]                   -0.612238
Avg. Drawdown [%]                   -0.069217
Max. Drawdown Duration        0 days 07:15:00
Avg. Drawdown Duration        0 days 00:13:00
# Trades                                  554
Win Rate [%]                        92.238267
Best Trade [%]                        0.62043
Worst Trade [%]                       -0.4004
Avg. Trade [%]                       0.249889
Max. Trade Duration           0 days 05:29:00
Avg. Trade Duration           0 days 01:01:00
Profit Factor                       45.692836
Expectancy [%]                        0.25011
SQN                                 24.637585
_strategy                      LiquidityZones
_equity_curve                             ...
_trades                        Size  Entry...
dtype: object

======================================================================
OPTIMIZING FOR MAXIMUM RETURN
======================================================================
                                                                                                                                                         
✨ OPTIMIZED RESULTS:
Start                     2025-08-26 15:41:00
End                       2025-09-23 15:40:00
Duration                     27 days 23:59:00
Exposure Time [%]                   89.414683
Equity Final [$]                4433017.47751
Equity Peak [$]                 4436848.83751
Return [%]                         343.301748
Buy & Hold Return [%]                2.958633
Return (Ann.) [%]           9329684018.214836
Volatility (Ann.) [%]       3822645126.797435
Sharpe Ratio                         2.440636
Sortino Ratio                             inf
Calmar Ratio               10406459092.434004
Max. Drawdown [%]                   -0.896528
Avg. Drawdown [%]                    -0.07201
Max. Drawdown Duration        0 days 07:15:00
Avg. Drawdown Duration        0 days 00:12:00
# Trades                                  571
Win Rate [%]                        92.469352
Best Trade [%]                       0.707359
Worst Trade [%]                     -0.497736
Avg. Trade [%]                       0.269069
Max. Trade Duration           0 days 05:29:00
Avg. Trade Duration           0 days 01:03:00
Profit Factor                        47.51583
Expectancy [%]                       0.269342
SQN                                 24.094095
_strategy                 LiquidityZones(z...
_equity_curve                             ...
_trades                        Size  Entry...
dtype: object

🎯 OPTIMAL PARAMETERS:
zone_proximity: 0.0025
min_tests: 1
compression_threshold: 0.004
take_profit: 0.008
stop_loss: 0.004
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

print("🎯 Moon Dev's LIQUIDITY ZONES Strategy V3 🎯")
print("=" * 70)

# Load data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1m-4wks-data.csv'
print(f"📊 Loading BTC 1-minute data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Identify liquidity zones (swing highs/lows)
data['Swing_High'] = data['High'].rolling(10).max()
data['Swing_Low'] = data['Low'].rolling(10).min()

# Recent highs and lows (liquidity areas)
data['Recent_High'] = data['High'].rolling(50).max()
data['Recent_Low'] = data['Low'].rolling(50).min()

# Liquidity zone strength (how many times tested)
data['High_Tests'] = (data['High'] >= data['Swing_High'] * 0.999).rolling(20).sum()
data['Low_Tests'] = (data['Low'] <= data['Swing_Low'] * 1.001).rolling(20).sum()

# Volume at zones
data['Volume_MA'] = data['Volume'].rolling(20).mean()
data['Zone_Volume'] = data['Volume'] / data['Volume_MA']

# Distance from liquidity zones
data['Distance_to_High'] = (data['Recent_High'] - data['Close']) / data['Close']
data['Distance_to_Low'] = (data['Close'] - data['Recent_Low']) / data['Close']

# RSI for momentum
data['RSI'] = ta.rsi(data['Close'], length=14)

# Price compression (range trading)
data['Price_Range'] = (data['High'].rolling(10).max() -
                       data['Low'].rolling(10).min()) / data['Close']

print(f"✅ Loaded {len(data):,} 1-minute bars")


class LiquidityZones(Strategy):
    """
    Trade liquidity grab and sweep patterns
    """

    zone_proximity = 0.002  # 0.2% from zone
    min_tests = 2  # Minimum zone tests
    compression_threshold = 0.003  # Price compression
    take_profit = 0.007
    stop_loss = 0.003

    def init(self):
        self.swing_high = self.I(lambda: self.data.Swing_High)
        self.swing_low = self.I(lambda: self.data.Swing_Low)
        self.high_tests = self.I(lambda: self.data.High_Tests)
        self.low_tests = self.I(lambda: self.data.Low_Tests)
        self.zone_volume = self.I(lambda: self.data.Zone_Volume)
        self.rsi = self.I(lambda: self.data.RSI)
        self.price_range = self.I(lambda: self.data.Price_Range)
        self.distance_high = self.I(lambda: self.data.Distance_to_High)
        self.distance_low = self.I(lambda: self.data.Distance_to_Low)

    def next(self):
        if len(self.data) < 50:
            return

        price = self.data.Close[-1]
        rsi = self.rsi[-1]

        if pd.isna(rsi):
            return

        # Exit on momentum shift
        if self.position:
            if self.position.is_long and rsi > 65:
                self.position.close()
            elif self.position.is_short and rsi < 35:
                self.position.close()
            return

        # Entry logic
        if not self.position:
            # BUY: Liquidity sweep at lows
            if (self.distance_low[-1] < self.zone_proximity and
                self.low_tests[-1] >= self.min_tests and
                self.price_range[-1] < self.compression_threshold and
                rsi < 40 and
                self.zone_volume[-1] > 1.2):

                # Liquidity grab - expect quick reversal
                tp = price * (1 + self.take_profit)
                sl = price * (1 - self.stop_loss)
                self.buy(tp=tp, sl=sl)

            # SELL: Liquidity sweep at highs
            elif (self.distance_high[-1] < self.zone_proximity and
                  self.high_tests[-1] >= self.min_tests and
                  self.price_range[-1] < self.compression_threshold and
                  rsi > 60 and
                  self.zone_volume[-1] > 1.2):

                # Liquidity grab - expect quick reversal
                tp = price * (1 - self.take_profit)
                sl = price * (1 + self.stop_loss)
                self.sell(tp=tp, sl=sl)


# Run backtest
print("\n" + "="*70)
print("RUNNING LIQUIDITY ZONES BACKTEST")
print("="*70)

bt = Backtest(
    data,
    LiquidityZones,
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
        zone_proximity=[0.0015, 0.002, 0.0025],
        min_tests=[1, 2, 3],
        compression_threshold=[0.002, 0.003, 0.004],
        take_profit=[0.006, 0.007, 0.008],
        stop_loss=[0.002, 0.003, 0.004],
        maximize='Return [%]',
        return_heatmap=False
    )

    print(f"\n✨ OPTIMIZED RESULTS:")
    print(optimization_results)

    print(f"\n🎯 OPTIMAL PARAMETERS:")
    print(f"zone_proximity: {optimization_results._strategy.zone_proximity}")
    print(f"min_tests: {optimization_results._strategy.min_tests}")
    print(f"compression_threshold: {optimization_results._strategy.compression_threshold}")
    print(f"take_profit: {optimization_results._strategy.take_profit}")
    print(f"stop_loss: {optimization_results._strategy.stop_loss}")

except Exception as e:
    print(f"Optimization failed: {str(e)}")

bt.plot()