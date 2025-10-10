"""
Supply and Demand Zones MEAN REVERSION Strategy
================================================

This strategy trades bounces off supply/demand zones expecting price to revert to the mean.

Theory:
- Zones act as magnetic levels where price tends to bounce
- Extreme moves to zones often reverse
- Best entries are at zone edges with reversal confirmation

Trading Logic:
- BUY when price touches demand zone and shows reversal
- SELL when price touches supply zone and shows reversal

5.96
Max Drawdown: -1.99%

📈 FULL BASELINE STATS:
======================================================================
Start                     2025-08-26 15:41:00
End                       2025-09-23 15:40:00
Duration                     27 days 23:59:00
Exposure Time [%]                    52.02381
Equity Final [$]                1118415.21824
Equity Peak [$]                 1124903.93024
Return [%]                          11.841522
Buy & Hold Return [%]                2.958633
Return (Ann.) [%]                  289.451588
Volatility (Ann.) [%]               48.561282
Sharpe Ratio                         5.960543
Sortino Ratio                       62.035103
Calmar Ratio                       145.095131
Max. Drawdown [%]                   -1.994909
Avg. Drawdown [%]                    -0.12352
Max. Drawdown Duration        5 days 10:39:00
Avg. Drawdown Duration        0 days 02:08:00
# Trades                                  105
Win Rate [%]                        63.809524
Best Trade [%]                       0.402835
Worst Trade [%]                     -0.408117
Avg. Trade [%]                       0.109385
Max. Trade Duration           1 days 06:28:00
Avg. Trade Duration           0 days 03:19:00
Profit Factor                        1.760317
Expectancy [%]                       0.110124
SQN                                  2.962757
_strategy                 SDZMeanReversion...
_equity_curve                             ...
_trades                        Size  Entry...
dtype: object

======================================================================
RUNNING OPTIMIZATION
======================================================================
🔄 Optimizing parameters...
                                                                                                                                                                                
✨ OPTIMIZED RESULTS:
======================================================================
Start                     2025-08-26 15:41:00
End                       2025-09-23 15:40:00
Duration                     27 days 23:59:00
Exposure Time [%]                   58.536706
Equity Final [$]                1140696.50971
Equity Peak [$]                 1162177.09753
Return [%]                          14.069651
Buy & Hold Return [%]                2.958633
Return (Ann.) [%]                  320.050928
Volatility (Ann.) [%]               54.998497
Sharpe Ratio                         5.819267
Sortino Ratio                       61.880071
Calmar Ratio                       117.861903
Max. Drawdown [%]                   -2.715474
Avg. Drawdown [%]                   -0.154907
Max. Drawdown Duration        4 days 21:25:00
Avg. Drawdown Duration        0 days 01:57:00
# Trades                                   33
Win Rate [%]                        72.727273
Best Trade [%]                       0.902061
Worst Trade [%]                     -0.908957
Avg. Trade [%]                       0.418305
Max. Trade Duration           2 days 05:29:00
Avg. Trade Duration           0 days 11:55:00
Profit Factor                         2.81109
Expectancy [%]                       0.421379
SQN                                  3.013433
_strategy                 SDZMeanReversion...
_equity_curve                             ...
_trades                       Size  EntryB...
dtype: object

🎯 OPTIMIZED PARAMETERS:
--------------------------------------------------
Lookback Period: 20 bars
Zone Penetration: 20%
RSI Oversold: 35
RSI Overbought: 70
Take Profit: 1.0%
Stop Loss: 0.8%

📊 IMPROVEMENT SUMMARY:
--------------------------------------------------
Baseline Return: 11.84%
Optimized Return: 14.07%
Improvement: 2.23%

📊 Generating plot...
(tflow) md@mds-MacBook-Pro moon-dev-trading-bots % 
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Supply and Demand Zones MEAN REVERSION Strategy 🌙")
print("=" * 70)

# Load BTC 1-minute data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1m-4wks-data.csv'
print(f"📊 Loading BTC 1-minute data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)

# Rename columns
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Add RSI for oversold/overbought confirmation
data['RSI'] = ta.rsi(data['Close'], length=14)

print(f"✅ Loaded {len(data):,} 1-minute bars")
print(f"📅 Date range: {data.index.min()} → {data.index.max()}")


class SDZMeanReversionStrategy(Strategy):
    """
    Supply and Demand Zones Mean Reversion Strategy

    Parameters:
    - lookback_period: Period for calculating zones
    - zone_penetration: How deep price must enter zone (0-1)
    - rsi_oversold: RSI level for oversold confirmation
    - rsi_overbought: RSI level for overbought confirmation
    - take_profit: Take profit at zone midpoint percentage
    - stop_loss: Stop loss beyond zone percentage
    """

    # Optimizable parameters
    lookback_period = 20  # Bars for zone calculation
    zone_penetration = 0.2  # Must penetrate 20% into zone (less restrictive)
    rsi_oversold = 40  # RSI oversold level (less extreme)
    rsi_overbought = 60  # RSI overbought level (less extreme)
    take_profit = 0.005  # 0.5% take profit
    stop_loss = 0.003  # 0.3% stop loss

    def init(self):
        """Initialize indicators"""
        # Calculate zones (matching nice_funcs.py logic)
        # Support: rolling min of CLOSE prices
        self.support = self.I(lambda: pd.Series(self.data.Close).rolling(
            window=self.lookback_period, min_periods=1).min())
        # Resistance: rolling max of CLOSE prices
        self.resistance = self.I(lambda: pd.Series(self.data.Close).rolling(
            window=self.lookback_period, min_periods=1).max())

        # Zone boundaries (demand zone low, supply zone high)
        self.supp_lo = self.I(lambda: pd.Series(self.data.Low).rolling(
            window=self.lookback_period, min_periods=1).min())
        self.res_hi = self.I(lambda: pd.Series(self.data.High).rolling(
            window=self.lookback_period, min_periods=1).max())

        # Zone midpoint (mean reversion target)
        self.zone_midpoint = self.I(lambda: (self.support + self.resistance) / 2)

        # RSI indicator
        self.rsi = self.I(lambda: self.data.RSI)

        # Calculate zone width for dynamic targets
        self.zone_width = self.I(lambda: self.resistance - self.support)

        # Track bounces
        self.bounce_count = 0

    def next(self):
        """Main strategy logic"""

        # Get current values
        current_price = self.data.Close[-1]
        current_rsi = self.rsi[-1] if self.rsi[-1] else 50

        # Skip if insufficient data
        if len(self.data) < self.lookback_period + 14:  # Just need lookback + RSI period
            return

        # Get zone boundaries (matching nice_funcs.py)
        # Demand zone: from supp_lo to support
        demand_bottom = self.supp_lo[-1]  # Lower bound of demand zone
        demand_top = self.support[-1]  # Upper bound of demand zone
        # Supply zone: from resistance to res_hi
        supply_bottom = self.resistance[-1]  # Lower bound of supply zone
        supply_top = self.res_hi[-1]  # Upper bound of supply zone
        midpoint = self.zone_midpoint[-1]
        zone_width = self.zone_width[-1]

        # Calculate zone penetration levels
        demand_zone_entry = demand_bottom + (demand_top - demand_bottom) * self.zone_penetration
        supply_zone_entry = supply_top - (supply_top - supply_bottom) * self.zone_penetration

        # Entry logic - only if no position
        if not self.position:

            # BUY signal: Price in demand zone with oversold RSI (simplified)
            if (current_price <= demand_zone_entry and
                current_price >= demand_bottom):

                # Just need RSI confirmation, no reversal pattern needed
                if current_rsi < self.rsi_oversold:

                    # Stop loss below demand zone
                    sl_price = current_price * (1 - self.stop_loss)

                    # Take profit using percentage (simpler and more reliable)
                    tp_price = current_price * (1 + self.take_profit)

                    self.buy(sl=sl_price, tp=tp_price)

            # SELL signal: Price in supply zone with overbought RSI (simplified)
            elif (current_price >= supply_zone_entry and
                  current_price <= supply_top):

                # Just need RSI confirmation, no reversal pattern needed
                if current_rsi > self.rsi_overbought:

                    # Stop loss above current price
                    sl_price = current_price * (1 + self.stop_loss)

                    # Take profit using percentage (simpler and more reliable)
                    tp_price = current_price * (1 - self.take_profit)

                    self.sell(sl=sl_price, tp=tp_price)


# Run baseline backtest
print("\n" + "="*70)
print("RUNNING BASELINE BACKTEST")
print("="*70)

bt = Backtest(
    data,
    SDZMeanReversionStrategy,
    cash=1000000,  # $1M for BTC trading at $100k+
    commission=0.001,
    exclusive_orders=True
)

# Run baseline
baseline_stats = bt.run()

print(f"\n📊 BASELINE RESULTS:")
print(f"Lookback Period: {SDZMeanReversionStrategy.lookback_period} bars")
print(f"Zone Penetration: {SDZMeanReversionStrategy.zone_penetration*100:.0f}%")
print(f"RSI Oversold: {SDZMeanReversionStrategy.rsi_oversold}")
print(f"RSI Overbought: {SDZMeanReversionStrategy.rsi_overbought}")
print(f"Take Profit: {SDZMeanReversionStrategy.take_profit*100:.1f}%")
print(f"Stop Loss: {SDZMeanReversionStrategy.stop_loss*100:.1f}%")
print("-" * 50)
print(f"Total Trades: {baseline_stats['# Trades']}")
print(f"Win Rate: {baseline_stats['Win Rate [%]']:.2f}%")
print(f"Return: {baseline_stats['Return [%]']:.2f}%")
print(f"Sharpe: {baseline_stats['Sharpe Ratio']:.2f}")
print(f"Max Drawdown: {baseline_stats['Max. Drawdown [%]']:.2f}%")

print("\n📈 FULL BASELINE STATS:")
print("="*70)
print(baseline_stats)

# Run optimization
print("\n" + "="*70)
print("RUNNING OPTIMIZATION")
print("="*70)
print("🔄 Optimizing parameters...")

try:
    optimization_results = bt.optimize(
        lookback_period=[20, 25, 30, 40],
        zone_penetration=[0.2, 0.3, 0.4, 0.5],
        rsi_oversold=[25, 30, 35],
        rsi_overbought=[65, 70, 75],
        take_profit=[0.01, 0.015, 0.02],
        stop_loss=[0.005, 0.008, 0.01],
        maximize='Sharpe Ratio',
        return_heatmap=False
    )

    print("\n✨ OPTIMIZED RESULTS:")
    print("="*70)
    print(optimization_results)

    print("\n🎯 OPTIMIZED PARAMETERS:")
    print("-" * 50)
    print(f"Lookback Period: {optimization_results._strategy.lookback_period} bars")
    print(f"Zone Penetration: {optimization_results._strategy.zone_penetration*100:.0f}%")
    print(f"RSI Oversold: {optimization_results._strategy.rsi_oversold}")
    print(f"RSI Overbought: {optimization_results._strategy.rsi_overbought}")
    print(f"Take Profit: {optimization_results._strategy.take_profit*100:.1f}%")
    print(f"Stop Loss: {optimization_results._strategy.stop_loss*100:.1f}%")

    print("\n📊 IMPROVEMENT SUMMARY:")
    print("-" * 50)
    baseline_return = baseline_stats['Return [%]']
    optimized_return = optimization_results['Return [%]']
    print(f"Baseline Return: {baseline_return:.2f}%")
    print(f"Optimized Return: {optimized_return:.2f}%")
    print(f"Improvement: {optimized_return - baseline_return:.2f}%")

except Exception as e:
    print(f"\n⚠️ Optimization failed: {str(e)}")
    print("Try adjusting parameter ranges.")

# Show plot
print("\n📊 Generating plot...")
bt.plot()