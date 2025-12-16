"""
Flip Flop SCALED ENTRY V2 - Moon Dev
=====================================
Based on the winning Flip Flop strategy (529% return)

VARIATION: Scale into the position with multiple buys
- After liquidation trigger, split entry into X number of buys
- Each buy at progressively lower prices
- Average into the position for better entry price

Optimizable: 3, 5, 7, or 10 entry splits

Theory: DCA into the dip for better average entry

Moon Dev
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print("Moon Dev's FLIP FLOP SCALED ENTRY V2")
print("Variation: Scale into position with multiple buys")
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


class FlipFlopScaledEntryV2(Strategy):
    """
    Flip Flop with Scaled Entry V2

    Entry Logic:
    - Detect liquidation trigger
    - Split entry into num_entries buys
    - Each entry X% apart (entry_spacing_pct)
    - First entry at trigger, subsequent entries lower

    Exit Logic (same as original):
    - TP hit -> flip to short
    - SL hit -> flip to short
    - TP/SL on short -> done
    """

    # Optimizable parameters
    liquidation_threshold = 500000  # From optimized flip flop
    lookback_bars = 3  # From optimized flip flop
    take_profit_pct = 1.5  # From optimized
    stop_loss_pct = 10.0  # From optimized

    # Scaled entry parameters
    num_entries = 5  # Number of entry splits (3, 5, 7, 10)
    entry_spacing_pct = 0.5  # Spacing between entries in %
    entry_expiry_bars = 288  # 24 hours to fill all entries

    position_size = 0.95

    def init(self):
        self.long_liq_volume = self.I(lambda: self.data.long_liq_volume)
        self.rolling_long_liq = self.I(
            lambda x: pd.Series(x).rolling(self.lookback_bars, min_periods=1).sum(),
            self.long_liq_volume
        )

        # State machine
        self.state = 'waiting'
        self.entry_price = 0

        # Scaled entry tracking
        self.scaling_active = False
        self.trigger_price = 0
        self.entries_filled = 0
        self.entry_targets = []
        self.total_entry_cost = 0
        self.total_entry_size = 0
        self.scaling_bar_count = 0

    def next(self):
        current_price = self.data.Close[-1]
        current_low = self.data.Low[-1]
        current_rolling_liq = self.rolling_long_liq[-1]

        # Calculate size per entry
        size_per_entry = self.position_size / self.num_entries

        # STATE: WAITING - look for trigger
        if self.state == 'waiting':
            if not self.position and not self.scaling_active:
                if current_rolling_liq >= self.liquidation_threshold:
                    # Got trigger - set up scaled entries
                    self.trigger_price = current_price
                    self.scaling_active = True
                    self.entries_filled = 0
                    self.scaling_bar_count = 0
                    self.total_entry_cost = 0
                    self.total_entry_size = 0

                    # Calculate entry targets
                    self.entry_targets = []
                    for i in range(self.num_entries):
                        target = self.trigger_price * (1 - (i * self.entry_spacing_pct / 100))
                        self.entry_targets.append(target)

                    # First entry immediately at trigger
                    self.buy(size=size_per_entry)
                    self.total_entry_cost += current_price * size_per_entry
                    self.total_entry_size += size_per_entry
                    self.entries_filled = 1
                    self.entry_price = current_price
                    self.state = 'scaling_long'

        # STATE: SCALING LONG - filling remaining entries
        elif self.state == 'scaling_long':
            self.scaling_bar_count += 1

            # Check if we can fill more entries
            if self.entries_filled < self.num_entries:
                # Check if scaling period expired
                if self.scaling_bar_count >= self.entry_expiry_bars:
                    # Stop scaling, move to long state with what we have
                    self.scaling_active = False
                    if self.total_entry_size > 0:
                        self.entry_price = self.total_entry_cost / self.total_entry_size
                    self.state = 'long'
                else:
                    # Check if next entry target hit
                    next_target = self.entry_targets[self.entries_filled]
                    if current_low <= next_target:
                        self.buy(size=size_per_entry)
                        self.total_entry_cost += next_target * size_per_entry
                        self.total_entry_size += size_per_entry
                        self.entries_filled += 1
                        # Update average entry price
                        self.entry_price = self.total_entry_cost / self.total_entry_size

                        # All entries filled
                        if self.entries_filled >= self.num_entries:
                            self.scaling_active = False
                            self.state = 'long'
            else:
                self.scaling_active = False
                self.state = 'long'

            # While scaling, still check TP/SL on current position
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

        # STATE: SHORT - check TP/SL
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
        self.trigger_price = 0
        self.entries_filled = 0
        self.entry_targets = []
        self.total_entry_cost = 0
        self.total_entry_size = 0
        self.scaling_bar_count = 0


# Run backtest
print("\n" + "="*70)
print("RUNNING BASELINE BACKTEST (5 entries, 0.5% spacing)")
print("="*70)

if len(data) > 100:
    bt = Backtest(
        data[['Open', 'High', 'Low', 'Close', 'Volume', 'long_liq_volume', 'short_liq_volume', 'net_liq_volume']],
        FlipFlopScaledEntryV2,
        cash=1000000,
        commission=0.001
    )

    baseline_stats = bt.run()

    print(f"\nMoon Dev's BASELINE RESULTS (FLIP FLOP SCALED ENTRY V2):")
    print(f"Liquidation Threshold: ${FlipFlopScaledEntryV2.liquidation_threshold:,}")
    print(f"Lookback Bars: {FlipFlopScaledEntryV2.lookback_bars}")
    print(f"Take Profit: {FlipFlopScaledEntryV2.take_profit_pct}%")
    print(f"Stop Loss: {FlipFlopScaledEntryV2.stop_loss_pct}%")
    print(f"Number of Entries: {FlipFlopScaledEntryV2.num_entries}")
    print(f"Entry Spacing: {FlipFlopScaledEntryV2.entry_spacing_pct}%")
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
            num_entries=[3, 5, 7, 10],
            entry_spacing_pct=[0.3, 0.5, 0.75, 1.0],
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
        print(f"Number of Entries: {opt_stats._strategy.num_entries}")
        print(f"Entry Spacing: {opt_stats._strategy.entry_spacing_pct}%")

        bt.plot()

    except Exception as e:
        print(f"Optimization failed: {e}")
        bt.plot()
