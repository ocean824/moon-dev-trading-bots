"""
Next Day Liquidation Reversal - CORE IDEA - Moon Dev
=====================================================
PREMISE: Big liquidations today predict opposite move tomorrow

Theory:
- When $10M+ LONG liquidations happen, price dumped hard
- The NEXT DAY (24 hours), shorts will get liquidated as price recovers
- So: Big long liqs today = BUY, expecting price up tomorrow
- And: Big short liqs today = SELL, expecting price down tomorrow

This is the CORE standalone test of this premise.

Testing thresholds: $5M, $10M, $15M, $20M

Moon Dev
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print("Moon Dev's NEXT DAY LIQUIDATION REVERSAL - Core Idea")
print("Premise: Big liqs today = opposite move tomorrow")
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


class NextDayReversalCore(Strategy):
    """
    Next Day Liquidation Reversal - Core Strategy

    Logic:
    - Detect big long liquidation event (> threshold)
    - Wait 24 hours (288 bars on 5min data)
    - Enter LONG expecting the reversal/short squeeze
    - Hold for X hours then exit

    Same logic inverted for short liquidations -> go SHORT next day
    """

    # Liquidation threshold to test
    liquidation_threshold = 10000000  # $10M default, test 5M, 10M, 15M, 20M

    # Timing parameters
    delay_bars = 288        # 24 hours wait (5min bars)
    hold_bars = 144         # Hold for 12 hours

    # Risk parameters
    take_profit_pct = 4.0
    stop_loss_pct = 3.0

    # Direction: 1 = trade long liqs (buy next day), 2 = trade short liqs (sell next day), 3 = both
    trade_direction = 3

    position_size = 0.95

    def init(self):
        self.long_liq_volume = self.I(lambda: self.data.long_liq_volume)
        self.short_liq_volume = self.I(lambda: self.data.short_liq_volume)

        # Rolling sum over a few bars to catch the liquidation event
        self.rolling_long_liq = self.I(
            lambda x: pd.Series(x).rolling(3, min_periods=1).sum(),
            self.long_liq_volume
        )
        self.rolling_short_liq = self.I(
            lambda x: pd.Series(x).rolling(3, min_periods=1).sum(),
            self.short_liq_volume
        )

        # Signal tracking
        self.pending_long_signal = False
        self.pending_short_signal = False
        self.signal_countdown = 0
        self.hold_countdown = 0
        self.entry_price = 0
        self.trade_type = None  # 'long' or 'short'

    def next(self):
        current_price = self.data.Close[-1]
        current_long_liq = self.rolling_long_liq[-1]
        current_short_liq = self.rolling_short_liq[-1]

        # In position - manage exit
        if self.position:
            self.hold_countdown -= 1

            if self.entry_price > 0:
                if self.trade_type == 'long':
                    pnl_pct = ((current_price - self.entry_price) / self.entry_price) * 100
                else:  # short
                    pnl_pct = ((self.entry_price - current_price) / self.entry_price) * 100

                # Take profit
                if pnl_pct >= self.take_profit_pct:
                    self.position.close()
                    self._reset()
                    return

                # Stop loss
                if pnl_pct <= -self.stop_loss_pct:
                    self.position.close()
                    self._reset()
                    return

                # Time exit
                if self.hold_countdown <= 0:
                    self.position.close()
                    self._reset()
                    return

            return

        # Not in position - check for new signals or pending signals

        # Countdown for pending signals
        if self.pending_long_signal or self.pending_short_signal:
            self.signal_countdown -= 1

            # Time to enter!
            if self.signal_countdown <= 0:
                if self.pending_long_signal:
                    self.buy(size=self.position_size)
                    self.entry_price = current_price
                    self.trade_type = 'long'
                    self.hold_countdown = self.hold_bars
                    self.pending_long_signal = False

                elif self.pending_short_signal:
                    self.sell(size=self.position_size)
                    self.entry_price = current_price
                    self.trade_type = 'short'
                    self.hold_countdown = self.hold_bars
                    self.pending_short_signal = False
                return

        # Look for new liquidation signals
        # Big LONG liquidations -> price dumped -> expect recovery -> BUY next day
        if (self.trade_direction == 1 or self.trade_direction == 3):
            if current_long_liq >= self.liquidation_threshold:
                if not self.pending_long_signal and not self.pending_short_signal:
                    self.pending_long_signal = True
                    self.signal_countdown = self.delay_bars

        # Big SHORT liquidations -> price pumped -> expect pullback -> SELL next day
        if (self.trade_direction == 2 or self.trade_direction == 3):
            if current_short_liq >= self.liquidation_threshold:
                if not self.pending_long_signal and not self.pending_short_signal:
                    self.pending_short_signal = True
                    self.signal_countdown = self.delay_bars

    def _reset(self):
        self.pending_long_signal = False
        self.pending_short_signal = False
        self.signal_countdown = 0
        self.hold_countdown = 0
        self.entry_price = 0
        self.trade_type = None


# Run backtest
print("\n" + "="*70)
print("RUNNING BASELINE BACKTEST ($10M threshold)")
print("="*70)

if len(data) > 100:
    bt = Backtest(
        data[['Open', 'High', 'Low', 'Close', 'Volume', 'long_liq_volume', 'short_liq_volume', 'net_liq_volume']],
        NextDayReversalCore,
        cash=1000000,
        commission=0.001
    )

    baseline_stats = bt.run()

    print(f"\nMoon Dev's BASELINE RESULTS (NEXT DAY REVERSAL CORE):")
    print(f"Liquidation Threshold: ${NextDayReversalCore.liquidation_threshold:,}")
    print(f"Delay: {NextDayReversalCore.delay_bars} bars ({NextDayReversalCore.delay_bars * 5 / 60:.0f} hours)")
    print(f"Hold: {NextDayReversalCore.hold_bars} bars ({NextDayReversalCore.hold_bars * 5 / 60:.0f} hours)")
    print(f"Take Profit: {NextDayReversalCore.take_profit_pct}%")
    print(f"Stop Loss: {NextDayReversalCore.stop_loss_pct}%")
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
            liquidation_threshold=[5000000, 10000000, 15000000, 20000000],  # $5M, $10M, $15M, $20M
            delay_bars=[144, 288, 432],  # 12hr, 24hr, 36hr
            hold_bars=[72, 144, 288],    # 6hr, 12hr, 24hr
            take_profit_pct=[3.0, 4.0, 5.0, 6.0],
            stop_loss_pct=[2.0, 3.0, 4.0],
            trade_direction=[1, 2, 3],   # long liqs only, short liqs only, both
            maximize='Return [%]',
            return_heatmap=False
        )

        trade_dir_desc = {1: "Long liqs only (buy)", 2: "Short liqs only (sell)", 3: "Both directions"}

        print("\nOPTIMIZED RESULTS:")
        print("="*70)
        print(opt_stats)

        print("\nOPTIMIZED PARAMETERS:")
        print("-" * 50)
        print(f"Liquidation Threshold: ${opt_stats._strategy.liquidation_threshold:,}")
        print(f"Delay: {opt_stats._strategy.delay_bars} bars ({opt_stats._strategy.delay_bars * 5 / 60:.0f} hours)")
        print(f"Hold: {opt_stats._strategy.hold_bars} bars ({opt_stats._strategy.hold_bars * 5 / 60:.0f} hours)")
        print(f"Take Profit: {opt_stats._strategy.take_profit_pct}%")
        print(f"Stop Loss: {opt_stats._strategy.stop_loss_pct}%")
        print(f"Trade Direction: {trade_dir_desc[opt_stats._strategy.trade_direction]}")

        bt.plot()

    except Exception as e:
        print(f"Optimization failed: {e}")
        bt.plot()
