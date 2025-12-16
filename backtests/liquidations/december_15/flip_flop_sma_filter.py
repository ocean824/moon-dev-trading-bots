"""
Flip Flop SMA FILTER Variation - Moon Dev
==========================================
Based on the winning Flip Flop strategy (529% return)

VARIATION: Add SMA filter to only take trades in trend direction
- Only BUY the dip if price is ABOVE the SMA (uptrend)
- Only FLIP to SHORT if price is BELOW the SMA (downtrend)

Theory: Filter out counter-trend trades for higher win rate

Moon Dev 🌙
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's FLIP FLOP SMA FILTER Strategy 🌙")
print("Variation: SMA trend filter for entries")
print("=" * 70)

# Data configuration
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/moondev_api/liq_data_BTC_5m_ohlcv.csv'
timeframe = '5-minute'

print(f"📊 Loading preprocessed {timeframe} BTC liquidation data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)

print(f"✅ Loaded {len(data):,} {timeframe} bars")

# Map liquidation columns
if 'long_liquidations' in data.columns and 'short_liquidations' in data.columns:
    data['long_liq_volume'] = data['long_liquidations']
    data['short_liq_volume'] = data['short_liquidations']
    data['net_liq_volume'] = data['short_liquidations'] - data['long_liquidations']
else:
    data['long_liq_volume'] = 0
    data['short_liq_volume'] = 0
    data['net_liq_volume'] = 0


class FlipFlopSmaFilterStrategy(Strategy):
    """
    Flip Flop with SMA Filter

    - Only buy if price > SMA (uptrend context)
    - Only flip to short if price < SMA (downtrend context)
    - Same TP/SL logic as original
    """

    # Optimizable parameters
    liquidation_threshold = 500000
    lookback_bars = 3
    take_profit_pct = 1.5
    stop_loss_pct = 10.0
    sma_period = 50  # SMA for trend filter

    position_size = 0.95

    def init(self):
        self.long_liq_volume = self.I(lambda: self.data.long_liq_volume)
        self.rolling_long_liq = self.I(
            lambda x: pd.Series(x).rolling(self.lookback_bars, min_periods=1).sum(),
            self.long_liq_volume
        )

        # SMA for trend filter
        self.sma = self.I(
            lambda x: pd.Series(x).rolling(self.sma_period, min_periods=1).mean(),
            self.data.Close
        )

        self.state = 'waiting'
        self.entry_price = 0

    def next(self):
        current_price = self.data.Close[-1]
        current_sma = self.sma[-1]
        current_rolling_liq = self.rolling_long_liq[-1]

        if np.isnan(current_sma):
            return

        price_above_sma = current_price > current_sma

        # STATE: WAITING
        if self.state == 'waiting':
            if not self.position:
                # Only buy if price above SMA (uptrend) AND liquidation signal
                if current_rolling_liq >= self.liquidation_threshold and price_above_sma:
                    self.buy(size=self.position_size)
                    self.entry_price = current_price
                    self.state = 'long'

        # STATE: LONG
        elif self.state == 'long':
            if self.position and self.position.is_long:
                pnl_pct = ((current_price - self.entry_price) / self.entry_price) * 100

                # Take profit - flip to short only if price below SMA
                if pnl_pct >= self.take_profit_pct:
                    self.position.close()
                    # Only flip to short if price is below SMA (downtrend)
                    if not price_above_sma:
                        self.sell(size=self.position_size)
                        self.entry_price = current_price
                        self.state = 'short'
                    else:
                        # Don't flip, just take profit and wait
                        self.state = 'waiting'
                        self.entry_price = 0

                # Stop loss - flip to short only if price below SMA
                elif pnl_pct <= -self.stop_loss_pct:
                    self.position.close()
                    if not price_above_sma:
                        self.sell(size=self.position_size)
                        self.entry_price = current_price
                        self.state = 'short'
                    else:
                        self.state = 'waiting'
                        self.entry_price = 0

            elif not self.position:
                self.state = 'waiting'
                self.entry_price = 0

        # STATE: SHORT
        elif self.state == 'short':
            if self.position and self.position.is_short:
                pnl_pct = ((self.entry_price - current_price) / self.entry_price) * 100

                if pnl_pct >= self.take_profit_pct:
                    self.position.close()
                    self.state = 'waiting'
                    self.entry_price = 0

                elif pnl_pct <= -self.stop_loss_pct:
                    self.position.close()
                    self.state = 'waiting'
                    self.entry_price = 0

            elif not self.position:
                self.state = 'waiting'
                self.entry_price = 0


# Run backtest
print("\n" + "="*70)
print("RUNNING BASELINE BACKTEST (Non-Optimized)")
print("="*70)

if len(data) > 100:
    bt = Backtest(
        data[['Open', 'High', 'Low', 'Close', 'Volume', 'long_liq_volume', 'short_liq_volume', 'net_liq_volume']],
        FlipFlopSmaFilterStrategy,
        cash=1000000,
        commission=0.001
    )

    baseline_stats = bt.run()

    print(f"\n📊 Moon Dev's BASELINE RESULTS (FLIP FLOP SMA FILTER):")
    print(f"Liquidation Threshold: ${FlipFlopSmaFilterStrategy.liquidation_threshold:,}")
    print(f"Lookback Bars: {FlipFlopSmaFilterStrategy.lookback_bars}")
    print(f"Take Profit: {FlipFlopSmaFilterStrategy.take_profit_pct}%")
    print(f"Stop Loss: {FlipFlopSmaFilterStrategy.stop_loss_pct}%")
    print(f"SMA Period: {FlipFlopSmaFilterStrategy.sma_period}")
    print("-" * 50)
    print(f"Total Trades: {baseline_stats['# Trades']}")
    print(f"Win Rate: {baseline_stats['Win Rate [%]']:.2f}%")
    print(f"Return: {baseline_stats['Return [%]']:.2f}%")
    print(f"Sharpe: {baseline_stats['Sharpe Ratio']:.2f}")
    print(f"Max Drawdown: {baseline_stats['Max. Drawdown [%]']:.2f}%")

    print("\n📈 FULL BASELINE STATS:")
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
            sma_period=[20, 50, 100, 200],
            maximize='Return [%]',
            return_heatmap=False
        )

        print("\n✨ OPTIMIZED RESULTS:")
        print("="*70)
        print(opt_stats)

        print("\n🎯 OPTIMIZED PARAMETERS:")
        print("-" * 50)
        print(f"Liquidation Threshold: ${opt_stats._strategy.liquidation_threshold:,}")
        print(f"Lookback Bars: {opt_stats._strategy.lookback_bars}")
        print(f"Take Profit: {opt_stats._strategy.take_profit_pct}%")
        print(f"Stop Loss: {opt_stats._strategy.stop_loss_pct}%")
        print(f"SMA Period: {opt_stats._strategy.sma_period}")

        bt.plot()

    except Exception as e:
        print(f"⚠️ Optimization failed: {e}")
        bt.plot()
