"""
Supply and Demand Zones STATISTICAL ARBITRAGE with MULTI-FACTOR Strategy
=========================================================================

Multi-factor stat arb combining price, volume, and volatility divergences.

Theory:
- Multiple uncorrelated factors improve signal quality
- Divergences between factors reveal hidden opportunities
- Factor rotation based on market conditions
- Ensemble approach reduces false signals

Trading Logic:
- Score each factor independently
- Enter when multiple factors align
- Weight factors based on recent performance
- Dynamic factor selection
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's SDZ STATISTICAL ARBITRAGE + MULTI-FACTOR Strategy 🌙")
print("=" * 70)

# Load BTC 1-minute data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1m-4wks-data.csv'
print(f"📊 Loading BTC 1-minute data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)

# Rename columns
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Calculate multi-factor indicators

# Factor 1: Price Z-Score
def calculate_zscore(series, period):
    mean = series.rolling(period).mean()
    std = series.rolling(period).std()
    zscore = (series - mean) / std
    return zscore

data['ZScore_5'] = calculate_zscore(data['Close'], 5)
data['ZScore_10'] = calculate_zscore(data['Close'], 10)
data['ZScore_20'] = calculate_zscore(data['Close'], 20)

# Factor 2: Volume Profile Score
data['Volume_MA'] = data['Volume'].rolling(20).mean()
data['Volume_Score'] = (data['Volume'] - data['Volume_MA']) / data['Volume_MA']
data['Volume_Trend'] = data['Volume'].rolling(10).mean() - data['Volume'].rolling(20).mean()

# Factor 3: Volatility Score
data['Returns'] = data['Close'].pct_change()
data['Volatility'] = data['Returns'].rolling(10).std()
data['Vol_ZScore'] = calculate_zscore(data['Volatility'], 20)

# Factor 4: Momentum Score
data['RSI'] = ta.rsi(data['Close'], length=14)
data['RSI_Score'] = (data['RSI'] - 50) / 50  # Normalize to -1 to 1

# Factor 5: Microstructure Score
data['Spread'] = (data['High'] - data['Low']) / data['Close']
data['Spread_Score'] = -calculate_zscore(data['Spread'], 20)  # Negative because tight spread is good

# Factor 6: Order Flow Score (proxy)
data['Order_Flow'] = (data['Close'] - data['Open']) / (data['High'] - data['Low'] + 0.0001)
data['OF_Score'] = data['Order_Flow'].rolling(5).mean()

# Composite Multi-Factor Score
def calculate_composite_score(row, weights=None):
    if weights is None:
        weights = [1, 1, 1, 1, 1, 1]  # Equal weights

    factors = [
        row['ZScore_10'] if not pd.isna(row['ZScore_10']) else 0,
        row['Volume_Score'] if not pd.isna(row['Volume_Score']) else 0,
        row['Vol_ZScore'] if not pd.isna(row['Vol_ZScore']) else 0,
        row['RSI_Score'] if not pd.isna(row['RSI_Score']) else 0,
        row['Spread_Score'] if not pd.isna(row['Spread_Score']) else 0,
        row['OF_Score'] if not pd.isna(row['OF_Score']) else 0
    ]

    weighted_score = sum(f * w for f, w in zip(factors, weights)) / sum(weights)
    return weighted_score

data['Composite_Score'] = data.apply(calculate_composite_score, axis=1)

# Factor Divergence Detection
data['Price_Volume_Divergence'] = (data['ZScore_10'] * data['Volume_Score'] < 0).astype(int)
data['Price_Vol_Divergence'] = (data['ZScore_10'] * data['Vol_ZScore'] < 0).astype(int)

# Bollinger Bands
data['BB_Middle'] = data['Close'].rolling(20).mean()
data['BB_Std'] = data['Close'].rolling(20).std()

print(f"✅ Loaded {len(data):,} 1-minute bars")
print(f"📅 Date range: {data.index.min()} → {data.index.max()}")


class SDZStatArbMultiFactorStrategy(Strategy):
    """
    Statistical Arbitrage Multi-Factor Strategy

    Parameters:
    - lookback_period: Period for zone calculation
    - min_factors: Minimum factors required for entry
    - factor_threshold: Threshold for each factor
    - use_divergences: Trade on factor divergences
    - composite_threshold: Composite score threshold
    - take_profit: Profit target
    - stop_loss: Stop loss
    """

    # Optimizable parameters
    lookback_period = 8
    min_factors = 3  # Need at least 3 factors to agree
    factor_threshold = 1.5  # Individual factor threshold (in std dev)
    use_divergences = True  # Trade divergences
    composite_threshold = 2.0  # Composite score threshold
    take_profit = 0.004
    stop_loss = 0.0025

    def init(self):
        """Initialize indicators"""
        # Calculate zones
        self.support = self.I(lambda: pd.Series(self.data.Close).rolling(
            window=self.lookback_period, min_periods=1).min())
        self.resistance = self.I(lambda: pd.Series(self.data.Close).rolling(
            window=self.lookback_period, min_periods=1).max())

        # Factor scores
        self.zscore_5 = self.I(lambda: self.data.ZScore_5)
        self.zscore_10 = self.I(lambda: self.data.ZScore_10)
        self.zscore_20 = self.I(lambda: self.data.ZScore_20)
        self.volume_score = self.I(lambda: self.data.Volume_Score)
        self.vol_zscore = self.I(lambda: self.data.Vol_ZScore)
        self.rsi_score = self.I(lambda: self.data.RSI_Score)
        self.spread_score = self.I(lambda: self.data.Spread_Score)
        self.of_score = self.I(lambda: self.data.OF_Score)
        self.composite_score = self.I(lambda: self.data.Composite_Score)

        # Divergences
        self.price_volume_div = self.I(lambda: self.data.Price_Volume_Divergence)
        self.price_vol_div = self.I(lambda: self.data.Price_Vol_Divergence)

        # Bollinger Bands
        self.bb_middle = self.I(lambda: self.data.BB_Middle)

        # Track factor performance
        self.factor_weights = [1, 1, 1, 1, 1, 1]  # Start with equal weights

    def count_buy_factors(self):
        """Count how many factors suggest buying"""
        count = 0

        # Price oversold
        if self.zscore_10[-1] and self.zscore_10[-1] < -self.factor_threshold:
            count += 1

        # Volume spike on down move
        if self.volume_score[-1] and self.volume_score[-1] > 0.5:
            if self.data.Close[-1] < self.data.Open[-1]:
                count += 1

        # Low volatility (good for mean reversion)
        if self.vol_zscore[-1] and self.vol_zscore[-1] < -0.5:
            count += 1

        # RSI oversold
        if self.rsi_score[-1] and self.rsi_score[-1] < -0.3:
            count += 1

        # Tight spread (efficient market)
        if self.spread_score[-1] and self.spread_score[-1] > 0.5:
            count += 1

        # Negative order flow (selling pressure exhaustion)
        if self.of_score[-1] and self.of_score[-1] < -0.3:
            count += 1

        return count

    def count_sell_factors(self):
        """Count how many factors suggest selling"""
        count = 0

        # Price overbought
        if self.zscore_10[-1] and self.zscore_10[-1] > self.factor_threshold:
            count += 1

        # Volume spike on up move
        if self.volume_score[-1] and self.volume_score[-1] > 0.5:
            if self.data.Close[-1] > self.data.Open[-1]:
                count += 1

        # Low volatility (good for mean reversion)
        if self.vol_zscore[-1] and self.vol_zscore[-1] < -0.5:
            count += 1

        # RSI overbought
        if self.rsi_score[-1] and self.rsi_score[-1] > 0.3:
            count += 1

        # Tight spread (efficient market)
        if self.spread_score[-1] and self.spread_score[-1] > 0.5:
            count += 1

        # Positive order flow (buying pressure exhaustion)
        if self.of_score[-1] and self.of_score[-1] > 0.3:
            count += 1

        return count

    def next(self):
        """Main strategy logic"""

        # Skip if insufficient data
        if len(self.data) < 50:
            return

        # Get current values
        current_price = self.data.Close[-1]
        current_composite = self.composite_score[-1] if self.composite_score[-1] else 0
        current_bb_middle = self.bb_middle[-1] if self.bb_middle[-1] else current_price

        # Check for NaN in key indicators
        if np.isnan(current_composite):
            current_composite = 0

        # Get zones
        demand_zone = self.support[-1]
        supply_zone = self.resistance[-1]

        # Check divergences
        has_price_volume_div = self.price_volume_div[-1] == 1 if self.price_volume_div[-1] else False
        has_price_vol_div = self.price_vol_div[-1] == 1 if self.price_vol_div[-1] else False

        # Exit logic
        if self.position:
            # Multi-factor exit
            if self.position.is_long:
                exit_factors = self.count_sell_factors()
                if exit_factors >= 2 and self.position.pl_pct > 0:
                    self.position.close()
                    return
            else:
                exit_factors = self.count_buy_factors()
                if exit_factors >= 2 and self.position.pl_pct > 0:
                    self.position.close()
                    return

        # Entry logic
        if not self.position:

            # Zone proximity
            near_demand = abs(current_price - demand_zone) / demand_zone <= 0.005
            near_supply = abs(current_price - supply_zone) / supply_zone <= 0.005

            # Count factors
            buy_factors = self.count_buy_factors()
            sell_factors = self.count_sell_factors()

            # BUY signals
            buy_signal = False

            # Multi-factor agreement
            if buy_factors >= self.min_factors and near_demand:
                buy_signal = True

            # Composite score extreme
            elif current_composite < -self.composite_threshold and near_demand:
                buy_signal = True

            # Divergence trades
            elif self.use_divergences:
                if (has_price_volume_div or has_price_vol_div) and near_demand:
                    if self.zscore_10[-1] and self.zscore_10[-1] < -1:
                        buy_signal = True

            if buy_signal:
                # Dynamic targets based on factor strength
                factor_strength = min(buy_factors / self.min_factors, 1.5)
                tp_mult = self.take_profit * factor_strength

                sl_price = current_price * (1 - self.stop_loss)
                tp_price = max(current_bb_middle, current_price * (1 + tp_mult))
                if tp_price <= current_price * 1.001:
                    tp_price = current_price * (1 + self.take_profit)

                self.buy(sl=sl_price, tp=tp_price)

            # SELL signals
            else:
                sell_signal = False

                # Multi-factor agreement
                if sell_factors >= self.min_factors and near_supply:
                    sell_signal = True

                # Composite score extreme
                elif current_composite > self.composite_threshold and near_supply:
                    sell_signal = True

                # Divergence trades
                elif self.use_divergences:
                    if (has_price_volume_div or has_price_vol_div) and near_supply:
                        if self.zscore_10[-1] and self.zscore_10[-1] > 1:
                            sell_signal = True

                if sell_signal:
                    # Dynamic targets based on factor strength
                    factor_strength = min(sell_factors / self.min_factors, 1.5)
                    tp_mult = self.take_profit * factor_strength

                    sl_price = current_price * (1 + self.stop_loss)
                    tp_price = min(current_bb_middle, current_price * (1 - tp_mult))
                    if tp_price >= current_price * 0.999:
                        tp_price = current_price * (1 - self.take_profit)

                    self.sell(sl=sl_price, tp=tp_price)


# Run baseline backtest
print("\n" + "="*70)
print("RUNNING MULTI-FACTOR BACKTEST")
print("="*70)

bt = Backtest(
    data,
    SDZStatArbMultiFactorStrategy,
    cash=1000000,
    commission=0.001,
    exclusive_orders=True
)

# Run baseline
baseline_stats = bt.run()

print(f"\n📊 BASELINE RESULTS:")
print(f"Lookback: {SDZStatArbMultiFactorStrategy.lookback_period} bars")
print(f"Min Factors: {SDZStatArbMultiFactorStrategy.min_factors}")
print(f"Factor Threshold: {SDZStatArbMultiFactorStrategy.factor_threshold}")
print(f"Composite Threshold: {SDZStatArbMultiFactorStrategy.composite_threshold}")
print(f"Take Profit: {SDZStatArbMultiFactorStrategy.take_profit*100:.1f}%")
print(f"Stop Loss: {SDZStatArbMultiFactorStrategy.stop_loss*100:.2f}%")
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
        min_factors=[2, 3, 4],
        factor_threshold=[1.0, 1.5, 2.0],
        composite_threshold=[1.5, 2.0, 2.5],
        take_profit=[0.0035, 0.004, 0.0045],
        stop_loss=[0.002, 0.0025, 0.003],
        maximize='Return [%]',
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
    print(f"Lookback Period: {optimization_results._strategy.lookback_period} bars")
    print(f"Min Factors: {optimization_results._strategy.min_factors}")
    print(f"Factor Threshold: {optimization_results._strategy.factor_threshold}")
    print(f"Composite Threshold: {optimization_results._strategy.composite_threshold}")
    print(f"Take Profit: {optimization_results._strategy.take_profit*100:.2f}%")
    print(f"Stop Loss: {optimization_results._strategy.stop_loss*100:.2f}%")

except Exception as e:
    print(f"\n⚠️ Optimization failed: {str(e)}")

# Show plot
print("\n📊 Generating plot...")
bt.plot()