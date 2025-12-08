"""
Double Dip Strategy - Moon Dev's Liquidation Bounce Play
=========================================================
Moon Dev's "Double Dip" Liquidation Strategy

Strategy Logic:
- BUY when LONG liquidations exceed threshold (e.g., $5M in last 5 minutes)
- Theory: After big long liquidations, price bounces back toward the SMA
- EXIT when price gets within X% of the 1-hour 40 SMA (bouncing up toward it)

Entry:
- Long liquidations > $5M (variable) in last 5 minutes (variable)
- Go LONG (buy the dip after forced long liquidations)

Exit:
- Close when price reaches within X% of the SMA (0.25%, 0.5%, 1%, etc.)
- Time-based exit after max hold hours
- NO stop loss, NO take profit - just SMA proximity and time exit

Variables to Optimize:
- liquidation_threshold: $5M default
- lookback_bars: How many 5-min bars to sum liquidations (1 bar = 5 min)
- sma_period: 40 (for 1-hour SMA on 5-min data, this would be 40 * 12 = 480 periods...
              but we'll let it be configurable)
- sma_distance_pct: 1% default - how close to SMA to exit
- max_hold_hours: Time-based exit

Moon Dev 🌙


LINE BACKTEST (Non-Optimized)
======================================================================

📊 Moon Dev's BASELINE RESULTS (DOUBLE DIP):
Liquidation Threshold: $1,000,000
Lookback Bars: 1 (5 minutes)
SMA Period: 12 bars (60 minutes)
SMA Distance Exit: 1.0%
Max Hold: 12 hours
--------------------------------------------------
Total Trades: 314
Win Rate: 28.66%
Return: -47.62%
Sharpe: 0.00
Max Drawdown: -49.34%

📈 FULL BASELINE STATS:
======================================================================
Start                     2024-06-04 12:50:00
End                       2025-12-05 12:45:00
Duration                    548 days 23:55:00
Exposure Time [%]                    0.519252
Equity Final [$]                 523805.94566
Equity Peak [$]                 1011101.11145
Return [%]                         -47.619405
Buy & Hold Return [%]               33.251745
Return (Ann.) [%]                  -34.810158
Volatility (Ann.) [%]               10.096174
Sharpe Ratio                              0.0
Sortino Ratio                             0.0
Calmar Ratio                              0.0
Max. Drawdown [%]                  -49.343613
Avg. Drawdown [%]                  -24.926502
Max. Drawdown Duration      541 days 00:05:00
Avg. Drawdown Duration      274 days 10:15:00
# Trades                                  314
Win Rate [%]                         28.66242
Best Trade [%]                       7.379505
Worst Trade [%]                    -15.500303
Avg. Trade [%]                      -0.227865
Max. Trade Duration           0 days 00:55:00
Avg. Trade Duration           0 days 00:09:00
Profit Factor                        0.446841
Expectancy [%]                      -0.220313
SQN                                 -3.765149
_strategy                   DoubleDipStrategy
_equity_curve                             ...
_trades                        Size  Entry...
dtype: object

======================================================================
RUNNING OPTIMIZATION - Moon Dev's Parameter Search
======================================================================
🔄 Optimizing parameters... This may take a few minutes...
                                                                   
✨ Moon Dev's OPTIMIZED RESULTS:
======================================================================
Start                     2024-06-04 12:50:00
End                       2025-12-05 12:45:00
Duration                    548 days 23:55:00
Exposure Time [%]                    0.234011
Equity Final [$]                1018070.44289
Equity Peak [$]                  1046514.6958
Return [%]                           1.807044
Buy & Hold Return [%]               33.251745
Return (Ann.) [%]                    1.195605
Volatility (Ann.) [%]                6.000835
Sharpe Ratio                          0.19924
Sortino Ratio                        0.348759
Calmar Ratio                          0.11173
Max. Drawdown [%]                  -10.700829
Avg. Drawdown [%]                   -3.102288
Max. Drawdown Duration      486 days 21:10:00
Avg. Drawdown Duration      102 days 16:02:00
# Trades                                   94
Win Rate [%]                        39.361702
Best Trade [%]                       4.261786
Worst Trade [%]                     -1.717561
Avg. Trade [%]                       0.017833
Max. Trade Duration           0 days 01:35:00
Avg. Trade Duration           0 days 00:15:00
Profit Factor                        1.081819
Expectancy [%]                        0.02152
SQN                                  0.240408
_strategy                 DoubleDipStrateg...
_equity_curve                             ...
_trades                       Size  EntryB...
dtype: object

🎯 OPTIMIZED PARAMETERS:
--------------------------------------------------
Liquidation Threshold: $4,000,000
Lookback Bars: 3 (15 minutes)
SMA Period: 24 bars (120 minutes)
SMA Distance Exit: 1.0%
Max Hold Hours: 2

📊 IMPROVEMENT SUMMARY:
--------------------------------------------------
Baseline Return: -47.62%
Optimized Return: 1.81%
Improvement: 49.43%

"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
from backtesting.lib import crossover
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's DOUBLE DIP Strategy 🌙")
print("Theory: Buy the dip after long liquidations, exit near the SMA bounce")
print("=" * 70)

# Data configuration
# Load preprocessed BTC data - 5-minute timeframe
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/moondev_api/liq_data_BTC_5m_ohlcv.csv'
timeframe = '5-minute'

print(f"📊 Loading preprocessed {timeframe} BTC liquidation data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)

# Data already has proper columns from preprocessing
print(f"✅ Loaded {len(data):,} {timeframe} bars")
print(f"📊 Data columns: {list(data.columns)}")

# Map liquidation columns to match strategy expectations
if 'long_liquidations' in data.columns and 'short_liquidations' in data.columns:
    data['long_liq_volume'] = data['long_liquidations']
    data['short_liq_volume'] = data['short_liquidations']
    data['net_liq_volume'] = data['short_liquidations'] - data['long_liquidations']
    data['total_liq_count'] = data['liquidation_count'] if 'liquidation_count' in data.columns else 0
    data['long_liq_count'] = (data['long_liquidations'] > 0).astype(int)
    data['short_liq_count'] = (data['short_liquidations'] > 0).astype(int)
else:
    # Create empty liquidation columns if they don't exist
    print("⚠️ Warning: Liquidation columns not found, creating empty columns")
    data['long_liq_volume'] = 0
    data['short_liq_volume'] = 0
    data['net_liq_volume'] = 0
    data['total_liq_count'] = 0
    data['long_liq_count'] = 0
    data['short_liq_count'] = 0


class DoubleDipStrategy(Strategy):
    """
    Moon Dev's Double Dip Strategy

    Entry Logic:
    - BUY when long liquidation volume (summed over lookback_bars) exceeds threshold
    - Only go LONG - we're buying the dip after forced long liquidations

    Exit Logic:
    - Close when price gets within sma_distance_pct of the SMA
    - Time-based exit after max_hold_hours
    - NO stop loss, NO take profit
    """

    # Optimizable parameters
    liquidation_threshold = 1000000  # $5M minimum long liquidation volume to trigger
    lookback_bars = 1  # How many 5-min bars to sum (1 = just current bar = 5 min)
    sma_period = 12  # SMA period (12 * 5min = 1 hour)
    sma_distance_pct = 1.0  # Exit when within 1% of SMA
    max_hold_hours = 12  # Maximum holding period

    # Position sizing
    position_size = 0.95  # Use 95% of available capital

    def init(self):
        """Initialize strategy indicators"""
        # Moon Dev's Double Dip Strategy Init

        # Store liquidation volumes as indicators
        self.long_liq_volume = self.I(lambda: self.data.long_liq_volume)

        # Calculate rolling sum of long liquidations over lookback period
        self.rolling_long_liq = self.I(
            lambda x: pd.Series(x).rolling(self.lookback_bars, min_periods=1).sum(),
            self.long_liq_volume
        )

        # Calculate SMA for exit signal
        self.sma = self.I(
            lambda x: pd.Series(x).rolling(self.sma_period, min_periods=1).mean(),
            self.data.Close
        )

    def next(self):
        """Main strategy logic - Double Dip approach"""

        current_price = self.data.Close[-1]
        current_sma = self.sma[-1]
        current_rolling_liq = self.rolling_long_liq[-1]

        # Skip if SMA not ready
        if np.isnan(current_sma):
            return

        # Calculate distance from SMA (as percentage)
        distance_from_sma = ((current_sma - current_price) / current_sma) * 100

        # Entry logic - BUY on big long liquidations
        if not self.position:

            # BUY when long liquidations exceed threshold
            # (Long liquidations = longs getting stopped out = price dropping = buy the dip)
            if current_rolling_liq >= self.liquidation_threshold:
                self.buy(size=self.position_size)

        # Exit logic
        else:
            # Check time-based exit first
            if len(self.trades) > 0:
                entry_time = self.trades[-1].entry_time
                current_time = self.data.index[-1]
                hours_held = (current_time - entry_time).total_seconds() / 3600

                if hours_held >= self.max_hold_hours:
                    self.position.close()
                    return

            # Check SMA proximity exit
            # We're long, so we want price to bounce UP toward SMA
            # Exit when price gets within sma_distance_pct of SMA
            # distance_from_sma > 0 means price is below SMA (which is expected after a dip)
            # As price bounces up, distance decreases
            # Exit when abs(distance) <= sma_distance_pct
            if abs(distance_from_sma) <= self.sma_distance_pct:
                self.position.close()


# Run backtest with baseline parameters
print("\n" + "="*70)
print("RUNNING BASELINE BACKTEST (Non-Optimized)")
print("="*70)

if len(data) > 100:
    bt = Backtest(
        data[['Open', 'High', 'Low', 'Close', 'Volume', 'long_liq_volume', 'short_liq_volume', 'net_liq_volume']],
        DoubleDipStrategy,
        cash=1000000,
        commission=0.001
    )

    # Run baseline
    baseline_stats = bt.run()

    print(f"\n📊 Moon Dev's BASELINE RESULTS (DOUBLE DIP):")
    print(f"Liquidation Threshold: ${DoubleDipStrategy.liquidation_threshold:,}")
    print(f"Lookback Bars: {DoubleDipStrategy.lookback_bars} ({DoubleDipStrategy.lookback_bars * 5} minutes)")
    print(f"SMA Period: {DoubleDipStrategy.sma_period} bars ({DoubleDipStrategy.sma_period * 5} minutes)")
    print(f"SMA Distance Exit: {DoubleDipStrategy.sma_distance_pct}%")
    print(f"Max Hold: {DoubleDipStrategy.max_hold_hours} hours")
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
            liquidation_threshold=range(1000000, 10000000, 1000000),  # $1M to $10M in $1M steps
            lookback_bars=[1, 2, 3],  # 5min to 30min lookback
            sma_period=[12, 24, 36],  # 1hr, 2hr, 3hr, 4hr SMA (on 5min data)
            sma_distance_pct=[0.5, 0.75, 1.0],  # Exit distance from SMA
            max_hold_hours=[2, 4, 6],  # Max hold time
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
        print(f"SMA Distance Exit: {optimization_results._strategy.sma_distance_pct}%")
        print(f"Max Hold Hours: {optimization_results._strategy.max_hold_hours}")

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
        print("Try adjusting the parameter ranges or using more data.")

        # Still show the baseline plot
        bt.plot()

else:
    print("❌ Insufficient data for backtesting")
