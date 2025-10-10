"""
Supply and Demand Zones STATISTICAL ARBITRAGE Strategy
=======================================================

Ultra high frequency statistical arbitrage using z-score mean reversion.

Theory:
- Price deviations from mean follow statistical distributions
- Extreme z-scores indicate overextension
- Combine with SDZ for high-probability reversions
- Multiple timeframe z-scores for confirmation

Trading Logic:
- Calculate z-score of price from rolling mean
- Enter when z-score extreme AND at zone
- Use Bollinger Band width for volatility adjustment
- Exit at z-score neutralization

================================================================================
DETAILED STRATEGY IMPLEMENTATION GUIDE FOR LIVE TRADING BOT
================================================================================

This strategy achieved 3,403 trades with 42.74% return and 59.98% win rate.
Optimized version: 4,044 trades with 91.18% return.

DATA REQUIREMENTS:
- 1-minute OHLCV data (minimum 50 bars history needed)
- Real-time Close price updates
- No volume data required for base strategy

INDICATOR CALCULATIONS:

1. Z-SCORE CALCULATION:
   - Formula: (Current_Close - Rolling_Mean) / Rolling_StdDev
   - Calculate for 3 periods: 5, 10, and 20 bars
   - Example: If 10-bar mean = $110,000, std = $500, current = $109,000
             Then z-score = (109,000 - 110,000) / 500 = -2.0

2. SUPPLY/DEMAND ZONES:
   - Demand Zone = Rolling MIN of Close prices over lookback period (8 bars)
   - Supply Zone = Rolling MAX of Close prices over lookback period (8 bars)
   - Zone proximity = Within 0.5% of zone level

3. BOLLINGER BANDS:
   - Middle = 20-bar SMA of Close
   - Std = 20-bar standard deviation
   - Upper = Middle + (2 * Std)
   - Lower = Middle - (2 * Std)
   - BB Width = (Upper - Lower) / Middle

4. PRICE PERCENTILE RANK:
   - Calculate rolling 50-bar percentile rank (0-100)

ENTRY CONDITIONS (BUY):
All BUY entries require: near_demand = abs(price - demand_zone) / demand_zone <= 0.005

Condition 1: Multi Z-Score Confirmation
   IF multi_zscore_confirm == True:
      Count how many are true:
      - z5 < -zscore_entry (default -2.0)
      - z10 < -zscore_entry * 0.9 (default -1.8)
      - z20 < -zscore_entry * 0.8 (default -1.6)
      IF count >= 2 AND near_demand: BUY

Condition 2: Single Z-Score Entry
   IF multi_zscore_confirm == False:
      IF z5 < -zscore_entry AND near_demand: BUY

Condition 3: Extreme Percentile
   IF price_rank < 10 AND near_demand: BUY

Condition 4: Z-Score Divergence
   IF z5 < -2.5 AND z10 > z5 + 0.5 AND price < zone_midpoint: BUY

ENTRY CONDITIONS (SELL):
All SELL entries require: near_supply = abs(price - supply_zone) / supply_zone <= 0.005

Condition 1: Multi Z-Score Confirmation
   IF multi_zscore_confirm == True:
      Count how many are true:
      - z5 > zscore_entry (default 2.0)
      - z10 > zscore_entry * 0.9 (default 1.8)
      - z20 > zscore_entry * 0.8 (default 1.6)
      IF count >= 2 AND near_supply: SELL

Condition 2: Single Z-Score Entry
   IF multi_zscore_confirm == False:
      IF z5 > zscore_entry AND near_supply: SELL

Condition 3: Extreme Percentile
   IF price_rank > 90 AND near_supply: SELL

Condition 4: Z-Score Divergence
   IF z5 > 2.5 AND z10 < z5 - 0.5 AND price > zone_midpoint: SELL

EXIT CONDITIONS (LONG POSITIONS):
1. Z-Score Normalization:
   IF (z5 > -zscore_exit OR z10 > -zscore_exit) AND position_profit > 0: CLOSE
   Default zscore_exit = 0.5

2. Z-Score Reversal (Force Exit):
   IF z5 > 1.0: CLOSE (regardless of profit)

3. Stop Loss: Entry_Price * (1 - stop_loss)
   Default stop_loss = 0.0025 (0.25%)

4. Take Profit: MAX(bb_middle, Entry_Price * (1 + take_profit))
   Default take_profit = 0.004 (0.4%)
   If calculated TP <= Entry * 1.001, use Entry * (1 + take_profit)

EXIT CONDITIONS (SHORT POSITIONS):
1. Z-Score Normalization:
   IF (z5 < zscore_exit OR z10 < zscore_exit) AND position_profit > 0: CLOSE

2. Z-Score Reversal (Force Exit):
   IF z5 < -1.0: CLOSE (regardless of profit)

3. Stop Loss: Entry_Price * (1 + stop_loss)

4. Take Profit: MIN(bb_middle, Entry_Price * (1 - take_profit))
   If calculated TP >= Entry * 0.999, use Entry * (1 - take_profit)

RISK MANAGEMENT:
- Only one position at a time (no pyramiding)
- BB Width Filter: Skip entry if BB_Width > bb_width_filter (default 0.03 = 3%)
- Position Size: Fixed (use same size for all trades)
- Commission: Account for 0.1% each way

OPTIMIZED PARAMETERS (Best Performance):
- lookback_period = 6 bars
- zscore_entry = 1.5
- zscore_exit = 0.3
- bb_width_filter = 0.04 (4%)
- take_profit = 0.0045 (0.45%)
- stop_loss = 0.002 (0.2%)
- multi_zscore_confirm = True

IMPLEMENTATION CHECKLIST:
□ Calculate rolling statistics (mean, std) for 5, 10, 20 periods
□ Calculate z-scores for each period
□ Track supply/demand zones (8-bar min/max)
□ Monitor zone proximity (0.5% threshold)
□ Check BB width before entry (avoid high volatility)
□ Implement all 4 entry conditions for each direction
□ Use dynamic TP based on BB middle vs percentage
□ Exit on z-score normalization with profit check
□ Force exit on z-score reversal
□ Ensure single position at a time

COMMON PITFALLS TO AVOID:
- Don't enter if BB width > 3% (high volatility)
- Don't use Open, High, Low prices for z-score (only Close)
- Ensure TP > Entry for longs, TP < Entry for shorts
- Check for NaN values in z-scores (use 0 if NaN)
- Wait for minimum 50 bars before starting trades
================================================================================

=======================================================
📊 Loading BTC 1-minute data...
✅ Loaded 40,320 1-minute bars
📅 Date range: 2025-08-26 15:41:00 → 2025-09-23 15:40:00

======================================================================
RUNNING STATISTICAL ARBITRAGE BACKTEST
======================================================================

📊 BASELINE RESULTS:
Lookback Period: 8 bars
Z-Score Entry: 2.0
Z-Score Exit: 0.5
Multi Z-Score: True
Take Profit: 0.4%
Stop Loss: 0.25%
--------------------------------------------------
🔥 Total Trades: 3403
Win Rate: 59.98%
Return: 42.74%
Sharpe: 1.81
Max Drawdown: -8.63%

📈 FULL BASELINE STATS:
======================================================================
Start                     2025-08-26 15:41:00
End                       2025-09-23 15:40:00
Duration                     27 days 23:59:00
Exposure Time [%]                    62.97619
Equity Final [$]               1427372.242503
Equity Peak [$]                1487824.570444
Return [%]                          42.737224
Buy & Hold Return [%]                2.958633
Return (Ann.) [%]                 7149.373996
Volatility (Ann.) [%]             3951.637141
Sharpe Ratio                         1.809218
Sortino Ratio                      283.420889
Calmar Ratio                       828.759325
Max. Drawdown [%]                   -8.626599
Avg. Drawdown [%]                   -0.139884
Max. Drawdown Duration        4 days 20:47:00
Avg. Drawdown Duration        0 days 00:52:00
# Trades                                 3403
Win Rate [%]                        59.976491
Best Trade [%]                       0.890203
Worst Trade [%]                     -0.360114
Avg. Trade [%]                        0.01097
Max. Trade Duration           0 days 00:28:00
Avg. Trade Duration           0 days 00:07:00
Profit Factor                        1.613702
Expectancy [%]                       0.010994
SQN                                   8.47889
_strategy                  SDZStatArbStrategy
_equity_curve                             ...
_trades                         Size  Entr...
dtype: object

======================================================================
OPTIMIZING FOR RETURN ON INVESTMENT
======================================================================
                                                                                                                                                                                                                                                                                             
✨ OPTIMIZED RESULTS:
======================================================================
Start                     2025-08-26 15:41:00
End                       2025-09-23 15:40:00
Duration                     27 days 23:59:00
Exposure Time [%]                   75.426587
Equity Final [$]               1911835.373441
Equity Peak [$]                1969590.863452
Return [%]                          91.183537
Buy & Hold Return [%]                2.958633
Return (Ann.) [%]               256819.248748
Volatility (Ann.) [%]           217486.856658
Sharpe Ratio                          1.18085
Sortino Ratio                     8503.068913
Calmar Ratio                     24382.108903
Max. Drawdown [%]                  -10.533102
Avg. Drawdown [%]                   -0.121626
Max. Drawdown Duration        4 days 11:09:00
Avg. Drawdown Duration        0 days 00:34:00
# Trades                                 4044
Win Rate [%]                        59.718101
Best Trade [%]                       1.001127
Worst Trade [%]                     -0.358361
Avg. Trade [%]                       0.016668
Max. Trade Duration           0 days 00:28:00
Avg. Trade Duration           0 days 00:07:00
Profit Factor                        1.988729
Expectancy [%]                       0.016697
SQN                                 12.428385
_strategy                 SDZStatArbStrate...
_equity_curve                             ...
_trades                         Size  Entr...
dtype: object

🎯 OPTIMIZED PARAMETERS:"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Supply and Demand Zones STATISTICAL ARBITRAGE Strategy 🌙")
print("=" * 70)

# Load BTC 1-minute data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1m-4wks-data.csv'
print(f"📊 Loading BTC 1-minute data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)

# Rename columns
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Calculate statistical indicators
# Z-score calculation
def calculate_zscore(series, period):
    mean = series.rolling(period).mean()
    std = series.rolling(period).std()
    zscore = (series - mean) / std
    return zscore

# Multiple timeframe z-scores
data['ZScore_5'] = calculate_zscore(data['Close'], 5)
data['ZScore_10'] = calculate_zscore(data['Close'], 10)
data['ZScore_20'] = calculate_zscore(data['Close'], 20)

# Bollinger Bands for volatility
data['BB_Middle'] = data['Close'].rolling(20).mean()
data['BB_Std'] = data['Close'].rolling(20).std()
data['BB_Upper'] = data['BB_Middle'] + (data['BB_Std'] * 2)
data['BB_Lower'] = data['BB_Middle'] - (data['BB_Std'] * 2)
data['BB_Width'] = (data['BB_Upper'] - data['BB_Lower']) / data['BB_Middle']

# Price percentile rank
data['Price_Rank'] = data['Close'].rolling(50).rank(pct=True) * 100

print(f"✅ Loaded {len(data):,} 1-minute bars")
print(f"📅 Date range: {data.index.min()} → {data.index.max()}")


class SDZStatArbStrategy(Strategy):
    """
    Statistical Arbitrage SDZ Strategy

    Parameters:
    - lookback_period: Period for zone calculation
    - zscore_entry: Z-score threshold for entry
    - zscore_exit: Z-score threshold for exit
    - multi_zscore_confirm: Require multiple z-scores to confirm
    - bb_width_filter: Maximum BB width for entry
    - take_profit: Profit target
    - stop_loss: Stop loss
    """

    # Optimizable parameters
    lookback_period = 8  # Zone lookback
    zscore_entry = 2.0  # Enter at 2 std dev
    zscore_exit = 0.5  # Exit at 0.5 std dev
    multi_zscore_confirm = True  # Require multiple confirmations
    bb_width_filter = 0.03  # Max 3% BB width
    take_profit = 0.004  # 0.4% take profit
    stop_loss = 0.0025  # 0.25% stop loss

    def init(self):
        """Initialize indicators"""
        # Calculate zones
        self.support = self.I(lambda: pd.Series(self.data.Close).rolling(
            window=self.lookback_period, min_periods=1).min())
        self.resistance = self.I(lambda: pd.Series(self.data.Close).rolling(
            window=self.lookback_period, min_periods=1).max())

        # Statistical indicators
        self.zscore_5 = self.I(lambda: self.data.ZScore_5)
        self.zscore_10 = self.I(lambda: self.data.ZScore_10)
        self.zscore_20 = self.I(lambda: self.data.ZScore_20)
        self.bb_width = self.I(lambda: self.data.BB_Width)
        self.bb_middle = self.I(lambda: self.data.BB_Middle)
        self.price_rank = self.I(lambda: self.data.Price_Rank)

        # Track entry z-score
        self.entry_zscore = 0

    def next(self):
        """Main strategy logic - statistical arbitrage"""

        # Skip if insufficient data
        if len(self.data) < 50:
            return

        # Get current values
        current_price = self.data.Close[-1]
        z5 = self.zscore_5[-1] if self.zscore_5[-1] and not np.isnan(self.zscore_5[-1]) else 0
        z10 = self.zscore_10[-1] if self.zscore_10[-1] and not np.isnan(self.zscore_10[-1]) else 0
        z20 = self.zscore_20[-1] if self.zscore_20[-1] and not np.isnan(self.zscore_20[-1]) else 0
        current_bb_width = self.bb_width[-1] if self.bb_width[-1] else 0.02
        current_bb_middle = self.bb_middle[-1] if self.bb_middle[-1] else current_price
        current_rank = self.price_rank[-1] if self.price_rank[-1] else 50

        # Get zones
        demand_zone = self.support[-1]
        supply_zone = self.resistance[-1]

        # Exit logic
        if self.position:
            # Exit when z-score normalizes
            if self.position.is_long:
                # Exit if any z-score goes positive (mean reversion complete)
                if z5 > -self.zscore_exit or z10 > -self.zscore_exit:
                    if self.position.pl_pct > 0:
                        self.position.close()
                        return
                # Exit if z-score reverses too much
                if z5 > 1:
                    self.position.close()
                    return
            else:
                # Exit if any z-score goes negative (mean reversion complete)
                if z5 < self.zscore_exit or z10 < self.zscore_exit:
                    if self.position.pl_pct > 0:
                        self.position.close()
                        return
                # Exit if z-score reverses too much
                if z5 < -1:
                    self.position.close()
                    return

        # Entry logic - only if no position
        if not self.position:

            # Check BB width filter (avoid trading in high volatility)
            if current_bb_width > self.bb_width_filter:
                return

            # Zone proximity
            near_demand = abs(current_price - demand_zone) / demand_zone <= 0.005
            near_supply = abs(current_price - supply_zone) / supply_zone <= 0.005

            # BUY signal - Oversold z-score at demand
            buy_signal = False

            if self.multi_zscore_confirm:
                # Multiple z-scores confirm oversold
                oversold_count = sum([
                    z5 < -self.zscore_entry,
                    z10 < -self.zscore_entry * 0.9,
                    z20 < -self.zscore_entry * 0.8
                ])
                if oversold_count >= 2 and near_demand:
                    buy_signal = True
            else:
                # Single z-score entry
                if z5 < -self.zscore_entry and near_demand:
                    buy_signal = True

            # Additional statistical conditions
            if not buy_signal:
                # Extreme percentile rank at demand
                if current_rank < 10 and near_demand:
                    buy_signal = True
                # Extreme z-score divergence
                elif z5 < -2.5 and z10 > z5 + 0.5:  # Divergence showing reversal
                    if current_price < (demand_zone + supply_zone) / 2:
                        buy_signal = True

            if buy_signal:
                # Dynamic targets based on z-score extremity
                zscore_mult = min(abs(z5) / self.zscore_entry, 1.5) if z5 != 0 else 1
                tp_mult = self.take_profit * zscore_mult

                sl_price = current_price * (1 - self.stop_loss)
                # For longs, BB middle should be above current price if we're oversold
                # Use the higher of BB middle or percentage target
                tp_price = max(current_bb_middle, current_price * (1 + tp_mult))
                # Final safety check
                if tp_price <= current_price * 1.001:  # Ensure at least 0.1% profit
                    tp_price = current_price * (1 + self.take_profit)

                self.buy(sl=sl_price, tp=tp_price)
                self.entry_zscore = z5

            # SELL signal - Overbought z-score at supply
            else:
                sell_signal = False

                if self.multi_zscore_confirm:
                    # Multiple z-scores confirm overbought
                    overbought_count = sum([
                        z5 > self.zscore_entry,
                        z10 > self.zscore_entry * 0.9,
                        z20 > self.zscore_entry * 0.8
                    ])
                    if overbought_count >= 2 and near_supply:
                        sell_signal = True
                else:
                    # Single z-score entry
                    if z5 > self.zscore_entry and near_supply:
                        sell_signal = True

                # Additional statistical conditions
                if not sell_signal:
                    # Extreme percentile rank at supply
                    if current_rank > 90 and near_supply:
                        sell_signal = True
                    # Extreme z-score divergence
                    elif z5 > 2.5 and z10 < z5 - 0.5:  # Divergence showing reversal
                        if current_price > (demand_zone + supply_zone) / 2:
                            sell_signal = True

                if sell_signal:
                    # Dynamic targets based on z-score extremity
                    zscore_mult = min(abs(z5) / self.zscore_entry, 1.5) if z5 != 0 else 1
                    tp_mult = self.take_profit * zscore_mult

                    sl_price = current_price * (1 + self.stop_loss)
                    # For shorts, BB middle should be below current price if we're overbought
                    # Use the lower of BB middle or percentage target
                    tp_price = min(current_bb_middle, current_price * (1 - tp_mult))
                    # Final safety check
                    if tp_price >= current_price * 0.999:  # Ensure at least 0.1% profit
                        tp_price = current_price * (1 - self.take_profit)

                    self.sell(sl=sl_price, tp=tp_price)
                    self.entry_zscore = z5


# Run baseline backtest
print("\n" + "="*70)
print("RUNNING STATISTICAL ARBITRAGE BACKTEST")
print("="*70)

bt = Backtest(
    data,
    SDZStatArbStrategy,
    cash=1000000,  # $1M for BTC trading
    commission=0.001,# .0003 for takes on aster, .00008 for makers
    exclusive_orders=True
)

# Run baseline
baseline_stats = bt.run()

print(f"\n📊 BASELINE RESULTS:")
print(f"Lookback Period: {SDZStatArbStrategy.lookback_period} bars")
print(f"Z-Score Entry: {SDZStatArbStrategy.zscore_entry}")
print(f"Z-Score Exit: {SDZStatArbStrategy.zscore_exit}")
print(f"Multi Z-Score: {SDZStatArbStrategy.multi_zscore_confirm}")
print(f"Take Profit: {SDZStatArbStrategy.take_profit*100:.1f}%")
print(f"Stop Loss: {SDZStatArbStrategy.stop_loss*100:.2f}%")
print("-" * 50)
print(f"🔥 Total Trades: {baseline_stats['# Trades']}")
print(f"Win Rate: {baseline_stats['Win Rate [%]']:.2f}%")
print(f"Return: {baseline_stats['Return [%]']:.2f}%")
print(f"Sharpe: {baseline_stats['Sharpe Ratio']:.2f}")
print(f"Max Drawdown: {baseline_stats['Max. Drawdown [%]']:.2f}%")

print("\n📈 FULL BASELINE STATS:")
print("="*70)
print(baseline_stats)

# Run optimization
print("\n" + "="*70)
print("OPTIMIZING FOR RETURN ON INVESTMENT")
print("="*70)

try:
    optimization_results = bt.optimize(
        lookback_period=[6, 8, 10],
        zscore_entry=[1.5, 2.0, 2.5],
        zscore_exit=[0.3, 0.5, 0.7],
        bb_width_filter=[0.02, 0.03, 0.04],
        take_profit=[0.0035, 0.004, 0.0045],
        stop_loss=[0.002, 0.0025, 0.003],
        maximize='Return [%]',  # Optimize for ROI
        return_heatmap=False
    )

    print("\n✨ OPTIMIZED RESULTS:")
    print("="*70)
    print(optimization_results)

    print("\n🎯 OPTIMIZED PARAMETERS:")
    print("-" * 50)
    print(f"🔥 Total Trades: {optimization_results['# Trades']}")
    print(f"Return: {optimization_results['Return [%]']:.2f}%")
    print(f"Win Rate: {optimization_results['Win Rate [%]']:.2f}%")
    print(f"Sharpe: {optimization_results['Sharpe Ratio']:.2f}")
    print(f"Lookback Period: {optimization_results._strategy.lookback_period} bars")
    print(f"Z-Score Entry: {optimization_results._strategy.zscore_entry}")
    print(f"Z-Score Exit: {optimization_results._strategy.zscore_exit}")
    print(f"BB Width Filter: {optimization_results._strategy.bb_width_filter*100:.1f}%")
    print(f"Take Profit: {optimization_results._strategy.take_profit*100:.2f}%")
    print(f"Stop Loss: {optimization_results._strategy.stop_loss*100:.2f}%")

except Exception as e:
    print(f"\n⚠️ Optimization failed: {str(e)}")

# Show plot
print("\n📊 Generating plot...")
bt.plot()