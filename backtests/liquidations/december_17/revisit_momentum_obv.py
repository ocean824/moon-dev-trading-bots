"""
Revisit Momentum + OBV (On Balance Volume) Divergence - Moon Dev
=================================================================
Based on BEST performer: revisit_momentum

ADDED: On Balance Volume divergence confirmation
- OBV adds volume on up days, subtracts on down days
- Bullish divergence: Price makes lower low, OBV makes higher low
- Shows accumulation happening despite price drop

Theory: OBV divergence at liquidation lows = accumulation before reversal

Moon Dev
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print("Moon Dev's REVISIT MOMENTUM + OBV Strategy")
print("On Balance Volume Divergence confirmation")
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


class RevisitMomentumObv(Strategy):
    """
    Revisit Momentum with OBV Divergence

    OBV (On Balance Volume):
    - If close > prev close: OBV += volume
    - If close < prev close: OBV -= volume
    - Running cumulative total

    Entry requires:
    1. Liquidation signal + revisit below low
    2. RSI oversold OR MACD bullish
    3. OBV divergence: price lower low but OBV higher low
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

    # OBV parameters
    obv_smoothing = 5  # Smooth OBV with MA for less noise

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

        # OBV (On Balance Volume)
        def calc_obv(close, volume):
            close_s = pd.Series(close)
            volume_s = pd.Series(volume)

            # Direction based on close vs previous close
            direction = np.sign(close_s.diff())
            direction.iloc[0] = 0

            obv = (direction * volume_s).cumsum()
            return obv

        def calc_obv_smoothed(close, volume, smoothing):
            close_s = pd.Series(close)
            volume_s = pd.Series(volume)

            direction = np.sign(close_s.diff())
            direction.iloc[0] = 0

            obv = (direction * volume_s).cumsum()
            obv_smooth = obv.rolling(window=smoothing, min_periods=1).mean()
            return obv_smooth

        self.obv = self.I(calc_obv, self.data.Close, self.data.Volume)
        self.obv_smooth = self.I(calc_obv_smoothed, self.data.Close, self.data.Volume, self.obv_smoothing)

        self.signal_active = False
        self.liquidation_low = 0
        self.liquidation_obv = 0
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
        current_obv = self.obv_smooth[-1]

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
            self.liquidation_obv = current_obv  # Record OBV at liquidation
            self.target_entry_price = self.liquidation_low * (1 - self.entry_below_pct / 100)
            self.signal_active = True
            self.signal_bar_count = 0

        if self.signal_active:
            self.signal_bar_count += 1

            if self.signal_bar_count >= self.order_expiry_bars:
                self._reset()
                return

            # Check for OBV divergence
            # Price made lower low (at target), but OBV is higher than at liquidation
            obv_divergence = current_obv > self.liquidation_obv

            # Price at target AND momentum confirmed AND OBV divergence
            if current_low <= self.target_entry_price and momentum_confirmed and obv_divergence:
                self.buy(size=self.position_size)
                self.actual_entry_price = self.target_entry_price
                self.signal_active = False

    def _reset(self):
        self.signal_active = False
        self.liquidation_low = 0
        self.liquidation_obv = 0
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
        RevisitMomentumObv,
        cash=1000000,
        commission=0.001
    )

    baseline_stats = bt.run()

    print(f"\nMoon Dev's BASELINE RESULTS (REVISIT MOMENTUM + OBV):")
    print(f"Liquidation Threshold: ${RevisitMomentumObv.liquidation_threshold:,}")
    print(f"Entry Below: {RevisitMomentumObv.entry_below_pct}%")
    print(f"Take Profit: {RevisitMomentumObv.take_profit_pct}%")
    print(f"Stop Loss: {RevisitMomentumObv.stop_loss_pct}%")
    print(f"OBV Smoothing: {RevisitMomentumObv.obv_smoothing}")
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
            obv_smoothing=[3, 5, 10, 20],
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
        print(f"OBV Smoothing: {opt_stats._strategy.obv_smoothing}")

        bt.plot()

    except Exception as e:
        print(f"Optimization failed: {e}")
        bt.plot()
