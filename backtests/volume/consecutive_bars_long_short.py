"""
Consecutive Bars Reversal Strategy - LONG & SHORT
==================================================

High-volume trading strategy that trades reversals after consecutive bars in the same direction.

Theory:
- After X consecutive bars in one direction, market often reverses
- Quick mean reversion trades with tight stops
- Generates high trade volume for active trading

Trading Logic:
- BUY after X consecutive down bars
- SELL after X consecutive up bars
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Consecutive Bars LONG-SHORT Volume Strategy 🌙")
print("=" * 70)

# Load BTC 1-minute data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1m-4wks-data.csv'
print(f"📊 Loading BTC 1-minute data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)

# Rename columns
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Check for NaN values
print(f"⚠️ NaN values in data: {data.isnull().sum().sum()}")
if data.isnull().sum().sum() > 0:
    print("Dropping NaN values...")
    data = data.dropna()

print(f"✅ Loaded {len(data):,} 1-minute bars")
print(f"📅 Date range: {data.index.min()} → {data.index.max()}")


class ConsecutiveBarsLongShortStrategy(Strategy):
    """
    Consecutive Bars Reversal - Long & Short

    Parameters:
    - consecutive_bars: Number of consecutive bars needed for signal
    - take_profit: Quick take profit %
    - stop_loss: Tight stop loss %
    - max_hold_bars: Maximum bars to hold position
    - min_bar_size: Minimum bar size (% of price) to count as valid move
    """

    # Optimizable parameters
    consecutive_bars = 4  # Need 4 bars in same direction
    take_profit = 0.02  # 2% take profit
    stop_loss = 0.02  # 2% stop loss
    max_hold_bars = 10  # Exit after 10 minutes max
    min_bar_size = 0.00001  # Minimum 0.001% move to count (very small for 1-min bars)

    def init(self):
        """Initialize indicators"""
        # Calculate price changes
        close_series = pd.Series(self.data.Close)
        self.pct_changes = self.I(lambda: close_series.pct_change().fillna(0))

        # Initialize tracking variables (not as indicators)
        self._consecutive_up = 0
        self._consecutive_down = 0
        self._entry_bar = 0

    def next(self):
        """Main strategy logic"""

        # Skip first few bars
        if len(self.data) < 2:
            return

        # Get current percentage change
        pct_change = self.pct_changes[-1]

        # Update consecutive counters
        if pct_change > self.min_bar_size:  # Up bar
            self._consecutive_up += 1
            self._consecutive_down = 0
        elif pct_change < -self.min_bar_size:  # Down bar
            self._consecutive_down += 1
            self._consecutive_up = 0
        else:  # Neutral bar (too small movement)
            self._consecutive_up = 0
            self._consecutive_down = 0

        # Exit logic for existing positions
        if self.position:
            bars_held = len(self.data) - self._entry_bar
            if bars_held >= self.max_hold_bars:
                self.position.close()
                return

        # Entry logic - only if no position
        if not self.position:
            current_close = self.data.Close[-1]

            # BUY signal: After X consecutive down bars (reversal)
            if self._consecutive_down >= self.consecutive_bars:

                # Calculate stops
                sl_price = current_close * (1 - self.stop_loss)
                tp_price = current_close * (1 + self.take_profit)

                self.buy(sl=sl_price, tp=tp_price)
                self._entry_bar = len(self.data)

                # Reset counter
                self._consecutive_down = 0

            # SELL signal: After X consecutive up bars (reversal)
            elif self._consecutive_up >= self.consecutive_bars:

                # Calculate stops
                sl_price = current_close * (1 + self.stop_loss)
                tp_price = current_close * (1 - self.take_profit)

                self.sell(sl=sl_price, tp=tp_price)
                self._entry_bar = len(self.data)

                # Reset counter
                self._consecutive_up = 0


# Run baseline backtest
print("\n" + "="*70)
print("RUNNING BASELINE BACKTEST (LONG-SHORT)")
print("="*70)

bt = Backtest(
    data,
    ConsecutiveBarsLongShortStrategy,
    cash=1000000,
    commission=0.001,
    exclusive_orders=True
)

# Run baseline
baseline_stats = bt.run()

print(f"\n📊 BASELINE RESULTS:")
print(f"Consecutive Bars: {ConsecutiveBarsLongShortStrategy.consecutive_bars}")
print(f"Take Profit: {ConsecutiveBarsLongShortStrategy.take_profit*100:.2f}%")
print(f"Stop Loss: {ConsecutiveBarsLongShortStrategy.stop_loss*100:.2f}%")
print(f"Max Hold: {ConsecutiveBarsLongShortStrategy.max_hold_bars} bars")
print(f"Min Bar Size: {ConsecutiveBarsLongShortStrategy.min_bar_size*100:.3f}%")
print("-" * 50)
print(f"Total Trades: {baseline_stats['# Trades']}")
if baseline_stats['# Trades'] > 0:
    print(f"Win Rate: {baseline_stats['Win Rate [%]']:.2f}%")
    print(f"Return: {baseline_stats['Return [%]']:.2f}%")
    print(f"Sharpe: {baseline_stats['Sharpe Ratio']:.2f}")
    print(f"Max Drawdown: {baseline_stats['Max. Drawdown [%]']:.2f}%")
    print(f"Avg Trade Duration: {baseline_stats['Avg. Trade Duration']}")

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
        consecutive_bars=[3, 4, 5, 6],
        take_profit=[0.015, 0.02, 0.025, 0.03],
        stop_loss=[0.01, 0.015, 0.02, 0.025],
        max_hold_bars=[5, 10, 15, 20],
        maximize='Sharpe Ratio',
        return_heatmap=False
    )

    print("\n✨ OPTIMIZED RESULTS:")
    print("="*70)
    print(optimization_results)

    print("\n🎯 OPTIMIZED PARAMETERS:")
    print("-" * 50)
    print(f"Consecutive Bars: {optimization_results._strategy.consecutive_bars}")
    print(f"Take Profit: {optimization_results._strategy.take_profit*100:.2f}%")
    print(f"Stop Loss: {optimization_results._strategy.stop_loss*100:.2f}%")
    print(f"Max Hold: {optimization_results._strategy.max_hold_bars} bars")

    print("\n📊 PERFORMANCE COMPARISON:")
    print("-" * 50)
    print(f"Baseline Trades: {baseline_stats['# Trades']}")
    print(f"Optimized Trades: {optimization_results['# Trades']}")
    print(f"Baseline Return: {baseline_stats['Return [%]']:.2f}%")
    print(f"Optimized Return: {optimization_results['Return [%]']:.2f}%")
    print(f"Improvement: {optimization_results['Return [%]'] - baseline_stats['Return [%]']:.2f}%")

except Exception as e:
    print(f"\n⚠️ Optimization failed: {str(e)}")

# Show plot
print("\n📊 Generating plot...")
bt.plot()