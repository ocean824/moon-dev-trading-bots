"""
Revisit Momentum NEXT DAY Variation - Moon Dev
===============================================
Based on BEST performer Revisit Momentum + Next Day Reversal premise

COMBINED IDEA:
- Revisit Momentum: Wait for revisit + RSI/MACD confirmation
- Next Day: Big liqs today = opposite move 24 hours later

New Logic:
1. Detect big long liquidation ($5M-$20M)
2. Record the LOW of that liquidation bar
3. WAIT 24 hours (let dust settle, let shorts get comfy)
4. After 24hr, look for price to revisit that low
5. Confirm with RSI oversold OR MACD bullish
6. Enter on confirmation expecting next-day reversal

Moon Dev
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print("Moon Dev's REVISIT MOMENTUM NEXT DAY Strategy")
print("Premise: Wait 24hr, revisit entry + momentum confirmation")
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


class RevisitMomentumNextDay(Strategy):
    """
    Revisit Momentum with Next Day Delay

    Entry:
    - Detect big long liquidation, record low
    - Wait 24 hours
    - After delay, look for price to revisit below that low
    - Confirm with RSI oversold OR MACD bullish cross
    - Enter LONG

    Exit:
    - Take profit at X%
    - Stop loss at Y%
    """

    # Next day parameters
    liquidation_threshold = 10000000  # $10M, test 5M, 10M, 15M, 20M
    delay_bars = 288  # 24 hours

    # Revisit parameters
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

        # State tracking
        self.pending_delay = False
        self.delay_countdown = 0
        self.liquidation_low = 0

        self.signal_active = False
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

        # Phase 1: Waiting for delay
        if self.pending_delay:
            self.delay_countdown -= 1

            if self.delay_countdown <= 0:
                self.pending_delay = False
                self.signal_active = True
                self.target_entry_price = self.liquidation_low * (1 - self.entry_below_pct / 100)
                self.signal_bar_count = 0
            return

        # Phase 2: Looking for revisit + momentum
        if self.signal_active:
            self.signal_bar_count += 1

            if self.signal_bar_count >= self.order_expiry_bars:
                self._reset()
                return

            # Price revisited AND momentum confirmed
            if current_low <= self.target_entry_price and momentum_confirmed:
                self.buy(size=self.position_size)
                self.actual_entry_price = self.target_entry_price
                self.signal_active = False
            return

        # Phase 0: Look for new liquidation signal
        if current_rolling_liq >= self.liquidation_threshold:
            if not self.pending_delay and not self.signal_active:
                self.liquidation_low = current_low
                self.pending_delay = True
                self.delay_countdown = self.delay_bars

    def _reset(self):
        self.pending_delay = False
        self.delay_countdown = 0
        self.liquidation_low = 0
        self.signal_active = False
        self.target_entry_price = 0
        self.signal_bar_count = 0
        self.actual_entry_price = 0


# Run backtest
print("\n" + "="*70)
print("RUNNING BASELINE BACKTEST ($10M threshold, 24hr delay)")
print("="*70)

if len(data) > 100:
    bt = Backtest(
        data[['Open', 'High', 'Low', 'Close', 'Volume', 'long_liq_volume', 'short_liq_volume', 'net_liq_volume']],
        RevisitMomentumNextDay,
        cash=1000000,
        commission=0.001
    )

    baseline_stats = bt.run()

    print(f"\nMoon Dev's BASELINE RESULTS (REVISIT MOMENTUM NEXT DAY):")
    print(f"Liquidation Threshold: ${RevisitMomentumNextDay.liquidation_threshold:,}")
    print(f"Delay: {RevisitMomentumNextDay.delay_bars} bars ({RevisitMomentumNextDay.delay_bars * 5 / 60:.0f} hours)")
    print(f"Entry Below: {RevisitMomentumNextDay.entry_below_pct}%")
    print(f"Take Profit: {RevisitMomentumNextDay.take_profit_pct}%")
    print(f"Stop Loss: {RevisitMomentumNextDay.stop_loss_pct}%")
    print(f"RSI Oversold: {RevisitMomentumNextDay.rsi_oversold}")
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
            liquidation_threshold=[5000000, 10000000, 15000000, 20000000],
            delay_bars=[144, 288, 432],  # 12hr, 24hr, 36hr
            entry_below_pct=[1.0, 1.5, 2.0, 2.5, 3.0],
            take_profit_pct=[4.0, 6.0, 8.0, 10.0],
            stop_loss_pct=[4.0, 6.0, 8.0],
            rsi_oversold=[25, 30, 35],
            maximize='Return [%]',
            return_heatmap=False
        )

        print("\nOPTIMIZED RESULTS:")
        print("="*70)
        print(opt_stats)

        print("\nOPTIMIZED PARAMETERS:")
        print("-" * 50)
        print(f"Liquidation Threshold: ${opt_stats._strategy.liquidation_threshold:,}")
        print(f"Delay: {opt_stats._strategy.delay_bars} bars ({opt_stats._strategy.delay_bars * 5 / 60:.0f} hours)")
        print(f"Entry Below: {opt_stats._strategy.entry_below_pct}%")
        print(f"Take Profit: {opt_stats._strategy.take_profit_pct}%")
        print(f"Stop Loss: {opt_stats._strategy.stop_loss_pct}%")
        print(f"RSI Oversold: {opt_stats._strategy.rsi_oversold}")

        bt.plot()

    except Exception as e:
        print(f"Optimization failed: {e}")
        bt.plot()
