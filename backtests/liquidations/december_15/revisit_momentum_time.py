"""
Revisit Momentum TIME-BASED SCALING - Moon Dev
===============================================
Based on the BEST performer: revisit_momentum

VARIATION: Time-based scale into position after momentum confirmation
- After price revisits + momentum confirms, spread buys evenly across X hours
- Test different hour configurations:
  - Mode 1: Buy at 1hr, 2hr, 4hr (3 buys)
  - Mode 2: Buy at 3hr, 4hr (2 buys)
  - Mode 3: Buy at 1hr, 2hr, 3hr, 4hr (4 buys)

Theory: Time-based DCA after momentum confirmation for optimal averaging

Moon Dev
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print("Moon Dev's REVISIT MOMENTUM TIME-BASED SCALING")
print("Variation: Spread buys evenly across hours after momentum confirmation")
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


class RevisitMomentumTimeStrategy(Strategy):
    """
    Revisit Momentum with Time-Based Scaling

    Entry Logic:
    - Detect liquidation, record low
    - Wait for price to revisit below liq low
    - Confirm momentum (RSI oversold OR MACD bullish)
    - Then spread buys across specified hours
    - time_mode: 1 = [1,2,4]hr, 2 = [3,4]hr, 3 = [1,2,3,4]hr

    Exit Logic:
    - Take profit at X%
    - Stop loss at Y%
    """

    # Optimizable parameters
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

    # Time-based entry parameters
    time_mode = 3  # 1 = [1,2,4]hr, 2 = [3,4]hr, 3 = [1,2,3,4]hr

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

        # Time mode configurations (in 5-min bars)
        self.time_configs = {
            1: [12, 24, 48],      # 1hr, 2hr, 4hr
            2: [36, 48],          # 3hr, 4hr
            3: [12, 24, 36, 48],  # 1hr, 2hr, 3hr, 4hr
        }

        # State tracking
        self.signal_active = False
        self.liquidation_low = 0
        self.first_entry_target = 0
        self.signal_bar_count = 0

        # Time-based entry tracking
        self.scaling_active = False
        self.bars_since_first_entry = 0
        self.entries_filled = 0
        self.entry_bars = []
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

        # Get entry schedule based on time_mode
        entry_schedule = self.time_configs.get(self.time_mode, [12, 24, 36, 48])
        num_entries = len(entry_schedule) + 1  # +1 for immediate first entry
        size_per_entry = self.position_size / num_entries

        # In position - check TP/SL and time-based entries
        if self.position:
            if self.avg_entry_price > 0:
                # Time-based additional entries
                if self.scaling_active:
                    self.bars_since_first_entry += 1

                    for i, bar_target in enumerate(self.entry_bars):
                        if self.bars_since_first_entry == bar_target and self.entries_filled == i + 1:
                            if self.entries_filled < num_entries:
                                self.buy(size=size_per_entry)
                                self.total_entry_cost += current_price * size_per_entry
                                self.total_entry_size += size_per_entry
                                self.entries_filled += 1
                                self.avg_entry_price = self.total_entry_cost / self.total_entry_size

                    # All entries filled
                    if self.entries_filled >= num_entries or self.bars_since_first_entry > max(self.entry_bars) + 12:
                        self.scaling_active = False

                pnl_pct = ((current_price - self.avg_entry_price) / self.avg_entry_price) * 100

                if pnl_pct >= self.take_profit_pct:
                    self.position.close()
                    self._reset()
                    return

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

            if self.signal_bar_count >= self.order_expiry_bars:
                self._reset()
                return

            # Price revisited AND momentum confirmed - start time-based scaling
            if current_low <= self.first_entry_target and momentum_confirmed:
                self.entry_bars = entry_schedule.copy()

                # First entry immediately
                self.buy(size=size_per_entry)
                self.total_entry_cost = current_price * size_per_entry
                self.total_entry_size = size_per_entry
                self.avg_entry_price = current_price
                self.entries_filled = 1
                self.bars_since_first_entry = 0
                self.scaling_active = True
                self.signal_active = False

    def _reset(self):
        self.signal_active = False
        self.liquidation_low = 0
        self.first_entry_target = 0
        self.signal_bar_count = 0
        self.scaling_active = False
        self.bars_since_first_entry = 0
        self.entries_filled = 0
        self.entry_bars = []
        self.total_entry_cost = 0
        self.total_entry_size = 0
        self.avg_entry_price = 0


# Run backtest
print("\n" + "="*70)
print("RUNNING BASELINE BACKTEST (Mode 3: 1,2,3,4 hours)")
print("="*70)

if len(data) > 100:
    bt = Backtest(
        data[['Open', 'High', 'Low', 'Close', 'Volume', 'long_liq_volume', 'short_liq_volume', 'net_liq_volume']],
        RevisitMomentumTimeStrategy,
        cash=1000000,
        commission=0.001
    )

    baseline_stats = bt.run()

    time_mode_desc = {1: "1hr, 2hr, 4hr", 2: "3hr, 4hr", 3: "1hr, 2hr, 3hr, 4hr"}

    print(f"\nMoon Dev's BASELINE RESULTS (REVISIT MOMENTUM TIME):")
    print(f"Liquidation Threshold: ${RevisitMomentumTimeStrategy.liquidation_threshold:,}")
    print(f"Entry Below Liq Low: {RevisitMomentumTimeStrategy.entry_below_pct}%")
    print(f"Take Profit: {RevisitMomentumTimeStrategy.take_profit_pct}%")
    print(f"Stop Loss: {RevisitMomentumTimeStrategy.stop_loss_pct}%")
    print(f"RSI Period: {RevisitMomentumTimeStrategy.rsi_period}, Oversold: {RevisitMomentumTimeStrategy.rsi_oversold}")
    print(f"Time Mode: {RevisitMomentumTimeStrategy.time_mode} ({time_mode_desc[RevisitMomentumTimeStrategy.time_mode]})")
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
            time_mode=[1, 2, 3],
            maximize='Return [%]',
            return_heatmap=False
        )

        print("\nOPTIMIZED RESULTS:")
        print("="*70)
        print(opt_stats)

        time_mode_desc = {1: "1hr, 2hr, 4hr", 2: "3hr, 4hr", 3: "1hr, 2hr, 3hr, 4hr"}

        print("\nOPTIMIZED PARAMETERS:")
        print("-" * 50)
        print(f"Liquidation Threshold: ${opt_stats._strategy.liquidation_threshold:,}")
        print(f"Entry Below Liq Low: {opt_stats._strategy.entry_below_pct}%")
        print(f"Take Profit: {opt_stats._strategy.take_profit_pct}%")
        print(f"Stop Loss: {opt_stats._strategy.stop_loss_pct}%")
        print(f"Time Mode: {opt_stats._strategy.time_mode} ({time_mode_desc[opt_stats._strategy.time_mode]})")

        bt.plot()

    except Exception as e:
        print(f"Optimization failed: {e}")
        bt.plot()
