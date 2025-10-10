"""
Supply and Demand Zones ULTRA HIGH FREQUENCY with Donchian Channels Strategy
=============================================================================

Ultra high frequency trading combining SDZ with Donchian channel breakouts.

Theory:
- Donchian channels show true price extremes over N periods
- Combine SDZ zones with Donchian bands for confluence
- Trade breakouts and reversals at channel boundaries
- Middle channel acts as dynamic equilibrium

Trading Logic:
- Buy when price touches lower Donchian AND demand zone
- Sell when price touches upper Donchian AND supply zone
- Use channel width for volatility-adjusted stops
- Quick scalps at channel extremes with zone confirmation
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Supply and Demand Zones ULTRA HIGH FREQ + DONCHIAN Strategy 🌙")
print("=" * 70)

# Load BTC 1-minute data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1m-4wks-data.csv'
print(f"📊 Loading BTC 1-minute data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)

# Rename columns
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

print(f"✅ Loaded {len(data):,} 1-minute bars")
print(f"📅 Date range: {data.index.min()} → {data.index.max()}")


class SDZUltraDonchianStrategy(Strategy):
    """
    Ultra High Frequency SDZ with Donchian Channels

    Parameters:
    - lookback_period: Period for SDZ calculation
    - donchian_period: Period for Donchian channels
    - channel_proximity: How close to channel for signal
    - zone_proximity: How close to SDZ for signal
    - channel_breakout_pct: Breakout threshold above/below channel
    - take_profit: Small for quick exits
    - stop_loss: Tight stop
    - max_hold_bars: Maximum bars to hold
    """

    # Optimizable parameters
    lookback_period = 8  # SDZ lookback
    donchian_period = 20  # Donchian period
    channel_proximity = 0.002  # 0.2% from channel
    zone_proximity = 0.008  # 0.8% from zone
    channel_breakout_pct = 0.001  # 0.1% breakout threshold
    take_profit = 0.003  # 0.3% take profit
    stop_loss = 0.002  # 0.2% stop loss
    max_hold_bars = 10  # Exit after 10 minutes max

    def init(self):
        """Initialize indicators"""
        # Calculate SDZ zones
        self.support = self.I(lambda: pd.Series(self.data.Close).rolling(
            window=self.lookback_period, min_periods=1).min())
        self.resistance = self.I(lambda: pd.Series(self.data.Close).rolling(
            window=self.lookback_period, min_periods=1).max())

        # Zone boundaries
        self.supp_lo = self.I(lambda: pd.Series(self.data.Low).rolling(
            window=self.lookback_period, min_periods=1).min())
        self.res_hi = self.I(lambda: pd.Series(self.data.High).rolling(
            window=self.lookback_period, min_periods=1).max())

        # Donchian Channels
        self.donchian_upper = self.I(lambda: pd.Series(self.data.High).rolling(
            window=self.donchian_period, min_periods=1).max())
        self.donchian_lower = self.I(lambda: pd.Series(self.data.Low).rolling(
            window=self.donchian_period, min_periods=1).min())
        self.donchian_middle = self.I(lambda: (self.donchian_upper + self.donchian_lower) / 2)

        # Channel width for volatility
        self.channel_width = self.I(lambda: (self.donchian_upper - self.donchian_lower) / self.donchian_middle)

        # Track entry bar
        self.entry_bar = 0

    def next(self):
        """Main strategy logic - high frequency with Donchian confirmation"""

        # Skip if insufficient data
        if len(self.data) < max(self.lookback_period, self.donchian_period):
            return

        # Get current values
        current_price = self.data.Close[-1]

        # Get SDZ zones
        demand_zone = self.support[-1]
        supply_zone = self.resistance[-1]
        demand_low = self.supp_lo[-1]
        supply_high = self.res_hi[-1]

        # Get Donchian values
        upper_channel = self.donchian_upper[-1]
        lower_channel = self.donchian_lower[-1]
        middle_channel = self.donchian_middle[-1]
        channel_width_pct = self.channel_width[-1] if self.channel_width[-1] else 0.01

        # Calculate positions relative to channels
        dist_to_upper = (upper_channel - current_price) / current_price
        dist_to_lower = (current_price - lower_channel) / current_price
        above_middle = current_price > middle_channel
        below_middle = current_price < middle_channel

        # Exit existing positions
        if self.position:
            bars_held = len(self.data) - self.entry_bar

            # Exit after max hold
            if bars_held >= self.max_hold_bars:
                self.position.close()
                return

            # Exit at middle channel (mean reversion)
            if self.position.is_long and current_price >= middle_channel:
                if self.position.pl_pct > 0:
                    self.position.close()
                    return
            elif self.position.is_short and current_price <= middle_channel:
                if self.position.pl_pct > 0:
                    self.position.close()
                    return

            # Quick profit exit
            if self.position.pl_pct >= self.take_profit * 0.25:
                self.position.close()
                return

        # Entry logic - only if no position
        if not self.position:

            # BUY signals - Confluence of Donchian lower and demand zones
            buy_conditions = []

            # At lower Donchian channel AND demand zone
            if dist_to_lower <= self.channel_proximity:
                if abs(current_price - demand_zone) / demand_zone <= self.zone_proximity:
                    buy_conditions.append("lower_channel_demand")

            # Breakout below lower channel with zone support
            if current_price < lower_channel * (1 - self.channel_breakout_pct):
                if abs(current_price - demand_low) / demand_low <= self.zone_proximity * 1.5:
                    buy_conditions.append("channel_breakout_low")

            # Below middle with demand zone confluence
            if below_middle and channel_width_pct < 0.02:  # Narrow channel
                if abs(current_price - demand_zone) / demand_zone <= self.zone_proximity:
                    buy_conditions.append("narrow_channel_demand")

            # Channel squeeze at demand
            if channel_width_pct < 0.01:  # Very narrow channel
                if abs(current_price - demand_zone) / demand_zone <= self.zone_proximity * 0.8:
                    buy_conditions.append("channel_squeeze_buy")

            # Donchian bounce from extreme
            if current_price <= lower_channel * 1.002:  # Just above lower
                if current_price > demand_low:  # But above extreme demand
                    buy_conditions.append("donchian_bounce")

            if buy_conditions:
                # Dynamic stop based on channel width
                channel_stop = min(channel_width_pct * 0.5, self.stop_loss)
                sl_price = current_price * (1 - channel_stop)
                # For longs, TP must be higher than entry - use max of middle channel or profit target
                tp_price = max(middle_channel, current_price * (1 + self.take_profit))
                # Ensure TP is above entry
                if tp_price <= current_price:
                    tp_price = current_price * (1 + self.take_profit)

                self.buy(sl=sl_price, tp=tp_price)
                self.entry_bar = len(self.data)

            # SELL signals - Confluence of Donchian upper and supply zones
            else:
                sell_conditions = []

                # At upper Donchian channel AND supply zone
                if dist_to_upper <= self.channel_proximity:
                    if abs(current_price - supply_zone) / supply_zone <= self.zone_proximity:
                        sell_conditions.append("upper_channel_supply")

                # Breakout above upper channel with zone resistance
                if current_price > upper_channel * (1 + self.channel_breakout_pct):
                    if abs(current_price - supply_high) / supply_high <= self.zone_proximity * 1.5:
                        sell_conditions.append("channel_breakout_high")

                # Above middle with supply zone confluence
                if above_middle and channel_width_pct < 0.02:  # Narrow channel
                    if abs(current_price - supply_zone) / supply_zone <= self.zone_proximity:
                        sell_conditions.append("narrow_channel_supply")

                # Channel squeeze at supply
                if channel_width_pct < 0.01:  # Very narrow channel
                    if abs(current_price - supply_zone) / supply_zone <= self.zone_proximity * 0.8:
                        sell_conditions.append("channel_squeeze_sell")

                # Donchian rejection from extreme
                if current_price >= upper_channel * 0.998:  # Just below upper
                    if current_price < supply_high:  # But below extreme supply
                        sell_conditions.append("donchian_rejection")

                if sell_conditions:
                    # Dynamic stop based on channel width
                    channel_stop = min(channel_width_pct * 0.5, self.stop_loss)
                    sl_price = current_price * (1 + channel_stop)
                    # For shorts, TP must be lower than entry - use min of middle channel or profit target
                    tp_price = min(middle_channel, current_price * (1 - self.take_profit))
                    # Ensure TP is below entry
                    if tp_price >= current_price:
                        tp_price = current_price * (1 - self.take_profit)

                    self.sell(sl=sl_price, tp=tp_price)
                    self.entry_bar = len(self.data)


# Run baseline backtest
print("\n" + "="*70)
print("RUNNING ULTRA HIGH FREQUENCY + DONCHIAN BACKTEST")
print("="*70)

bt = Backtest(
    data,
    SDZUltraDonchianStrategy,
    cash=1000000,  # $1M for BTC trading
    commission=0.001,
    exclusive_orders=True
)

# Run baseline
baseline_stats = bt.run()

print(f"\n📊 BASELINE RESULTS:")
print(f"SDZ Lookback: {SDZUltraDonchianStrategy.lookback_period} bars")
print(f"Donchian Period: {SDZUltraDonchianStrategy.donchian_period} bars")
print(f"Channel Proximity: {SDZUltraDonchianStrategy.channel_proximity*100:.1f}%")
print(f"Zone Proximity: {SDZUltraDonchianStrategy.zone_proximity*100:.1f}%")
print(f"Take Profit: {SDZUltraDonchianStrategy.take_profit*100:.1f}%")
print(f"Stop Loss: {SDZUltraDonchianStrategy.stop_loss*100:.1f}%")
print(f"Max Hold: {SDZUltraDonchianStrategy.max_hold_bars} bars")
print("-" * 50)
print(f"🔥 Total Trades: {baseline_stats['# Trades']}")
print(f"Win Rate: {baseline_stats['Win Rate [%]']:.2f}%")
print(f"Return: {baseline_stats['Return [%]']:.2f}%")
print(f"Sharpe: {baseline_stats['Sharpe Ratio']:.2f}")
print(f"Max Drawdown: {baseline_stats['Max. Drawdown [%]']:.2f}%")

print("\n📈 FULL BASELINE STATS:")
print("="*70)
print(baseline_stats)

# Run optimization for high trades with better returns
print("\n" + "="*70)
print("OPTIMIZING FOR HIGH TRADES WITH PROFITABILITY")
print("="*70)

try:
    optimization_results = bt.optimize(
        lookback_period=[6, 8, 10],
        donchian_period=[15, 20, 25],
        channel_proximity=[0.001, 0.002, 0.003],
        zone_proximity=[0.006, 0.008, 0.01],
        take_profit=[0.0025, 0.003, 0.0035],
        stop_loss=[0.0015, 0.002, 0.0025],
        max_hold_bars=[8, 10, 12],
        maximize='Return [%]',  # Optimize for returns
        constraint=lambda p: p['# Trades'] > 800,  # Keep high trade count
        return_heatmap=False
    )

    print("\n✨ OPTIMIZED RESULTS:")
    print("="*70)
    print(optimization_results)

    print("\n🎯 OPTIMIZED PARAMETERS:")
    print("-" * 50)
    print(f"🔥 Total Trades: {optimization_results['# Trades']}")
    print(f"Return: {optimization_results['Return [%]']:.2f}%")
    print(f"Win Rate: {optimization_results['Win Rate [%]']:.2f}%")
    print(f"Donchian Period: {optimization_results._strategy.donchian_period} bars")
    print(f"Channel Proximity: {optimization_results._strategy.channel_proximity*100:.1f}%")

except Exception as e:
    print(f"\n⚠️ Optimization failed: {str(e)}")

# Show plot
print("\n📊 Generating plot...")
bt.plot()