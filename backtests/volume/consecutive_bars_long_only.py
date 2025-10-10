"""
Consecutive Bars Reversal Strategy - LONG ONLY
===============================================

High-volume trading strategy that only takes long positions after consecutive down bars.

Theory:
- After X consecutive down bars, market often bounces
- Long-only approach for bull market bias
- Quick scalping trades with tight stops

Trading Logic:
- BUY after X consecutive down bars
- NO SHORT trades
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Consecutive Bars LONG-ONLY Volume Strategy 🌙")
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


class ConsecutiveBarsLongOnlyStrategy(Strategy):
    """
    Consecutive Bars Reversal - Long Only

    Parameters:
    - consecutive_bars: Number of consecutive down bars for buy signal
    - take_profit: Quick take profit %
    - stop_loss: Tight stop loss %
    - max_hold_bars: Maximum bars to hold position
    - min_bar_size: Minimum bar size to count
    - aggressive_mode: If True, uses fewer bars for more trades
    """

    # Optimizable parameters
    consecutive_bars = 3  # Need 3 down bars for long entry
    take_profit = 0.02  # 2% take profit
    stop_loss = 0.02  # 2% stop loss
    max_hold_bars = 15  # Exit after 15 minutes max
    min_bar_size = 0.00005  # Very small threshold for more signals
    aggressive_mode = 1  # 1 = aggressive, 0 = conservative

    def init(self):
        """Initialize indicators"""
        # Calculate price changes
        close_series = pd.Series(self.data.Close)
        self.pct_changes = self.I(lambda: close_series.pct_change().fillna(0))

        # Track recent lows for better entries
        self.recent_low = self.I(lambda: pd.Series(self.data.Low).rolling(
            window=20, min_periods=1).min())

        # Initialize tracking variables (not as indicators)
        self._consecutive_down = 0
        self._entry_bar = 0

    def next(self):
        """Main strategy logic"""

        # Skip first few bars
        if len(self.data) < 2:
            return

        # Get current values
        current_close = self.data.Close[-1]
        current_low = self.data.Low[-1]

        # Get current percentage change
        pct_change = self.pct_changes[-1]

        # Update consecutive down counter
        if pct_change < -self.min_bar_size:  # Down bar
            self._consecutive_down += 1
        else:
            self._consecutive_down = 0

        # Exit logic for existing positions
        if self.position:
            bars_held = len(self.data) - self._entry_bar
            if bars_held >= self.max_hold_bars:
                self.position.close()
                return

            # Early exit if quick profit (scalping)
            if self.position.pl_pct >= self.take_profit * 0.5:  # 50% of target
                self.position.close()
                return

        # Entry logic - LONG ONLY
        if not self.position:

            # Determine required bars based on mode
            required_bars = self.consecutive_bars if not self.aggressive_mode else max(2, self.consecutive_bars - 1)

            # BUY signal: After consecutive down bars
            if self._consecutive_down >= required_bars:

                # Additional filter: Price near recent low (oversold)
                if current_low <= self.recent_low[-1] * 1.002:  # Within 0.2% of recent low

                    # Calculate stops
                    sl_price = current_close * (1 - self.stop_loss)
                    tp_price = current_close * (1 + self.take_profit)

                    self.buy(sl=sl_price, tp=tp_price)
                    self._entry_bar = len(self.data)

                    # Reset counter
                    self._consecutive_down = 0


# Run baseline backtest
print("\n" + "="*70)
print("RUNNING BASELINE BACKTEST (LONG-ONLY)")
print("="*70)

bt = Backtest(
    data,
    ConsecutiveBarsLongOnlyStrategy,
    cash=1000000,
    commission=0.001,
    exclusive_orders=True
)

# Run baseline
baseline_stats = bt.run()

print(f"\n📊 BASELINE RESULTS:")
print(f"Consecutive Bars: {ConsecutiveBarsLongOnlyStrategy.consecutive_bars}")
print(f"Take Profit: {ConsecutiveBarsLongOnlyStrategy.take_profit*100:.2f}%")
print(f"Stop Loss: {ConsecutiveBarsLongOnlyStrategy.stop_loss*100:.2f}%")
print(f"Max Hold: {ConsecutiveBarsLongOnlyStrategy.max_hold_bars} bars")
print(f"Min Bar Size: {ConsecutiveBarsLongOnlyStrategy.min_bar_size*100:.4f}%")
print(f"Aggressive Mode: {'Yes' if ConsecutiveBarsLongOnlyStrategy.aggressive_mode else 'No'}")
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
        consecutive_bars=[2, 3, 4, 5],
        take_profit=[0.015, 0.02, 0.025, 0.03],
        stop_loss=[0.01, 0.015, 0.02, 0.025],
        max_hold_bars=[10, 15, 20],
        aggressive_mode=[0, 1],
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
    print(f"Aggressive Mode: {'Yes' if optimization_results._strategy.aggressive_mode else 'No'}")

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