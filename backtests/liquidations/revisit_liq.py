"""
Revisit Liquidation Strategy - Moon Dev's "Price Will Return" Play
===================================================================
Moon Dev's "Revisit Liquidation" Strategy

Strategy Logic:
1. Detect big LONG liquidation event ($5M+)
2. Record the LOWEST price during that liquidation bar
3. Place a LIMIT BUY order X% BELOW that lowest price
4. Theory: Price will revisit (and go below) that liquidation low in the next day or two
5. Hold with TP/SL

Entry:
- Long liquidations > threshold (e.g., $5M)
- Get the LOW price of that bar
- Set limit buy at LOW * (1 - entry_below_pct)
- Order stays open until filled or expires

Exit:
- Take profit at X% (8% default)
- Stop loss at Y% (10% default)

Variables to Optimize:
- liquidation_threshold: $5M default
- lookback_bars: How many 5-min bars to sum liquidations
- entry_below_pct: How far below the liquidation low to place order (0.5%, 1%)
- take_profit_pct: 2%, 4%, 6%, 8%
- stop_loss_pct: 2%, 4%, 6%, 10%
- order_expiry_bars: How long the limit order stays valid

Moon Dev 🌙

📈 FULL BASELINE STATS:
======================================================================
Start                     2024-06-04 12:50:00
End                       2025-12-05 12:45:00
Duration                    548 days 23:55:00
Exposure Time [%]                   26.397743
Equity Final [$]                 964693.78198
Equity Peak [$]                  1881227.0289
Return [%]                          -3.530622
Buy & Hold Return [%]               33.251745
Return (Ann.) [%]                   -2.357185
Volatility (Ann.) [%]               29.997087
Sharpe Ratio                              0.0
Sortino Ratio                             0.0
Calmar Ratio                              0.0
Max. Drawdown [%]                  -52.936739
Avg. Drawdown [%]                   -2.919031
Max. Drawdown Duration      255 days 03:35:00
Avg. Drawdown Duration        4 days 16:54:00
# Trades                                   19
Win Rate [%]                        47.368421
Best Trade [%]                      21.823902
Worst Trade [%]                    -16.778479
Avg. Trade [%]                      -0.190845
Max. Trade Duration          24 days 02:20:00
Avg. Trade Duration           7 days 14:59:00
Profit Factor                        1.059079
Expectancy [%]                       0.207179
SQN                                 -0.078612
_strategy                  RevisitLiqStrategy
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
Exposure Time [%]                   33.414289
Equity Final [$]                2927417.52171
Equity Peak [$]                 3540638.22135
Return [%]                         192.741752
Buy & Hold Return [%]               33.251745
Return (Ann.) [%]                  103.974646
Volatility (Ann.) [%]               72.321681
Sharpe Ratio                         1.437669
Sortino Ratio                        6.468087
Calmar Ratio                          2.83861
Max. Drawdown [%]                  -36.628718
Avg. Drawdown [%]                   -2.799523
Max. Drawdown Duration      255 days 03:35:00
Avg. Drawdown Duration        4 days 10:27:00
# Trades                                   49
Win Rate [%]                        69.387755
Best Trade [%]                      21.078678
Worst Trade [%]                     -9.530465
Avg. Trade [%]                       2.405616
Max. Trade Duration          13 days 08:00:00
Avg. Trade Duration           3 days 17:47:00
Profit Factor                        2.878758
Expectancy [%]                       2.579034
SQN                                  2.561741
_strategy                 RevisitLiqStrate...
_equity_curve                             ...
_trades                       Size  EntryB...
dtype: object

🎯 OPTIMIZED PARAMETERS:
--------------------------------------------------
Liquidation Threshold: $2,000,000
Lookback Bars: 1 (5 minutes)
Entry Below Liq Low: 2.0%
Take Profit: 6.0%
Stop Loss: 6.0%

"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's REVISIT LIQUIDATION Strategy 🌙")
print("Theory: Price will revisit the liquidation low - place limit order below it")
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


class RevisitLiqStrategy(Strategy):
    """
    Moon Dev's Revisit Liquidation Strategy

    Entry Logic:
    - Detect big long liquidation
    - Get the LOW price of that bar
    - Set target entry price = LOW * (1 - entry_below_pct)
    - Wait for price to reach target (simulating limit order)

    Exit Logic:
    - Take profit at X%
    - Stop loss at Y%
    - Order expires after X bars if not filled
    """

    # Optimizable parameters
    liquidation_threshold = 5000000  # $5M minimum long liquidation volume
    lookback_bars = 1  # How many 5-min bars to sum
    entry_below_pct = 1.0  # Place order 1% below the liquidation low
    take_profit_pct = 8.0  # 8% take profit
    stop_loss_pct = 10.0  # 10% stop loss
    order_expiry_bars = 576  # Order expires after 576 bars (48 hours on 5min data)

    # Position sizing
    position_size = 0.95

    def init(self):
        """Initialize strategy indicators"""
        # Moon Dev's Revisit Liquidation Strategy Init

        self.long_liq_volume = self.I(lambda: self.data.long_liq_volume)

        self.rolling_long_liq = self.I(
            lambda x: pd.Series(x).rolling(self.lookback_bars, min_periods=1).sum(),
            self.long_liq_volume
        )

        # Track pending limit order
        self.order_pending = False
        self.target_entry_price = 0
        self.order_bar_count = 0
        self.liquidation_low = 0
        self.actual_entry_price = 0  # Track actual entry for TP/SL calc

    def next(self):
        """Main strategy logic - Revisit Liquidation approach"""

        current_price = self.data.Close[-1]
        current_low = self.data.Low[-1]
        current_rolling_liq = self.rolling_long_liq[-1]

        # In position - check for TP/SL exit
        if self.position:
            if self.actual_entry_price > 0:
                pnl_pct = ((current_price - self.actual_entry_price) / self.actual_entry_price) * 100

                # Take profit hit
                if pnl_pct >= self.take_profit_pct:
                    self.position.close()
                    self.actual_entry_price = 0

                # Stop loss hit
                elif pnl_pct <= -self.stop_loss_pct:
                    self.position.close()
                    self.actual_entry_price = 0
            return

        # Not in position - look for entry
        # Check for new liquidation signal
        if current_rolling_liq >= self.liquidation_threshold and not self.order_pending:
            # Record the low of this liquidation bar
            self.liquidation_low = current_low
            # Set target entry price below the liquidation low
            self.target_entry_price = self.liquidation_low * (1 - self.entry_below_pct / 100)
            self.order_pending = True
            self.order_bar_count = 0

        # If we have a pending order, check if price reached our target
        if self.order_pending:
            self.order_bar_count += 1

            # Order expired
            if self.order_bar_count >= self.order_expiry_bars:
                self.order_pending = False
                self.target_entry_price = 0
                self.order_bar_count = 0
                self.liquidation_low = 0

            # Price reached our limit order level - BUY!
            # Check if the low of this bar went below our target (would have filled limit order)
            elif current_low <= self.target_entry_price:
                # Buy without SL/TP - we'll manage exits manually
                self.buy(size=self.position_size)
                self.actual_entry_price = self.target_entry_price

                # Reset order tracking
                self.order_pending = False
                self.target_entry_price = 0
                self.order_bar_count = 0
                self.liquidation_low = 0


# Run backtest with baseline parameters
print("\n" + "="*70)
print("RUNNING BASELINE BACKTEST (Non-Optimized)")
print("="*70)

if len(data) > 100:
    bt = Backtest(
        data[['Open', 'High', 'Low', 'Close', 'Volume', 'long_liq_volume', 'short_liq_volume', 'net_liq_volume']],
        RevisitLiqStrategy,
        cash=1000000,
        commission=0.001
    )

    # Run baseline
    baseline_stats = bt.run()

    print(f"\n📊 Moon Dev's BASELINE RESULTS (REVISIT LIQUIDATION):")
    print(f"Liquidation Threshold: ${RevisitLiqStrategy.liquidation_threshold:,}")
    print(f"Lookback Bars: {RevisitLiqStrategy.lookback_bars} ({RevisitLiqStrategy.lookback_bars * 5} minutes)")
    print(f"Entry Below Liq Low: {RevisitLiqStrategy.entry_below_pct}%")
    print(f"Take Profit: {RevisitLiqStrategy.take_profit_pct}%")
    print(f"Stop Loss: {RevisitLiqStrategy.stop_loss_pct}%")
    print(f"Order Expiry: {RevisitLiqStrategy.order_expiry_bars} bars ({RevisitLiqStrategy.order_expiry_bars * 5 / 60:.1f} hours)")
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
            liquidation_threshold=range(2000000, 8000000, 1000000),  # $2M to $8M
            lookback_bars=[1, 2, 3],  # 5min to 15min lookback
            entry_below_pct=[0.5, 1.0, 1.5, 2.0],  # How far below liquidation low
            take_profit_pct=[2.0, 4.0, 6.0, 8.0],  # TP options
            stop_loss_pct=[2.0, 4.0, 6.0, 10.0],  # SL options
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
        print(f"Entry Below Liq Low: {optimization_results._strategy.entry_below_pct}%")
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
