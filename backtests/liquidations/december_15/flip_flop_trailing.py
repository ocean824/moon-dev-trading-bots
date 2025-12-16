"""
Flip Flop TRAILING STOP Variation - Moon Dev
=============================================
Based on the winning Flip Flop strategy (529% return)

VARIATION: Instead of fixed TP/SL, use a TRAILING STOP
- Buy the dip on liquidation
- Use trailing stop instead of fixed TP
- When trailing stop hit on long, flip to short
- Use trailing stop on short too

Theory: Capture more of the move with trailing stops instead of fixed TP

Moon Dev 🌙
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's FLIP FLOP TRAILING STOP Strategy 🌙")
print("Variation: Trailing stops instead of fixed TP")
print("=" * 70)

# Data configuration
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/moondev_api/liq_data_BTC_5m_ohlcv.csv'
timeframe = '5-minute'

print(f"📊 Loading preprocessed {timeframe} BTC liquidation data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)

print(f"✅ Loaded {len(data):,} {timeframe} bars")

# Map liquidation columns
if 'long_liquidations' in data.columns and 'short_liquidations' in data.columns:
    data['long_liq_volume'] = data['long_liquidations']
    data['short_liq_volume'] = data['short_liquidations']
    data['net_liq_volume'] = data['short_liquidations'] - data['long_liquidations']
else:
    data['long_liq_volume'] = 0
    data['short_liq_volume'] = 0
    data['net_liq_volume'] = 0


class FlipFlopTrailingStrategy(Strategy):
    """
    Flip Flop with Trailing Stop

    - Buy on liquidation signal
    - Trail stop at X% from highest price
    - When stopped out of long, flip to short
    - Trail stop on short at X% from lowest price
    """

    # Optimizable parameters
    liquidation_threshold = 500000  # From optimized flip flop
    lookback_bars = 3  # From optimized flip flop
    trailing_stop_pct = 2.0  # Trailing stop distance
    initial_stop_pct = 10.0  # Initial stop before trailing kicks in
    min_profit_to_trail = 1.0  # Minimum profit before trailing activates

    position_size = 0.95

    def init(self):
        self.long_liq_volume = self.I(lambda: self.data.long_liq_volume)
        self.rolling_long_liq = self.I(
            lambda x: pd.Series(x).rolling(self.lookback_bars, min_periods=1).sum(),
            self.long_liq_volume
        )

        self.state = 'waiting'
        self.entry_price = 0
        self.highest_since_entry = 0
        self.lowest_since_entry = 0

    def next(self):
        current_price = self.data.Close[-1]
        current_rolling_liq = self.rolling_long_liq[-1]

        # STATE: WAITING
        if self.state == 'waiting':
            if not self.position:
                if current_rolling_liq >= self.liquidation_threshold:
                    self.buy(size=self.position_size)
                    self.entry_price = current_price
                    self.highest_since_entry = current_price
                    self.state = 'long'

        # STATE: LONG with trailing stop
        elif self.state == 'long':
            if self.position and self.position.is_long:
                # Update highest price
                if current_price > self.highest_since_entry:
                    self.highest_since_entry = current_price

                pnl_pct = ((current_price - self.entry_price) / self.entry_price) * 100
                drawdown_from_high = ((self.highest_since_entry - current_price) / self.highest_since_entry) * 100

                # If in profit and trailing activates
                if pnl_pct >= self.min_profit_to_trail:
                    # Trailing stop hit
                    if drawdown_from_high >= self.trailing_stop_pct:
                        self.position.close()
                        # Flip to short
                        self.sell(size=self.position_size)
                        self.entry_price = current_price
                        self.lowest_since_entry = current_price
                        self.state = 'short'
                else:
                    # Initial stop loss before trailing kicks in
                    if pnl_pct <= -self.initial_stop_pct:
                        self.position.close()
                        # Flip to short
                        self.sell(size=self.position_size)
                        self.entry_price = current_price
                        self.lowest_since_entry = current_price
                        self.state = 'short'

            elif not self.position:
                self.state = 'waiting'
                self.entry_price = 0

        # STATE: SHORT with trailing stop
        elif self.state == 'short':
            if self.position and self.position.is_short:
                # Update lowest price
                if current_price < self.lowest_since_entry:
                    self.lowest_since_entry = current_price

                pnl_pct = ((self.entry_price - current_price) / self.entry_price) * 100
                drawup_from_low = ((current_price - self.lowest_since_entry) / self.lowest_since_entry) * 100

                # If in profit and trailing activates
                if pnl_pct >= self.min_profit_to_trail:
                    # Trailing stop hit
                    if drawup_from_low >= self.trailing_stop_pct:
                        self.position.close()
                        self.state = 'waiting'
                        self.entry_price = 0
                else:
                    # Initial stop loss
                    if pnl_pct <= -self.initial_stop_pct:
                        self.position.close()
                        self.state = 'waiting'
                        self.entry_price = 0

            elif not self.position:
                self.state = 'waiting'
                self.entry_price = 0


# Run backtest
print("\n" + "="*70)
print("RUNNING BASELINE BACKTEST (Non-Optimized)")
print("="*70)

if len(data) > 100:
    bt = Backtest(
        data[['Open', 'High', 'Low', 'Close', 'Volume', 'long_liq_volume', 'short_liq_volume', 'net_liq_volume']],
        FlipFlopTrailingStrategy,
        cash=1000000,
        commission=0.001
    )

    baseline_stats = bt.run()

    print(f"\n📊 Moon Dev's BASELINE RESULTS (FLIP FLOP TRAILING):")
    print(f"Liquidation Threshold: ${FlipFlopTrailingStrategy.liquidation_threshold:,}")
    print(f"Lookback Bars: {FlipFlopTrailingStrategy.lookback_bars}")
    print(f"Trailing Stop: {FlipFlopTrailingStrategy.trailing_stop_pct}%")
    print(f"Initial Stop: {FlipFlopTrailingStrategy.initial_stop_pct}%")
    print(f"Min Profit to Trail: {FlipFlopTrailingStrategy.min_profit_to_trail}%")
    print("-" * 50)
    print(f"Total Trades: {baseline_stats['# Trades']}")
    print(f"Win Rate: {baseline_stats['Win Rate [%]']:.2f}%")
    print(f"Return: {baseline_stats['Return [%]']:.2f}%")
    print(f"Sharpe: {baseline_stats['Sharpe Ratio']:.2f}")
    print(f"Max Drawdown: {baseline_stats['Max. Drawdown [%]']:.2f}%")

    print("\n📈 FULL BASELINE STATS:")
    print("="*70)
    print(baseline_stats)

    # Optimization
    print("\n" + "="*70)
    print("RUNNING OPTIMIZATION")
    print("="*70)

    try:
        opt_stats = bt.optimize(
            liquidation_threshold=range(300000, 1000000, 100000),
            lookback_bars=[1, 2, 3, 4],
            trailing_stop_pct=[1.0, 1.5, 2.0, 2.5, 3.0],
            initial_stop_pct=[5.0, 7.5, 10.0],
            min_profit_to_trail=[0.5, 1.0, 1.5],
            maximize='Return [%]',
            return_heatmap=False
        )

        print("\n✨ OPTIMIZED RESULTS:")
        print("="*70)
        print(opt_stats)

        print("\n🎯 OPTIMIZED PARAMETERS:")
        print("-" * 50)
        print(f"Liquidation Threshold: ${opt_stats._strategy.liquidation_threshold:,}")
        print(f"Lookback Bars: {opt_stats._strategy.lookback_bars}")
        print(f"Trailing Stop: {opt_stats._strategy.trailing_stop_pct}%")
        print(f"Initial Stop: {opt_stats._strategy.initial_stop_pct}%")
        print(f"Min Profit to Trail: {opt_stats._strategy.min_profit_to_trail}%")

        bt.plot()

    except Exception as e:
        print(f"⚠️ Optimization failed: {e}")
        bt.plot()
