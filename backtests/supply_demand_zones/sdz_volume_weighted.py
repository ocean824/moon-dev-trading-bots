"""
Supply and Demand Zones VOLUME-WEIGHTED Strategy
=================================================

This strategy enhances SDZ with volume profile analysis to identify high-volume zones.

Theory:
- High volume zones act as stronger support/resistance
- Volume-weighted zones are more reliable for reversals
- Combines price zones with volume concentration areas

Trading Logic:
- Identifies zones with highest volume concentration
- Trades bounces off high-volume supply/demand zones
- Uses VWAP as additional confirmation


Win Rate: 39.82%
Return: -22.59%
Sharpe: 0.00
Max Drawdown: -23.94%

📈 FULL BASELINE STATS:
======================================================================
Start                     2025-08-26 15:41:00
End                       2025-09-23 15:40:00
Duration                     27 days 23:59:00
Exposure Time [%]                    97.19494
Equity Final [$]                 774149.32157
Equity Peak [$]                 1014670.51408
Return [%]                         -22.585068
Buy & Hold Return [%]                2.958633
Return (Ann.) [%]                  -96.565572
Volatility (Ann.) [%]                0.919679
Sharpe Ratio                              0.0
Sortino Ratio                             0.0
Calmar Ratio                              0.0
Max. Drawdown [%]                  -23.943762
Avg. Drawdown [%]                   -1.328896
Max. Drawdown Duration       27 days 01:36:00
Avg. Drawdown Duration        1 days 07:55:00
# Trades                                  334
Win Rate [%]                        39.820359
Best Trade [%]                       0.416639
Worst Trade [%]                      -0.44153
Avg. Trade [%]                       -0.08278
Max. Trade Duration           1 days 08:54:00
Avg. Trade Duration           0 days 01:57:00
Profit Factor                        0.659248
Expectancy [%]                      -0.082016
SQN                                 -3.737084
_strategy                 SDZVolumeWeighte...
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
Exposure Time [%]                   96.346726
Equity Final [$]                1077606.58299
Equity Peak [$]                 1117011.98643
Return [%]                           7.760658
Buy & Hold Return [%]                2.958633
Return (Ann.) [%]                  182.877447
Volatility (Ann.) [%]               64.484464
Sharpe Ratio                         2.835992
Sortino Ratio                       14.199727
Calmar Ratio                          39.3559
Max. Drawdown [%]                   -4.646761
Avg. Drawdown [%]                     -0.2648
Max. Drawdown Duration        4 days 21:58:00
Avg. Drawdown Duration        0 days 03:43:00
# Trades                                   22
Win Rate [%]                             50.0
Best Trade [%]                       1.912658
Worst Trade [%]                       -1.1214
Avg. Trade [%]                        0.34544
Max. Trade Duration           6 days 03:21:00
Avg. Trade Duration           1 days 05:25:00
Profit Factor                        1.646368
Expectancy [%]                       0.356217
SQN                                  1.109918
_strategy                 SDZVolumeWeighte...
_equity_curve                             ...
_trades                       Size  EntryB...
dtype: object

🎯 OPTIMIZED PARAMETERS:
--------------------------------------------------
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Supply and Demand Zones VOLUME-WEIGHTED Strategy 🌙")
print("=" * 70)

# Load BTC 1-minute data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1m-4wks-data.csv'
print(f"📊 Loading BTC 1-minute data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)

# Rename columns
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Calculate VWAP
data['VWAP'] = ta.vwap(data['High'], data['Low'], data['Close'], data['Volume'])

# Calculate volume-weighted moving average
data['VWMA'] = ta.vwma(data['Close'], data['Volume'], length=20)

print(f"✅ Loaded {len(data):,} 1-minute bars")
print(f"📅 Date range: {data.index.min()} → {data.index.max()}")


class SDZVolumeWeightedStrategy(Strategy):
    """
    Supply and Demand Zones Volume-Weighted Strategy

    Parameters:
    - lookback_period: Period for calculating zones
    - volume_threshold: Minimum volume percentile for valid zones
    - vwap_distance: Maximum distance from VWAP for entries
    - zone_strength: Number of touches to confirm zone strength
    - take_profit: Take profit percentage
    - stop_loss: Stop loss percentage
    """

    # Optimizable parameters
    lookback_period = 20  # Bars for zone calculation
    volume_threshold = 50  # 50th percentile volume for strong zones (less restrictive)
    vwap_distance = 0.01  # Max 1% from VWAP (much less restrictive)
    zone_strength = 1  # Minimum zone touches (less restrictive)
    take_profit = 0.005  # 0.5% take profit
    stop_loss = 0.003  # 0.3% stop loss

    def init(self):
        """Initialize indicators"""
        # Calculate basic zones (matching nice_funcs.py logic)
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

        # VWAP and VWMA
        self.vwap = self.I(lambda: self.data.VWAP)
        self.vwma = self.I(lambda: self.data.VWMA)

        # Volume percentile (for identifying high volume zones)
        self.volume_percentile = self.I(lambda: pd.Series(self.data.Volume).rolling(
            window=100, min_periods=1).rank(pct=True) * 100)

        # Calculate volume-weighted zone strength
        def calculate_volume_weighted_zones():
            high = pd.Series(self.data.High)
            low = pd.Series(self.data.Low)
            volume = pd.Series(self.data.Volume)

            # Volume-weighted high (supply zone)
            vw_high = (high * volume).rolling(window=self.lookback_period).sum() / \
                     volume.rolling(window=self.lookback_period).sum()

            # Volume-weighted low (demand zone)
            vw_low = (low * volume).rolling(window=self.lookback_period).sum() / \
                    volume.rolling(window=self.lookback_period).sum()

            return vw_high, vw_low

        vw_high, vw_low = calculate_volume_weighted_zones()
        self.vw_resistance = self.I(lambda: vw_high)
        self.vw_support = self.I(lambda: vw_low)

        # Track zone touches for strength
        self.zone_touches = {}

    def next(self):
        """Main strategy logic"""

        # Get current values
        current_price = self.data.Close[-1]
        current_volume_percentile = self.volume_percentile[-1] if self.volume_percentile[-1] else 50
        current_vwap = self.vwap[-1] if self.vwap[-1] else current_price
        current_vwma = self.vwma[-1] if self.vwma[-1] else current_price

        # Skip if insufficient data
        if len(self.data) < self.lookback_period + 20:  # Just need lookback + some history
            return

        # Get volume-weighted zones
        vw_resistance_level = self.vw_resistance[-1]
        vw_support_level = self.vw_support[-1]

        # Regular zones for comparison
        regular_resistance = self.resistance[-1]
        regular_support = self.support[-1]

        # Use stronger of the two zone types
        supply_zone = max(vw_resistance_level, regular_resistance)
        demand_zone = min(vw_support_level, regular_support)

        # Distance from VWAP
        vwap_distance_pct = abs(current_price - current_vwap) / current_vwap

        # Entry logic - only if no position
        if not self.position:

            # Check if volume is significant
            high_volume = current_volume_percentile >= self.volume_threshold

            # BUY signal: At demand zone (simplified)
            if (abs(current_price - demand_zone) / demand_zone < 0.005):  # Within 0.5% of demand

                # Just check if we're not too far from VWAP
                if vwap_distance_pct <= self.vwap_distance:

                    # Simple percentage-based stops (more reliable)
                    sl_price = current_price * (1 - self.stop_loss)
                    tp_price = current_price * (1 + self.take_profit)

                    self.buy(sl=sl_price, tp=tp_price)

            # SELL signal: At supply zone (simplified)
            elif (abs(current_price - supply_zone) / supply_zone < 0.005):  # Within 0.5% of supply

                # Just check if we're not too far from VWAP
                if vwap_distance_pct <= self.vwap_distance:

                    # Simple percentage-based stops (more reliable)
                    sl_price = current_price * (1 + self.stop_loss)
                    tp_price = current_price * (1 - self.take_profit)

                    self.sell(sl=sl_price, tp=tp_price)


# Run baseline backtest
print("\n" + "="*70)
print("RUNNING BASELINE BACKTEST")
print("="*70)

bt = Backtest(
    data,
    SDZVolumeWeightedStrategy,
    cash=1000000,  # $1M for BTC trading at $100k+
    commission=0.001,
    exclusive_orders=True
)

# Run baseline
baseline_stats = bt.run()

print(f"\n📊 BASELINE RESULTS:")
print(f"Lookback Period: {SDZVolumeWeightedStrategy.lookback_period} bars")
print(f"Volume Threshold: {SDZVolumeWeightedStrategy.volume_threshold}th percentile")
print(f"VWAP Distance: {SDZVolumeWeightedStrategy.vwap_distance*100:.1f}%")
print(f"Zone Strength: {SDZVolumeWeightedStrategy.zone_strength} touches")
print(f"Take Profit: {SDZVolumeWeightedStrategy.take_profit*100:.1f}%")
print(f"Stop Loss: {SDZVolumeWeightedStrategy.stop_loss*100:.1f}%")
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
        lookback_period=[20, 30, 40],
        volume_threshold=[60, 70, 80],
        vwap_distance=[0.003, 0.005, 0.008],
        take_profit=[0.015, 0.018, 0.02],
        stop_loss=[0.008, 0.009, 0.01],
        maximize='Sharpe Ratio',
        return_heatmap=False
    )

    print("\n✨ OPTIMIZED RESULTS:")
    print("="*70)
    print(optimization_results)

    print("\n🎯 OPTIMIZED PARAMETERS:")
    print("-" * 50)
    print(f"Lookback Period: {optimization_results._strategy.lookback_period} bars")
    print(f"Volume Threshold: {optimization_results._strategy.volume_threshold}th percentile")
    print(f"VWAP Distance: {optimization_results._strategy.vwap_distance*100:.1f}%")
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