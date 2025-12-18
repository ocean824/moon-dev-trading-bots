"""
Flip Flop NEXT DAY Variation - Moon Dev
========================================
Based on winning Flip Flop + Next Day Reversal premise

COMBINED IDEA:
- Flip Flop: Buy dip on liquidation, flip to short on TP/SL
- Next Day: Big liqs today = opposite move 24 hours later

New Logic:
1. Detect big long liquidation ($5M-$20M)
2. WAIT 24 hours (let the dust settle)
3. Then enter using Flip Flop mechanics
4. Expectation: Next day is the recovery/reversal day

Moon Dev
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print("Moon Dev's FLIP FLOP NEXT DAY Strategy")
print("Premise: Wait 24hr after big liqs, then flip flop")
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


class FlipFlopNextDay(Strategy):
    """
    Flip Flop with Next Day Delay

    Entry:
    - Detect big long liquidation
    - Wait 24 hours
    - Enter LONG (expecting next day reversal)

    Exit (Flip Flop style):
    - TP hit -> flip to short
    - SL hit -> flip to short
    - TP/SL on short -> done
    """

    # Next day parameters
    liquidation_threshold = 10000000  # $10M, test 5M, 10M, 15M, 20M
    delay_bars = 288  # 24 hours

    # Flip Flop parameters (from optimized)
    lookback_bars = 3
    take_profit_pct = 1.5
    stop_loss_pct = 10.0

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

        # Next day tracking
        self.pending_signal = False
        self.signal_countdown = 0

    def next(self):
        current_price = self.data.Close[-1]
        current_rolling_liq = self.rolling_long_liq[-1]

        # STATE: WAITING
        if self.state == 'waiting':
            # Check for pending signal countdown
            if self.pending_signal:
                self.signal_countdown -= 1

                # Time to enter after 24hr delay
                if self.signal_countdown <= 0:
                    self.buy(size=self.position_size)
                    self.entry_price = current_price
                    self.state = 'long'
                    self.pending_signal = False
                return

            # Look for new big liquidation signal
            if not self.position and not self.pending_signal:
                if current_rolling_liq >= self.liquidation_threshold:
                    self.pending_signal = True
                    self.signal_countdown = self.delay_bars

        # STATE: LONG
        elif self.state == 'long':
            if self.position and self.position.is_long:
                pnl_pct = ((current_price - self.entry_price) / self.entry_price) * 100

                # Take profit -> flip to short
                if pnl_pct >= self.take_profit_pct:
                    self.position.close()
                    self.sell(size=self.position_size)
                    self.entry_price = current_price
                    self.state = 'short'

                # Stop loss -> flip to short
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
        self.pending_signal = False
        self.signal_countdown = 0


# Run backtest
print("\n" + "="*70)
print("RUNNING BASELINE BACKTEST ($10M threshold, 24hr delay)")
print("="*70)

if len(data) > 100:
    bt = Backtest(
        data[['Open', 'High', 'Low', 'Close', 'Volume', 'long_liq_volume', 'short_liq_volume', 'net_liq_volume']],
        FlipFlopNextDay,
        cash=1000000,
        commission=0.001
    )

    baseline_stats = bt.run()

    print(f"\nMoon Dev's BASELINE RESULTS (FLIP FLOP NEXT DAY):")
    print(f"Liquidation Threshold: ${FlipFlopNextDay.liquidation_threshold:,}")
    print(f"Delay: {FlipFlopNextDay.delay_bars} bars ({FlipFlopNextDay.delay_bars * 5 / 60:.0f} hours)")
    print(f"Take Profit: {FlipFlopNextDay.take_profit_pct}%")
    print(f"Stop Loss: {FlipFlopNextDay.stop_loss_pct}%")
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
            liquidation_threshold=[5000000, 10000000, 15000000, 20000000],
            delay_bars=[144, 288, 432],  # 12hr, 24hr, 36hr
            lookback_bars=[1, 2, 3, 4],
            take_profit_pct=[1.0, 1.5, 2.0, 2.5],
            stop_loss_pct=[5.0, 7.5, 10.0],
            maximize='Return [%]',
            return_heatmap=False
        )

        print("\nOPTIMIZED RESULTS:")
        print("="*70)
        print(opt_stats)

        print("\nOPTIMIZED PARAMETERS:")
        print("-" * 50)
        print(f"Liquidation Threshold: ${opt_stats._strategy.liquidation_threshold:,}")
        print(f"Delay: {opt_stats._strategy.delay_bars} bars ({opt_stats._strategy.delay_bars * 5 / 60:.0f} hours)")
        print(f"Lookback Bars: {opt_stats._strategy.lookback_bars}")
        print(f"Take Profit: {opt_stats._strategy.take_profit_pct}%")
        print(f"Stop Loss: {opt_stats._strategy.stop_loss_pct}%")

        bt.plot()

    except Exception as e:
        print(f"Optimization failed: {e}")
        bt.plot()
