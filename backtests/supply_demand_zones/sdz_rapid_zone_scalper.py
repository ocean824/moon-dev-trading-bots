"""
Supply and Demand Zones RAPID ZONE SCALPER Strategy
====================================================

Aggressive scalping strategy that trades zone boundaries with no hold time.

Theory:
- Trade both zone entries AND exits
- Use momentum to determine direction
- Ultra-quick exits on any profit
- Trade zone-to-zone movements

Trading Logic:
- Enter on zone touch
- Exit on opposite zone touch OR tiny profit
- No complex confirmations
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Supply and Demand Zones RAPID ZONE SCALPER Strategy 🌙")
print("=" * 70)

# Load BTC 1-minute data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1m-4wks-data.csv'
print(f"📊 Loading BTC 1-minute data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)

# Rename columns
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Add simple momentum indicator
data['Momentum'] = data['Close'].pct_change(3)  # 3-bar momentum

print(f"✅ Loaded {len(data):,} 1-minute bars")
print(f"📅 Date range: {data.index.min()} → {data.index.max()}")


class SDZRapidZoneScalperStrategy(Strategy):
    """
    Rapid Zone Scalper - Trade Every Zone Boundary

    Parameters:
    - lookback_period: Period for zone calculation
    - zone_buffer: Buffer around zones (smaller = more trades)
    - scalp_profit: Tiny profit target for instant exit
    - stop_loss: Tight stop
    - momentum_filter: Minimum momentum to trade
    """

    # Optimizable parameters
    lookback_period = 8  # Very short for rapid zone changes
    zone_buffer = 0.0005  # 0.05% buffer (very tight)
    scalp_profit = 0.002  # 0.2% instant profit target (increased to avoid rounding)
    stop_loss = 0.003  # 0.3% stop loss
    momentum_filter = 0.0  # No momentum filter (trade everything)

    def init(self):
        """Initialize indicators"""
        # Calculate zones
        self.support = self.I(lambda: pd.Series(self.data.Close).rolling(
            window=self.lookback_period, min_periods=1).min())
        self.resistance = self.I(lambda: pd.Series(self.data.Close).rolling(
            window=self.lookback_period, min_periods=1).max())

        # Zone boundaries
        self.supp_lo = self.I(lambda: pd.Series(self.data.Low).rolling(
            window=self.lookback_period, min_periods=1).min())
        self.res_hi = self.I(lambda: pd.Series(self.data.High).rolling(
            window=self.lookback_period, min_periods=1).max())

        # Momentum
        self.momentum = self.I(lambda: self.data.Momentum)

        # Zone midpoint for targets
        self.zone_mid = self.I(lambda: (self.support + self.resistance) / 2)

    def next(self):
        """Main strategy logic - aggressive scalping"""

        # Skip if insufficient data
        if len(self.data) < self.lookback_period + 3:
            return

        # Get current values
        current_price = self.data.Close[-1]
        current_momentum = self.momentum[-1] if self.momentum[-1] else 0

        # Get zones
        support = self.support[-1]
        resistance = self.resistance[-1]
        supp_lo = self.supp_lo[-1]
        res_hi = self.res_hi[-1]
        zone_mid = self.zone_mid[-1]

        # Quick exit on any profit
        if self.position:
            if self.position.pl_pct >= self.scalp_profit * 0.5:  # Exit at 50% of target
                self.position.close()
                return

        # Entry logic - only if no position
        if not self.position:

            # Define entry zones with buffer
            demand_entry = support * (1 + self.zone_buffer)
            supply_entry = resistance * (1 - self.zone_buffer)

            # Additional aggressive entries
            demand_extreme = supp_lo * (1 + self.zone_buffer)
            supply_extreme = res_hi * (1 - self.zone_buffer)

            # BUY signals (multiple conditions for more trades)
            buy_signal = False

            # Buy at demand zone
            if current_price <= demand_entry:
                buy_signal = True

            # Buy at extreme demand
            elif current_price <= demand_extreme:
                buy_signal = True

            # Buy on positive momentum bounce
            elif current_price < zone_mid and current_momentum > self.momentum_filter:
                buy_signal = True

            if buy_signal:
                sl_price = current_price * (1 - self.stop_loss)
                tp_price = current_price * (1 + self.scalp_profit)
                self.buy(sl=sl_price, tp=tp_price)

            # SELL signals (multiple conditions for more trades)
            else:
                sell_signal = False

                # Sell at supply zone
                if current_price >= supply_entry:
                    sell_signal = True

                # Sell at extreme supply
                elif current_price >= supply_extreme:
                    sell_signal = True

                # Sell on negative momentum
                elif current_price > zone_mid and current_momentum < -self.momentum_filter:
                    sell_signal = True

                if sell_signal:
                    sl_price = current_price * (1 + self.stop_loss)
                    tp_price = current_price * (1 - self.scalp_profit)
                    self.sell(sl=sl_price, tp=tp_price)


# Run baseline backtest
print("\n" + "="*70)
print("RUNNING RAPID ZONE SCALPER BACKTEST")
print("="*70)

bt = Backtest(
    data,
    SDZRapidZoneScalperStrategy,
    cash=1000000,  # $1M for BTC trading
    commission=0.001,
    exclusive_orders=True
)

# Run baseline
baseline_stats = bt.run()

print(f"\n📊 BASELINE RESULTS:")
print(f"Lookback Period: {SDZRapidZoneScalperStrategy.lookback_period} bars")
print(f"Zone Buffer: {SDZRapidZoneScalperStrategy.zone_buffer*100:.2f}%")
print(f"Scalp Profit: {SDZRapidZoneScalperStrategy.scalp_profit*100:.1f}%")
print(f"Stop Loss: {SDZRapidZoneScalperStrategy.stop_loss*100:.1f}%")
print("-" * 50)
print(f"🔥 Total Trades: {baseline_stats['# Trades']}")
print(f"Win Rate: {baseline_stats['Win Rate [%]']:.2f}%")
print(f"Return: {baseline_stats['Return [%]']:.2f}%")
print(f"Max Drawdown: {baseline_stats['Max. Drawdown [%]']:.2f}%")

print("\n📈 FULL BASELINE STATS:")
print("="*70)
print(baseline_stats)

# Run optimization for maximum trades
print("\n" + "="*70)
print("OPTIMIZING FOR MAXIMUM TRADES")
print("="*70)

try:
    optimization_results = bt.optimize(
        lookback_period=[5, 6, 8, 10],
        zone_buffer=[0.0003, 0.0005, 0.001],
        scalp_profit=[0.0008, 0.001, 0.0012],
        stop_loss=[0.0015, 0.002, 0.0025],
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
    print(f"Zone Buffer: {optimization_results._strategy.zone_buffer*100:.3f}%")
    print(f"Scalp Profit: {optimization_results._strategy.scalp_profit*100:.2f}%")

except Exception as e:
    print(f"\n⚠️ Optimization failed: {str(e)}")

# Show plot
print("\n📊 Generating plot...")
bt.plot()