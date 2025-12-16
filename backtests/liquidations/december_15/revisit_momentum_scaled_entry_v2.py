"""
Revisit Momentum SCALED ENTRY V2 - Moon Dev
============================================
Based on the BEST performer: revisit_momentum

VARIATION: Scale into the position with multiple buys
- After liquidation trigger + momentum confirmation
- Split entry into X number of buys at progressively lower prices
- Average into the position for better entry price

Optimizable: 3, 5, 7, or 10 entry splits

Theory: DCA into the momentum-confirmed revisit for optimal entries

Moon Dev
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print("Moon Dev's REVISIT MOMENTUM SCALED ENTRY V2")
print("Variation: Scale into position with momentum confirmation")
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


class RevisitMomentumScaledEntryV2(Strategy):
    """
    Revisit Momentum with Scaled Entry V2

    Entry Logic:
    - Detect liquidation trigger, record low
    - Wait for price to drop below liq low
    - Confirm momentum (RSI oversold OR MACD bullish)
    - Split entry into num_entries buys
    - Each entry X% apart below the first entry

    Exit Logic:
    - Take profit at X%
    - Stop loss at Y%
    """

    # Optimizable parameters from revisit momentum
    liquidation_threshold = 2000000
    lookback_bars = 1
    entry_below_pct = 2.0
    take_profit_pct = 6.0
    stop_loss_pct = 6.0
    order_expiry_bars = 576

    # Momentum parameters
    rsi_period = 14
    rsi_oversold = 30
    macd_fast = 12
    macd_slow = 26
    macd_signal = 9

    # Scaled entry parameters
    num_entries = 5  # Number of entry splits (3, 5, 7, 10)
    entry_spacing_pct = 0.5  # Spacing between entries in %

    position_size = 0.95

    def init(self):
        self.long_liq_volume = self.I(lambda: self.data.long_liq_volume)
        self.rolling_long_liq = self.I(
            lambda x: pd.Series(x).rolling(self.lookback_bars, min_periods=1).sum(),
            self.long_liq_volume
        )

        # RSI calculation
        def calc_rsi(close, period):
            close_series = pd.Series(close)
            delta = close_series.diff()
            gain = delta.where(delta > 0, 0).rolling(window=period, min_periods=1).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period, min_periods=1).mean()
            rs = gain / loss.replace(0, np.inf)
            rsi = 100 - (100 / (1 + rs))
            return rsi

        self.rsi = self.I(calc_rsi, self.data.Close, self.rsi_period)

        # MACD calculation
        def calc_macd_line(close, fast, slow):
            close_series = pd.Series(close)
            ema_fast = close_series.ewm(span=fast, adjust=False).mean()
            ema_slow = close_series.ewm(span=slow, adjust=False).mean()
            return ema_fast - ema_slow

        def calc_macd_signal(close, fast, slow, signal):
            close_series = pd.Series(close)
            ema_fast = close_series.ewm(span=fast, adjust=False).mean()
            ema_slow = close_series.ewm(span=slow, adjust=False).mean()
            macd_line = ema_fast - ema_slow
            return macd_line.ewm(span=signal, adjust=False).mean()

        self.macd_line = self.I(calc_macd_line, self.data.Close, self.macd_fast, self.macd_slow)
        self.macd_signal_line = self.I(calc_macd_signal, self.data.Close, self.macd_fast, self.macd_slow, self.macd_signal)

        # State tracking
        self.signal_active = False
        self.liquidation_low = 0
        self.first_entry_target = 0
        self.signal_bar_count = 0

        # Scaled entry tracking
        self.scaling_active = False
        self.entries_filled = 0
        self.entry_targets = []
        self.total_entry_cost = 0
        self.total_entry_size = 0
        self.avg_entry_price = 0

    def next(self):
        current_price = self.data.Close[-1]
        current_low = self.data.Low[-1]
        current_rolling_liq = self.rolling_long_liq[-1]
        current_rsi = self.rsi[-1]
        current_macd = self.macd_line[-1]
        current_macd_signal = self.macd_signal_line[-1]

        # Previous bar MACD for crossover detection
        prev_macd = self.macd_line[-2] if len(self.macd_line) > 1 else current_macd
        prev_macd_signal = self.macd_signal_line[-2] if len(self.macd_signal_line) > 1 else current_macd_signal

        # Momentum confirmation
        rsi_oversold = current_rsi <= self.rsi_oversold
        macd_bullish_cross = (prev_macd < prev_macd_signal) and (current_macd >= current_macd_signal)
        momentum_confirmed = rsi_oversold or macd_bullish_cross

        size_per_entry = self.position_size / self.num_entries

        # In position - check TP/SL and additional entries
        if self.position:
            if self.avg_entry_price > 0:
                pnl_pct = ((current_price - self.avg_entry_price) / self.avg_entry_price) * 100

                # Check for additional entries while in position
                if self.scaling_active and self.entries_filled < self.num_entries:
                    next_target = self.entry_targets[self.entries_filled]
                    if current_low <= next_target:
                        self.buy(size=size_per_entry)
                        self.total_entry_cost += next_target * size_per_entry
                        self.total_entry_size += size_per_entry
                        self.entries_filled += 1
                        self.avg_entry_price = self.total_entry_cost / self.total_entry_size

                        if self.entries_filled >= self.num_entries:
                            self.scaling_active = False

                # Take profit
                if pnl_pct >= self.take_profit_pct:
                    self.position.close()
                    self._reset()
                    return

                # Stop loss
                elif pnl_pct <= -self.stop_loss_pct:
                    self.position.close()
                    self._reset()
                    return

            return

        # Not in position
        # Check for new liquidation signal
        if current_rolling_liq >= self.liquidation_threshold and not self.signal_active:
            self.liquidation_low = current_low
            self.first_entry_target = self.liquidation_low * (1 - self.entry_below_pct / 100)
            self.signal_active = True
            self.signal_bar_count = 0

        # Check for first entry (revisit + momentum)
        if self.signal_active and not self.scaling_active:
            self.signal_bar_count += 1

            # Signal expired
            if self.signal_bar_count >= self.order_expiry_bars:
                self._reset()
                return

            # Price revisited AND momentum confirmed - start scaling in
            if current_low <= self.first_entry_target and momentum_confirmed:
                # Set up all entry targets
                self.entry_targets = []
                for i in range(self.num_entries):
                    target = self.first_entry_target * (1 - (i * self.entry_spacing_pct / 100))
                    self.entry_targets.append(target)

                # First entry
                self.buy(size=size_per_entry)
                self.total_entry_cost = self.first_entry_target * size_per_entry
                self.total_entry_size = size_per_entry
                self.avg_entry_price = self.first_entry_target
                self.entries_filled = 1
                self.scaling_active = True
                self.signal_active = False

    def _reset(self):
        self.signal_active = False
        self.liquidation_low = 0
        self.first_entry_target = 0
        self.signal_bar_count = 0
        self.scaling_active = False
        self.entries_filled = 0
        self.entry_targets = []
        self.total_entry_cost = 0
        self.total_entry_size = 0
        self.avg_entry_price = 0


# Run backtest
print("\n" + "="*70)
print("RUNNING BASELINE BACKTEST (5 entries, 0.5% spacing)")
print("="*70)

if len(data) > 100:
    bt = Backtest(
        data[['Open', 'High', 'Low', 'Close', 'Volume', 'long_liq_volume', 'short_liq_volume', 'net_liq_volume']],
        RevisitMomentumScaledEntryV2,
        cash=1000000,
        commission=0.001
    )

    baseline_stats = bt.run()

    print(f"\nMoon Dev's BASELINE RESULTS (REVISIT MOMENTUM SCALED ENTRY V2):")
    print(f"Liquidation Threshold: ${RevisitMomentumScaledEntryV2.liquidation_threshold:,}")
    print(f"Entry Below Liq Low: {RevisitMomentumScaledEntryV2.entry_below_pct}%")
    print(f"Take Profit: {RevisitMomentumScaledEntryV2.take_profit_pct}%")
    print(f"Stop Loss: {RevisitMomentumScaledEntryV2.stop_loss_pct}%")
    print(f"RSI Period: {RevisitMomentumScaledEntryV2.rsi_period}, Oversold: {RevisitMomentumScaledEntryV2.rsi_oversold}")
    print(f"Number of Entries: {RevisitMomentumScaledEntryV2.num_entries}")
    print(f"Entry Spacing: {RevisitMomentumScaledEntryV2.entry_spacing_pct}%")
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
            take_profit_pct=[4.0, 6.0, 8.0, 10.0],
            stop_loss_pct=[4.0, 6.0, 8.0],
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
        print(f"Entry Below Liq Low: {opt_stats._strategy.entry_below_pct}%")
        print(f"Take Profit: {opt_stats._strategy.take_profit_pct}%")
        print(f"Stop Loss: {opt_stats._strategy.stop_loss_pct}%")
        print(f"Number of Entries: {opt_stats._strategy.num_entries}")
        print(f"Entry Spacing: {opt_stats._strategy.entry_spacing_pct}%")

        bt.plot()

    except Exception as e:
        print(f"Optimization failed: {e}")
        bt.plot()
