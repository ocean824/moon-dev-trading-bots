"""
SMA Rejection Strategy - Moon Dev's Rebound Short Play
=======================================================
Moon Dev's "SMA Rejection" Liquidation Strategy

Strategy Logic:
1. Wait for big LONG liquidation event (price dumps)
2. DON'T buy the dip - instead WAIT for price to rebound
3. When price rebounds to within X% of the SMA -> SHORT
4. Theory: After big liquidation, price bounces but then rejects at SMA and continues down

Entry:
- Long liquidations > threshold (signal to watch)
- Wait for price to rebound to within X% of SMA
- Then SHORT (expecting rejection and continuation down)

Exit:
- Take profit at X% (2% default)
- Stop loss at Y% (3% default)

Variables to Optimize:
- liquidation_threshold: Entry trigger
- lookback_bars: How many 5-min bars to sum liquidations
- sma_period: SMA period (12 = 1 hour on 5min data)
- sma_distance_pct: How close to SMA before shorting (0.5% default)
- take_profit_pct: 2% default
- stop_loss_pct: 3% default
- signal_expiry_bars: How long the liquidation signal stays valid

Moon Dev 🌙
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's SMA REJECTION Strategy 🌙")
print("Theory: Wait for liquidation, wait for rebound to SMA, then SHORT the rejection")
print("=" * 70)

# Data configuration
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/moondev_api/liq_data_BTC_5m_ohlcv.csv'
timeframe = '5-minute'

print(f"📊 Loading preprocessed {timeframe} BTC liquidation data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)

print(f"✅ Loaded {len(data):,} {timeframe} bars")
print(f"📊 Data columns: {list(data.columns)}")

# Map liquidation columns
if 'long_liquidations' in data.columns and 'short_liquidations' in data.columns:
    data['long_liq_volume'] = data['long_liquidations']
    data['short_liq_volume'] = data['short_liquidations']
    data['net_liq_volume'] = data['short_liquidations'] - data['long_liquidations']
else:
    print("⚠️ Warning: Liquidation columns not found, creating empty columns")
    data['long_liq_volume'] = 0
    data['short_liq_volume'] = 0
    data['net_liq_volume'] = 0


class SmaRejectionStrategy(Strategy):
    """
    Moon Dev's SMA Rejection Strategy

    Entry Logic:
    - Detect big long liquidation (signal armed)
    - Wait for price to rebound to within sma_distance_pct of SMA
    - SHORT when price reaches SMA zone (expecting rejection)

    Exit Logic:
    - Take profit at X%
    - Stop loss at Y%
    """

    # Optimizable parameters
    liquidation_threshold = 1000000  # $1M minimum long liquidation volume
    lookback_bars = 1  # How many 5-min bars to sum
    sma_period = 12  # 12 * 5min = 1 hour SMA
    sma_distance_pct = 0.5  # Short when price within 0.5% of SMA
    take_profit_pct = 2.0  # 2% take profit
    stop_loss_pct = 3.0  # 3% stop loss
    signal_expiry_bars = 72  # Signal expires after 72 bars (6 hours on 5min data)

    # Position sizing
    position_size = 0.95

    def init(self):
        """Initialize strategy indicators"""
        # Moon Dev's SMA Rejection Strategy Init

        self.long_liq_volume = self.I(lambda: self.data.long_liq_volume)

        self.rolling_long_liq = self.I(
            lambda x: pd.Series(x).rolling(self.lookback_bars, min_periods=1).sum(),
            self.long_liq_volume
        )

        # Calculate SMA
        self.sma = self.I(
            lambda x: pd.Series(x).rolling(self.sma_period, min_periods=1).mean(),
            self.data.Close
        )

        # Track if we have an active liquidation signal waiting for SMA touch
        self.signal_armed = False
        self.signal_bar_count = 0

    def next(self):
        """Main strategy logic - SMA Rejection approach"""

        current_price = self.data.Close[-1]
        current_sma = self.sma[-1]
        current_rolling_liq = self.rolling_long_liq[-1]

        # Skip if SMA not ready
        if np.isnan(current_sma):
            return

        # Calculate distance from SMA (as percentage)
        # Positive = price below SMA, Negative = price above SMA
        distance_from_sma_pct = ((current_sma - current_price) / current_sma) * 100

        # Not in position - look for entry
        if not self.position:

            # Check for new liquidation signal
            if current_rolling_liq >= self.liquidation_threshold:
                self.signal_armed = True
                self.signal_bar_count = 0

            # If signal is armed, wait for price to rebound to SMA
            if self.signal_armed:
                self.signal_bar_count += 1

                # Signal expired
                if self.signal_bar_count >= self.signal_expiry_bars:
                    self.signal_armed = False
                    self.signal_bar_count = 0

                # Price has rebounded to within X% of SMA - SHORT!
                # We want price to be close to SMA (small distance)
                elif abs(distance_from_sma_pct) <= self.sma_distance_pct:
                    # Calculate SL and TP prices for SHORT
                    entry_price = current_price
                    sl_price = entry_price * (1 + self.stop_loss_pct / 100)  # SL above for short
                    tp_price = entry_price * (1 - self.take_profit_pct / 100)  # TP below for short

                    self.sell(size=self.position_size, sl=sl_price, tp=tp_price)
                    self.signal_armed = False
                    self.signal_bar_count = 0


# Run backtest with baseline parameters
print("\n" + "="*70)
print("RUNNING BASELINE BACKTEST (Non-Optimized)")
print("="*70)

if len(data) > 100:
    bt = Backtest(
        data[['Open', 'High', 'Low', 'Close', 'Volume', 'long_liq_volume', 'short_liq_volume', 'net_liq_volume']],
        SmaRejectionStrategy,
        cash=1000000,
        commission=0.001
    )

    # Run baseline
    baseline_stats = bt.run()

    print(f"\n📊 Moon Dev's BASELINE RESULTS (SMA REJECTION):")
    print(f"Liquidation Threshold: ${SmaRejectionStrategy.liquidation_threshold:,}")
    print(f"Lookback Bars: {SmaRejectionStrategy.lookback_bars} ({SmaRejectionStrategy.lookback_bars * 5} minutes)")
    print(f"SMA Period: {SmaRejectionStrategy.sma_period} bars ({SmaRejectionStrategy.sma_period * 5} minutes)")
    print(f"SMA Distance to Short: {SmaRejectionStrategy.sma_distance_pct}%")
    print(f"Take Profit: {SmaRejectionStrategy.take_profit_pct}%")
    print(f"Stop Loss: {SmaRejectionStrategy.stop_loss_pct}%")
    print(f"Signal Expiry: {SmaRejectionStrategy.signal_expiry_bars} bars ({SmaRejectionStrategy.signal_expiry_bars * 5 / 60:.1f} hours)")
    print("-" * 50)
    print(f"Total Trades: {baseline_stats['# Trades']}")
    print(f"Win Rate: {baseline_stats['Win Rate [%]']:.2f}%")
    print(f"Return: {baseline_stats['Return [%]']:.2f}%")
    print(f"Sharpe: {baseline_stats['Sharpe Ratio']:.2f}")
    print(f"Max Drawdown: {baseline_stats['Max. Drawdown [%]']:.2f}%")

    print("\n📈 FULL BASELINE STATS:")
    print("="*70)
    print(baseline_stats)

    # Run optimization
    print("\n" + "="*70)
    print("RUNNING OPTIMIZATION - Moon Dev's Parameter Search")
    print("="*70)
    print("🔄 Optimizing parameters... This may take a few minutes...")

    try:
        optimization_results = bt.optimize(
            liquidation_threshold=range(500000, 3000000, 500000),  # $500k to $3M
            lookback_bars=[1, 2, 3],  # 5min to 15min lookback
            sma_period=[12, 24, 36],  # 1hr, 2hr, 3hr SMA
            sma_distance_pct=[0.25, 0.5, 0.75, 1.0],  # Distance from SMA to trigger
            take_profit_pct=[1.5, 2.0, 2.5, 3.0],  # TP options
            stop_loss_pct=[2.0, 3.0, 4.0, 5.0],  # SL options
            maximize='Return [%]',
            return_heatmap=False
        )

        print("\n✨ Moon Dev's OPTIMIZED RESULTS:")
        print("="*70)
        print(optimization_results)

        # Extract and display optimized parameters
        print("\n🎯 OPTIMIZED PARAMETERS:")
        print("-" * 50)
        print(f"Liquidation Threshold: ${optimization_results._strategy.liquidation_threshold:,}")
        print(f"Lookback Bars: {optimization_results._strategy.lookback_bars} ({optimization_results._strategy.lookback_bars * 5} minutes)")
        print(f"SMA Period: {optimization_results._strategy.sma_period} bars ({optimization_results._strategy.sma_period * 5} minutes)")
        print(f"SMA Distance to Short: {optimization_results._strategy.sma_distance_pct}%")
        print(f"Take Profit: {optimization_results._strategy.take_profit_pct}%")
        print(f"Stop Loss: {optimization_results._strategy.stop_loss_pct}%")

        # Compare baseline vs optimized
        print("\n📊 IMPROVEMENT SUMMARY:")
        print("-" * 50)
        baseline_return = baseline_stats['Return [%]']
        optimized_return = optimization_results['Return [%]']
        print(f"Baseline Return: {baseline_return:.2f}%")
        print(f"Optimized Return: {optimized_return:.2f}%")
        print(f"Improvement: {optimized_return - baseline_return:.2f}%")

        # Show the plot
        bt.plot()

    except Exception as e:
        print(f"\n⚠️ Optimization failed: {str(e)}")
        print("This may happen if there aren't enough trades with the current parameter ranges.")

        # Still show the baseline plot
        bt.plot()

else:
    print("❌ Insufficient data for backtesting")
