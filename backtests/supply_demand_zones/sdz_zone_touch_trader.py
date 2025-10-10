"""
Supply and Demand Zones ZONE TOUCH TRADER Strategy
===================================================

Trades EVERY zone touch with multiple entry techniques for maximum volume.

Theory:
- Trade on first touch of any zone
- Trade on zone re-tests
- Trade on zone breakouts
- Trade on zone breakdowns
- Maximum possible entries

Trading Logic:
- Multiple entry conditions all active simultaneously
- No waiting periods between trades
- Minimal filters for maximum activity
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Supply and Demand Zones ZONE TOUCH TRADER Strategy 🌙")
print("=" * 70)

# Load BTC 1-minute data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1m-4wks-data.csv'
print(f"📊 Loading BTC 1-minute data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)

# Rename columns
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Add rate of change for additional signals
data['ROC'] = data['Close'].pct_change(2)  # 2-bar rate of change

print(f"✅ Loaded {len(data):,} 1-minute bars")
print(f"📅 Date range: {data.index.min()} → {data.index.max()}")


class SDZZoneTouchTraderStrategy(Strategy):
    """
    Zone Touch Trader - Maximum Volume Through Multiple Entry Types

    Parameters:
    - lookback_short: Short period for fast zones
    - lookback_long: Long period for major zones
    - touch_threshold: How close counts as a "touch"
    - micro_profit: Ultra-small profit target
    - micro_loss: Ultra-small stop loss
    """

    # Optimizable parameters
    lookback_short = 5  # Ultra-short for rapid zones
    lookback_long = 15  # Longer for major zones
    touch_threshold = 0.002  # 0.2% counts as zone touch
    micro_profit = 0.0015  # 0.15% profit
    micro_loss = 0.001  # 0.1% stop

    def init(self):
        """Initialize indicators"""
        # Fast zones (more signals)
        self.support_fast = self.I(lambda: pd.Series(self.data.Close).rolling(
            window=self.lookback_short, min_periods=1).min())
        self.resistance_fast = self.I(lambda: pd.Series(self.data.Close).rolling(
            window=self.lookback_short, min_periods=1).max())

        # Slow zones (major levels)
        self.support_slow = self.I(lambda: pd.Series(self.data.Close).rolling(
            window=self.lookback_long, min_periods=1).min())
        self.resistance_slow = self.I(lambda: pd.Series(self.data.Close).rolling(
            window=self.lookback_long, min_periods=1).max())

        # Extreme zones
        self.low_extreme = self.I(lambda: pd.Series(self.data.Low).rolling(
            window=self.lookback_short, min_periods=1).min())
        self.high_extreme = self.I(lambda: pd.Series(self.data.High).rolling(
            window=self.lookback_short, min_periods=1).max())

        # Rate of change
        self.roc = self.I(lambda: self.data.ROC)

        # Track last trade bar to allow rapid re-entry
        self.last_trade_bar = -10  # Start with -10 to allow immediate trading

    def next(self):
        """Main strategy logic - trade all zone interactions"""

        # Skip if insufficient data
        if len(self.data) < self.lookback_long:
            return

        # Get current values
        current_price = self.data.Close[-1]
        current_roc = self.roc[-1] if self.roc[-1] else 0

        # Get all zone levels
        sup_fast = self.support_fast[-1]
        res_fast = self.resistance_fast[-1]
        sup_slow = self.support_slow[-1]
        res_slow = self.resistance_slow[-1]
        low_ext = self.low_extreme[-1]
        high_ext = self.high_extreme[-1]

        # Allow new trades after just 1 bar
        bars_since_trade = len(self.data) - self.last_trade_bar

        # Entry logic - only if no position and enough time passed
        if not self.position and bars_since_trade > 1:

            # Create multiple buy conditions
            buy_signals = []

            # Fast support touch
            if abs(current_price - sup_fast) / sup_fast <= self.touch_threshold:
                buy_signals.append("fast_support")

            # Slow support touch
            if abs(current_price - sup_slow) / sup_slow <= self.touch_threshold:
                buy_signals.append("slow_support")

            # Extreme low touch
            if abs(current_price - low_ext) / low_ext <= self.touch_threshold:
                buy_signals.append("extreme_low")

            # Positive ROC at any support
            if current_roc > 0 and current_price < (sup_fast + res_fast) / 2:
                buy_signals.append("positive_roc")

            # Below midpoint with any support nearby
            midpoint = (res_slow + sup_slow) / 2
            if current_price < midpoint * 0.995:  # 0.5% below midpoint
                buy_signals.append("below_mid")

            # Execute buy if any signal triggered
            if buy_signals:
                sl_price = current_price * (1 - self.micro_loss)
                tp_price = current_price * (1 + self.micro_profit)
                self.buy(sl=sl_price, tp=tp_price)
                self.last_trade_bar = len(self.data)

            else:
                # Create multiple sell conditions
                sell_signals = []

                # Fast resistance touch
                if abs(current_price - res_fast) / res_fast <= self.touch_threshold:
                    sell_signals.append("fast_resistance")

                # Slow resistance touch
                if abs(current_price - res_slow) / res_slow <= self.touch_threshold:
                    sell_signals.append("slow_resistance")

                # Extreme high touch
                if abs(current_price - high_ext) / high_ext <= self.touch_threshold:
                    sell_signals.append("extreme_high")

                # Negative ROC at any resistance
                if current_roc < 0 and current_price > (sup_fast + res_fast) / 2:
                    sell_signals.append("negative_roc")

                # Above midpoint with any resistance nearby
                midpoint = (res_slow + sup_slow) / 2
                if current_price > midpoint * 1.005:  # 0.5% above midpoint
                    sell_signals.append("above_mid")

                # Execute sell if any signal triggered
                if sell_signals:
                    sl_price = current_price * (1 + self.micro_loss)
                    tp_price = current_price * (1 - self.micro_profit)
                    self.sell(sl=sl_price, tp=tp_price)
                    self.last_trade_bar = len(self.data)


# Run baseline backtest
print("\n" + "="*70)
print("RUNNING ZONE TOUCH TRADER BACKTEST")
print("="*70)

bt = Backtest(
    data,
    SDZZoneTouchTraderStrategy,
    cash=1000000,  # $1M for BTC trading
    commission=0.001,
    exclusive_orders=True
)

# Run baseline
baseline_stats = bt.run()

print(f"\n📊 BASELINE RESULTS:")
print(f"Lookback Short: {SDZZoneTouchTraderStrategy.lookback_short} bars")
print(f"Lookback Long: {SDZZoneTouchTraderStrategy.lookback_long} bars")
print(f"Touch Threshold: {SDZZoneTouchTraderStrategy.touch_threshold*100:.1f}%")
print(f"Micro Profit: {SDZZoneTouchTraderStrategy.micro_profit*100:.2f}%")
print(f"Micro Loss: {SDZZoneTouchTraderStrategy.micro_loss*100:.1f}%")
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
        lookback_short=[3, 5, 7],
        lookback_long=[10, 15, 20],
        touch_threshold=[0.001, 0.002, 0.003],
        micro_profit=[0.0015, 0.002, 0.0025],  # Increased minimum to avoid rounding
        micro_loss=[0.001, 0.0012, 0.0015],  # Increased to avoid rounding
        maximize='# Trades',  # Maximize trade count!
        return_heatmap=False
    )

    print("\n✨ OPTIMIZED RESULTS:")
    print("="*70)
    print(optimization_results)

    print("\n🎯 OPTIMIZED PARAMETERS:")
    print("-" * 50)
    print(f"🔥 Total Trades: {optimization_results['# Trades']}")
    print(f"Lookback Short: {optimization_results._strategy.lookback_short} bars")
    print(f"Lookback Long: {optimization_results._strategy.lookback_long} bars")
    print(f"Touch Threshold: {optimization_results._strategy.touch_threshold*100:.1f}%")
    print(f"Return: {optimization_results['Return [%]']:.2f}%")

except Exception as e:
    print(f"\n⚠️ Optimization failed: {str(e)}")

# Show plot
print("\n📊 Generating plot...")
bt.plot()