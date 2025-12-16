"""
Revisit Momentum LOW DRAWDOWN - Circuit Breaker - Moon Dev
===========================================================
Based on revisit_momentum but focused on REDUCING DRAWDOWN

APPROACH: Drawdown Circuit Breaker + Equity Curve Trading
- Track running drawdown from peak equity
- STOP trading when drawdown exceeds threshold
- Resume trading after recovery or cooldown period
- Trade smaller after hitting circuit breaker

Theory:
- Big drawdowns compound when you keep trading during bad periods
- Stop the bleeding by pausing trades
- Come back with smaller size after recovery

Moon Dev
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print("Moon Dev's REVISIT MOMENTUM LOW DRAWDOWN - Circuit Breaker")
print("Focus: Reduce drawdown with trading pause during losing streaks")
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


class RevisitMomentumLowDdCircuit(Strategy):
    """
    Revisit Momentum with Circuit Breaker for Low Drawdown

    Circuit Breaker Logic:
    1. Track peak equity and current drawdown
    2. When drawdown > circuit_breaker_pct, STOP trading
    3. Wait for cooldown_bars OR recovery to resume
    4. After circuit break, trade at reduced_size_pct until new high

    Also includes:
    - Consecutive loss limit
    - Tighter stops during recovery period
    """

    # Base parameters
    liquidation_threshold = 2000000
    lookback_bars = 1
    entry_below_pct = 2.0
    take_profit_pct = 6.0
    stop_loss_pct = 4.0  # Tighter stop for drawdown control
    order_expiry_bars = 576

    # Momentum parameters
    rsi_period = 14
    rsi_oversold = 30
    macd_fast = 12
    macd_slow = 26
    macd_signal = 9

    # Circuit breaker parameters
    circuit_breaker_pct = 15.0    # Stop trading at 15% drawdown
    cooldown_bars = 288           # 24 hours cooldown (5min bars)
    reduced_size_pct = 50.0       # Trade at 50% size after circuit break
    recovery_threshold_pct = 5.0  # Resume full size after recovering 5%
    max_consecutive_losses = 3    # Pause after 3 losses in a row

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

        # Signal tracking
        self.signal_active = False
        self.liquidation_low = 0
        self.target_entry_price = 0
        self.signal_bar_count = 0
        self.actual_entry_price = 0

        # Circuit breaker tracking
        self.peak_equity = 1000000  # Starting cash
        self.circuit_triggered = False
        self.cooldown_counter = 0
        self.reduced_mode = False
        self.consecutive_losses = 0
        self.last_trade_pnl = 0

    def next(self):
        current_price = self.data.Close[-1]
        current_low = self.data.Low[-1]
        current_rolling_liq = self.rolling_long_liq[-1]
        current_rsi = self.rsi[-1]
        current_macd = self.macd_line[-1]
        current_macd_signal = self.macd_signal_line[-1]

        prev_macd = self.macd_line[-2] if len(self.macd_line) > 1 else current_macd
        prev_macd_signal = self.macd_signal_line[-2] if len(self.macd_signal_line) > 1 else current_macd_signal

        # Get current equity
        current_equity = self.equity

        # Update peak equity
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity
            self.reduced_mode = False  # Back to full size at new high
            self.consecutive_losses = 0

        # Calculate current drawdown
        current_dd = ((self.peak_equity - current_equity) / self.peak_equity) * 100

        # Circuit breaker check
        if self.circuit_triggered:
            self.cooldown_counter += 1

            # Check for recovery or cooldown complete
            recovery = ((current_equity - (self.peak_equity * (1 - self.circuit_breaker_pct/100))) /
                       (self.peak_equity * self.circuit_breaker_pct/100)) * 100

            if self.cooldown_counter >= self.cooldown_bars or recovery >= self.recovery_threshold_pct:
                self.circuit_triggered = False
                self.reduced_mode = True  # Trade reduced size after circuit break
                self.cooldown_counter = 0

        # Trigger circuit breaker
        if current_dd >= self.circuit_breaker_pct and not self.circuit_triggered:
            self.circuit_triggered = True
            self.cooldown_counter = 0
            # Close any open position
            if self.position:
                self.position.close()
                self._reset_signal()
            return

        # If circuit breaker is active, don't trade
        if self.circuit_triggered:
            return

        # Check consecutive losses
        if self.consecutive_losses >= self.max_consecutive_losses:
            # Mini circuit breaker - skip this signal
            if not self.position:
                self.consecutive_losses = 0  # Reset after skipping one
            return

        # Momentum confirmation
        rsi_oversold = current_rsi <= self.rsi_oversold
        macd_bullish_cross = (prev_macd < prev_macd_signal) and (current_macd >= current_macd_signal)
        momentum_confirmed = rsi_oversold or macd_bullish_cross

        # In position
        if self.position:
            if self.actual_entry_price > 0:
                pnl_pct = ((current_price - self.actual_entry_price) / self.actual_entry_price) * 100

                # Use tighter stops in reduced mode
                effective_stop = self.stop_loss_pct * 0.75 if self.reduced_mode else self.stop_loss_pct

                if pnl_pct >= self.take_profit_pct:
                    self.position.close()
                    self.consecutive_losses = 0  # Reset on win
                    self._reset_signal()

                elif pnl_pct <= -effective_stop:
                    self.position.close()
                    self.consecutive_losses += 1
                    self._reset_signal()
            return

        # Not in position - look for entry
        if current_rolling_liq >= self.liquidation_threshold and not self.signal_active:
            self.liquidation_low = current_low
            self.target_entry_price = self.liquidation_low * (1 - self.entry_below_pct / 100)
            self.signal_active = True
            self.signal_bar_count = 0

        if self.signal_active:
            self.signal_bar_count += 1

            if self.signal_bar_count >= self.order_expiry_bars:
                self._reset_signal()
                return

            if current_low <= self.target_entry_price and momentum_confirmed:
                # Determine position size based on mode
                if self.reduced_mode:
                    size = self.position_size * (self.reduced_size_pct / 100)
                else:
                    size = self.position_size

                self.buy(size=size)
                self.actual_entry_price = self.target_entry_price
                self.signal_active = False

    def _reset_signal(self):
        self.signal_active = False
        self.liquidation_low = 0
        self.target_entry_price = 0
        self.signal_bar_count = 0
        self.actual_entry_price = 0


# Run backtest
print("\n" + "="*70)
print("RUNNING BASELINE BACKTEST (Circuit Breaker)")
print("="*70)

if len(data) > 100:
    bt = Backtest(
        data[['Open', 'High', 'Low', 'Close', 'Volume', 'long_liq_volume', 'short_liq_volume', 'net_liq_volume']],
        RevisitMomentumLowDdCircuit,
        cash=1000000,
        commission=0.001
    )

    baseline_stats = bt.run()

    print(f"\nMoon Dev's BASELINE RESULTS (LOW DD - CIRCUIT BREAKER):")
    print(f"Liquidation Threshold: ${RevisitMomentumLowDdCircuit.liquidation_threshold:,}")
    print(f"Circuit Breaker: {RevisitMomentumLowDdCircuit.circuit_breaker_pct}% drawdown")
    print(f"Cooldown: {RevisitMomentumLowDdCircuit.cooldown_bars} bars ({RevisitMomentumLowDdCircuit.cooldown_bars * 5 / 60:.1f} hours)")
    print(f"Reduced Size After Break: {RevisitMomentumLowDdCircuit.reduced_size_pct}%")
    print(f"Max Consecutive Losses: {RevisitMomentumLowDdCircuit.max_consecutive_losses}")
    print(f"Stop Loss: {RevisitMomentumLowDdCircuit.stop_loss_pct}%")
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
            circuit_breaker_pct=[10.0, 15.0, 20.0],
            cooldown_bars=[144, 288, 576],  # 12hr, 24hr, 48hr
            reduced_size_pct=[30.0, 50.0, 70.0],
            stop_loss_pct=[3.0, 4.0, 5.0, 6.0],
            max_consecutive_losses=[2, 3, 4],
            maximize='Sharpe Ratio',
            return_heatmap=False
        )

        print("\nOPTIMIZED RESULTS:")
        print("="*70)
        print(opt_stats)

        print("\nOPTIMIZED PARAMETERS:")
        print("-" * 50)
        print(f"Liquidation Threshold: ${opt_stats._strategy.liquidation_threshold:,}")
        print(f"Circuit Breaker: {opt_stats._strategy.circuit_breaker_pct}% drawdown")
        print(f"Cooldown: {opt_stats._strategy.cooldown_bars} bars")
        print(f"Reduced Size: {opt_stats._strategy.reduced_size_pct}%")
        print(f"Stop Loss: {opt_stats._strategy.stop_loss_pct}%")
        print(f"Max Consecutive Losses: {opt_stats._strategy.max_consecutive_losses}")

        bt.plot()

    except Exception as e:
        print(f"Optimization failed: {e}")
        bt.plot()
