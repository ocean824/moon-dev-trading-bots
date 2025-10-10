"""
Supply and Demand Zones ULTRA HIGH FREQUENCY with VWAP Strategy
================================================================

Ultra high frequency trading with VWAP mean reversion for better profitability.

Theory:
- Trade zone touches with VWAP as dynamic support/resistance
- Price above VWAP = bullish bias, below = bearish bias
- VWAP deviation bands for extreme conditions
- Quick mean reversion trades to VWAP

Trading Logic:
- Buy at demand zones when below VWAP (mean reversion)
- Sell at supply zones when above VWAP
- Use VWAP bands for additional entries
- Maintain ultra-high frequency with VWAP confirmation
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Supply and Demand Zones ULTRA HIGH FREQ + VWAP Strategy 🌙")
print("=" * 70)

# Load BTC 1-minute data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1m-4wks-data.csv'
print(f"📊 Loading BTC 1-minute data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)

# Rename columns
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Calculate VWAP and bands
data['VWAP'] = ta.vwap(data['High'], data['Low'], data['Close'], data['Volume'])

# Calculate VWAP standard deviation bands
typical_price = (data['High'] + data['Low'] + data['Close']) / 3
squared_diff = (typical_price - data['VWAP']) ** 2
data['VWAP_STD'] = (squared_diff.rolling(window=20).mean()) ** 0.5

# VWAP bands
data['VWAP_Upper'] = data['VWAP'] + (data['VWAP_STD'] * 2)
data['VWAP_Lower'] = data['VWAP'] - (data['VWAP_STD'] * 2)

print(f"✅ Loaded {len(data):,} 1-minute bars")
print(f"📅 Date range: {data.index.min()} → {data.index.max()}")


class SDZUltraVWAPStrategy(Strategy):
    """
    Ultra High Frequency SDZ with VWAP Mean Reversion

    Parameters:
    - lookback_period: Very short period for rapid zone updates
    - zone_proximity: How close to zone to trigger
    - vwap_deviation: Max deviation from VWAP for trades
    - vwap_band_mult: Multiplier for VWAP bands
    - take_profit: Small for quick exits
    - stop_loss: Tight stop
    - max_hold_bars: Maximum bars to hold
    """

    # Optimizable parameters
    lookback_period = 7  # Very short lookback
    zone_proximity = 0.01  # 1% proximity
    vwap_deviation = 0.005  # Max 0.5% from VWAP for mean reversion
    vwap_band_mult = 1.5  # VWAP band multiplier
    take_profit = 0.0025  # 0.25% take profit
    stop_loss = 0.0018  # 0.18% stop loss
    max_hold_bars = 8  # Exit after 8 minutes max

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

        # VWAP indicators
        self.vwap = self.I(lambda: self.data.VWAP)
        self.vwap_upper = self.I(lambda: self.data.VWAP_Upper)
        self.vwap_lower = self.I(lambda: self.data.VWAP_Lower)

        # Track entry bar
        self.entry_bar = 0

    def next(self):
        """Main strategy logic - high frequency with VWAP filter"""

        # Skip if insufficient data
        if len(self.data) < max(self.lookback_period, 25):
            return

        # Get current values
        current_price = self.data.Close[-1]
        current_vwap = self.vwap[-1] if self.vwap[-1] else current_price
        current_vwap_upper = self.vwap_upper[-1] if self.vwap_upper[-1] else current_vwap * 1.01
        current_vwap_lower = self.vwap_lower[-1] if self.vwap_lower[-1] else current_vwap * 0.99

        # Get zones
        demand_zone = self.support[-1]
        supply_zone = self.resistance[-1]
        demand_low = self.supp_lo[-1]
        supply_high = self.res_hi[-1]

        # Calculate VWAP position
        vwap_distance = (current_price - current_vwap) / current_vwap
        above_vwap = current_price > current_vwap
        below_vwap = current_price < current_vwap

        # Exit existing positions
        if self.position:
            bars_held = len(self.data) - self.entry_bar

            # Exit after max hold
            if bars_held >= self.max_hold_bars:
                self.position.close()
                return

            # Quick exit at VWAP (mean reversion target)
            if self.position.is_long and current_price >= current_vwap:
                if self.position.pl_pct > 0:
                    self.position.close()
                    return
            elif self.position.is_short and current_price <= current_vwap:
                if self.position.pl_pct > 0:
                    self.position.close()
                    return

        # Entry logic - only if no position
        if not self.position:

            # BUY signals - Mean reversion to VWAP from below
            buy_conditions = []

            # Demand zone touch when below VWAP
            if abs(current_price - demand_zone) / demand_zone <= self.zone_proximity:
                if below_vwap and abs(vwap_distance) <= self.vwap_deviation * 2:
                    buy_conditions.append("demand_below_vwap")

            # Extreme oversold at VWAP lower band
            if current_price <= current_vwap_lower:
                if abs(current_price - demand_low) / demand_low <= self.zone_proximity * 1.5:
                    buy_conditions.append("vwap_lower_band")

            # Strong mean reversion opportunity
            if below_vwap and vwap_distance < -self.vwap_deviation:
                if current_price < supply_zone * 0.98:  # Not near resistance
                    buy_conditions.append("vwap_mean_reversion")

            # Zone bounce with VWAP support
            if abs(current_price - current_vwap) / current_vwap <= 0.001:  # At VWAP
                if abs(current_price - demand_zone) / demand_zone <= self.zone_proximity * 1.2:
                    buy_conditions.append("vwap_support")

            if buy_conditions:
                # Target is VWAP or take profit, whichever is closer
                vwap_target = min(current_vwap, current_price * (1 + self.take_profit))
                sl_price = current_price * (1 - self.stop_loss)
                tp_price = max(vwap_target, current_price * (1 + self.take_profit))

                self.buy(sl=sl_price, tp=tp_price)
                self.entry_bar = len(self.data)

            # SELL signals - Mean reversion to VWAP from above
            else:
                sell_conditions = []

                # Supply zone touch when above VWAP
                if abs(current_price - supply_zone) / supply_zone <= self.zone_proximity:
                    if above_vwap and abs(vwap_distance) <= self.vwap_deviation * 2:
                        sell_conditions.append("supply_above_vwap")

                # Extreme overbought at VWAP upper band
                if current_price >= current_vwap_upper:
                    if abs(current_price - supply_high) / supply_high <= self.zone_proximity * 1.5:
                        sell_conditions.append("vwap_upper_band")

                # Strong mean reversion opportunity
                if above_vwap and vwap_distance > self.vwap_deviation:
                    if current_price > demand_zone * 1.02:  # Not near support
                        sell_conditions.append("vwap_mean_reversion")

                # Zone rejection with VWAP resistance
                if abs(current_price - current_vwap) / current_vwap <= 0.001:  # At VWAP
                    if abs(current_price - supply_zone) / supply_zone <= self.zone_proximity * 1.2:
                        sell_conditions.append("vwap_resistance")

                if sell_conditions:
                    # Target is VWAP or take profit, whichever is closer
                    vwap_target = max(current_vwap, current_price * (1 - self.take_profit))
                    sl_price = current_price * (1 + self.stop_loss)
                    tp_price = min(vwap_target, current_price * (1 - self.take_profit))

                    self.sell(sl=sl_price, tp=tp_price)
                    self.entry_bar = len(self.data)


# Run baseline backtest
print("\n" + "="*70)
print("RUNNING ULTRA HIGH FREQUENCY + VWAP BACKTEST")
print("="*70)

bt = Backtest(
    data,
    SDZUltraVWAPStrategy,
    cash=1000000,  # $1M for BTC trading
    commission=0.001,
    exclusive_orders=True
)

# Run baseline
baseline_stats = bt.run()

print(f"\n📊 BASELINE RESULTS:")
print(f"Lookback Period: {SDZUltraVWAPStrategy.lookback_period} bars")
print(f"Zone Proximity: {SDZUltraVWAPStrategy.zone_proximity*100:.1f}%")
print(f"VWAP Deviation: {SDZUltraVWAPStrategy.vwap_deviation*100:.1f}%")
print(f"Take Profit: {SDZUltraVWAPStrategy.take_profit*100:.2f}%")
print(f"Stop Loss: {SDZUltraVWAPStrategy.stop_loss*100:.2f}%")
print(f"Max Hold: {SDZUltraVWAPStrategy.max_hold_bars} bars")
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
        lookback_period=[5, 7, 9],
        zone_proximity=[0.008, 0.01, 0.012],
        vwap_deviation=[0.003, 0.005, 0.007],
        take_profit=[0.002, 0.0025, 0.003],
        stop_loss=[0.0015, 0.0018, 0.002],
        max_hold_bars=[6, 8, 10],
        maximize='Return [%]',  # Optimize for returns
        constraint=lambda p: p['# Trades'] > 1000,  # Keep high trade count
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
    print(f"Lookback Period: {optimization_results._strategy.lookback_period} bars")
    print(f"VWAP Deviation: {optimization_results._strategy.vwap_deviation*100:.1f}%")

except Exception as e:
    print(f"\n⚠️ Optimization failed: {str(e)}")

# Show plot
print("\n📊 Generating plot...")
bt.plot()