"""
Time Exit Liquidation Strategy - Moon Dev's Pure Time-Based Exit
=================================================================
Moon Dev's Time Exit Liquidation Strategy

Strategy Logic:
- BUY when LONG liquidations exceed threshold (e.g., $1M)
- EXIT purely based on time - hold for X hours then close
- NO stop loss, NO take profit, NO SMA - just time

Entry:
- Long liquidations > $1M (variable)
- Go LONG (buy the dip after forced long liquidations)

Exit:
- Time-based exit only after X hours (20, 24, 28 hours tested)
- NO stop loss, NO take profit

Variables to Optimize:
- liquidation_threshold: $1M default
- lookback_bars: How many 5-min bars to sum liquidations
- hold_hours: 20, 24, 28 hours

Moon Dev 🌙

==========================================
RUNNING BASELINE BACKTEST (Non-Optimized)
======================================================================

📊 Moon Dev's BASELINE RESULTS (TIME EXIT):
Liquidation Threshold: $1,000,000
Lookback Bars: 1 (5 minutes)
Hold Hours: 24 hours
--------------------------------------------------
Total Trades: 175
Win Rate: 42.86%
Return: -41.00%
Sharpe: 0.00
Max Drawdown: -53.96%

📈 FULL BASELINE STATS:
======================================================================
Start                     2024-06-04 12:50:00
End                       2025-12-05 12:45:00
Duration                    548 days 23:55:00
Exposure Time [%]                   32.097501
Equity Final [$]                 589986.55083
Equity Peak [$]                 1254667.54538
Return [%]                         -41.001345
Buy & Hold Return [%]               33.251745
Return (Ann.) [%]                  -29.283836
Volatility (Ann.) [%]                22.25359
Sharpe Ratio                              0.0
Sortino Ratio                             0.0
Calmar Ratio                              0.0
Max. Drawdown [%]                  -53.961019
Avg. Drawdown [%]                   -3.490154
Max. Drawdown Duration      356 days 11:20:00
Avg. Drawdown Duration       10 days 18:13:00
# Trades                                  175
Win Rate [%]                        42.857143
Best Trade [%]                       6.789125
Worst Trade [%]                    -14.345877
Avg. Trade [%]                      -0.356448
Max. Trade Duration           1 days 00:05:00
Avg. Trade Duration           1 days 00:05:00
Profit Factor                        0.744042
Expectancy [%]                      -0.313576
SQN                                 -1.222298
_strategy                 TimeExitLiqStrategy
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
Exposure Time [%]                    9.795588
Equity Final [$]                1012506.44215
Equity Peak [$]                 1074950.69244
Return [%]                           1.250644
Buy & Hold Return [%]               33.251745
Return (Ann.) [%]                    0.828237
Volatility (Ann.) [%]               16.527919
Sharpe Ratio                         0.050111
Sortino Ratio                         0.08482
Calmar Ratio                         0.032758
Max. Drawdown [%]                   -25.28364
Avg. Drawdown [%]                   -6.042195
Max. Drawdown Duration      272 days 21:55:00
Avg. Drawdown Duration       48 days 16:55:00
# Trades                                   64
Win Rate [%]                           40.625
Best Trade [%]                       6.613351
Worst Trade [%]                     -3.754081
Avg. Trade [%]                       0.022366
Max. Trade Duration           0 days 20:05:00
Avg. Trade Duration           0 days 20:05:00
Profit Factor                        1.052541
Expectancy [%]                       0.052674
SQN                                   0.07155
_strategy                 TimeExitLiqStrat...
_equity_curve                             ...
_trades                       Size  EntryB...
dtype: object

🎯 OPTIMIZED PARAMETERS:
--------------------------------------------------
Liquidation Threshold: $4,000,000
Lookback Bars: 6 (30 minutes)
Hold Hours: 20 hours

📊 IMPROVEMENT SUMMARY:
--------------------------------------------------
Baseline Return: -41.00%
Optimized Return: 1.25%
Improvement: 42.25%
(tflow) md@mds-MacBook-Pro moon-dev-trading-bots %
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's TIME EXIT Liquidation Strategy 🌙")
print("Theory: Buy the dip after long liquidations, exit purely on time")
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
else:
    print("⚠️ Warning: Liquidation columns not found, creating empty columns")
    data['long_liq_volume'] = 0
    data['short_liq_volume'] = 0
    data['net_liq_volume'] = 0


class TimeExitLiqStrategy(Strategy):
    """
    Moon Dev's Time Exit Liquidation Strategy

    Entry Logic:
    - BUY when long liquidation volume (summed over lookback_bars) exceeds threshold
    - Only go LONG - we're buying the dip after forced long liquidations

    Exit Logic:
    - Time-based exit ONLY after hold_hours
    - NO stop loss, NO take profit
    """

    # Optimizable parameters
    liquidation_threshold = 1000000  # $1M minimum long liquidation volume to trigger
    lookback_bars = 1  # How many 5-min bars to sum (1 = just current bar = 5 min)
    hold_hours = 24  # Hold for exactly this many hours then exit

    # Position sizing
    position_size = 0.95  # Use 95% of available capital

    def init(self):
        """Initialize strategy indicators"""
        # Moon Dev's Time Exit Strategy Init

        # Store liquidation volumes as indicators
        self.long_liq_volume = self.I(lambda: self.data.long_liq_volume)

        # Calculate rolling sum of long liquidations over lookback period
        self.rolling_long_liq = self.I(
            lambda x: pd.Series(x).rolling(self.lookback_bars, min_periods=1).sum(),
            self.long_liq_volume
        )

    def next(self):
        """Main strategy logic - Time Exit approach"""

        current_rolling_liq = self.rolling_long_liq[-1]

        # Entry logic - BUY on big long liquidations
        if not self.position:

            # BUY when long liquidations exceed threshold
            if current_rolling_liq >= self.liquidation_threshold:
                self.buy(size=self.position_size)

        # Exit logic - TIME ONLY
        else:
            if len(self.trades) > 0:
                entry_time = self.trades[-1].entry_time
                current_time = self.data.index[-1]
                hours_held = (current_time - entry_time).total_seconds() / 3600

                if hours_held >= self.hold_hours:
                    self.position.close()


# Run backtest with baseline parameters
print("\n" + "="*70)
print("RUNNING BASELINE BACKTEST (Non-Optimized)")
print("="*70)

if len(data) > 100:
    bt = Backtest(
        data[['Open', 'High', 'Low', 'Close', 'Volume', 'long_liq_volume', 'short_liq_volume', 'net_liq_volume']],
        TimeExitLiqStrategy,
        cash=1000000,
        commission=0.001
    )

    # Run baseline
    baseline_stats = bt.run()

    print(f"\n📊 Moon Dev's BASELINE RESULTS (TIME EXIT):")
    print(f"Liquidation Threshold: ${TimeExitLiqStrategy.liquidation_threshold:,}")
    print(f"Lookback Bars: {TimeExitLiqStrategy.lookback_bars} ({TimeExitLiqStrategy.lookback_bars * 5} minutes)")
    print(f"Hold Hours: {TimeExitLiqStrategy.hold_hours} hours")
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
            liquidation_threshold=range(500000, 5000000, 500000),  # $500k to $5M in $500k steps
            lookback_bars=[1, 2, 3, 4, 5, 6],  # 5min to 30min lookback
            hold_hours=[20, 24, 28],  # Time exit options
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
        print(f"Hold Hours: {optimization_results._strategy.hold_hours} hours")

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
