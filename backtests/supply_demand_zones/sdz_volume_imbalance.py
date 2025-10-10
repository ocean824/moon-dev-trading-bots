"""
Supply and Demand Zones VOLUME IMBALANCE Strategy
==================================================

Ultra high frequency trading based on buy/sell volume imbalances at zones.

Theory:
- Volume imbalances reveal true supply/demand
- Large buy volume at demand = strong support
- Large sell volume at supply = strong resistance
- Trade the imbalance correction

Trading Logic:
- Calculate buy vs sell volume approximation
- Enter when imbalance is extreme at zones
- Quick exits when balance restored
- Use cumulative delta for confirmation
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Supply and Demand Zones VOLUME IMBALANCE Strategy 🌙")
print("=" * 70)

# Load BTC 1-minute data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1m-4wks-data.csv'
print(f"📊 Loading BTC 1-minute data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)

# Rename columns
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Calculate volume imbalance indicators
# Approximate buy/sell volume
data['Price_Change'] = data['Close'] - data['Open']
data['Buy_Volume'] = data['Volume'] * (data['Price_Change'] > 0).astype(int)
data['Sell_Volume'] = data['Volume'] * (data['Price_Change'] < 0).astype(int)

# Volume imbalance ratio
data['Volume_Imbalance'] = (data['Buy_Volume'] - data['Sell_Volume']) / data['Volume'].where(data['Volume'] > 0, 1)

# Cumulative volume delta
data['CVD'] = (data['Buy_Volume'] - data['Sell_Volume']).cumsum()
data['CVD_MA'] = data['CVD'].rolling(20).mean()

# Volume rate of change
data['Volume_ROC'] = data['Volume'].pct_change(5)

print(f"✅ Loaded {len(data):,} 1-minute bars")
print(f"📅 Date range: {data.index.min()} → {data.index.max()}")


class SDZVolumeImbalanceStrategy(Strategy):
    """
    Volume Imbalance SDZ Strategy

    Parameters:
    - lookback_period: Period for zone calculation
    - imbalance_threshold: Minimum imbalance for entry
    - cvd_divergence_bars: Bars to check for CVD divergence
    - volume_spike: Minimum volume increase
    - take_profit: Quick profit target
    - stop_loss: Tight stop
    - rebalance_exit: Exit when imbalance normalizes
    """

    # Optimizable parameters
    lookback_period = 7  # Short for quick zones
    imbalance_threshold = 0.3  # 30% imbalance minimum
    cvd_divergence_bars = 10  # Look back for divergence
    volume_spike = 1.5  # 1.5x average volume
    take_profit = 0.0035  # 0.35% take profit
    stop_loss = 0.002  # 0.2% stop loss
    rebalance_exit = 0.1  # Exit when imbalance < 10%

    def init(self):
        """Initialize indicators"""
        # Calculate zones
        self.support = self.I(lambda: pd.Series(self.data.Close).rolling(
            window=self.lookback_period, min_periods=1).min())
        self.resistance = self.I(lambda: pd.Series(self.data.Close).rolling(
            window=self.lookback_period, min_periods=1).max())

        # Volume indicators
        self.volume_imbalance = self.I(lambda: self.data.Volume_Imbalance)
        self.cvd = self.I(lambda: self.data.CVD)
        self.cvd_ma = self.I(lambda: self.data.CVD_MA)
        self.volume_roc = self.I(lambda: self.data.Volume_ROC)
        self.volume = self.I(lambda: self.data.Volume)

        # Volume moving average
        self.volume_ma = self.I(lambda: pd.Series(self.data.Volume).rolling(
            window=20, min_periods=1).mean())

        # Track entry imbalance
        self.entry_imbalance = 0
        self.entry_bar = 0

    def next(self):
        """Main strategy logic - volume imbalance trading"""

        # Skip if insufficient data
        if len(self.data) < 30:
            return

        # Get current values
        current_price = self.data.Close[-1]
        current_imbalance = self.volume_imbalance[-1] if self.volume_imbalance[-1] else 0
        current_cvd = self.cvd[-1] if self.cvd[-1] else 0
        current_cvd_ma = self.cvd_ma[-1] if self.cvd_ma[-1] else 0
        current_volume = self.volume[-1]
        current_volume_ma = self.volume_ma[-1] if self.volume_ma[-1] else 1
        current_volume_roc = self.volume_roc[-1] if self.volume_roc[-1] else 0

        # Get zones
        demand_zone = self.support[-1]
        supply_zone = self.resistance[-1]

        # Check for CVD divergence
        cvd_divergence = False
        if len(self.data) > self.cvd_divergence_bars:
            price_change = (current_price - self.data.Close[-self.cvd_divergence_bars]) / self.data.Close[-self.cvd_divergence_bars]
            cvd_change = (current_cvd - self.cvd[-self.cvd_divergence_bars]) / abs(self.cvd[-self.cvd_divergence_bars]) if self.cvd[-self.cvd_divergence_bars] != 0 else 0

            # Bullish divergence: price down, CVD up
            if price_change < -0.001 and cvd_change > 0.01:
                cvd_divergence = "bullish"
            # Bearish divergence: price up, CVD down
            elif price_change > 0.001 and cvd_change < -0.01:
                cvd_divergence = "bearish"

        # Exit logic
        if self.position:
            bars_held = len(self.data) - self.entry_bar

            # Exit if imbalance normalizes
            if abs(current_imbalance) < self.rebalance_exit:
                if self.position.pl_pct > 0:
                    self.position.close()
                    return

            # Exit if imbalance reverses
            if self.position.is_long:
                if current_imbalance < -self.rebalance_exit:  # Selling pressure
                    self.position.close()
                    return
            else:
                if current_imbalance > self.rebalance_exit:  # Buying pressure
                    self.position.close()
                    return

            # Time exit
            if bars_held > 15:
                self.position.close()
                return

        # Entry logic - only if no position
        if not self.position:

            # Volume spike requirement
            volume_spike = current_volume > current_volume_ma * self.volume_spike

            # Zone proximity
            near_demand = abs(current_price - demand_zone) / demand_zone <= 0.005
            near_supply = abs(current_price - supply_zone) / supply_zone <= 0.005

            # BUY signal - Buying imbalance at demand
            buy_signal = False

            # Strong buy imbalance at demand
            if near_demand and current_imbalance > self.imbalance_threshold:
                if volume_spike or current_volume_roc > 0.5:
                    buy_signal = True

            # CVD bullish divergence
            elif cvd_divergence == "bullish" and near_demand:
                buy_signal = True

            # Extreme buy imbalance anywhere
            elif current_imbalance > self.imbalance_threshold * 1.5:
                if current_price < (demand_zone + supply_zone) / 2:
                    buy_signal = True

            if buy_signal:
                sl_price = current_price * (1 - self.stop_loss)
                tp_price = current_price * (1 + self.take_profit)
                self.buy(sl=sl_price, tp=tp_price)
                self.entry_imbalance = current_imbalance
                self.entry_bar = len(self.data)

            # SELL signal - Selling imbalance at supply
            else:
                sell_signal = False

                # Strong sell imbalance at supply
                if near_supply and current_imbalance < -self.imbalance_threshold:
                    if volume_spike or current_volume_roc > 0.5:
                        sell_signal = True

                # CVD bearish divergence
                elif cvd_divergence == "bearish" and near_supply:
                    sell_signal = True

                # Extreme sell imbalance anywhere
                elif current_imbalance < -self.imbalance_threshold * 1.5:
                    if current_price > (demand_zone + supply_zone) / 2:
                        sell_signal = True

                if sell_signal:
                    sl_price = current_price * (1 + self.stop_loss)
                    tp_price = current_price * (1 - self.take_profit)
                    self.sell(sl=sl_price, tp=tp_price)
                    self.entry_imbalance = current_imbalance
                    self.entry_bar = len(self.data)


# Run baseline backtest
print("\n" + "="*70)
print("RUNNING VOLUME IMBALANCE BACKTEST")
print("="*70)

bt = Backtest(
    data,
    SDZVolumeImbalanceStrategy,
    cash=1000000,  # $1M for BTC trading
    commission=0.001,
    exclusive_orders=True
)

# Run baseline
baseline_stats = bt.run()

print(f"\n📊 BASELINE RESULTS:")
print(f"Lookback Period: {SDZVolumeImbalanceStrategy.lookback_period} bars")
print(f"Imbalance Threshold: {SDZVolumeImbalanceStrategy.imbalance_threshold*100:.0f}%")
print(f"Volume Spike: {SDZVolumeImbalanceStrategy.volume_spike}x")
print(f"Take Profit: {SDZVolumeImbalanceStrategy.take_profit*100:.2f}%")
print(f"Stop Loss: {SDZVolumeImbalanceStrategy.stop_loss*100:.1f}%")
print("-" * 50)
print(f"🔥 Total Trades: {baseline_stats['# Trades']}")
print(f"Win Rate: {baseline_stats['Win Rate [%]']:.2f}%")
print(f"Return: {baseline_stats['Return [%]']:.2f}%")
print(f"Sharpe: {baseline_stats['Sharpe Ratio']:.2f}")
print(f"Max Drawdown: {baseline_stats['Max. Drawdown [%]']:.2f}%")

print("\n📈 FULL BASELINE STATS:")
print("="*70)
print(baseline_stats)

# Run optimization
print("\n" + "="*70)
print("OPTIMIZING FOR BETTER RETURNS")
print("="*70)

try:
    optimization_results = bt.optimize(
        lookback_period=[5, 7, 9],
        imbalance_threshold=[0.2, 0.3, 0.4],
        volume_spike=[1.3, 1.5, 2.0],
        take_profit=[0.003, 0.0035, 0.004],
        stop_loss=[0.0015, 0.002, 0.0025],
        rebalance_exit=[0.05, 0.1, 0.15],
        maximize='Sharpe Ratio',
        constraint=lambda p: p['# Trades'] > 300,
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
    print(f"Sharpe: {optimization_results['Sharpe Ratio']:.2f}")

except Exception as e:
    print(f"\n⚠️ Optimization failed: {str(e)}")

# Show plot
print("\n📊 Generating plot...")
bt.plot()