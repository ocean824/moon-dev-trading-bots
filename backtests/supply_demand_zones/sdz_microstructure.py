"""
Supply and Demand Zones MICROSTRUCTURE Strategy
================================================

Ultra high frequency trading on microstructure inefficiencies at zones.

Theory:
- Small price dislocations correct quickly
- Spread approximation shows market stress
- Tick analysis reveals true direction
- Micro reversals at zone boundaries

Trading Logic:
- Track micro price movements (tick analysis)
- Enter on micro exhaustion patterns
- Use spread proxy for market stress
- Ultra-quick scalps on inefficiencies
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Supply and Demand Zones MICROSTRUCTURE Strategy 🌙")
print("=" * 70)

# Load BTC 1-minute data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1m-4wks-data.csv'
print(f"📊 Loading BTC 1-minute data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)

# Rename columns
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Calculate microstructure indicators
# Spread approximation
data['Spread'] = (data['High'] - data['Low']) / data['Close']
data['Spread_MA'] = data['Spread'].rolling(20).mean()

# Micro momentum (tick analysis)
data['Micro_Move'] = data['Close'] - data['Open']
data['Micro_Direction'] = np.sign(data['Micro_Move'])
data['Micro_Streak'] = (data['Micro_Direction'].groupby((data['Micro_Direction'] != data['Micro_Direction'].shift()).cumsum()).cumcount() + 1) * data['Micro_Direction']

# Price efficiency ratio (straight line vs actual path)
data['Efficiency'] = abs(data['Close'] - data['Close'].shift(5)) / (abs(data['Close'] - data['Close'].shift(1)).rolling(5).sum() + 0.0001)

# Micro volatility
data['Micro_Vol'] = data['Close'].pct_change().rolling(5).std()

# Order flow proxy
data['OF_Proxy'] = (2 * data['Close'] - data['High'] - data['Low']) / (data['High'] - data['Low'] + 0.0001)

print(f"✅ Loaded {len(data):,} 1-minute bars")
print(f"📅 Date range: {data.index.min()} → {data.index.max()}")


class SDZMicrostructureStrategy(Strategy):
    """
    Microstructure SDZ Strategy

    Parameters:
    - lookback_period: Period for zone calculation
    - spread_threshold: Maximum spread for entry
    - micro_streak_reversal: Streak length for reversal
    - efficiency_threshold: Minimum efficiency for trend
    - micro_vol_filter: Maximum micro volatility
    - take_profit: Quick scalp target
    - stop_loss: Tight stop
    """

    # Optimizable parameters
    lookback_period = 6  # Very short zones
    spread_threshold = 0.001  # Max 0.1% spread
    micro_streak_reversal = 3  # Reverse after 3 same direction
    efficiency_threshold = 0.3  # Minimum 30% efficiency
    micro_vol_filter = 0.002  # Max 0.2% micro volatility
    take_profit = 0.0025  # 0.25% quick scalp
    stop_loss = 0.0015  # 0.15% tight stop

    def init(self):
        """Initialize indicators"""
        # Calculate zones
        self.support = self.I(lambda: pd.Series(self.data.Close).rolling(
            window=self.lookback_period, min_periods=1).min())
        self.resistance = self.I(lambda: pd.Series(self.data.Close).rolling(
            window=self.lookback_period, min_periods=1).max())

        # Microstructure indicators
        self.spread = self.I(lambda: self.data.Spread)
        self.spread_ma = self.I(lambda: self.data.Spread_MA)
        self.micro_streak = self.I(lambda: self.data.Micro_Streak)
        self.efficiency = self.I(lambda: self.data.Efficiency)
        self.micro_vol = self.I(lambda: self.data.Micro_Vol)
        self.of_proxy = self.I(lambda: self.data.OF_Proxy)

        # Track micro patterns
        self.consecutive_highs = 0
        self.consecutive_lows = 0
        self.entry_spread = 0

    def next(self):
        """Main strategy logic - microstructure scalping"""

        # Skip if insufficient data
        if len(self.data) < 25:
            return

        # Get current values
        current_price = self.data.Close[-1]
        current_spread = self.spread[-1] if self.spread[-1] else 0.001
        current_spread_ma = self.spread_ma[-1] if self.spread_ma[-1] else 0.001
        current_streak = self.micro_streak[-1] if self.micro_streak[-1] else 0
        current_efficiency = self.efficiency[-1] if self.efficiency[-1] else 0.5
        current_micro_vol = self.micro_vol[-1] if self.micro_vol[-1] else 0.001
        current_of_proxy = self.of_proxy[-1] if self.of_proxy[-1] else 0

        # Get zones
        demand_zone = self.support[-1]
        supply_zone = self.resistance[-1]

        # Update micro patterns
        if len(self.data) > 1:
            if current_price > self.data.High[-2]:
                self.consecutive_highs += 1
                self.consecutive_lows = 0
            elif current_price < self.data.Low[-2]:
                self.consecutive_lows += 1
                self.consecutive_highs = 0
            else:
                self.consecutive_highs = max(0, self.consecutive_highs - 1)
                self.consecutive_lows = max(0, self.consecutive_lows - 1)

        # Exit logic
        if self.position:
            # Exit on spread widening (market stress)
            if current_spread > self.entry_spread * 2:
                self.position.close()
                return

            # Exit on efficiency breakdown
            if current_efficiency < 0.1:  # Very inefficient = choppy
                if self.position.pl_pct > -self.stop_loss * 0.5:
                    self.position.close()
                    return

            # Quick scalp exit
            if self.position.pl_pct >= self.take_profit * 0.4:
                self.position.close()
                return

        # Entry logic - only if no position
        if not self.position:

            # Filter: Good market conditions
            if current_spread > self.spread_threshold:
                return  # Spread too wide
            if current_micro_vol > self.micro_vol_filter:
                return  # Too volatile

            # Zone proximity
            near_demand = abs(current_price - demand_zone) / demand_zone <= 0.003
            near_supply = abs(current_price - supply_zone) / supply_zone <= 0.003

            # BUY signals - Micro exhaustion at demand
            buy_signal = False

            # Streak reversal at demand
            if current_streak <= -self.micro_streak_reversal and near_demand:
                buy_signal = True

            # Consecutive lows exhaustion
            elif self.consecutive_lows >= 3 and near_demand:
                if current_of_proxy > -0.5:  # Not extreme selling
                    buy_signal = True

            # Efficiency breakdown reversal
            elif current_efficiency < 0.2 and near_demand:
                if len(self.data) > 2:
                    if self.efficiency[-2] > 0.3:  # Was efficient, now not
                        buy_signal = True

            # Micro volatility squeeze
            elif current_micro_vol < 0.0005 and near_demand:  # Very low volatility
                if current_spread < current_spread_ma * 0.7:  # Tight spread
                    buy_signal = True

            # Order flow reversal
            elif current_of_proxy < -0.7 and near_demand:
                if len(self.data) > 2:
                    if self.of_proxy[-2] > -0.3:  # Quick OF change
                        buy_signal = True

            if buy_signal:
                sl_price = current_price * (1 - self.stop_loss)
                tp_price = current_price * (1 + self.take_profit)
                self.buy(sl=sl_price, tp=tp_price)
                self.entry_spread = current_spread

            # SELL signals - Micro exhaustion at supply
            else:
                sell_signal = False

                # Streak reversal at supply
                if current_streak >= self.micro_streak_reversal and near_supply:
                    sell_signal = True

                # Consecutive highs exhaustion
                elif self.consecutive_highs >= 3 and near_supply:
                    if current_of_proxy < 0.5:  # Not extreme buying
                        sell_signal = True

                # Efficiency breakdown reversal
                elif current_efficiency < 0.2 and near_supply:
                    if len(self.data) > 2:
                        if self.efficiency[-2] > 0.3:  # Was efficient, now not
                            sell_signal = True

                # Micro volatility squeeze
                elif current_micro_vol < 0.0005 and near_supply:  # Very low volatility
                    if current_spread < current_spread_ma * 0.7:  # Tight spread
                        sell_signal = True

                # Order flow reversal
                elif current_of_proxy > 0.7 and near_supply:
                    if len(self.data) > 2:
                        if self.of_proxy[-2] < 0.3:  # Quick OF change
                            sell_signal = True

                if sell_signal:
                    sl_price = current_price * (1 + self.stop_loss)
                    tp_price = current_price * (1 - self.take_profit)
                    self.sell(sl=sl_price, tp=tp_price)
                    self.entry_spread = current_spread


# Run baseline backtest
print("\n" + "="*70)
print("RUNNING MICROSTRUCTURE BACKTEST")
print("="*70)

bt = Backtest(
    data,
    SDZMicrostructureStrategy,
    cash=1000000,  # $1M for BTC trading
    commission=0.001,
    exclusive_orders=True
)

# Run baseline
baseline_stats = bt.run()

print(f"\n📊 BASELINE RESULTS:")
print(f"Lookback Period: {SDZMicrostructureStrategy.lookback_period} bars")
print(f"Spread Threshold: {SDZMicrostructureStrategy.spread_threshold*100:.2f}%")
print(f"Streak Reversal: {SDZMicrostructureStrategy.micro_streak_reversal} bars")
print(f"Take Profit: {SDZMicrostructureStrategy.take_profit*100:.2f}%")
print(f"Stop Loss: {SDZMicrostructureStrategy.stop_loss*100:.2f}%")
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
print("OPTIMIZING FOR HIGH FREQUENCY PROFITS")
print("="*70)

try:
    optimization_results = bt.optimize(
        lookback_period=[5, 6, 7],
        spread_threshold=[0.0008, 0.001, 0.0012],
        micro_streak_reversal=[2, 3, 4],
        efficiency_threshold=[0.2, 0.3, 0.4],
        take_profit=[0.002, 0.0025, 0.003],
        stop_loss=[0.0012, 0.0015, 0.0018],
        maximize='Return [%]',
        constraint=lambda p: p['# Trades'] > 1000,
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