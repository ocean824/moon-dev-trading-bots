"""
Revisit Liquidation DCA Variation - Moon Dev
=============================================
Based on the winning Revisit Liq strategy (192% return)

VARIATION: Dollar Cost Average into the position
- On first revisit of liquidation low, enter 50% position
- If price drops further, add another 50% at lower level
- Better average entry price

Theory: DCA into the bounce for better entries

Moon Dev 🌙
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's REVISIT LIQUIDATION DCA Strategy 🌙")
print("Variation: Dollar cost average into position")
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


class RevisitDcaStrategy(Strategy):
    """
    Revisit Liquidation with DCA

    - Detect liquidation, record low
    - First entry at X% below low (50% size)
    - Second entry at Y% below low (remaining 50%)
    - Average entry price for better risk/reward
    """

    # Optimizable parameters
    liquidation_threshold = 2000000  # From optimized revisit
    lookback_bars = 1
    entry1_below_pct = 2.0  # First entry 2% below liq low
    entry2_below_pct = 4.0  # Second entry 4% below liq low
    take_profit_pct = 6.0  # From optimized
    stop_loss_pct = 6.0  # From optimized
    order_expiry_bars = 576  # 48 hours

    position_size = 0.95

    def init(self):
        self.long_liq_volume = self.I(lambda: self.data.long_liq_volume)
        self.rolling_long_liq = self.I(
            lambda x: pd.Series(x).rolling(self.lookback_bars, min_periods=1).sum(),
            self.long_liq_volume
        )

        self.signal_active = False
        self.liquidation_low = 0
        self.entry1_target = 0
        self.entry2_target = 0
        self.signal_bar_count = 0
        self.entries_made = 0
        self.avg_entry_price = 0

    def next(self):
        current_price = self.data.Close[-1]
        current_low = self.data.Low[-1]
        current_rolling_liq = self.rolling_long_liq[-1]

        # In position - check TP/SL
        if self.position:
            if self.avg_entry_price > 0:
                pnl_pct = ((current_price - self.avg_entry_price) / self.avg_entry_price) * 100

                # Check for second entry opportunity while in position
                if self.entries_made == 1 and self.signal_active:
                    if current_low <= self.entry2_target:
                        # Add to position (DCA)
                        self.buy(size=self.position_size * 0.5)
                        new_entry = self.entry2_target
                        self.avg_entry_price = (self.avg_entry_price + new_entry) / 2
                        self.entries_made = 2
                        self.signal_active = False

                # Take profit
                if pnl_pct >= self.take_profit_pct:
                    self.position.close()
                    self._reset()

                # Stop loss
                elif pnl_pct <= -self.stop_loss_pct:
                    self.position.close()
                    self._reset()
            return

        # Not in position
        # Check for new liquidation signal
        if current_rolling_liq >= self.liquidation_threshold and not self.signal_active:
            self.liquidation_low = current_low
            self.entry1_target = self.liquidation_low * (1 - self.entry1_below_pct / 100)
            self.entry2_target = self.liquidation_low * (1 - self.entry2_below_pct / 100)
            self.signal_active = True
            self.signal_bar_count = 0
            self.entries_made = 0

        # Check for entry
        if self.signal_active:
            self.signal_bar_count += 1

            # Signal expired
            if self.signal_bar_count >= self.order_expiry_bars:
                self._reset()
                return

            # First entry
            if self.entries_made == 0 and current_low <= self.entry1_target:
                self.buy(size=self.position_size * 0.5)
                self.avg_entry_price = self.entry1_target
                self.entries_made = 1

    def _reset(self):
        self.signal_active = False
        self.liquidation_low = 0
        self.entry1_target = 0
        self.entry2_target = 0
        self.signal_bar_count = 0
        self.entries_made = 0
        self.avg_entry_price = 0


# Run backtest
print("\n" + "="*70)
print("RUNNING BASELINE BACKTEST (Non-Optimized)")
print("="*70)

if len(data) > 100:
    bt = Backtest(
        data[['Open', 'High', 'Low', 'Close', 'Volume', 'long_liq_volume', 'short_liq_volume', 'net_liq_volume']],
        RevisitDcaStrategy,
        cash=1000000,
        commission=0.001
    )

    baseline_stats = bt.run()

    print(f"\n📊 Moon Dev's BASELINE RESULTS (REVISIT DCA):")
    print(f"Liquidation Threshold: ${RevisitDcaStrategy.liquidation_threshold:,}")
    print(f"Entry 1 Below: {RevisitDcaStrategy.entry1_below_pct}%")
    print(f"Entry 2 Below: {RevisitDcaStrategy.entry2_below_pct}%")
    print(f"Take Profit: {RevisitDcaStrategy.take_profit_pct}%")
    print(f"Stop Loss: {RevisitDcaStrategy.stop_loss_pct}%")
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
            liquidation_threshold=range(1000000, 4000000, 500000),
            entry1_below_pct=[1.0, 1.5, 2.0, 2.5],
            entry2_below_pct=[3.0, 4.0, 5.0, 6.0],
            take_profit_pct=[4.0, 6.0, 8.0],
            stop_loss_pct=[4.0, 6.0, 8.0],
            maximize='Return [%]',
            return_heatmap=False
        )

        print("\n✨ OPTIMIZED RESULTS:")
        print("="*70)
        print(opt_stats)

        print("\n🎯 OPTIMIZED PARAMETERS:")
        print("-" * 50)
        print(f"Liquidation Threshold: ${opt_stats._strategy.liquidation_threshold:,}")
        print(f"Entry 1 Below: {opt_stats._strategy.entry1_below_pct}%")
        print(f"Entry 2 Below: {opt_stats._strategy.entry2_below_pct}%")
        print(f"Take Profit: {opt_stats._strategy.take_profit_pct}%")
        print(f"Stop Loss: {opt_stats._strategy.stop_loss_pct}%")

        bt.plot()

    except Exception as e:
        print(f"⚠️ Optimization failed: {e}")
        bt.plot()
