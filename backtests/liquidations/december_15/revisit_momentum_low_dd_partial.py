"""
Revisit Momentum LOW DRAWDOWN - Partial Profits + Trailing - Moon Dev
======================================================================
Based on revisit_momentum but focused on REDUCING DRAWDOWN

APPROACH: Partial Profit Taking + Trailing Stop
- Take 50% profit at first target (lock in gains)
- Trail remaining 50% with a trailing stop
- Never give back all the gains

Theory:
- Big drawdowns happen when winning trades reverse into losers
- Lock in partial profits early to reduce drawdown
- Let remaining position ride with protection

Moon Dev
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print("Moon Dev's REVISIT MOMENTUM LOW DRAWDOWN - Partial Profits")
print("Focus: Reduce drawdown with partial profit taking + trailing")
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


class RevisitMomentumLowDdPartial(Strategy):
    """
    Revisit Momentum with Partial Profits for Low Drawdown

    Exit Strategy:
    1. Initial stop loss at X%
    2. When price hits first_tp_pct, sell partial_exit_pct of position
    3. Move stop to breakeven for remaining position
    4. Trail remaining position with trailing_pct from high
    """

    # Base parameters
    liquidation_threshold = 2000000
    lookback_bars = 1
    entry_below_pct = 2.0
    order_expiry_bars = 576

    # Momentum parameters
    rsi_period = 14
    rsi_oversold = 30
    macd_fast = 12
    macd_slow = 26
    macd_signal = 9

    # Partial profit parameters
    first_tp_pct = 3.0         # Take first partial at 3%
    partial_exit_pct = 50.0    # Exit 50% of position at first TP
    trailing_pct = 2.0         # Trail remaining by 2% from high
    initial_stop_pct = 4.0     # Initial stop at 4%

    position_size = 0.95

    def init(self):
        self.long_liq_volume = self.I(lambda: self.data.long_liq_volume)
        self.rolling_long_liq = self.I(
            lambda x: pd.Series(x).rolling(self.lookback_bars, min_periods=1).sum(),
            self.long_liq_volume
        )

        # RSI
        def calc_rsi(close, period):
            close_series = pd.Series(close)
            delta = close_series.diff()
            gain = delta.where(delta > 0, 0).rolling(window=period, min_periods=1).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period, min_periods=1).mean()
            rs = gain / loss.replace(0, np.inf)
            rsi = 100 - (100 / (1 + rs))
            return rsi

        self.rsi = self.I(calc_rsi, self.data.Close, self.rsi_period)

        # MACD
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

        self.signal_active = False
        self.liquidation_low = 0
        self.target_entry_price = 0
        self.signal_bar_count = 0
        self.actual_entry_price = 0

        # Partial profit tracking
        self.partial_taken = False
        self.highest_since_entry = 0
        self.trailing_active = False

    def next(self):
        current_price = self.data.Close[-1]
        current_low = self.data.Low[-1]
        current_rolling_liq = self.rolling_long_liq[-1]
        current_rsi = self.rsi[-1]
        current_macd = self.macd_line[-1]
        current_macd_signal = self.macd_signal_line[-1]

        prev_macd = self.macd_line[-2] if len(self.macd_line) > 1 else current_macd
        prev_macd_signal = self.macd_signal_line[-2] if len(self.macd_signal_line) > 1 else current_macd_signal

        # Momentum confirmation
        rsi_oversold = current_rsi <= self.rsi_oversold
        macd_bullish_cross = (prev_macd < prev_macd_signal) and (current_macd >= current_macd_signal)
        momentum_confirmed = rsi_oversold or macd_bullish_cross

        # In position
        if self.position:
            if self.actual_entry_price > 0:
                pnl_pct = ((current_price - self.actual_entry_price) / self.actual_entry_price) * 100

                # Update highest price
                if current_price > self.highest_since_entry:
                    self.highest_since_entry = current_price

                # Phase 1: Before partial profit taken
                if not self.partial_taken:
                    # Check for first TP - take partial
                    if pnl_pct >= self.first_tp_pct:
                        # Close partial position (50%) - portion must be fraction 0-1
                        close_fraction = self.partial_exit_pct / 100
                        self.position.close(close_fraction)
                        self.partial_taken = True
                        self.trailing_active = True
                        # Reset highest for trailing
                        self.highest_since_entry = current_price

                    # Initial stop loss
                    elif pnl_pct <= -self.initial_stop_pct:
                        self.position.close()
                        self._reset()
                        return

                # Phase 2: After partial taken - trail remaining
                else:
                    # Calculate drawdown from highest
                    if self.highest_since_entry > 0:
                        drawdown_from_high = ((self.highest_since_entry - current_price) / self.highest_since_entry) * 100

                        # Trailing stop hit
                        if drawdown_from_high >= self.trailing_pct:
                            self.position.close()
                            self._reset()
                            return

                    # Breakeven stop (never lose after partial taken)
                    if current_price <= self.actual_entry_price:
                        self.position.close()
                        self._reset()
                        return

            return

        # Not in position
        if current_rolling_liq >= self.liquidation_threshold and not self.signal_active:
            self.liquidation_low = current_low
            self.target_entry_price = self.liquidation_low * (1 - self.entry_below_pct / 100)
            self.signal_active = True
            self.signal_bar_count = 0

        if self.signal_active:
            self.signal_bar_count += 1

            if self.signal_bar_count >= self.order_expiry_bars:
                self._reset()
                return

            if current_low <= self.target_entry_price and momentum_confirmed:
                self.buy(size=self.position_size)
                self.actual_entry_price = self.target_entry_price
                self.highest_since_entry = current_price
                self.partial_taken = False
                self.trailing_active = False
                self.signal_active = False

    def _reset(self):
        self.signal_active = False
        self.liquidation_low = 0
        self.target_entry_price = 0
        self.signal_bar_count = 0
        self.actual_entry_price = 0
        self.partial_taken = False
        self.highest_since_entry = 0
        self.trailing_active = False


# Run backtest
print("\n" + "="*70)
print("RUNNING BASELINE BACKTEST (Partial Profits + Trailing)")
print("="*70)

if len(data) > 100:
    bt = Backtest(
        data[['Open', 'High', 'Low', 'Close', 'Volume', 'long_liq_volume', 'short_liq_volume', 'net_liq_volume']],
        RevisitMomentumLowDdPartial,
        cash=1000000,
        commission=0.001
    )

    baseline_stats = bt.run()

    print(f"\nMoon Dev's BASELINE RESULTS (LOW DD - PARTIAL PROFITS):")
    print(f"Liquidation Threshold: ${RevisitMomentumLowDdPartial.liquidation_threshold:,}")
    print(f"First TP: {RevisitMomentumLowDdPartial.first_tp_pct}%")
    print(f"Partial Exit: {RevisitMomentumLowDdPartial.partial_exit_pct}%")
    print(f"Trailing Stop: {RevisitMomentumLowDdPartial.trailing_pct}%")
    print(f"Initial Stop: {RevisitMomentumLowDdPartial.initial_stop_pct}%")
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
    print("RUNNING OPTIMIZATION (Minimizing Drawdown)")
    print("="*70)

    try:
        opt_stats = bt.optimize(
            liquidation_threshold=range(1000000, 4000000, 500000),
            first_tp_pct=[2.0, 3.0, 4.0, 5.0],
            partial_exit_pct=[40.0, 50.0, 60.0, 75.0],
            trailing_pct=[1.5, 2.0, 2.5, 3.0],
            initial_stop_pct=[3.0, 4.0, 5.0, 6.0],
            maximize='Sharpe Ratio',
            return_heatmap=False
        )

        print("\nOPTIMIZED RESULTS:")
        print("="*70)
        print(opt_stats)

        print("\nOPTIMIZED PARAMETERS:")
        print("-" * 50)
        print(f"Liquidation Threshold: ${opt_stats._strategy.liquidation_threshold:,}")
        print(f"First TP: {opt_stats._strategy.first_tp_pct}%")
        print(f"Partial Exit: {opt_stats._strategy.partial_exit_pct}%")
        print(f"Trailing Stop: {opt_stats._strategy.trailing_pct}%")
        print(f"Initial Stop: {opt_stats._strategy.initial_stop_pct}%")

        bt.plot()

    except Exception as e:
        print(f"Optimization failed: {e}")
        bt.plot()
