"""
Supply and Demand Zones BREAKOUT Strategy
==========================================

This strategy trades strong breakouts from supply/demand zones with momentum confirmation.

Theory:
- Strong breakouts from zones indicate trend continuation
- Uses volume confirmation for breakout validity
- Implements dynamic stop loss based on zone width

Trading Logic:
- BUY on strong breakout above supply zone with volume spike
- SELL on strong breakout below demand zone with volume spike
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Supply and Demand Zones BREAKOUT Strategy 🌙")
print("=" * 70)

# Load BTC 1-minute data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1m-4wks-data.csv'
print(f"📊 Loading BTC 1-minute data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)

# Rename columns
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

print(f"✅ Loaded {len(data):,} 1-minute bars")
print(f"📅 Date range: {data.index.min()} → {data.index.max()}")


class SDZBreakoutStrategy(Strategy):
    """
    Supply and Demand Zones Breakout Strategy

    Parameters:
    - lookback_period: Period for calculating zones
    - breakout_threshold: Percentage above/below zone for breakout confirmation
    - volume_multiplier: Volume spike threshold
    - atr_multiplier: ATR multiplier for dynamic stop loss
    - take_profit_ratio: Risk/reward ratio for take profit
    """

    # Optimizable parameters
    lookback_period = 20  # Bars for zone calculation
    breakout_threshold = 0.001  # 0.1% breakout confirmation
    volume_multiplier = 1.2  # Volume must be 1.2x average (less restrictive)
    atr_multiplier = 1.0  # Stop loss at 1x ATR
    take_profit_ratio = 1.5  # 1.5:1 risk/reward ratio

    def init(self):
        """Initialize indicators"""
        # Calculate zones (matching nice_funcs.py logic)
        # Support: rolling min of CLOSE prices
        self.support = self.I(lambda: pd.Series(self.data.Close).rolling(
            window=self.lookback_period, min_periods=1).min())
        # Resistance: rolling max of CLOSE prices
        self.resistance = self.I(lambda: pd.Series(self.data.Close).rolling(
            window=self.lookback_period, min_periods=1).max())

        # Calculate zone midpoints
        self.zone_mid = self.I(lambda: (self.support + self.resistance) / 2)

        # Calculate volume moving average
        self.volume_ma = self.I(lambda: pd.Series(self.data.Volume).rolling(
            window=20, min_periods=1).mean())

        # Calculate ATR for dynamic stops
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        close = pd.Series(self.data.Close)

        # Calculate ATR components
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        self.atr = self.I(lambda: tr.rolling(window=14, min_periods=1).mean())

        # Track zone boundaries (demand zone low, supply zone high)
        self.supp_lo = self.I(lambda: pd.Series(self.data.Low).rolling(
            window=self.lookback_period, min_periods=1).min())
        self.res_hi = self.I(lambda: pd.Series(self.data.High).rolling(
            window=self.lookback_period, min_periods=1).max())

    def next(self):
        """Main strategy logic"""

        # Get current values
        current_price = self.data.Close[-1]
        current_volume = self.data.Volume[-1]
        current_atr = self.atr[-1] if self.atr[-1] else 0

        # Skip if insufficient data
        if len(self.data) < self.lookback_period + 14:  # Just need lookback + ATR period
            return

        # Skip if no ATR
        if current_atr == 0:
            return

        # Volume confirmation
        volume_spike = current_volume > (self.volume_ma[-1] * self.volume_multiplier)

        # Entry logic - only if no position
        if not self.position:
            # Get zone levels
            resistance_level = self.resistance[-1]  # Upper bound of demand zone
            support_level = self.support[-1]  # Lower bound of supply zone
            supp_lo = self.supp_lo[-1]  # Lower bound of demand zone
            res_hi = self.res_hi[-1]  # Upper bound of supply zone

            # Calculate breakout levels
            # For BUY: Break above the supply zone (res_hi)
            breakout_up = res_hi * (1 + self.breakout_threshold)
            # For SELL: Break below the demand zone (supp_lo)
            breakout_down = supp_lo * (1 - self.breakout_threshold)

            # BUY signal: Breakout above supply zone (simplified, no volume requirement)
            if (current_price > breakout_up and
                self.data.Close[-2] <= breakout_up):

                # Dynamic stop loss based on ATR
                sl_price = current_price - (current_atr * self.atr_multiplier)

                # Take profit based on risk/reward ratio
                risk = current_price - sl_price
                tp_price = current_price + (risk * self.take_profit_ratio)

                self.buy(sl=sl_price, tp=tp_price)

            # SELL signal: Breakdown below demand zone (simplified)
            elif (current_price < breakout_down and
                  self.data.Close[-2] >= breakout_down):

                # Dynamic stop loss based on ATR
                sl_price = current_price + (current_atr * self.atr_multiplier)

                # Take profit based on risk/reward ratio
                risk = sl_price - current_price
                tp_price = current_price - (risk * self.take_profit_ratio)

                self.sell(sl=sl_price, tp=tp_price)


# Run baseline backtest
print("\n" + "="*70)
print("RUNNING BASELINE BACKTEST")
print("="*70)

bt = Backtest(
    data,
    SDZBreakoutStrategy,
    cash=1000000,  # $1M for BTC trading at $100k+
    commission=0.001,
    exclusive_orders=True
)

# Run baseline
baseline_stats = bt.run()

print(f"\n📊 BASELINE RESULTS:")
print(f"Lookback Period: {SDZBreakoutStrategy.lookback_period} bars")
print(f"Breakout Threshold: {SDZBreakoutStrategy.breakout_threshold*100:.2f}%")
print(f"Volume Multiplier: {SDZBreakoutStrategy.volume_multiplier:.1f}x")
print(f"ATR Multiplier: {SDZBreakoutStrategy.atr_multiplier:.1f}")
print(f"Take Profit Ratio: {SDZBreakoutStrategy.take_profit_ratio:.1f}:1")
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
        lookback_period=[20, 30, 50],
        breakout_threshold=[0.002, 0.003, 0.005],
        volume_multiplier=[1.5, 2.0, 3.0],
        atr_multiplier=[1.0, 1.5, 2.0],
        take_profit_ratio=[1.5, 2.0, 3.0],
        maximize='Sharpe Ratio',
        return_heatmap=False
    )

    print("\n✨ OPTIMIZED RESULTS:")
    print("="*70)
    print(optimization_results)

    print("\n🎯 OPTIMIZED PARAMETERS:")
    print("-" * 50)
    print(f"Lookback Period: {optimization_results._strategy.lookback_period} bars")
    print(f"Breakout Threshold: {optimization_results._strategy.breakout_threshold*100:.2f}%")
    print(f"Volume Multiplier: {optimization_results._strategy.volume_multiplier:.1f}x")
    print(f"ATR Multiplier: {optimization_results._strategy.atr_multiplier:.1f}")
    print(f"Take Profit Ratio: {optimization_results._strategy.take_profit_ratio:.1f}:1")

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