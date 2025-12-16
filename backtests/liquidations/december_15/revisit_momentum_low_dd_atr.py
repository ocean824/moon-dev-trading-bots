"""
Revisit Momentum LOW DRAWDOWN - ATR Position Sizing - Moon Dev
===============================================================
Based on revisit_momentum but focused on REDUCING DRAWDOWN

APPROACH: ATR-Based Position Sizing
- When volatility (ATR) is HIGH -> use SMALLER position size
- When volatility (ATR) is LOW -> use LARGER position size
- Also use ATR-based stops instead of fixed % stops

Theory:
- Big drawdowns happen during volatile periods with full size positions
- Scale position size inversely to volatility
- Normalize risk per trade regardless of market conditions

Moon Dev
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print("Moon Dev's REVISIT MOMENTUM LOW DRAWDOWN - ATR Sizing")
print("Focus: Reduce drawdown with volatility-adjusted position sizing")
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


class RevisitMomentumLowDdAtr(Strategy):
    """
    Revisit Momentum with ATR-Based Position Sizing for Low Drawdown

    Key Changes:
    1. Position size scaled by inverse ATR (high vol = small size)
    2. Stops based on ATR multiples (adapts to volatility)
    3. Max position cap to prevent over-leveraging in calm markets
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

    # ATR-based risk management
    atr_period = 14
    atr_stop_multiplier = 2.0  # Stop at X * ATR from entry
    atr_tp_multiplier = 3.0    # TP at X * ATR from entry

    # Position sizing
    base_risk_pct = 2.0        # Risk X% of equity per trade
    max_position_pct = 50.0    # Never use more than X% of equity
    min_position_pct = 10.0    # Never use less than X% of equity

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

        # ATR for volatility
        def calc_atr(high, low, close, period):
            high_s = pd.Series(high)
            low_s = pd.Series(low)
            close_s = pd.Series(close)

            tr1 = high_s - low_s
            tr2 = abs(high_s - close_s.shift(1))
            tr3 = abs(low_s - close_s.shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(window=period, min_periods=1).mean()
            return atr

        self.atr = self.I(calc_atr, self.data.High, self.data.Low, self.data.Close, self.atr_period)

        # ATR percentile for position sizing (compare current ATR to historical)
        def calc_atr_percentile(high, low, close, period):
            high_s = pd.Series(high)
            low_s = pd.Series(low)
            close_s = pd.Series(close)

            tr1 = high_s - low_s
            tr2 = abs(high_s - close_s.shift(1))
            tr3 = abs(low_s - close_s.shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(window=period, min_periods=1).mean()

            # Rolling percentile over 100 periods
            atr_pct = atr.rolling(window=100, min_periods=20).apply(
                lambda x: pd.Series(x).rank(pct=True).iloc[-1], raw=False
            )
            return atr_pct

        self.atr_percentile = self.I(calc_atr_percentile, self.data.High, self.data.Low, self.data.Close, self.atr_period)

        self.signal_active = False
        self.liquidation_low = 0
        self.target_entry_price = 0
        self.signal_bar_count = 0
        self.actual_entry_price = 0
        self.stop_price = 0
        self.tp_price = 0

    def next(self):
        current_price = self.data.Close[-1]
        current_low = self.data.Low[-1]
        current_rolling_liq = self.rolling_long_liq[-1]
        current_rsi = self.rsi[-1]
        current_macd = self.macd_line[-1]
        current_macd_signal = self.macd_signal_line[-1]
        current_atr = self.atr[-1]
        current_atr_pct = self.atr_percentile[-1]

        prev_macd = self.macd_line[-2] if len(self.macd_line) > 1 else current_macd
        prev_macd_signal = self.macd_signal_line[-2] if len(self.macd_signal_line) > 1 else current_macd_signal

        if np.isnan(current_atr) or np.isnan(current_rsi) or current_atr <= 0:
            return

        # Momentum confirmation
        rsi_oversold = current_rsi <= self.rsi_oversold
        macd_bullish_cross = (prev_macd < prev_macd_signal) and (current_macd >= current_macd_signal)
        momentum_confirmed = rsi_oversold or macd_bullish_cross

        # In position - check ATR-based TP/SL
        if self.position:
            if self.actual_entry_price > 0:
                # ATR-based exits
                if current_price >= self.tp_price:
                    self.position.close()
                    self._reset()
                    return

                elif current_price <= self.stop_price:
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
                # Calculate ATR-based position size
                # Higher ATR percentile = smaller position
                if np.isnan(current_atr_pct):
                    current_atr_pct = 0.5  # Default to middle

                # Invert: high volatility = small size
                # ATR percentile 0.9 (high vol) -> size multiplier 0.1
                # ATR percentile 0.1 (low vol) -> size multiplier 0.9
                vol_multiplier = 1.0 - current_atr_pct
                vol_multiplier = max(0.2, min(1.0, vol_multiplier))  # Clamp between 0.2 and 1.0

                # Calculate position size
                position_pct = self.base_risk_pct / (current_atr / current_price * 100) * vol_multiplier
                position_pct = max(self.min_position_pct, min(self.max_position_pct, position_pct))
                position_size = position_pct / 100

                # Set ATR-based stops
                self.actual_entry_price = self.target_entry_price
                self.stop_price = self.actual_entry_price - (current_atr * self.atr_stop_multiplier)
                self.tp_price = self.actual_entry_price + (current_atr * self.atr_tp_multiplier)

                self.buy(size=position_size)
                self.signal_active = False

    def _reset(self):
        self.signal_active = False
        self.liquidation_low = 0
        self.target_entry_price = 0
        self.signal_bar_count = 0
        self.actual_entry_price = 0
        self.stop_price = 0
        self.tp_price = 0


# Run backtest
print("\n" + "="*70)
print("RUNNING BASELINE BACKTEST (ATR Position Sizing)")
print("="*70)

if len(data) > 100:
    bt = Backtest(
        data[['Open', 'High', 'Low', 'Close', 'Volume', 'long_liq_volume', 'short_liq_volume', 'net_liq_volume']],
        RevisitMomentumLowDdAtr,
        cash=1000000,
        commission=0.001
    )

    baseline_stats = bt.run()

    print(f"\nMoon Dev's BASELINE RESULTS (LOW DD - ATR SIZING):")
    print(f"Liquidation Threshold: ${RevisitMomentumLowDdAtr.liquidation_threshold:,}")
    print(f"ATR Period: {RevisitMomentumLowDdAtr.atr_period}")
    print(f"ATR Stop Multiplier: {RevisitMomentumLowDdAtr.atr_stop_multiplier}x")
    print(f"ATR TP Multiplier: {RevisitMomentumLowDdAtr.atr_tp_multiplier}x")
    print(f"Base Risk %: {RevisitMomentumLowDdAtr.base_risk_pct}%")
    print(f"Position Range: {RevisitMomentumLowDdAtr.min_position_pct}% - {RevisitMomentumLowDdAtr.max_position_pct}%")
    print("-" * 50)
    print(f"Total Trades: {baseline_stats['# Trades']}")
    print(f"Win Rate: {baseline_stats['Win Rate [%]']:.2f}%")
    print(f"Return: {baseline_stats['Return [%]']:.2f}%")
    print(f"Sharpe: {baseline_stats['Sharpe Ratio']:.2f}")
    print(f"Max Drawdown: {baseline_stats['Max. Drawdown [%]']:.2f}%")

    print("\nFULL BASELINE STATS:")
    print("="*70)
    print(baseline_stats)

    # Optimization focused on drawdown
    print("\n" + "="*70)
    print("RUNNING OPTIMIZATION (Minimizing Drawdown)")
    print("="*70)

    try:
        # Custom optimization to balance return and drawdown
        opt_stats = bt.optimize(
            liquidation_threshold=range(1000000, 4000000, 500000),
            atr_stop_multiplier=[1.5, 2.0, 2.5, 3.0],
            atr_tp_multiplier=[2.0, 3.0, 4.0],
            base_risk_pct=[1.0, 2.0, 3.0],
            max_position_pct=[30.0, 50.0, 70.0],
            maximize='Sharpe Ratio',  # Sharpe balances return vs risk
            return_heatmap=False
        )

        print("\nOPTIMIZED RESULTS:")
        print("="*70)
        print(opt_stats)

        print("\nOPTIMIZED PARAMETERS:")
        print("-" * 50)
        print(f"Liquidation Threshold: ${opt_stats._strategy.liquidation_threshold:,}")
        print(f"ATR Stop Multiplier: {opt_stats._strategy.atr_stop_multiplier}x")
        print(f"ATR TP Multiplier: {opt_stats._strategy.atr_tp_multiplier}x")
        print(f"Base Risk %: {opt_stats._strategy.base_risk_pct}%")
        print(f"Max Position %: {opt_stats._strategy.max_position_pct}%")

        bt.plot()

    except Exception as e:
        print(f"Optimization failed: {e}")
        bt.plot()
