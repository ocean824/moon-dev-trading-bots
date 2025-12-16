"""
Revisit Liq ADX - Moon Dev
===========================
Based on the winning Revisit Liq strategy (192% return)

VARIATION: Add ADX (Average Directional Index) filter
- ADX measures trend strength (not direction)
- High ADX = strong trend, Low ADX = choppy/ranging
- Can use to filter entries

Options:
1. Only enter when ADX > threshold (strong trend = bigger moves)
2. Only enter when ADX < threshold (ranging = mean reversion works)
3. Use +DI/-DI for direction confirmation

Moon Dev
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print("Moon Dev's REVISIT LIQ ADX Strategy")
print("Variation: ADX trend strength filter")
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


class RevisitLiqAdxStrategy(Strategy):
    """
    Revisit Liq with ADX Filter

    ADX Modes:
    - adx_mode 1: Only enter when ADX > threshold (trending)
    - adx_mode 2: Only enter when ADX < threshold (ranging/mean reversion)
    - adx_mode 3: Use +DI > -DI for long bias confirmation

    Entry: Wait for revisit below liq low + ADX confirmation
    Exit: TP/SL
    """

    # Optimizable parameters
    liquidation_threshold = 2000000
    lookback_bars = 1
    entry_below_pct = 2.0
    take_profit_pct = 6.0
    stop_loss_pct = 6.0
    order_expiry_bars = 576

    # ADX parameters
    adx_period = 14
    adx_threshold = 25
    adx_mode = 2  # 1=trending, 2=ranging, 3=DI confirmation

    position_size = 0.95

    def init(self):
        self.long_liq_volume = self.I(lambda: self.data.long_liq_volume)
        self.rolling_long_liq = self.I(
            lambda x: pd.Series(x).rolling(self.lookback_bars, min_periods=1).sum(),
            self.long_liq_volume
        )

        # ADX calculation
        def calc_adx(high, low, close, period):
            high_s = pd.Series(high)
            low_s = pd.Series(low)
            close_s = pd.Series(close)

            tr1 = high_s - low_s
            tr2 = abs(high_s - close_s.shift(1))
            tr3 = abs(low_s - close_s.shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(window=period, min_periods=1).mean()

            up_move = high_s - high_s.shift(1)
            down_move = low_s.shift(1) - low_s

            plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
            minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

            plus_dm_smooth = pd.Series(plus_dm).rolling(window=period, min_periods=1).mean()
            minus_dm_smooth = pd.Series(minus_dm).rolling(window=period, min_periods=1).mean()

            plus_di = 100 * (plus_dm_smooth / atr.replace(0, np.inf))
            minus_di = 100 * (minus_dm_smooth / atr.replace(0, np.inf))

            dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, np.inf)
            adx = dx.rolling(window=period, min_periods=1).mean()

            return adx

        def calc_plus_di(high, low, close, period):
            high_s = pd.Series(high)
            low_s = pd.Series(low)
            close_s = pd.Series(close)

            tr1 = high_s - low_s
            tr2 = abs(high_s - close_s.shift(1))
            tr3 = abs(low_s - close_s.shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(window=period, min_periods=1).mean()

            up_move = high_s - high_s.shift(1)
            down_move = low_s.shift(1) - low_s
            plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
            plus_dm_smooth = pd.Series(plus_dm).rolling(window=period, min_periods=1).mean()
            plus_di = 100 * (plus_dm_smooth / atr.replace(0, np.inf))

            return plus_di

        def calc_minus_di(high, low, close, period):
            high_s = pd.Series(high)
            low_s = pd.Series(low)
            close_s = pd.Series(close)

            tr1 = high_s - low_s
            tr2 = abs(high_s - close_s.shift(1))
            tr3 = abs(low_s - close_s.shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(window=period, min_periods=1).mean()

            up_move = high_s - high_s.shift(1)
            down_move = low_s.shift(1) - low_s
            minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
            minus_dm_smooth = pd.Series(minus_dm).rolling(window=period, min_periods=1).mean()
            minus_di = 100 * (minus_dm_smooth / atr.replace(0, np.inf))

            return minus_di

        self.adx = self.I(calc_adx, self.data.High, self.data.Low, self.data.Close, self.adx_period)
        self.plus_di = self.I(calc_plus_di, self.data.High, self.data.Low, self.data.Close, self.adx_period)
        self.minus_di = self.I(calc_minus_di, self.data.High, self.data.Low, self.data.Close, self.adx_period)

        self.signal_active = False
        self.liquidation_low = 0
        self.target_entry_price = 0
        self.signal_bar_count = 0
        self.actual_entry_price = 0

    def next(self):
        current_price = self.data.Close[-1]
        current_low = self.data.Low[-1]
        current_rolling_liq = self.rolling_long_liq[-1]
        current_adx = self.adx[-1]
        current_plus_di = self.plus_di[-1]
        current_minus_di = self.minus_di[-1]

        if np.isnan(current_adx):
            return

        # ADX filter based on mode
        adx_confirmed = False
        if self.adx_mode == 1:
            adx_confirmed = current_adx > self.adx_threshold
        elif self.adx_mode == 2:
            adx_confirmed = current_adx < self.adx_threshold
        elif self.adx_mode == 3:
            adx_confirmed = current_plus_di > current_minus_di

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

            # Price at target AND ADX confirms
            if current_low <= self.target_entry_price and adx_confirmed:
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
print("RUNNING BASELINE BACKTEST (ADX Mode 2: Ranging)")
print("="*70)

if len(data) > 100:
    bt = Backtest(
        data[['Open', 'High', 'Low', 'Close', 'Volume', 'long_liq_volume', 'short_liq_volume', 'net_liq_volume']],
        RevisitLiqAdxStrategy,
        cash=1000000,
        commission=0.001
    )

    baseline_stats = bt.run()

    adx_mode_desc = {1: "Trending (ADX > threshold)", 2: "Ranging (ADX < threshold)", 3: "+DI > -DI confirmation"}

    print(f"\nMoon Dev's BASELINE RESULTS (REVISIT LIQ ADX):")
    print(f"Liquidation Threshold: ${RevisitLiqAdxStrategy.liquidation_threshold:,}")
    print(f"Entry Below Liq Low: {RevisitLiqAdxStrategy.entry_below_pct}%")
    print(f"Take Profit: {RevisitLiqAdxStrategy.take_profit_pct}%")
    print(f"Stop Loss: {RevisitLiqAdxStrategy.stop_loss_pct}%")
    print(f"ADX Period: {RevisitLiqAdxStrategy.adx_period}")
    print(f"ADX Threshold: {RevisitLiqAdxStrategy.adx_threshold}")
    print(f"ADX Mode: {RevisitLiqAdxStrategy.adx_mode} ({adx_mode_desc[RevisitLiqAdxStrategy.adx_mode]})")
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
            adx_threshold=[15, 20, 25, 30],
            adx_mode=[1, 2, 3],
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
        print(f"ADX Threshold: {opt_stats._strategy.adx_threshold}")
        print(f"ADX Mode: {opt_stats._strategy.adx_mode} ({adx_mode_desc[opt_stats._strategy.adx_mode]})")

        bt.plot()

    except Exception as e:
        print(f"Optimization failed: {e}")
        bt.plot()
