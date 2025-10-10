"""
Supply and Demand Zones ULTRA HIGH FREQUENCY with ADX Strategy
================================================================

Ultra high frequency trading with ADX trend strength filter for better entries.

Theory:
- Trade zone touches only when ADX confirms trend strength
- ADX > 25 for trending markets, ADX < 25 for ranging markets
- Use +DI/-DI for directional confirmation
- Maintain high trade frequency with better quality signals

Trading Logic:
- Enter on zone touch WITH trend when ADX > threshold
- Quick scalp exits but with trend confirmation
- ADX filter reduces false signals while keeping volume high
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Supply and Demand Zones ULTRA HIGH FREQ + ADX Strategy 🌙")
print("=" * 70)

# Load BTC 1-minute data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1m-4wks-data.csv'
print(f"📊 Loading BTC 1-minute data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)

# Rename columns
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Calculate ADX indicators
adx_data = ta.adx(data['High'], data['Low'], data['Close'], length=14)
data['ADX'] = adx_data['ADX_14']
data['DI_plus'] = adx_data['DMP_14']
data['DI_minus'] = adx_data['DMN_14']

print(f"✅ Loaded {len(data):,} 1-minute bars")
print(f"📅 Date range: {data.index.min()} → {data.index.max()}")


class SDZUltraADXStrategy(Strategy):
    """
    Ultra High Frequency SDZ with ADX Filtering

    Parameters:
    - lookback_period: Very short period for rapid zone updates
    - zone_proximity: How close to zone to trigger
    - adx_threshold: Minimum ADX for trend trades
    - adx_range_max: Maximum ADX for range trades
    - take_profit: Small for quick exits
    - stop_loss: Tight stop
    - max_hold_bars: Maximum bars to hold
    """

    # Optimizable parameters
    lookback_period = 8  # Very short lookback
    zone_proximity = 0.008  # 0.8% proximity (tighter than original)
    adx_threshold = 20  # Minimum ADX for trending
    adx_range_max = 30  # Max ADX for ranging markets
    take_profit = 0.003  # 0.3% take profit
    stop_loss = 0.002  # 0.2% stop loss
    max_hold_bars = 10  # Exit after 10 minutes max

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

        # ADX indicators
        self.adx = self.I(lambda: self.data.ADX)
        self.di_plus = self.I(lambda: self.data.DI_plus)
        self.di_minus = self.I(lambda: self.data.DI_minus)

        # Track entry bar
        self.entry_bar = 0

    def next(self):
        """Main strategy logic - high frequency with ADX filter"""

        # Skip if insufficient data
        if len(self.data) < max(self.lookback_period, 20):
            return

        # Get current values
        current_price = self.data.Close[-1]
        current_adx = self.adx[-1] if self.adx[-1] else 20
        current_di_plus = self.di_plus[-1] if self.di_plus[-1] else 0
        current_di_minus = self.di_minus[-1] if self.di_minus[-1] else 0

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

            # Quick exit on small profit (20% of target)
            if self.position.pl_pct >= self.take_profit * 0.2:
                self.position.close()
                return

        # Entry logic - only if no position
        if not self.position:

            # Determine market condition
            is_trending = current_adx > self.adx_threshold
            is_ranging = current_adx <= self.adx_range_max
            bullish_bias = current_di_plus > current_di_minus
            bearish_bias = current_di_minus > current_di_plus

            # BUY signals with ADX confirmation
            buy_conditions = []

            # Demand zone touch with bullish confirmation
            if abs(current_price - demand_zone) / demand_zone <= self.zone_proximity:
                if (is_trending and bullish_bias) or is_ranging:
                    buy_conditions.append("demand_zone")

            # Extreme demand with any positive DI
            if abs(current_price - demand_low) / demand_low <= self.zone_proximity:
                if current_di_plus > 15:  # Minimal bullish pressure
                    buy_conditions.append("extreme_demand")

            # Zone midpoint buy in ranging market
            zone_mid = (demand_zone + supply_zone) / 2
            if is_ranging and current_price < zone_mid * 0.995:
                buy_conditions.append("range_buy")

            if buy_conditions:
                sl_price = current_price * (1 - self.stop_loss)
                tp_price = current_price * (1 + self.take_profit)
                self.buy(sl=sl_price, tp=tp_price)
                self.entry_bar = len(self.data)

            # SELL signals with ADX confirmation
            else:
                sell_conditions = []

                # Supply zone touch with bearish confirmation
                if abs(current_price - supply_zone) / supply_zone <= self.zone_proximity:
                    if (is_trending and bearish_bias) or is_ranging:
                        sell_conditions.append("supply_zone")

                # Extreme supply with any negative DI
                if abs(current_price - supply_high) / supply_high <= self.zone_proximity:
                    if current_di_minus > 15:  # Minimal bearish pressure
                        sell_conditions.append("extreme_supply")

                # Zone midpoint sell in ranging market
                zone_mid = (demand_zone + supply_zone) / 2
                if is_ranging and current_price > zone_mid * 1.005:
                    sell_conditions.append("range_sell")

                if sell_conditions:
                    sl_price = current_price * (1 + self.stop_loss)
                    tp_price = current_price * (1 - self.take_profit)
                    self.sell(sl=sl_price, tp=tp_price)
                    self.entry_bar = len(self.data)


# Run baseline backtest
print("\n" + "="*70)
print("RUNNING ULTRA HIGH FREQUENCY + ADX BACKTEST")
print("="*70)

bt = Backtest(
    data,
    SDZUltraADXStrategy,
    cash=1000000,  # $1M for BTC trading
    commission=0.001,
    exclusive_orders=True
)

# Run baseline
baseline_stats = bt.run()

print(f"\n📊 BASELINE RESULTS:")
print(f"Lookback Period: {SDZUltraADXStrategy.lookback_period} bars")
print(f"Zone Proximity: {SDZUltraADXStrategy.zone_proximity*100:.1f}%")
print(f"ADX Threshold: {SDZUltraADXStrategy.adx_threshold}")
print(f"Take Profit: {SDZUltraADXStrategy.take_profit*100:.1f}%")
print(f"Stop Loss: {SDZUltraADXStrategy.stop_loss*100:.1f}%")
print(f"Max Hold: {SDZUltraADXStrategy.max_hold_bars} bars")
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
print("OPTIMIZING FOR MAXIMUM TRADES WITH PROFIT")
print("="*70)

try:
    optimization_results = bt.optimize(
        lookback_period=[6, 8, 10, 12],
        zone_proximity=[0.006, 0.008, 0.01, 0.012],
        adx_threshold=[15, 20, 25],
        take_profit=[0.0025, 0.003, 0.0035],
        stop_loss=[0.0015, 0.002, 0.0025],
        max_hold_bars=[8, 10, 15],
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
    print(f"Lookback Period: {optimization_results._strategy.lookback_period} bars")
    print(f"Zone Proximity: {optimization_results._strategy.zone_proximity*100:.1f}%")
    print(f"ADX Threshold: {optimization_results._strategy.adx_threshold}")

except Exception as e:
    print(f"\n⚠️ Optimization failed: {str(e)}")

# Show plot
print("\n📊 Generating plot...")
bt.plot()