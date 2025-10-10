"""
Supply and Demand Zones ULTRA HIGH FREQUENCY Strategy
======================================================

Maximum volume strategy - trades every tiny zone touch with minimal filters.

Theory:
- Trade EVERY zone interaction
- Minimal confirmation requirements
- Tiny stops for rapid turnover
- Accept lower win rate for massive trade volume

Trading Logic:
- Enter immediately when price touches any zone edge
- No volume or VWAP requirements
- Quick scalp exits
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Supply and Demand Zones ULTRA HIGH FREQUENCY Strategy 🌙")
print("=" * 70)

# Load BTC 1-minute data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1m-4wks-data.csv'
print(f"📊 Loading BTC 1-minute data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)

# Rename columns
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

print(f"✅ Loaded {len(data):,} 1-minute bars")
print(f"📅 Date range: {data.index.min()} → {data.index.max()}")


class SDZUltraHighFrequencyStrategy(Strategy):
    """
    Ultra High Frequency SDZ Strategy - Maximum Trade Volume

    Parameters:
    - lookback_period: Very short period for rapid zone updates
    - zone_proximity: How close to zone to trigger (larger = more trades)
    - take_profit: Very small for quick exits
    - stop_loss: Very small for quick stops
    - max_hold_bars: Maximum bars to hold (force exit)
    """

    # Optimizable parameters
    lookback_period = 10  # Very short lookback for more zone changes
    zone_proximity = 0.01  # Within 1% of zone (very loose)
    take_profit = 0.002  # 0.2% take profit (tiny)
    stop_loss = 0.0015  # 0.15% stop loss (tiny)
    max_hold_bars = 5  # Exit after 5 minutes max

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

        # Track entry bar
        self.entry_bar = 0

    def next(self):
        """Main strategy logic - trade every zone touch"""

        # Skip if insufficient data
        if len(self.data) < self.lookback_period:
            return

        # Get current values
        current_price = self.data.Close[-1]

        # Get zones
        demand_zone = self.support[-1]
        supply_zone = self.resistance[-1]
        demand_low = self.supp_lo[-1]
        supply_high = self.res_hi[-1]

        # Exit existing positions after max hold
        if self.position:
            bars_held = len(self.data) - self.entry_bar
            if bars_held >= self.max_hold_bars:
                self.position.close()
                return

        # Entry logic - only if no position
        if not self.position:

            # BUY signal: Price within proximity of demand zone
            if abs(current_price - demand_zone) / demand_zone <= self.zone_proximity:

                # Simple stops
                sl_price = current_price * (1 - self.stop_loss)
                tp_price = current_price * (1 + self.take_profit)

                self.buy(sl=sl_price, tp=tp_price)
                self.entry_bar = len(self.data)

            # SELL signal: Price within proximity of supply zone
            elif abs(current_price - supply_zone) / supply_zone <= self.zone_proximity:

                # Simple stops
                sl_price = current_price * (1 + self.stop_loss)
                tp_price = current_price * (1 - self.take_profit)

                self.sell(sl=sl_price, tp=tp_price)
                self.entry_bar = len(self.data)

            # Additional entries at zone extremes
            # BUY at demand zone low
            elif abs(current_price - demand_low) / demand_low <= self.zone_proximity:
                sl_price = current_price * (1 - self.stop_loss)
                tp_price = current_price * (1 + self.take_profit)
                self.buy(sl=sl_price, tp=tp_price)
                self.entry_bar = len(self.data)

            # SELL at supply zone high
            elif abs(current_price - supply_high) / supply_high <= self.zone_proximity:
                sl_price = current_price * (1 + self.stop_loss)
                tp_price = current_price * (1 - self.take_profit)
                self.sell(sl=sl_price, tp=tp_price)
                self.entry_bar = len(self.data)


# Run baseline backtest
print("\n" + "="*70)
print("RUNNING ULTRA HIGH FREQUENCY BACKTEST")
print("="*70)

bt = Backtest(
    data,
    SDZUltraHighFrequencyStrategy,
    cash=1000000,  # $1M for BTC trading
    commission=0.001,
    exclusive_orders=True
)

# Run baseline
baseline_stats = bt.run()

print(f"\n📊 BASELINE RESULTS:")
print(f"Lookback Period: {SDZUltraHighFrequencyStrategy.lookback_period} bars")
print(f"Zone Proximity: {SDZUltraHighFrequencyStrategy.zone_proximity*100:.1f}%")
print(f"Take Profit: {SDZUltraHighFrequencyStrategy.take_profit*100:.2f}%")
print(f"Stop Loss: {SDZUltraHighFrequencyStrategy.stop_loss*100:.2f}%")
print(f"Max Hold: {SDZUltraHighFrequencyStrategy.max_hold_bars} bars")
print("-" * 50)
print(f"🔥 Total Trades: {baseline_stats['# Trades']}")
print(f"Win Rate: {baseline_stats['Win Rate [%]']:.2f}%")
print(f"Return: {baseline_stats['Return [%]']:.2f}%")
print(f"Max Drawdown: {baseline_stats['Max. Drawdown [%]']:.2f}%")

print("\n📈 FULL BASELINE STATS:")
print("="*70)
print(baseline_stats)

# Run optimization for even more trades
print("\n" + "="*70)
print("OPTIMIZING FOR MAXIMUM TRADES")
print("="*70)

try:
    optimization_results = bt.optimize(
        lookback_period=[5, 8, 10, 12],
        zone_proximity=[0.008, 0.01, 0.015, 0.02],
        take_profit=[0.0015, 0.002, 0.0025],
        stop_loss=[0.001, 0.0015, 0.002],
        max_hold_bars=[3, 5, 8],
        maximize='# Trades',  # Maximize trade count!
        return_heatmap=False
    )

    print("\n✨ OPTIMIZED RESULTS:")
    print("="*70)
    print(optimization_results)

    print("\n🎯 OPTIMIZED PARAMETERS:")
    print("-" * 50)
    print(f"🔥 Total Trades: {optimization_results['# Trades']}")
    print(f"Lookback Period: {optimization_results._strategy.lookback_period} bars")
    print(f"Zone Proximity: {optimization_results._strategy.zone_proximity*100:.1f}%")
    print(f"Take Profit: {optimization_results._strategy.take_profit*100:.2f}%")
    print(f"Stop Loss: {optimization_results._strategy.stop_loss*100:.2f}%")

except Exception as e:
    print(f"\n⚠️ Optimization failed: {str(e)}")

# Show plot
print("\n📊 Generating plot...")
bt.plot()