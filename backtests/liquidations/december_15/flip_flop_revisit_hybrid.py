"""
HYBRID Strategy: Flip Flop + Revisit Combined - Moon Dev
=========================================================
Combining the two winning strategies:
- Flip Flop (529% return)
- Revisit Liq (192% return)

HYBRID APPROACH:
1. Detect liquidation event
2. DON'T enter immediately (like flip flop does)
3. WAIT for price to revisit below liquidation low (like revisit)
4. Enter long on revisit
5. Then use FLIP FLOP exit logic (TP/SL -> flip to short -> TP/SL)

Theory: Get better entry (revisit) + capture mean reversion (flip flop)

Moon Dev
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print("Moon Dev's HYBRID FLIP FLOP + REVISIT Strategy")
print("Combining: Revisit entry timing + Flip Flop exit mechanics")
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


class HybridFlipFlopRevisitStrategy(Strategy):
    """
    Hybrid: Revisit Entry + Flip Flop Exit

    Entry (from Revisit):
    - Detect liquidation signal
    - Record the LOW of that bar
    - Wait for price to drop X% below that low
    - Enter long when price revisits

    Exit (from Flip Flop):
    - TP hit on long -> flip to short
    - SL hit on long -> flip to short
    - TP/SL on short -> done

    Best of both worlds: Better entry + mean reversion capture
    """

    # Entry parameters (from Revisit optimized)
    liquidation_threshold = 2000000
    lookback_bars = 1
    entry_below_pct = 2.0
    order_expiry_bars = 576  # 48 hours

    # Exit parameters (from Flip Flop optimized)
    take_profit_pct = 1.5
    stop_loss_pct = 10.0

    position_size = 0.95

    def init(self):
        self.long_liq_volume = self.I(lambda: self.data.long_liq_volume)
        self.rolling_long_liq = self.I(
            lambda x: pd.Series(x).rolling(self.lookback_bars, min_periods=1).sum(),
            self.long_liq_volume
        )

        # State machine: waiting -> pending_entry -> long -> short -> waiting
        self.state = 'waiting'
        self.liquidation_low = 0
        self.target_entry_price = 0
        self.signal_bar_count = 0
        self.entry_price = 0

    def next(self):
        current_price = self.data.Close[-1]
        current_low = self.data.Low[-1]
        current_rolling_liq = self.rolling_long_liq[-1]

        # STATE: WAITING - look for liquidation signal
        if self.state == 'waiting':
            if current_rolling_liq >= self.liquidation_threshold:
                # Got liquidation signal - set up revisit entry
                self.liquidation_low = current_low
                self.target_entry_price = self.liquidation_low * (1 - self.entry_below_pct / 100)
                self.signal_bar_count = 0
                self.state = 'pending_entry'

        # STATE: PENDING ENTRY - wait for price to revisit
        elif self.state == 'pending_entry':
            self.signal_bar_count += 1

            # Signal expired
            if self.signal_bar_count >= self.order_expiry_bars:
                self._reset()
                return

            # Price revisited below liquidation low - ENTER LONG
            if current_low <= self.target_entry_price:
                self.buy(size=self.position_size)
                self.entry_price = self.target_entry_price
                self.state = 'long'

        # STATE: LONG - Flip Flop exit logic
        elif self.state == 'long':
            if self.position and self.position.is_long:
                pnl_pct = ((current_price - self.entry_price) / self.entry_price) * 100

                # Take profit - FLIP to short
                if pnl_pct >= self.take_profit_pct:
                    self.position.close()
                    self.sell(size=self.position_size)
                    self.entry_price = current_price
                    self.state = 'short'

                # Stop loss - FLIP to short
                elif pnl_pct <= -self.stop_loss_pct:
                    self.position.close()
                    self.sell(size=self.position_size)
                    self.entry_price = current_price
                    self.state = 'short'

            elif not self.position:
                # Position closed externally
                self.state = 'waiting'
                self.entry_price = 0

        # STATE: SHORT - exit and done
        elif self.state == 'short':
            if self.position and self.position.is_short:
                pnl_pct = ((self.entry_price - current_price) / self.entry_price) * 100

                # Take profit on short
                if pnl_pct >= self.take_profit_pct:
                    self.position.close()
                    self._reset()

                # Stop loss on short
                elif pnl_pct <= -self.stop_loss_pct:
                    self.position.close()
                    self._reset()

            elif not self.position:
                self._reset()

    def _reset(self):
        self.state = 'waiting'
        self.liquidation_low = 0
        self.target_entry_price = 0
        self.signal_bar_count = 0
        self.entry_price = 0


# Run backtest
print("\n" + "="*70)
print("RUNNING BASELINE BACKTEST (Non-Optimized)")
print("="*70)

if len(data) > 100:
    bt = Backtest(
        data[['Open', 'High', 'Low', 'Close', 'Volume', 'long_liq_volume', 'short_liq_volume', 'net_liq_volume']],
        HybridFlipFlopRevisitStrategy,
        cash=1000000,
        commission=0.001
    )

    baseline_stats = bt.run()

    print(f"\nMoon Dev's BASELINE RESULTS (HYBRID FLIP FLOP + REVISIT):")
    print(f"Liquidation Threshold: ${HybridFlipFlopRevisitStrategy.liquidation_threshold:,}")
    print(f"Entry Below Liq Low: {HybridFlipFlopRevisitStrategy.entry_below_pct}%")
    print(f"Take Profit: {HybridFlipFlopRevisitStrategy.take_profit_pct}%")
    print(f"Stop Loss: {HybridFlipFlopRevisitStrategy.stop_loss_pct}%")
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
            liquidation_threshold=range(1000000, 4000000, 500000),
            entry_below_pct=[1.0, 1.5, 2.0, 2.5, 3.0],
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
        print(f"Entry Below Liq Low: {opt_stats._strategy.entry_below_pct}%")
        print(f"Take Profit: {opt_stats._strategy.take_profit_pct}%")
        print(f"Stop Loss: {opt_stats._strategy.stop_loss_pct}%")

        # Compare with original strategies
        print("\nCOMPARISON WITH ORIGINAL STRATEGIES:")
        print("-" * 50)
        print("Original Flip Flop: 529% return")
        print("Original Revisit Liq: 192% return")
        print(f"Hybrid Strategy: {opt_stats['Return [%]']:.2f}% return")

        bt.plot()

    except Exception as e:
        print(f"Optimization failed: {e}")
        bt.plot()
