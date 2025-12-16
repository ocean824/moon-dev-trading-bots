"""
Revisit Momentum MULTI-TIMEFRAME V2 - Moon Dev
===============================================
Based on revisit_momentum (the best performer)

VARIATION: Multi-timeframe momentum confirmation
- Use fast RSI (7 period) for timing
- Use slow RSI (21 period) for trend
- Both must be oversold for entry

Theory: Alignment across timeframes = stronger signal

Moon Dev
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print("Moon Dev's REVISIT MOMENTUM MULTI-TIMEFRAME V2")
print("Variation: Fast + Slow RSI alignment")
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


class RevisitMomentumMultiTfV2(Strategy):
    """
    Revisit Momentum with Multi-Timeframe RSI V2

    - Detect liquidation, record low
    - Wait for price to drop below liq low
    - Require BOTH fast RSI and slow RSI to be oversold
    - Stronger alignment = higher probability
    """

    # Optimizable parameters
    liquidation_threshold = 2000000
    lookback_bars = 1
    entry_below_pct = 2.0
    take_profit_pct = 6.0
    stop_loss_pct = 6.0
    order_expiry_bars = 576

    # Multi-timeframe RSI parameters
    rsi_fast_period = 7
    rsi_slow_period = 21
    rsi_fast_oversold = 25  # Faster RSI can be more extreme
    rsi_slow_oversold = 35  # Slower RSI confirms trend

    position_size = 0.95

    def init(self):
        self.long_liq_volume = self.I(lambda: self.data.long_liq_volume)
        self.rolling_long_liq = self.I(
            lambda x: pd.Series(x).rolling(self.lookback_bars, min_periods=1).sum(),
            self.long_liq_volume
        )

        # RSI calculation function
        def calc_rsi(close, period):
            close_series = pd.Series(close)
            delta = close_series.diff()
            gain = delta.where(delta > 0, 0).rolling(window=period, min_periods=1).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period, min_periods=1).mean()
            rs = gain / loss.replace(0, np.inf)
            rsi = 100 - (100 / (1 + rs))
            return rsi

        # Fast RSI (for timing)
        self.rsi_fast = self.I(calc_rsi, self.data.Close, self.rsi_fast_period)

        # Slow RSI (for trend confirmation)
        self.rsi_slow = self.I(calc_rsi, self.data.Close, self.rsi_slow_period)

        self.signal_active = False
        self.liquidation_low = 0
        self.target_entry_price = 0
        self.signal_bar_count = 0
        self.actual_entry_price = 0

    def next(self):
        current_price = self.data.Close[-1]
        current_low = self.data.Low[-1]
        current_rolling_liq = self.rolling_long_liq[-1]
        current_rsi_fast = self.rsi_fast[-1]
        current_rsi_slow = self.rsi_slow[-1]

        if np.isnan(current_rsi_fast) or np.isnan(current_rsi_slow):
            return

        # Multi-timeframe momentum confirmation
        fast_oversold = current_rsi_fast <= self.rsi_fast_oversold
        slow_oversold = current_rsi_slow <= self.rsi_slow_oversold
        momentum_confirmed = fast_oversold and slow_oversold

        # In position - check TP/SL
        if self.position:
            if self.actual_entry_price > 0:
                pnl_pct = ((current_price - self.actual_entry_price) / self.actual_entry_price) * 100

                if pnl_pct >= self.take_profit_pct:
                    self.position.close()
                    self._reset()

                elif pnl_pct <= -self.stop_loss_pct:
                    self.position.close()
                    self._reset()
            return

        # Not in position
        # Check for new liquidation signal
        if current_rolling_liq >= self.liquidation_threshold and not self.signal_active:
            self.liquidation_low = current_low
            self.target_entry_price = self.liquidation_low * (1 - self.entry_below_pct / 100)
            self.signal_active = True
            self.signal_bar_count = 0

        # Check for entry
        if self.signal_active:
            self.signal_bar_count += 1

            if self.signal_bar_count >= self.order_expiry_bars:
                self._reset()
                return

            # Price at target AND both RSIs oversold
            if current_low <= self.target_entry_price and momentum_confirmed:
                self.buy(size=self.position_size)
                self.actual_entry_price = self.target_entry_price
                self.signal_active = False

    def _reset(self):
        self.signal_active = False
        self.liquidation_low = 0
        self.target_entry_price = 0
        self.signal_bar_count = 0
        self.actual_entry_price = 0


# Run backtest
print("\n" + "="*70)
print("RUNNING BASELINE BACKTEST (Non-Optimized)")
print("="*70)

if len(data) > 100:
    bt = Backtest(
        data[['Open', 'High', 'Low', 'Close', 'Volume', 'long_liq_volume', 'short_liq_volume', 'net_liq_volume']],
        RevisitMomentumMultiTfV2,
        cash=1000000,
        commission=0.001
    )

    baseline_stats = bt.run()

    print(f"\nMoon Dev's BASELINE RESULTS (MULTI-TIMEFRAME V2):")
    print(f"Liquidation Threshold: ${RevisitMomentumMultiTfV2.liquidation_threshold:,}")
    print(f"Entry Below: {RevisitMomentumMultiTfV2.entry_below_pct}%")
    print(f"Take Profit: {RevisitMomentumMultiTfV2.take_profit_pct}%")
    print(f"Stop Loss: {RevisitMomentumMultiTfV2.stop_loss_pct}%")
    print(f"Fast RSI: {RevisitMomentumMultiTfV2.rsi_fast_period} period, oversold at {RevisitMomentumMultiTfV2.rsi_fast_oversold}")
    print(f"Slow RSI: {RevisitMomentumMultiTfV2.rsi_slow_period} period, oversold at {RevisitMomentumMultiTfV2.rsi_slow_oversold}")
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
            rsi_fast_oversold=[20, 25, 30],
            rsi_slow_oversold=[30, 35, 40],
            maximize='Return [%]',
            return_heatmap=False
        )

        print("\nOPTIMIZED RESULTS:")
        print("="*70)
        print(opt_stats)

        print("\nOPTIMIZED PARAMETERS:")
        print("-" * 50)
        print(f"Liquidation Threshold: ${opt_stats._strategy.liquidation_threshold:,}")
        print(f"Entry Below: {opt_stats._strategy.entry_below_pct}%")
        print(f"Take Profit: {opt_stats._strategy.take_profit_pct}%")
        print(f"Stop Loss: {opt_stats._strategy.stop_loss_pct}%")
        print(f"Fast RSI Oversold: {opt_stats._strategy.rsi_fast_oversold}")
        print(f"Slow RSI Oversold: {opt_stats._strategy.rsi_slow_oversold}")

        bt.plot()

    except Exception as e:
        print(f"Optimization failed: {e}")
        bt.plot()
