"""
Inverse Liquidation Spread Strategy (Contrarian/Fade the Liquidations)
=========================================================================
Moon Dev's Contrarian Liquidation Strategy

This strategy trades AGAINST liquidations (contrarian/reversal):
- When long positions are liquidated → BUY (catch the bounce after cascade)
- When short positions are liquidated → SELL (catch the reversal after squeeze)

KEY FEATURE: Spread parameter - waits for price to move X% from liquidation
before entering. This helps catch better entries after the initial cascade.

Example: If longs liquidated at $100k with 0.5% spread, we buy at $99,500

ptimizable parameters
    liquidation_threshold = 300,000  # Minimum USD liquidation volume to trigger trade
    spread_pct = 0.5  # 0.5% spread - wait for price to move this % before entry
    take_profit = 1.0  # 1% take profit
    stop_loss = 2.0     # 2% stop loss
    max_hold_hours = 2  # Maximum holding period



📈 FULL BASELINE STATS:
======================================================================
Start                     2024-06-04 12:50:00
End                       2025-12-05 12:45:00
Duration                    548 days 23:55:00
Exposure Time [%]                   18.952388
Equity Final [$]             434184816.945563
Equity Peak [$]              471423862.322682
Return [%]                       43318.481695
Buy & Hold Return [%]               33.251745
Return (Ann.) [%]                 5480.808586
Volatility (Ann.) [%]             2728.834428
Sharpe Ratio                          2.00848
Sortino Ratio                      264.623236
Calmar Ratio                       216.181509
Max. Drawdown [%]                  -25.352809
Avg. Drawdown [%]                   -1.026923
Max. Drawdown Duration       31 days 18:35:00
Avg. Drawdown Duration        0 days 08:54:00
# Trades                                 2793
Win Rate [%]                        62.620838
Best Trade [%]                      29.155453
Worst Trade [%]                    -17.995656
Avg. Trade [%]                       0.230311
Max. Trade Duration           0 days 02:05:00
Avg. Trade Duration           0 days 00:49:00
Profit Factor                          1.9789
Expectancy [%]                       0.236539
SQN                                  7.560437
_strategy                 InverseLiquidati...
_equity_curve                             ...
_trades                         Size  Entr...
dtype: object

                                                                                                                 
✨ Moon Dev's OPTIMIZED RESULTS:
======================================================================
Start                     2024-06-04 12:50:00
End                       2025-12-05 12:45:00
Duration                    548 days 23:55:00
Exposure Time [%]                   25.345957
Equity Final [$]             511024806.832596
Equity Peak [$]              540574317.096695
Return [%]                       51002.480683
Buy & Hold Return [%]               33.251745
Return (Ann.) [%]                 6156.748977
Volatility (Ann.) [%]             4166.580705
Sharpe Ratio                          1.47765
Sortino Ratio                      183.340399
Calmar Ratio                       134.653913
Max. Drawdown [%]                  -45.722763
Avg. Drawdown [%]                   -1.031957
Max. Drawdown Duration       47 days 15:30:00
Avg. Drawdown Duration        0 days 08:21:00
# Trades                                 2665
Win Rate [%]                        65.853659
Best Trade [%]                      29.155453
Worst Trade [%]                    -25.619581
Avg. Trade [%]                       0.247545
Max. Trade Duration           0 days 04:05:00
Avg. Trade Duration           0 days 01:11:00
Profit Factor                         1.94737
Expectancy [%]                       0.258157
SQN                                  4.407568
_strategy                 InverseLiquidati...
_equity_curve                             ...
_trades                         Size  Entr...
dtype: object







                                                                                                                                  
✨ Moon Dev's OPTIMIZED RESULTS:
======================================================================
Start                     2024-06-04 12:50:00
End                       2025-12-05 12:45:00
Duration                    548 days 23:55:00
Exposure Time [%]                   14.996964
Equity Final [$]            1425764197.892908
Equity Peak [$]             1480229664.279406
Return [%]                      142476.419789
Buy & Hold Return [%]               33.251745
Return (Ann.) [%]                 12184.27155
Volatility (Ann.) [%]             5501.980532
Sharpe Ratio                         2.214525
Sortino Ratio                      923.416206
Calmar Ratio                       985.711732
Max. Drawdown [%]                  -12.360887
Avg. Drawdown [%]                    -0.87304
Max. Drawdown Duration       14 days 21:50:00
Avg. Drawdown Duration        0 days 07:01:00
# Trades                                 2338
Win Rate [%]                        65.183918
Best Trade [%]                      29.155453
Worst Trade [%]                     -7.913764
Avg. Trade [%]                        0.32849
Max. Trade Duration           0 days 02:05:00
Avg. Trade Duration           0 days 00:46:00
Profit Factor                         2.68103
Expectancy [%]                       0.334119
SQN                                  9.501118
_strategy                 InverseLiquidati...
_equity_curve                             ...
_trades                          Size  Ent...
dtype: object

🎯 OPTIMIZED PARAMETERS:
--------------------------------------------------
Liquidation Threshold: $300,000
Spread: 1.00%
Take Profit: 1.0%
Stop Loss: 2.0%
Max Hold Hours: 2


--- 

"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
from backtesting.lib import crossover
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's INVERSE Liquidation Spread Strategy 🌙")
print("Theory: Buy when longs are liquidated (contrarian), Sell when shorts are liquidated")
print("Spread: Wait for price to drop X% before entry after liquidation signal")
print("=" * 70)

# Data configuration
# Load preprocessed BTC data - choose between 1-minute and 5-minute
# Just comment/uncomment to switch between timeframes

# Option 1: 1-minute data
# data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/moondev_api/liq_data_BTC_1m_ohlcv.csv'
# timeframe = '1-minute'

# # Option 2: 5-minute data (currently active)
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


class InverseLiquidationSpreadStrategy(Strategy):
    """
    Moon Dev's Inverse Liquidation Spread Strategy (Contrarian)

    Entry Logic (OPPOSITE of momentum):
    - BUY when long liquidation volume exceeds threshold (fade the cascade, catch bounce)
    - SELL when short liquidation volume exceeds threshold (fade the squeeze, catch reversal)

    Spread Feature:
    - Wait for price to move spread_pct% from liquidation price before entering
    - For longs liquidated: wait for price to DROP spread_pct% then BUY
    - For shorts liquidated: wait for price to RISE spread_pct% then SELL

    Exit Logic:
    - Take profit at X%
    - Stop loss at Y%
    - Time-based exit after max_hold_hours
    """

    # Optimizable parameters
    liquidation_threshold = 300000  # Minimum USD liquidation volume to trigger trade
    spread_pct = 0.5  # 0.5% spread - wait for price to move this % before entry
    take_profit = 1.0  # 1% take profit
    stop_loss = 2.0     # 2% stop loss
    max_hold_hours = 2  # Maximum holding period

    # Position sizing
    position_size = 0.95  # Use 95% of available capital

    def init(self):
        """Initialize strategy indicators"""
        # Moon Dev's Inverse Liquidation Strategy Init

        # Store liquidation volumes as indicators
        self.long_liq_volume = self.I(lambda: self.data.long_liq_volume)
        self.short_liq_volume = self.I(lambda: self.data.short_liq_volume)
        self.net_liq_volume = self.I(lambda: self.data.net_liq_volume)

        # Calculate rolling averages for context
        self.avg_long_liq = self.I(lambda x: pd.Series(x).rolling(24).mean(), self.long_liq_volume)
        self.avg_short_liq = self.I(lambda x: pd.Series(x).rolling(24).mean(), self.short_liq_volume)

        # Track pending signals with target prices
        self.pending_long_signal = False
        self.pending_short_signal = False
        self.long_target_price = 0
        self.short_target_price = 0

    def next(self):
        """Main strategy logic - INVERSE/CONTRARIAN approach with spread"""

        # Get current liquidation volumes
        current_long_liq = self.long_liq_volume[-1]
        current_short_liq = self.short_liq_volume[-1]
        current_price = self.data.Close[-1]

        # Check for new liquidation signals (when not in position)
        if not self.position:

            # Check for long liquidation signal - we want to BUY (contrarian)
            # But wait for price to drop spread_pct% first
            if current_long_liq >= self.liquidation_threshold:
                # Set target price: current price minus spread (convert % to decimal)
                self.long_target_price = current_price * (1 - self.spread_pct / 100)
                self.pending_long_signal = True
                self.pending_short_signal = False  # Cancel any pending short

            # Check for short liquidation signal - we want to SELL (contrarian)
            # But wait for price to rise spread_pct% first
            elif current_short_liq >= self.liquidation_threshold:
                # Set target price: current price plus spread (convert % to decimal)
                self.short_target_price = current_price * (1 + self.spread_pct / 100)
                self.pending_short_signal = True
                self.pending_long_signal = False  # Cancel any pending long

            # Execute pending long signal if price reached target
            if self.pending_long_signal and current_price <= self.long_target_price:
                sl_price = current_price * (1 - self.stop_loss / 100)
                tp_price = current_price * (1 + self.take_profit / 100)

                self.buy(size=self.position_size, sl=sl_price, tp=tp_price)
                self.pending_long_signal = False
                self.long_target_price = 0

            # Execute pending short signal if price reached target
            elif self.pending_short_signal and current_price >= self.short_target_price:
                sl_price = current_price * (1 + self.stop_loss / 100)
                tp_price = current_price * (1 - self.take_profit / 100)

                self.sell(size=self.position_size, sl=sl_price, tp=tp_price)
                self.pending_short_signal = False
                self.short_target_price = 0

        # Exit logic - time-based exit
        else:
            # Clear pending signals when in position
            self.pending_long_signal = False
            self.pending_short_signal = False

            if len(self.trades) > 0:
                entry_time = self.trades[-1].entry_time
                current_time = self.data.index[-1]
                hours_held = (current_time - entry_time).total_seconds() / 3600

                if hours_held >= self.max_hold_hours:
                    self.position.close()


# Run backtest with baseline parameters
print("\n" + "="*70)
print("RUNNING BASELINE BACKTEST (Non-Optimized)")
print("="*70)

if len(data) > 100:
    bt = Backtest(
        data[['Open', 'High', 'Low', 'Close', 'Volume', 'long_liq_volume', 'short_liq_volume', 'net_liq_volume']],
        InverseLiquidationSpreadStrategy,
        cash=1000000,
        commission=0.001
    )

    # Run baseline
    baseline_stats = bt.run()

    print(f"\n📊 Moon Dev's BASELINE RESULTS (INVERSE/CONTRARIAN):")
    print(f"Liquidation Threshold: ${InverseLiquidationSpreadStrategy.liquidation_threshold:,}")
    print(f"Spread: {InverseLiquidationSpreadStrategy.spread_pct:.2f}%")
    print(f"Take Profit: {InverseLiquidationSpreadStrategy.take_profit:.1f}%")
    print(f"Stop Loss: {InverseLiquidationSpreadStrategy.stop_loss:.1f}%")
    print(f"Max Hold: {InverseLiquidationSpreadStrategy.max_hold_hours} hours")
    print("-" * 50)
    print(f"Total Trades: {baseline_stats['# Trades']}")
    print(f"Win Rate: {baseline_stats['Win Rate [%]']:.2f}%")
    print(f"Return: {baseline_stats['Return [%]']:.2f}%")
    print(f"Sharpe: {baseline_stats['Sharpe Ratio']:.2f}")
    print(f"Max Drawdown: {baseline_stats['Max. Drawdown [%]']:.2f}%")

    print("\n📈 FULL BASELINE STATS:")
    print("="*70)
    print(baseline_stats)

    # Run optimization automatically
    print("\n" + "="*70)
    print("RUNNING OPTIMIZATION - Moon Dev's Parameter Search")
    print("="*70)
    print("🔄 Optimizing parameters... This may take a few minutes...")

    # Run the optimizer with error handling
    try:
        optimization_results = bt.optimize(
            #liquidation_threshold=range(100000, 1000000, 100000),  # $100k to $1M in $25k steps
            spread_pct=[0.5, 0.75, 1.0],  # 0.1% to 1% spread
            take_profit=[1.0, 1.5, 2.0, 2.5],  # 1% to 2%
            stop_loss=[1.0, 1.5, 2.0, 2.5],  # 1% to 2%
            max_hold_hours=[2],  # 2 to 4 hours
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
        print(f"Spread: {optimization_results._strategy.spread_pct:.2f}%")
        print(f"Take Profit: {optimization_results._strategy.take_profit:.1f}%")
        print(f"Stop Loss: {optimization_results._strategy.stop_loss:.1f}%")
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
