"""
Revisit Momentum RSI DIVERGENCE V2 - Moon Dev
==============================================
Based on revisit_momentum (the best performer)

VARIATION: Look for RSI BULLISH DIVERGENCE at the revisit level
- Price makes lower low (revisiting below liq low)
- RSI makes higher low (divergence = hidden strength)
- More selective but higher probability entries

Theory: RSI divergence signals exhaustion of selling pressure

Moon Dev
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print("Moon Dev's REVISIT MOMENTUM RSI DIVERGENCE V2")
print("Variation: Bullish RSI divergence confirmation")
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


class RevisitMomentumRsiDivergenceV2(Strategy):
    """
    Revisit Momentum with RSI Divergence V2

    - Detect liquidation, record low and RSI at that moment
    - Wait for price to drop below liq low
    - Check if RSI is HIGHER than at liquidation (bullish divergence)
    - Enter on divergence confirmation
    """

    # Optimizable parameters
    liquidation_threshold = 2000000
    lookback_bars = 1
    entry_below_pct = 2.0
    take_profit_pct = 6.0
    stop_loss_pct = 6.0
    order_expiry_bars = 576

    # RSI parameters
    rsi_period = 14
    min_rsi_divergence = 5  # RSI must be at least X points higher than at liq event

    position_size = 0.95

    def init(self):
        self.long_liq_volume = self.I(lambda: self.data.long_liq_volume)
        self.rolling_long_liq = self.I(
            lambda x: pd.Series(x).rolling(self.lookback_bars, min_periods=1).sum(),
            self.long_liq_volume
        )

        # RSI calculation
        def calc_rsi(close, period):
            close_series = pd.Series(close)
            delta = close_series.diff()
            gain = delta.where(delta > 0, 0).rolling(window=period, min_periods=1).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period, min_periods=1).mean()
            rs = gain / loss.replace(0, np.inf)
            rsi = 100 - (100 / (1 + rs))
            return rsi

        self.rsi = self.I(calc_rsi, self.data.Close, self.rsi_period)

        self.signal_active = False
        self.liquidation_low = 0
        self.liquidation_rsi = 0  # RSI at the liquidation event
        self.target_entry_price = 0
        self.signal_bar_count = 0
        self.actual_entry_price = 0

    def next(self):
        current_price = self.data.Close[-1]
        current_low = self.data.Low[-1]
        current_rolling_liq = self.rolling_long_liq[-1]
        current_rsi = self.rsi[-1]

        if np.isnan(current_rsi):
            return

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
            self.liquidation_rsi = current_rsi  # Record RSI at liquidation
            self.target_entry_price = self.liquidation_low * (1 - self.entry_below_pct / 100)
            self.signal_active = True
            self.signal_bar_count = 0

        # Check for entry
        if self.signal_active:
            self.signal_bar_count += 1

            if self.signal_bar_count >= self.order_expiry_bars:
                self._reset()
                return

            # Price at target - check for RSI bullish divergence
            if current_low <= self.target_entry_price:
                # Bullish divergence: price lower low, RSI higher low
                rsi_divergence = current_rsi - self.liquidation_rsi

                if rsi_divergence >= self.min_rsi_divergence:
                    # Divergence confirmed - ENTER
                    self.buy(size=self.position_size)
                    self.actual_entry_price = self.target_entry_price
                    self.signal_active = False

    def _reset(self):
        self.signal_active = False
        self.liquidation_low = 0
        self.liquidation_rsi = 0
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
        RevisitMomentumRsiDivergenceV2,
        cash=1000000,
        commission=0.001
    )

    baseline_stats = bt.run()

    print(f"\nMoon Dev's BASELINE RESULTS (RSI DIVERGENCE V2):")
    print(f"Liquidation Threshold: ${RevisitMomentumRsiDivergenceV2.liquidation_threshold:,}")
    print(f"Entry Below: {RevisitMomentumRsiDivergenceV2.entry_below_pct}%")
    print(f"Take Profit: {RevisitMomentumRsiDivergenceV2.take_profit_pct}%")
    print(f"Stop Loss: {RevisitMomentumRsiDivergenceV2.stop_loss_pct}%")
    print(f"RSI Period: {RevisitMomentumRsiDivergenceV2.rsi_period}")
    print(f"Min RSI Divergence: {RevisitMomentumRsiDivergenceV2.min_rsi_divergence}")
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
            min_rsi_divergence=[3, 5, 7, 10],
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
        print(f"Min RSI Divergence: {opt_stats._strategy.min_rsi_divergence}")

        bt.plot()

    except Exception as e:
        print(f"Optimization failed: {e}")
        bt.plot()
