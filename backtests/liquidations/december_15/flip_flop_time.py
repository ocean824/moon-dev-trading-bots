"""
Flip Flop TIME-BASED SCALING - Moon Dev
========================================
Based on the winning Flip Flop strategy (529% return)

VARIATION: Time-based scale into position
- After liquidation trigger, spread buys evenly across X hours
- Test different hour configurations:
  - Mode 1: Buy at 1hr, 2hr, 4hr (3 buys)
  - Mode 2: Buy at 3hr, 4hr (2 buys)
  - Mode 3: Buy at 1hr, 2hr, 3hr, 4hr (4 buys)

Theory: Time-based DCA removes price guessing, just averages over time

Moon Dev
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print("Moon Dev's FLIP FLOP TIME-BASED SCALING")
print("Variation: Spread buys evenly across hours after trigger")
print("=" * 70)

# Data configuration
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/moondev_api/liq_data_BTC_5m_ohlcv.csv'
timeframe = '5-minute'

print(f"Loading preprocessed {timeframe} BTC liquidation data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)

print(f"Loaded {len(data):,} {timeframe} bars")

# Map liquidation columns
if 'long_liquidations' in data.columns and 'short_liquidations' in data.columns:
    data['long_liq_volume'] = data['long_liquidations']
    data['short_liq_volume'] = data['short_liquidations']
    data['net_liq_volume'] = data['short_liquidations'] - data['long_liquidations']
else:
    data['long_liq_volume'] = 0
    data['short_liq_volume'] = 0
    data['net_liq_volume'] = 0


class FlipFlopTimeStrategy(Strategy):
    """
    Flip Flop with Time-Based Scaling

    Entry Logic:
    - Detect liquidation trigger
    - Spread buys across specified hours
    - time_mode: 1 = [1,2,4]hr, 2 = [3,4]hr, 3 = [1,2,3,4]hr

    Exit Logic (same as original):
    - TP hit -> flip to short
    - SL hit -> flip to short
    - TP/SL on short -> done
    """

    # Optimizable parameters
    liquidation_threshold = 500000
    lookback_bars = 3
    take_profit_pct = 1.5
    stop_loss_pct = 10.0

    # Time-based entry parameters
    # time_mode: 1 = buy at 1,2,4 hours | 2 = buy at 3,4 hours | 3 = buy at 1,2,3,4 hours
    time_mode = 3

    position_size = 0.95

    def init(self):
        self.long_liq_volume = self.I(lambda: self.data.long_liq_volume)
        self.rolling_long_liq = self.I(
            lambda x: pd.Series(x).rolling(self.lookback_bars, min_periods=1).sum(),
            self.long_liq_volume
        )

        # Time mode configurations (in 5-min bars)
        # 1 hour = 12 bars, 2 hours = 24 bars, etc.
        self.time_configs = {
            1: [12, 24, 48],      # 1hr, 2hr, 4hr
            2: [36, 48],          # 3hr, 4hr
            3: [12, 24, 36, 48],  # 1hr, 2hr, 3hr, 4hr
        }

        # State machine
        self.state = 'waiting'
        self.entry_price = 0

        # Time-based entry tracking
        self.scaling_active = False
        self.trigger_bar = 0
        self.bars_since_trigger = 0
        self.entries_filled = 0
        self.entry_bars = []
        self.total_entry_cost = 0
        self.total_entry_size = 0

    def next(self):
        current_price = self.data.Close[-1]
        current_rolling_liq = self.rolling_long_liq[-1]

        # Get entry schedule based on time_mode
        entry_schedule = self.time_configs.get(self.time_mode, [12, 24, 36, 48])
        num_entries = len(entry_schedule)
        size_per_entry = self.position_size / num_entries

        # STATE: WAITING - look for trigger
        if self.state == 'waiting':
            if not self.position and not self.scaling_active:
                if current_rolling_liq >= self.liquidation_threshold:
                    # Got trigger - start time-based scaling
                    self.scaling_active = True
                    self.bars_since_trigger = 0
                    self.entries_filled = 0
                    self.entry_bars = entry_schedule.copy()
                    self.total_entry_cost = 0
                    self.total_entry_size = 0

                    # First entry immediately
                    self.buy(size=size_per_entry)
                    self.total_entry_cost += current_price * size_per_entry
                    self.total_entry_size += size_per_entry
                    self.entries_filled = 1
                    self.entry_price = current_price
                    self.state = 'scaling_long'

        # STATE: SCALING LONG - filling entries over time
        elif self.state == 'scaling_long':
            self.bars_since_trigger += 1

            # Check if it's time for next entry
            if self.entries_filled < num_entries:
                next_entry_bar = self.entry_bars[self.entries_filled - 1] if self.entries_filled > 0 else 0

                # Find which entry we should be at based on bars elapsed
                for i in range(self.entries_filled, num_entries):
                    if self.bars_since_trigger >= self.entry_bars[i - 1] if i > 0 else True:
                        # Time to make next entry
                        if self.bars_since_trigger >= (self.entry_bars[i] if i < len(self.entry_bars) else self.entry_bars[-1]):
                            continue
                        if i == self.entries_filled:
                            target_bar = self.entry_bars[i]
                            if self.bars_since_trigger >= target_bar:
                                self.buy(size=size_per_entry)
                                self.total_entry_cost += current_price * size_per_entry
                                self.total_entry_size += size_per_entry
                                self.entries_filled += 1
                                self.entry_price = self.total_entry_cost / self.total_entry_size
                                break

                # Simplified: check each entry time
                for i, bar_target in enumerate(self.entry_bars):
                    if self.bars_since_trigger == bar_target and self.entries_filled == i + 1:
                        if self.entries_filled < num_entries:
                            self.buy(size=size_per_entry)
                            self.total_entry_cost += current_price * size_per_entry
                            self.total_entry_size += size_per_entry
                            self.entries_filled += 1
                            self.entry_price = self.total_entry_cost / self.total_entry_size

                # All entries filled or past max time
                if self.entries_filled >= num_entries or self.bars_since_trigger > max(self.entry_bars) + 12:
                    self.scaling_active = False
                    self.state = 'long'

            # While scaling, still check TP/SL
            if self.position and self.position.is_long and self.entry_price > 0:
                pnl_pct = ((current_price - self.entry_price) / self.entry_price) * 100

                if pnl_pct >= self.take_profit_pct:
                    self.position.close()
                    self.sell(size=self.position_size)
                    self.entry_price = current_price
                    self.state = 'short'
                    self.scaling_active = False

                elif pnl_pct <= -self.stop_loss_pct:
                    self.position.close()
                    self.sell(size=self.position_size)
                    self.entry_price = current_price
                    self.state = 'short'
                    self.scaling_active = False

        # STATE: LONG - check TP/SL
        elif self.state == 'long':
            if self.position and self.position.is_long:
                pnl_pct = ((current_price - self.entry_price) / self.entry_price) * 100

                if pnl_pct >= self.take_profit_pct:
                    self.position.close()
                    self.sell(size=self.position_size)
                    self.entry_price = current_price
                    self.state = 'short'

                elif pnl_pct <= -self.stop_loss_pct:
                    self.position.close()
                    self.sell(size=self.position_size)
                    self.entry_price = current_price
                    self.state = 'short'

            elif not self.position:
                self._reset()

        # STATE: SHORT
        elif self.state == 'short':
            if self.position and self.position.is_short:
                pnl_pct = ((self.entry_price - current_price) / self.entry_price) * 100

                if pnl_pct >= self.take_profit_pct:
                    self.position.close()
                    self._reset()

                elif pnl_pct <= -self.stop_loss_pct:
                    self.position.close()
                    self._reset()

            elif not self.position:
                self._reset()

    def _reset(self):
        self.state = 'waiting'
        self.entry_price = 0
        self.scaling_active = False
        self.bars_since_trigger = 0
        self.entries_filled = 0
        self.entry_bars = []
        self.total_entry_cost = 0
        self.total_entry_size = 0


# Run backtest
print("\n" + "="*70)
print("RUNNING BASELINE BACKTEST (Mode 3: 1,2,3,4 hours)")
print("="*70)

if len(data) > 100:
    bt = Backtest(
        data[['Open', 'High', 'Low', 'Close', 'Volume', 'long_liq_volume', 'short_liq_volume', 'net_liq_volume']],
        FlipFlopTimeStrategy,
        cash=1000000,
        commission=0.001
    )

    baseline_stats = bt.run()

    time_mode_desc = {1: "1hr, 2hr, 4hr", 2: "3hr, 4hr", 3: "1hr, 2hr, 3hr, 4hr"}

    print(f"\nMoon Dev's BASELINE RESULTS (FLIP FLOP TIME):")
    print(f"Liquidation Threshold: ${FlipFlopTimeStrategy.liquidation_threshold:,}")
    print(f"Lookback Bars: {FlipFlopTimeStrategy.lookback_bars}")
    print(f"Take Profit: {FlipFlopTimeStrategy.take_profit_pct}%")
    print(f"Stop Loss: {FlipFlopTimeStrategy.stop_loss_pct}%")
    print(f"Time Mode: {FlipFlopTimeStrategy.time_mode} ({time_mode_desc[FlipFlopTimeStrategy.time_mode]})")
    print("-" * 50)
    print(f"Total Trades: {baseline_stats['# Trades']}")
    print(f"Win Rate: {baseline_stats['Win Rate [%]']:.2f}%")
    print(f"Return: {baseline_stats['Return [%]']:.2f}%")
    print(f"Sharpe: {baseline_stats['Sharpe Ratio']:.2f}")
    print(f"Max Drawdown: {baseline_stats['Max. Drawdown [%]']:.2f}%")

    print("\nFULL BASELINE STATS:")
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
            take_profit_pct=[1.0, 1.5, 2.0, 2.5],
            stop_loss_pct=[5.0, 7.5, 10.0],
            time_mode=[1, 2, 3],
            maximize='Return [%]',
            return_heatmap=False
        )

        print("\nOPTIMIZED RESULTS:")
        print("="*70)
        print(opt_stats)

        print("\nOPTIMIZED PARAMETERS:")
        print("-" * 50)
        print(f"Liquidation Threshold: ${opt_stats._strategy.liquidation_threshold:,}")
        print(f"Lookback Bars: {opt_stats._strategy.lookback_bars}")
        print(f"Take Profit: {opt_stats._strategy.take_profit_pct}%")
        print(f"Stop Loss: {opt_stats._strategy.stop_loss_pct}%")
        print(f"Time Mode: {opt_stats._strategy.time_mode} ({time_mode_desc[opt_stats._strategy.time_mode]})")

        bt.plot()

    except Exception as e:
        print(f"Optimization failed: {e}")
        bt.plot()
