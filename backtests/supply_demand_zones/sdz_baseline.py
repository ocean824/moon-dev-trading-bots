"""
Supply and Demand Zones (SDZ) Baseline Strategy
=================================================

This strategy identifies supply and demand zones based on support/resistance levels
and trades breakouts from these zones.

Theory:
- Demand Zone (DZ): Area where buying pressure exceeds selling (support levels)
- Supply Zone (SZ): Area where selling pressure exceeds buying (resistance levels)
- Uses rolling min/max to identify zones dynamically

Trading Logic:
- BUY when price breaks above demand zone
- SELL when price breaks below supply zone
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Supply and Demand Zones BASELINE Strategy 🌙")
print("=" * 70)

# Load BTC 1-minute data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1m-4wks-data.csv'
print(f"📊 Loading BTC 1-minute data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)

# Rename columns to match backtesting.py requirements
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

print(f"✅ Loaded {len(data):,} 1-minute bars")
print(f"📅 Date range: {data.index.min()} → {data.index.max()}")


class SDZBaselineStrategy(Strategy):
    """
    Supply and Demand Zones Baseline Strategy

    Parameters:
    - lookback_period: Period for calculating support/resistance zones
    - min_zone_width: Minimum zone width as % of price
    - take_profit_pct: Take profit percentage
    - stop_loss_pct: Stop loss percentage
    """

    # Optimizable parameters
    lookback_period = 20  # Bars to look back for zones
    min_zone_width = 0.001  # Minimum 0.1% zone width
    take_profit_pct = 0.003  # 0.3% take profit
    stop_loss_pct = 0.002  # 0.2% stop loss

    def init(self):
        """Initialize indicators"""
        # Calculate rolling support and resistance (matching nice_funcs.py logic)
        # Support: rolling min of CLOSE prices
        self.support = self.I(lambda: pd.Series(self.data.Close).rolling(
            window=self.lookback_period, min_periods=1).min())
        # Resistance: rolling max of CLOSE prices
        self.resistance = self.I(lambda: pd.Series(self.data.Close).rolling(
            window=self.lookback_period, min_periods=1).max())

        # Additional zone boundaries (demand zone low, supply zone high)
        # supp_lo: min of lows over lookback period
        self.supp_lo = self.I(lambda: pd.Series(self.data.Low).rolling(
            window=self.lookback_period, min_periods=1).min())
        # res_hi: max of highs over lookback period
        self.res_hi = self.I(lambda: pd.Series(self.data.High).rolling(
            window=self.lookback_period, min_periods=1).max())

    def next(self):
        """Main strategy logic"""

        # Skip if we don't have enough data
        if len(self.data) < self.lookback_period:
            return

        # Get current values
        current_price = self.data.Close[-1]
        current_support = self.support[-1]
        current_resistance = self.resistance[-1]

        # Calculate zone width
        zone_width = (current_resistance - current_support) / current_price

        # Skip if zone is too narrow (likely ranging market)
        if zone_width < self.min_zone_width:
            return

        # Entry logic - only if no position
        if not self.position:

            # Get zone boundaries
            current_supp_lo = self.supp_lo[-1]
            current_res_hi = self.res_hi[-1]

            # Define demand zone: supp_lo to support
            # Define supply zone: resistance to res_hi

            # BUY signal: Price enters demand zone (between supp_lo and support)
            if current_supp_lo <= current_price <= current_support:

                # Set stop loss below support
                sl_price = current_support * (1 - self.stop_loss_pct)

                # Set take profit
                tp_price = current_price * (1 + self.take_profit_pct)

                # Ensure TP > entry > SL
                if tp_price > current_price > sl_price:
                    self.buy(sl=sl_price, tp=tp_price)

            # SELL signal: Price enters supply zone (between resistance and res_hi)
            elif current_resistance <= current_price <= current_res_hi:

                # Set stop loss above resistance
                sl_price = current_resistance * (1 + self.stop_loss_pct)

                # Set take profit
                tp_price = current_price * (1 - self.take_profit_pct)

                # Ensure SL > entry > TP for short
                if sl_price > current_price > tp_price:
                    self.sell(sl=sl_price, tp=tp_price)


# Run baseline backtest
print("\n" + "="*70)
print("RUNNING BASELINE BACKTEST")
print("="*70)

bt = Backtest(
    data,
    SDZBaselineStrategy,
    cash=1000000,  # $1M for BTC trading at $100k+
    commission=0.001,
    exclusive_orders=True
)

# Run baseline
baseline_stats = bt.run()

print(f"\n📊 BASELINE RESULTS:")
print(f"Lookback Period: {SDZBaselineStrategy.lookback_period} bars")
print(f"Min Zone Width: {SDZBaselineStrategy.min_zone_width*100:.2f}%")
print(f"Take Profit: {SDZBaselineStrategy.take_profit_pct*100:.1f}%")
print(f"Stop Loss: {SDZBaselineStrategy.stop_loss_pct*100:.1f}%")
print("-" * 50)
print(f"Total Trades: {baseline_stats['# Trades']}")
if baseline_stats['# Trades'] > 0:
    print(f"Win Rate: {baseline_stats['Win Rate [%]']:.2f}%")
    print(f"Return: {baseline_stats['Return [%]']:.2f}%")
    print(f"Sharpe: {baseline_stats['Sharpe Ratio']:.2f}")
    print(f"Max Drawdown: {baseline_stats['Max. Drawdown [%]']:.2f}%")
else:
    print("No trades generated - adjusting parameters needed")

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
        lookback_period=[10, 20, 30, 50],
        min_zone_width=[0.0005, 0.001, 0.002],
        take_profit_pct=[0.002, 0.003, 0.004, 0.005],
        stop_loss_pct=[0.001, 0.002, 0.003],
        maximize='Return [%]',  # Changed from Sharpe to Return
        constraint=lambda p: p.take_profit_pct > p.stop_loss_pct,  # TP must be > SL
        return_heatmap=False
    )

    print("\n✨ OPTIMIZED RESULTS:")
    print("="*70)
    print(optimization_results)

    print("\n🎯 OPTIMIZED PARAMETERS:")
    print("-" * 50)
    print(f"Lookback Period: {optimization_results._strategy.lookback_period} bars")
    print(f"Min Zone Width: {optimization_results._strategy.min_zone_width*100:.2f}%")
    print(f"Take Profit: {optimization_results._strategy.take_profit_pct*100:.1f}%")
    print(f"Stop Loss: {optimization_results._strategy.stop_loss_pct*100:.1f}%")

    print("\n📊 IMPROVEMENT SUMMARY:")
    print("-" * 50)
    baseline_return = baseline_stats['Return [%]']
    optimized_return = optimization_results['Return [%]']
    print(f"Baseline Return: {baseline_return:.2f}%")
    print(f"Optimized Return: {optimized_return:.2f}%")
    print(f"Improvement: {optimized_return - baseline_return:.2f}%")

except Exception as e:
    print(f"\n⚠️ Optimization failed: {str(e)}")
    print("Try adjusting parameter ranges or using more data.")

# Show plot
print("\n📊 Generating plot...")
bt.plot()