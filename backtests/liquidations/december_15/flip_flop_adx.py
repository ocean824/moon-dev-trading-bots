"""
Flip Flop ADX - Moon Dev
=========================
Based on the winning Flip Flop strategy (529% return)

VARIATION: Add ADX (Average Directional Index) filter
- ADX measures trend strength (not direction)
- High ADX = strong trend, Low ADX = choppy/ranging
- Can use to filter entries or exits

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

print("Moon Dev's FLIP FLOP ADX Strategy")
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


class FlipFlopAdxStrategy(Strategy):
    """
    Flip Flop with ADX Filter

    ADX Modes:
    - adx_mode 1: Only enter when ADX > threshold (trending)
    - adx_mode 2: Only enter when ADX < threshold (ranging/mean reversion)
    - adx_mode 3: Use +DI > -DI for long bias confirmation

    Entry/Exit same as original Flip Flop
    """

    # Optimizable parameters
    liquidation_threshold = 500000
    lookback_bars = 3
    take_profit_pct = 1.5
    stop_loss_pct = 10.0

    # ADX parameters
    adx_period = 14
    adx_threshold = 25  # Classic threshold for trend strength
    adx_mode = 2  # 1=trending only, 2=ranging only, 3=DI confirmation

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

            # True Range
            tr1 = high_s - low_s
            tr2 = abs(high_s - close_s.shift(1))
            tr3 = abs(low_s - close_s.shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(window=period, min_periods=1).mean()

            # Directional Movement
            up_move = high_s - high_s.shift(1)
            down_move = low_s.shift(1) - low_s

            plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
            minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

            plus_dm_smooth = pd.Series(plus_dm).rolling(window=period, min_periods=1).mean()
            minus_dm_smooth = pd.Series(minus_dm).rolling(window=period, min_periods=1).mean()

            # Directional Indicators
            plus_di = 100 * (plus_dm_smooth / atr.replace(0, np.inf))
            minus_di = 100 * (minus_dm_smooth / atr.replace(0, np.inf))

            # ADX
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

        self.state = 'waiting'
        self.entry_price = 0

    def next(self):
        current_price = self.data.Close[-1]
        current_rolling_liq = self.rolling_long_liq[-1]
        current_adx = self.adx[-1]
        current_plus_di = self.plus_di[-1]
        current_minus_di = self.minus_di[-1]

        if np.isnan(current_adx):
            return

        # ADX filter based on mode
        adx_confirmed = False
        if self.adx_mode == 1:
            # Mode 1: Only trade in strong trends (ADX > threshold)
            adx_confirmed = current_adx > self.adx_threshold
        elif self.adx_mode == 2:
            # Mode 2: Only trade in ranging markets (ADX < threshold) - mean reversion
            adx_confirmed = current_adx < self.adx_threshold
        elif self.adx_mode == 3:
            # Mode 3: +DI > -DI for bullish bias (good for buying dips)
            adx_confirmed = current_plus_di > current_minus_di

        # STATE: WAITING
        if self.state == 'waiting':
            if not self.position:
                # Only enter if liquidation signal AND ADX confirms
                if current_rolling_liq >= self.liquidation_threshold and adx_confirmed:
                    self.buy(size=self.position_size)
                    self.entry_price = current_price
                    self.state = 'long'

        # STATE: LONG
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


# Run backtest
print("\n" + "="*70)
print("RUNNING BASELINE BACKTEST (ADX Mode 2: Ranging)")
print("="*70)

if len(data) > 100:
    bt = Backtest(
        data[['Open', 'High', 'Low', 'Close', 'Volume', 'long_liq_volume', 'short_liq_volume', 'net_liq_volume']],
        FlipFlopAdxStrategy,
        cash=1000000,
        commission=0.001
    )

    baseline_stats = bt.run()

    adx_mode_desc = {1: "Trending (ADX > threshold)", 2: "Ranging (ADX < threshold)", 3: "+DI > -DI confirmation"}

    print(f"\nMoon Dev's BASELINE RESULTS (FLIP FLOP ADX):")
    print(f"Liquidation Threshold: ${FlipFlopAdxStrategy.liquidation_threshold:,}")
    print(f"Lookback Bars: {FlipFlopAdxStrategy.lookback_bars}")
    print(f"Take Profit: {FlipFlopAdxStrategy.take_profit_pct}%")
    print(f"Stop Loss: {FlipFlopAdxStrategy.stop_loss_pct}%")
    print(f"ADX Period: {FlipFlopAdxStrategy.adx_period}")
    print(f"ADX Threshold: {FlipFlopAdxStrategy.adx_threshold}")
    print(f"ADX Mode: {FlipFlopAdxStrategy.adx_mode} ({adx_mode_desc[FlipFlopAdxStrategy.adx_mode]})")
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
        print(f"Lookback Bars: {opt_stats._strategy.lookback_bars}")
        print(f"Take Profit: {opt_stats._strategy.take_profit_pct}%")
        print(f"Stop Loss: {opt_stats._strategy.stop_loss_pct}%")
        print(f"ADX Threshold: {opt_stats._strategy.adx_threshold}")
        print(f"ADX Mode: {opt_stats._strategy.adx_mode} ({adx_mode_desc[opt_stats._strategy.adx_mode]})")

        bt.plot()

    except Exception as e:
        print(f"Optimization failed: {e}")
        bt.plot()
