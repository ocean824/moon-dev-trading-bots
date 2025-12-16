"""
Revisit Momentum STOCHASTIC RSI V2 - Moon Dev
==============================================
Based on revisit_momentum (the best performer)

VARIATION: Use Stochastic RSI instead of regular RSI
- Stoch RSI is more sensitive to momentum shifts
- Better at catching exact bottoms
- K and D lines provide crossover signals

Theory: Stoch RSI catches momentum reversals faster than regular RSI

Moon Dev
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print("Moon Dev's REVISIT MOMENTUM STOCHASTIC RSI V2")
print("Variation: Stochastic RSI for faster momentum detection")
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


class RevisitMomentumStochRsiV2(Strategy):
    """
    Revisit Momentum with Stochastic RSI V2

    - Detect liquidation, record low
    - Wait for price to drop below liq low
    - Use Stochastic RSI for momentum confirmation
    - Enter when Stoch RSI K crosses above D from oversold

    Stochastic RSI Formula:
    1. Calculate RSI
    2. Apply Stochastic formula to RSI: (RSI - lowest RSI) / (highest RSI - lowest RSI)
    3. Smooth with K and D periods
    """

    # Optimizable parameters
    liquidation_threshold = 2000000
    lookback_bars = 1
    entry_below_pct = 2.0
    take_profit_pct = 6.0
    stop_loss_pct = 6.0
    order_expiry_bars = 576

    # Stochastic RSI parameters
    rsi_period = 14
    stoch_period = 14
    k_period = 3
    d_period = 3
    stoch_oversold = 20  # Stoch RSI oversold level

    position_size = 0.95

    def init(self):
        self.long_liq_volume = self.I(lambda: self.data.long_liq_volume)
        self.rolling_long_liq = self.I(
            lambda x: pd.Series(x).rolling(self.lookback_bars, min_periods=1).sum(),
            self.long_liq_volume
        )

        # Stochastic RSI calculation
        def calc_stoch_rsi_k(close, rsi_period, stoch_period, k_period):
            close_series = pd.Series(close)

            # Calculate RSI
            delta = close_series.diff()
            gain = delta.where(delta > 0, 0).rolling(window=rsi_period, min_periods=1).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period, min_periods=1).mean()
            rs = gain / loss.replace(0, np.inf)
            rsi = 100 - (100 / (1 + rs))

            # Calculate Stochastic RSI
            rsi_min = rsi.rolling(window=stoch_period, min_periods=1).min()
            rsi_max = rsi.rolling(window=stoch_period, min_periods=1).max()
            stoch_rsi = (rsi - rsi_min) / (rsi_max - rsi_min + 0.0001) * 100

            # Smooth with K period
            stoch_rsi_k = stoch_rsi.rolling(window=k_period, min_periods=1).mean()

            return stoch_rsi_k

        def calc_stoch_rsi_d(close, rsi_period, stoch_period, k_period, d_period):
            close_series = pd.Series(close)

            # Calculate RSI
            delta = close_series.diff()
            gain = delta.where(delta > 0, 0).rolling(window=rsi_period, min_periods=1).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period, min_periods=1).mean()
            rs = gain / loss.replace(0, np.inf)
            rsi = 100 - (100 / (1 + rs))

            # Calculate Stochastic RSI
            rsi_min = rsi.rolling(window=stoch_period, min_periods=1).min()
            rsi_max = rsi.rolling(window=stoch_period, min_periods=1).max()
            stoch_rsi = (rsi - rsi_min) / (rsi_max - rsi_min + 0.0001) * 100

            # Smooth with K period then D period
            stoch_rsi_k = stoch_rsi.rolling(window=k_period, min_periods=1).mean()
            stoch_rsi_d = stoch_rsi_k.rolling(window=d_period, min_periods=1).mean()

            return stoch_rsi_d

        self.stoch_rsi_k = self.I(calc_stoch_rsi_k, self.data.Close, self.rsi_period, self.stoch_period, self.k_period)
        self.stoch_rsi_d = self.I(calc_stoch_rsi_d, self.data.Close, self.rsi_period, self.stoch_period, self.k_period, self.d_period)

        self.signal_active = False
        self.liquidation_low = 0
        self.target_entry_price = 0
        self.signal_bar_count = 0
        self.actual_entry_price = 0

    def next(self):
        current_price = self.data.Close[-1]
        current_low = self.data.Low[-1]
        current_rolling_liq = self.rolling_long_liq[-1]
        current_k = self.stoch_rsi_k[-1]
        current_d = self.stoch_rsi_d[-1]

        # Previous bar for crossover detection
        prev_k = self.stoch_rsi_k[-2] if len(self.stoch_rsi_k) > 1 else current_k
        prev_d = self.stoch_rsi_d[-2] if len(self.stoch_rsi_d) > 1 else current_d

        if np.isnan(current_k) or np.isnan(current_d):
            return

        # Stochastic RSI momentum confirmation:
        # K crosses above D from oversold zone
        stoch_oversold = current_k <= self.stoch_oversold or prev_k <= self.stoch_oversold
        k_crosses_above_d = (prev_k < prev_d) and (current_k >= current_d)
        momentum_confirmed = stoch_oversold and k_crosses_above_d

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

            # Price at target AND Stoch RSI confirms momentum
            if current_low <= self.target_entry_price and momentum_confirmed:
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
print("RUNNING BASELINE BACKTEST (Non-Optimized)")
print("="*70)

if len(data) > 100:
    bt = Backtest(
        data[['Open', 'High', 'Low', 'Close', 'Volume', 'long_liq_volume', 'short_liq_volume', 'net_liq_volume']],
        RevisitMomentumStochRsiV2,
        cash=1000000,
        commission=0.001
    )

    baseline_stats = bt.run()

    print(f"\nMoon Dev's BASELINE RESULTS (STOCHASTIC RSI V2):")
    print(f"Liquidation Threshold: ${RevisitMomentumStochRsiV2.liquidation_threshold:,}")
    print(f"Entry Below: {RevisitMomentumStochRsiV2.entry_below_pct}%")
    print(f"Take Profit: {RevisitMomentumStochRsiV2.take_profit_pct}%")
    print(f"Stop Loss: {RevisitMomentumStochRsiV2.stop_loss_pct}%")
    print(f"RSI Period: {RevisitMomentumStochRsiV2.rsi_period}")
    print(f"Stoch Period: {RevisitMomentumStochRsiV2.stoch_period}")
    print(f"Stoch Oversold: {RevisitMomentumStochRsiV2.stoch_oversold}")
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
            stoch_oversold=[15, 20, 25, 30],
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
        print(f"Stoch Oversold: {opt_stats._strategy.stoch_oversold}")

        bt.plot()

    except Exception as e:
        print(f"Optimization failed: {e}")
        bt.plot()
