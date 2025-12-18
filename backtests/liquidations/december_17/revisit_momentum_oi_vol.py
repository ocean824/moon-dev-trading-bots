"""
Revisit Momentum + OI-Volume Correlation - Moon Dev
====================================================
Based on BEST performer: revisit_momentum

ADDED: Open Interest and Volume correlation analysis
- Track relationship between OI changes and volume
- High volume + OI decreasing = positions closing (capitulation)
- High volume + OI increasing after liq = new positions opening (reversal)

Theory: OI-Volume divergence signals smart money positioning

Moon Dev
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print("Moon Dev's REVISIT MOMENTUM + OI-VOLUME Strategy")
print("Open Interest and Volume Correlation")
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


class RevisitMomentumOiVol(Strategy):
    """
    Revisit Momentum with OI-Volume Correlation

    Since we don't have direct OI data, we use liquidations as proxy:
    - High long liquidations = forced position closing = OI decreasing
    - After liquidations, if volume stays high = new positions opening

    Entry requires:
    1. Liquidation signal + revisit below low
    2. RSI oversold OR MACD bullish
    3. Volume increasing (relative to liquidation bar) = new interest
    4. Long liquidations decreasing = capitulation over
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

    # OI-Volume correlation parameters
    volume_ma_period = 20
    volume_spike_mult = 1.2  # Volume must be X times avg for interest
    liq_cooldown_mult = 0.5  # Liqs must drop to X of trigger level

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

        # Volume MA
        self.volume_ma = self.I(
            lambda x: pd.Series(x).rolling(self.volume_ma_period, min_periods=1).mean(),
            self.data.Volume
        )

        self.signal_active = False
        self.liquidation_low = 0
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
            self.trigger_liq_level = current_rolling_liq
            self.target_entry_price = self.liquidation_low * (1 - self.entry_below_pct / 100)
            self.signal_active = True
            self.signal_bar_count = 0

        if self.signal_active:
            self.signal_bar_count += 1

            if self.signal_bar_count >= self.order_expiry_bars:
                self._reset()
                return

            # OI-Volume correlation checks:
            # 1. Volume still elevated (interest in the market)
            volume_elevated = current_volume >= current_volume_ma * self.volume_spike_mult

            # 2. Liquidations cooled down (capitulation over)
            liqs_cooled = current_rolling_liq <= self.trigger_liq_level * self.liq_cooldown_mult

            oi_vol_confirmed = volume_elevated and liqs_cooled

            # Price at target AND momentum confirmed AND OI-Vol correlation
            if current_low <= self.target_entry_price and momentum_confirmed and oi_vol_confirmed:
                self.buy(size=self.position_size)
                self.actual_entry_price = self.target_entry_price
                self.signal_active = False

    def _reset(self):
        self.signal_active = False
        self.liquidation_low = 0
        self.trigger_liq_level = 0
        self.target_entry_price = 0
        self.signal_bar_count = 0
        self.actual_entry_price = 0


# Run backtest
print("\n" + "="*70)
print("RUNNING BASELINE BACKTEST")
print("="*70)

if len(data) > 100:
    bt = Backtest(
        data[['Open', 'High', 'Low', 'Close', 'Volume', 'long_liq_volume', 'short_liq_volume', 'net_liq_volume']],
        RevisitMomentumOiVol,
        cash=1000000,
        commission=0.001
    )

    baseline_stats = bt.run()

    print(f"\nMoon Dev's BASELINE RESULTS (REVISIT MOMENTUM + OI-VOL):")
    print(f"Liquidation Threshold: ${RevisitMomentumOiVol.liquidation_threshold:,}")
    print(f"Entry Below: {RevisitMomentumOiVol.entry_below_pct}%")
    print(f"Take Profit: {RevisitMomentumOiVol.take_profit_pct}%")
    print(f"Stop Loss: {RevisitMomentumOiVol.stop_loss_pct}%")
    print(f"Volume Spike Mult: {RevisitMomentumOiVol.volume_spike_mult}x")
    print(f"Liq Cooldown Mult: {RevisitMomentumOiVol.liq_cooldown_mult}x")
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
            volume_spike_mult=[1.0, 1.2, 1.5, 2.0],
            liq_cooldown_mult=[0.3, 0.5, 0.7],
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
        print(f"Volume Spike Mult: {opt_stats._strategy.volume_spike_mult}x")
        print(f"Liq Cooldown Mult: {opt_stats._strategy.liq_cooldown_mult}x")

        bt.plot()

    except Exception as e:
        print(f"Optimization failed: {e}")
        bt.plot()
