"""
Flip Flop Strategy - Moon Dev's Long-to-Short Liquidation Play
===============================================================
Moon Dev's "Flip Flop" Liquidation Strategy

Strategy Logic:
1. BUY when LONG liquidations exceed threshold (buy the dip)
2. When LONG hits take profit, FLIP to SHORT (double sell to go short)
3. Hold SHORT until it hits take profit
4. Done - two trades per signal

Entry:
- Long liquidations > threshold
- Go LONG first (buy the dip after forced long liquidations)

Exit/Flip:
- LONG: Take profit at X% (1.5%, 2%, 2.5%), Stop loss at Y% (5%, 7.5%, 10%)
- When LONG TP hits -> FLIP to SHORT (sell 2x to go from long to short)
- SHORT: Take profit at X% (same), Stop loss at Y% (same)

Variables to Optimize:
- liquidation_threshold: Entry trigger
- lookback_bars: How many 5-min bars to sum liquidations

- take_profit_pct: 1.5%, 2%, 2.5%
- stop_loss_pct: 5%, 7.5%, 10%

Moon Dev 🌙


    ======================================================================
RUNNING BASELINE BACKTEST (Non-Optimized)
======================================================================

📊 Moon Dev's BASELINE RESULTS (FLIP FLOP):
Liquidation Threshold: $5,000,000
Lookback Bars: 1 (5 minutes)
Take Profit: 2.0%
Stop Loss: 5.0%
--------------------------------------------------
Total Trades: 63
Win Rate: 65.08%
Return: -14.33%
Sharpe: 0.00
Max Drawdown: -35.34%

📈 FULL BASELINE STATS:
======================================================================
Start                     2024-06-04 12:50:00
End                       2025-12-05 12:45:00
Duration                    548 days 23:55:00
Exposure Time [%]                   18.344591
Equity Final [$]                 856747.95265
Equity Peak [$]                 1301298.62612
Return [%]                         -14.325205
Buy & Hold Return [%]               33.251745
Return (Ann.) [%]                   -9.751736
Volatility (Ann.) [%]                18.42532
Sharpe Ratio                              0.0
Sortino Ratio                             0.0
Calmar Ratio                              0.0
Max. Drawdown [%]                  -35.344787
Avg. Drawdown [%]                   -3.748015
Max. Drawdown Duration      501 days 16:45:00
Avg. Drawdown Duration       28 days 11:40:00
# Trades                                   63
Win Rate [%]                        65.079365
Best Trade [%]                       3.445636
Worst Trade [%]                    -18.261003
Avg. Trade [%]                      -0.304522
Max. Trade Duration          12 days 14:50:00
Avg. Trade Duration           1 days 14:20:00
Profit Factor                        0.825554
Expectancy [%]                      -0.238047
SQN                                 -0.544879
_strategy                    FlipFlopStrategy
_equity_curve                             ...
_trades                       Size  EntryB...
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
Exposure Time [%]                   84.813297
Equity Final [$]                6295604.29106
Equity Peak [$]                 6815387.78686
Return [%]                         529.560429
Buy & Hold Return [%]               33.251745
Return (Ann.) [%]                  234.545957
Volatility (Ann.) [%]              222.534527
Sharpe Ratio                         1.053976
Sortino Ratio                        7.728553
Calmar Ratio                         3.846198
Max. Drawdown [%]                  -60.981255
Avg. Drawdown [%]                   -2.783829
Max. Drawdown Duration      172 days 02:20:00
Avg. Drawdown Duration        2 days 23:35:00
# Trades                                  362
Win Rate [%]                         81.21547
Best Trade [%]                      19.508909
Worst Trade [%]                    -15.889771
Avg. Trade [%]                       0.542195
Max. Trade Duration          25 days 08:35:00
Avg. Trade Duration           1 days 06:50:00
Profit Factor                        1.787954
Expectancy [%]                       0.604366
SQN                                   1.98264
_strategy                 FlipFlopStrategy...
_equity_curve                             ...
_trades                        Size  Entry...
dtype: object

🎯 OPTIMIZED PARAMETERS:
--------------------------------------------------
Liquidation Threshold: $500,000
Lookback Bars: 3 (15 minutes)
Take Profit: 1.5%
Stop Loss: 10.0%

📊 IMPROVEMENT SUMMARY:
--------------------------------------------------
Baseline Return: -14.33%
Optimized Return: 529.56%
Improvement: 543.89%
(tflow) md@mds-MacBook-Pro moon-dev-trading-bots % 
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's FLIP FLOP Strategy 🌙")
print("Theory: Buy the dip, take profit, flip short, take profit again")
print("=" * 70)

# Data configuration
data_path = '/Users/tc/Dropbox/dev/github/moon-dev-trading-bots/backtests/liquidations/liq_data_BTC_5m_ohlcv.csv'
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


class FlipFlopStrategy(Strategy):
    """
    Moon Dev's Flip Flop Strategy

    Entry Logic:
    - BUY when long liquidation volume exceeds threshold
    - Track state: WAITING -> LONG -> SHORT -> DONE

    Exit Logic:
    - LONG: TP at X%, SL at Y%
    - On LONG TP hit -> flip to SHORT
    - SHORT: TP at X%, SL at Y%
    - On SHORT TP/SL hit -> back to WAITING for next signal

    """

    # Optimizable parameters
    liquidation_threshold = 500000  # $1M minimum long liquidation volume
    lookback_bars = 3  # How many 5-min bars to sum
    take_profit_pct = 1.5 # 2% take profit
    stop_loss_pct = 10.0  # 5% stop loss

    # Position sizing
    position_size = 0.95

    def init(self):
        """Initialize strategy indicators"""
        # Moon Dev's Flip Flop Strategy Init

        self.long_liq_volume = self.I(lambda: self.data.long_liq_volume)

        self.rolling_long_liq = self.I(
            lambda x: pd.Series(x).rolling(self.lookback_bars, min_periods=1).sum(),
            self.long_liq_volume
        )

        # State tracking: 'waiting', 'long', 'short'
        self.state = 'waiting'
        self.entry_price = 0

    def next(self):
        """Main strategy logic - Flip Flop approach"""

        current_price = self.data.Close[-1]
        current_rolling_liq = self.rolling_long_liq[-1]

        # STATE: WAITING - Look for liquidation signal to go LONG
        if self.state == 'waiting':
            if not self.position:
                if current_rolling_liq >= self.liquidation_threshold:
                    self.buy(size=self.position_size)
                    self.entry_price = current_price
                    self.state = 'long'

        # STATE: LONG - Watch for TP or SL
        elif self.state == 'long':
            if self.position and self.position.is_long:
                pnl_pct = ((current_price - self.entry_price) / self.entry_price) * 100

                # Take profit hit - FLIP TO SHORT
                if pnl_pct >= self.take_profit_pct:
                    # Close long and open short (sell 2x to flip)
                    self.position.close()
                    self.sell(size=self.position_size)
                    self.entry_price = current_price
                    self.state = 'short'

                # Stop loss hit - back to waiting
                elif pnl_pct <= -self.stop_loss_pct:
                    self.position.close()
                    self.state = 'waiting'
                    self.entry_price = 0

            # Position closed externally somehow
            elif not self.position:
                self.state = 'waiting'
                self.entry_price = 0

        # STATE: SHORT - Watch for TP or SL
        elif self.state == 'short':
            if self.position and self.position.is_short:
                # For short: profit when price drops
                pnl_pct = ((self.entry_price - current_price) / self.entry_price) * 100

                # Take profit hit - done with this cycle
                if pnl_pct >= self.take_profit_pct:
                    self.position.close()
                    self.state = 'waiting'
                    self.entry_price = 0

                # Stop loss hit - done with this cycle
                elif pnl_pct <= -self.stop_loss_pct:
                    self.position.close()
                    self.state = 'waiting'
                    self.entry_price = 0

            # Position closed externally somehow
            elif not self.position:
                self.state = 'waiting'
                self.entry_price = 0


# Run backtest with baseline parameters
print("\n" + "="*70)
print("RUNNING BASELINE BACKTEST (Non-Optimized)")
print("="*70)

if len(data) > 100:
    bt = Backtest(
        data[['Open', 'High', 'Low', 'Close', 'Volume', 'long_liq_volume', 'short_liq_volume', 'net_liq_volume']],
        FlipFlopStrategy,
        cash=1000000,
        commission=0.001
    )

    # Run baseline
    baseline_stats = bt.run()

    print(f"\n📊 Moon Dev's BASELINE RESULTS (FLIP FLOP):")
    print(f"Liquidation Threshold: ${FlipFlopStrategy.liquidation_threshold:,}")
    print(f"Lookback Bars: {FlipFlopStrategy.lookback_bars} ({FlipFlopStrategy.lookback_bars * 5} minutes)")
    print(f"Take Profit: {FlipFlopStrategy.take_profit_pct}%")
    print(f"Stop Loss: {FlipFlopStrategy.stop_loss_pct}%")
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
            liquidation_threshold=range(500000, 5000000, 500000),  # $500k to $5M
            lookback_bars=[1, 2, 3],  # 5min to 15min lookback
            take_profit_pct=[1.5, 2.0, 2.5],  # TP options
            stop_loss_pct=[5.0, 7.5, 10.0],  # SL options
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
