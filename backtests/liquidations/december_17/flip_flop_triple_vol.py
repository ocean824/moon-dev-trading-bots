"""
Flip Flop + TRIPLE VOLUME (CVD + OBV + OI-Vol) - Moon Dev
==========================================================
Based on winning Flip Flop strategy (529% return)

COMBINED: All three volume indicators for entry confirmation
- CVD (Cumulative Volume Delta) divergence
- OBV (On Balance Volume) divergence
- OI-Volume correlation (volume elevated, liqs cooled)

Theory: Flip flop with volume confirmation = better entries

Moon Dev
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print("Moon Dev's FLIP FLOP + TRIPLE VOLUME Strategy")
print("CVD + OBV + OI-Vol combined with Flip Flop")
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


class FlipFlopTripleVol(Strategy):
    """
    Flip Flop with Triple Volume Confirmation

    Entry:
    - Liquidation signal
    - Volume confirmation (CVD/OBV/OI-Vol)

    Exit (Flip Flop):
    - TP hit -> flip to short
    - SL hit -> flip to short
    - TP/SL on short -> done
    """

    # Flip Flop parameters (from optimized)
    liquidation_threshold = 500000
    lookback_bars = 3
    take_profit_pct = 1.5
    stop_loss_pct = 10.0

    # Volume parameters
    obv_smoothing = 5
    volume_ma_period = 20
    volume_spike_mult = 1.2
    liq_cooldown_mult = 0.5

    # Confirmation mode: 1=any one, 2=any two, 3=all three
    vol_confirm_mode = 1  # Less strict for flip flop since it trades more

    position_size = 0.95

    def init(self):
        self.long_liq_volume = self.I(lambda: self.data.long_liq_volume)
        self.rolling_long_liq = self.I(
            lambda x: pd.Series(x).rolling(self.lookback_bars, min_periods=1).sum(),
            self.long_liq_volume
        )

        # CVD
        def calc_cvd(open_p, close, volume):
            open_s = pd.Series(open_p)
            close_s = pd.Series(close)
            volume_s = pd.Series(volume)
            delta = np.where(close_s > open_s, volume_s, -volume_s)
            delta = np.where(close_s == open_s, 0, delta)
            cvd = pd.Series(delta).cumsum()
            return cvd

        self.cvd = self.I(calc_cvd, self.data.Open, self.data.Close, self.data.Volume)

        # OBV
        def calc_obv_smoothed(close, volume, smoothing):
            close_s = pd.Series(close)
            volume_s = pd.Series(volume)
            direction = np.sign(close_s.diff())
            direction.iloc[0] = 0
            obv = (direction * volume_s).cumsum()
            obv_smooth = obv.rolling(window=smoothing, min_periods=1).mean()
            return obv_smooth

        self.obv = self.I(calc_obv_smoothed, self.data.Close, self.data.Volume, self.obv_smoothing)

        # Volume MA
        self.volume_ma = self.I(
            lambda x: pd.Series(x).rolling(self.volume_ma_period, min_periods=1).mean(),
            self.data.Volume
        )

        # Recent CVD/OBV for divergence (look back N bars)
        self.lookback_cvd = 0
        self.lookback_obv = 0
        self.lookback_liq = 0

        self.state = 'waiting'
        self.entry_price = 0

    def next(self):
        current_price = self.data.Close[-1]
        current_rolling_liq = self.rolling_long_liq[-1]
        current_cvd = self.cvd[-1]
        current_obv = self.obv[-1]
        current_volume = self.data.Volume[-1]
        current_volume_ma = self.volume_ma[-1]

        # Get values from N bars ago for divergence check
        lookback = min(self.lookback_bars * 2, len(self.cvd) - 1)
        if lookback > 0:
            past_cvd = self.cvd[-lookback]
            past_obv = self.obv[-lookback]
            past_liq = self.rolling_long_liq[-lookback]
        else:
            past_cvd = current_cvd
            past_obv = current_obv
            past_liq = current_rolling_liq

        # STATE: WAITING
        if self.state == 'waiting':
            if not self.position:
                if current_rolling_liq >= self.liquidation_threshold:
                    # Check volume confirmations
                    cvd_rising = current_cvd > past_cvd
                    obv_rising = current_obv > past_obv
                    volume_elevated = current_volume >= current_volume_ma * self.volume_spike_mult

                    confirmations = sum([cvd_rising, obv_rising, volume_elevated])

                    if confirmations >= self.vol_confirm_mode:
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
print("RUNNING BASELINE BACKTEST")
print("="*70)

if len(data) > 100:
    bt = Backtest(
        data[['Open', 'High', 'Low', 'Close', 'Volume', 'long_liq_volume', 'short_liq_volume', 'net_liq_volume']],
        FlipFlopTripleVol,
        cash=1000000,
        commission=0.001
    )

    baseline_stats = bt.run()

    vol_mode_desc = {1: "Any 1 of 3", 2: "Any 2 of 3", 3: "All 3"}

    print(f"\nMoon Dev's BASELINE RESULTS (FLIP FLOP + TRIPLE VOL):")
    print(f"Liquidation Threshold: ${FlipFlopTripleVol.liquidation_threshold:,}")
    print(f"Lookback Bars: {FlipFlopTripleVol.lookback_bars}")
    print(f"Take Profit: {FlipFlopTripleVol.take_profit_pct}%")
    print(f"Stop Loss: {FlipFlopTripleVol.stop_loss_pct}%")
    print(f"Volume Confirm Mode: {vol_mode_desc[FlipFlopTripleVol.vol_confirm_mode]}")
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
            vol_confirm_mode=[1, 2, 3],
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
        print(f"Volume Confirm Mode: {vol_mode_desc[opt_stats._strategy.vol_confirm_mode]}")

        bt.plot()

    except Exception as e:
        print(f"Optimization failed: {e}")
        bt.plot()
