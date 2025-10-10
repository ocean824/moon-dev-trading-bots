"""
Supply and Demand Zones MOMENTUM BURST Strategy
================================================

Ultra high frequency trading on explosive momentum moves at zone boundaries.

Theory:
- Trade only when momentum explodes at key zones
- Quick entries on momentum acceleration
- Exit on momentum exhaustion or reversal
- Volume must confirm the momentum move

Trading Logic:
- Enter when momentum spikes AND price hits zone
- Use momentum ROC for acceleration detection
- Exit when momentum slows or reverses
- Trail stops with momentum strength
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Supply and Demand Zones MOMENTUM BURST Strategy 🌙")
print("=" * 70)

# Load BTC 1-minute data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1m-4wks-data.csv'
print(f"📊 Loading BTC 1-minute data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)

# Rename columns
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Calculate momentum indicators
data['Momentum'] = data['Close'].pct_change(3)
data['Momentum_Accel'] = data['Momentum'].diff()  # Acceleration
data['Volume_Ratio'] = data['Volume'] / data['Volume'].rolling(20).mean()

# RSI for momentum strength
data['RSI'] = ta.rsi(data['Close'], length=6)  # Very short RSI

print(f"✅ Loaded {len(data):,} 1-minute bars")
print(f"📅 Date range: {data.index.min()} → {data.index.max()}")


class SDZMomentumBurstStrategy(Strategy):
    """
    Momentum Burst SDZ Strategy

    Parameters:
    - lookback_period: Period for zone calculation
    - momentum_threshold: Minimum momentum for entry
    - accel_threshold: Minimum acceleration
    - volume_multiplier: Volume spike requirement
    - take_profit: Dynamic based on momentum
    - stop_loss: Tight stop
    - momentum_exit_threshold: Exit when momentum drops below this
    """

    # Optimizable parameters
    lookback_period = 6  # Very short for quick zones
    momentum_threshold = 0.002  # 0.2% momentum minimum
    accel_threshold = 0.0005  # Acceleration threshold
    volume_multiplier = 1.2  # Volume must be 1.2x average
    take_profit = 0.004  # 0.4% base take profit
    stop_loss = 0.002  # 0.2% stop loss
    momentum_exit_threshold = 0.0005  # Exit if momentum drops below 0.05%

    def init(self):
        """Initialize indicators"""
        # Calculate zones
        self.support = self.I(lambda: pd.Series(self.data.Close).rolling(
            window=self.lookback_period, min_periods=1).min())
        self.resistance = self.I(lambda: pd.Series(self.data.Close).rolling(
            window=self.lookback_period, min_periods=1).max())

        # Momentum indicators
        self.momentum = self.I(lambda: self.data.Momentum)
        self.momentum_accel = self.I(lambda: self.data.Momentum_Accel)
        self.volume_ratio = self.I(lambda: self.data.Volume_Ratio)
        self.rsi = self.I(lambda: self.data.RSI)

        # Track entry momentum
        self.entry_momentum = 0

    def next(self):
        """Main strategy logic - momentum burst trading"""

        # Skip if insufficient data
        if len(self.data) < 25:
            return

        # Get current values
        current_price = self.data.Close[-1]
        current_momentum = self.momentum[-1] if self.momentum[-1] else 0
        current_accel = self.momentum_accel[-1] if self.momentum_accel[-1] else 0
        current_volume_ratio = self.volume_ratio[-1] if self.volume_ratio[-1] else 1
        current_rsi = self.rsi[-1] if self.rsi[-1] else 50

        # Get zones
        demand_zone = self.support[-1]
        supply_zone = self.resistance[-1]

        # Exit logic - momentum-based
        if self.position:
            # Exit if momentum reverses significantly
            if self.position.is_long:
                if current_momentum < -self.momentum_exit_threshold:
                    self.position.close()
                    return
                # Exit if momentum drops below entry momentum
                if current_momentum < self.entry_momentum * 0.3:
                    if self.position.pl_pct > 0:
                        self.position.close()
                        return
            else:
                if current_momentum > self.momentum_exit_threshold:
                    self.position.close()
                    return
                # Exit if momentum rises above entry momentum
                if current_momentum > self.entry_momentum * 0.3:
                    if self.position.pl_pct > 0:
                        self.position.close()
                        return

            # Trail stop based on momentum strength
            if self.position.pl_pct > self.take_profit * 0.5:
                # Tighten stop when in profit
                if self.position.is_long:
                    new_sl = current_price * (1 - self.stop_loss * 0.5)
                    if new_sl > self.position.sl:
                        self.position.sl = new_sl
                else:
                    new_sl = current_price * (1 + self.stop_loss * 0.5)
                    if new_sl < self.position.sl:
                        self.position.sl = new_sl

        # Entry logic - only if no position
        if not self.position:

            # Zone proximity
            near_demand = abs(current_price - demand_zone) / demand_zone <= 0.005
            near_supply = abs(current_price - supply_zone) / supply_zone <= 0.005

            # BUY signal - Upward momentum burst at demand
            if (near_demand and
                current_momentum > self.momentum_threshold and
                current_accel > self.accel_threshold and
                current_volume_ratio > self.volume_multiplier and
                current_rsi < 70):  # Not overbought

                # Dynamic TP based on momentum strength
                momentum_multiplier = min(abs(current_momentum) / self.momentum_threshold, 2)
                tp_multiplier = self.take_profit * momentum_multiplier

                sl_price = current_price * (1 - self.stop_loss)
                tp_price = current_price * (1 + tp_multiplier)

                self.buy(sl=sl_price, tp=tp_price)
                self.entry_momentum = current_momentum

            # SELL signal - Downward momentum burst at supply
            elif (near_supply and
                  current_momentum < -self.momentum_threshold and
                  current_accel < -self.accel_threshold and
                  current_volume_ratio > self.volume_multiplier and
                  current_rsi > 30):  # Not oversold

                # Dynamic TP based on momentum strength
                momentum_multiplier = min(abs(current_momentum) / self.momentum_threshold, 2)
                tp_multiplier = self.take_profit * momentum_multiplier

                sl_price = current_price * (1 + self.stop_loss)
                tp_price = current_price * (1 - tp_multiplier)

                self.sell(sl=sl_price, tp=tp_price)
                self.entry_momentum = current_momentum


# Run baseline backtest
print("\n" + "="*70)
print("RUNNING MOMENTUM BURST BACKTEST")
print("="*70)

bt = Backtest(
    data,
    SDZMomentumBurstStrategy,
    cash=1000000,  # $1M for BTC trading
    commission=0.001,
    exclusive_orders=True
)

# Run baseline
baseline_stats = bt.run()

print(f"\n📊 BASELINE RESULTS:")
print(f"Lookback Period: {SDZMomentumBurstStrategy.lookback_period} bars")
print(f"Momentum Threshold: {SDZMomentumBurstStrategy.momentum_threshold*100:.1f}%")
print(f"Acceleration Threshold: {SDZMomentumBurstStrategy.accel_threshold*100:.2f}%")
print(f"Take Profit: {SDZMomentumBurstStrategy.take_profit*100:.1f}%")
print(f"Stop Loss: {SDZMomentumBurstStrategy.stop_loss*100:.1f}%")
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
print("OPTIMIZING FOR PROFITABILITY WITH HIGH TRADES")
print("="*70)

try:
    optimization_results = bt.optimize(
        lookback_period=[5, 6, 8],
        momentum_threshold=[0.0015, 0.002, 0.0025],
        accel_threshold=[0.0003, 0.0005, 0.0007],
        volume_multiplier=[1.1, 1.2, 1.5],
        take_profit=[0.003, 0.004, 0.005],
        stop_loss=[0.0015, 0.002, 0.0025],
        maximize='Sharpe Ratio',  # Optimize for risk-adjusted returns
        constraint=lambda p: p['# Trades'] > 500,  # Keep trades high
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