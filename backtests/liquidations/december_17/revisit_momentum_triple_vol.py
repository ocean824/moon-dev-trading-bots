"""
Revisit Momentum + TRIPLE VOLUME (CVD + OBV + OI-Vol) - Moon Dev
================================================================
Based on BEST performer: revisit_momentum

COMBINED: All three volume indicators together
- CVD (Cumulative Volume Delta) divergence
- OBV (On Balance Volume) divergence
- OI-Volume correlation (volume elevated, liqs cooled)

Theory: Triple confirmation = highest probability setups

Moon Dev
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print("Moon Dev's REVISIT MOMENTUM + TRIPLE VOLUME Strategy")
print("CVD + OBV + OI-Vol all combined")
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


class RevisitMomentumTripleVol(Strategy):
    """
    Revisit Momentum with Triple Volume Confirmation

    Requires ALL THREE:
    1. CVD divergence (price lower, CVD higher)
    2. OBV divergence (price lower, OBV higher)
    3. OI-Vol correlation (volume up, liqs down)

    Plus standard momentum (RSI/MACD)

    Very selective but very high probability
    """

    # Base parameters
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

    # Volume parameters
    obv_smoothing = 5
    volume_ma_period = 20
    volume_spike_mult = 1.2
    liq_cooldown_mult = 0.5

    # Confirmation mode: 1=any one, 2=any two, 3=all three
    vol_confirm_mode = 2

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

        def calc_macd_signal_line(close, fast, slow, signal):
            close_series = pd.Series(close)
            ema_fast = close_series.ewm(span=fast, adjust=False).mean()
            ema_slow = close_series.ewm(span=slow, adjust=False).mean()
            macd_line = ema_fast - ema_slow
            return macd_line.ewm(span=signal, adjust=False).mean()

        self.macd_line = self.I(calc_macd_line, self.data.Close, self.macd_fast, self.macd_slow)
        self.macd_signal_line = self.I(calc_macd_signal_line, self.data.Close, self.macd_fast, self.macd_slow, self.macd_signal)

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

        self.signal_active = False
        self.liquidation_low = 0
        self.liquidation_cvd = 0
        self.liquidation_obv = 0
        self.trigger_liq_level = 0
        self.target_entry_price = 0
        self.signal_bar_count = 0
        self.actual_entry_price = 0

    def next(self):
        current_price = self.data.Close[-1]
        current_low = self.data.Low[-1]
        current_rolling_liq = self.rolling_long_liq[-1]
        current_rsi = self.rsi[-1]
        current_macd = self.macd_line[-1]
        current_macd_signal = self.macd_signal_line[-1]
        current_cvd = self.cvd[-1]
        current_obv = self.obv[-1]
        current_volume = self.data.Volume[-1]
        current_volume_ma = self.volume_ma[-1]

        prev_macd = self.macd_line[-2] if len(self.macd_line) > 1 else current_macd
        prev_macd_signal = self.macd_signal_line[-2] if len(self.macd_signal_line) > 1 else current_macd_signal

        # Momentum confirmation
        rsi_oversold = current_rsi <= self.rsi_oversold
        macd_bullish_cross = (prev_macd < prev_macd_signal) and (current_macd >= current_macd_signal)
        momentum_confirmed = rsi_oversold or macd_bullish_cross

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
        if current_rolling_liq >= self.liquidation_threshold and not self.signal_active:
            self.liquidation_low = current_low
            self.liquidation_cvd = current_cvd
            self.liquidation_obv = current_obv
            self.trigger_liq_level = current_rolling_liq
            self.target_entry_price = self.liquidation_low * (1 - self.entry_below_pct / 100)
            self.signal_active = True
            self.signal_bar_count = 0

        if self.signal_active:
            self.signal_bar_count += 1

            if self.signal_bar_count >= self.order_expiry_bars:
                self._reset()
                return

            # Check all three volume indicators
            cvd_divergence = current_cvd > self.liquidation_cvd
            obv_divergence = current_obv > self.liquidation_obv
            volume_elevated = current_volume >= current_volume_ma * self.volume_spike_mult
            liqs_cooled = current_rolling_liq <= self.trigger_liq_level * self.liq_cooldown_mult
            oi_vol_confirmed = volume_elevated and liqs_cooled

            # Count confirmations
            confirmations = sum([cvd_divergence, obv_divergence, oi_vol_confirmed])

            # Check based on mode
            vol_confirmed = confirmations >= self.vol_confirm_mode

            # Price at target AND momentum confirmed AND volume confirmed
            if current_low <= self.target_entry_price and momentum_confirmed and vol_confirmed:
                self.buy(size=self.position_size)
                self.actual_entry_price = self.target_entry_price
                self.signal_active = False

    def _reset(self):
        self.signal_active = False
        self.liquidation_low = 0
        self.liquidation_cvd = 0
        self.liquidation_obv = 0
        self.trigger_liq_level = 0
        self.target_entry_price = 0
        self.signal_bar_count = 0
        self.actual_entry_price = 0


# Run backtest
print("\n" + "="*70)
print("RUNNING BASELINE BACKTEST (Require 2 of 3 volume confirmations)")
print("="*70)

if len(data) > 100:
    bt = Backtest(
        data[['Open', 'High', 'Low', 'Close', 'Volume', 'long_liq_volume', 'short_liq_volume', 'net_liq_volume']],
        RevisitMomentumTripleVol,
        cash=1000000,
        commission=0.001
    )

    baseline_stats = bt.run()

    vol_mode_desc = {1: "Any 1 of 3", 2: "Any 2 of 3", 3: "All 3"}

    print(f"\nMoon Dev's BASELINE RESULTS (TRIPLE VOLUME):")
    print(f"Liquidation Threshold: ${RevisitMomentumTripleVol.liquidation_threshold:,}")
    print(f"Entry Below: {RevisitMomentumTripleVol.entry_below_pct}%")
    print(f"Take Profit: {RevisitMomentumTripleVol.take_profit_pct}%")
    print(f"Stop Loss: {RevisitMomentumTripleVol.stop_loss_pct}%")
    print(f"Volume Confirm Mode: {vol_mode_desc[RevisitMomentumTripleVol.vol_confirm_mode]}")
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
        print(f"Entry Below: {opt_stats._strategy.entry_below_pct}%")
        print(f"Take Profit: {opt_stats._strategy.take_profit_pct}%")
        print(f"Stop Loss: {opt_stats._strategy.stop_loss_pct}%")
        print(f"Volume Confirm Mode: {vol_mode_desc[opt_stats._strategy.vol_confirm_mode]}")

        bt.plot()

    except Exception as e:
        print(f"Optimization failed: {e}")
        bt.plot()
