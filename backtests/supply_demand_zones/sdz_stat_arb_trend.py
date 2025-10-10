"""
Supply and Demand Zones STATISTICAL ARBITRAGE with TREND FILTER Strategy
=========================================================================

Enhanced stat arb that filters trades based on underlying trend strength.

Theory:
- Mean reversion works better in ranging markets
- Trend trades work better in trending markets
- Combine z-score with trend detection for optimal entries
- Use EMA ribbon and ADX for trend confirmation

Trading Logic:
- In strong trends: Trade with trend at extreme z-scores
- In ranging markets: Trade mean reversion at any z-score
- Dynamic z-score thresholds based on trend strength
- Exit based on trend exhaustion signals
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's SDZ STATISTICAL ARBITRAGE + TREND FILTER Strategy 🌙")
print("=" * 70)

# Load BTC 1-minute data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1m-4wks-data.csv'
print(f"📊 Loading BTC 1-minute data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)

# Rename columns
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Calculate statistical indicators
def calculate_zscore(series, period):
    mean = series.rolling(period).mean()
    std = series.rolling(period).std()
    zscore = (series - mean) / std
    return zscore

# Multiple timeframe z-scores
data['ZScore_5'] = calculate_zscore(data['Close'], 5)
data['ZScore_10'] = calculate_zscore(data['Close'], 10)
data['ZScore_20'] = calculate_zscore(data['Close'], 20)

# Trend indicators
data['EMA_8'] = ta.ema(data['Close'], length=8)
data['EMA_21'] = ta.ema(data['Close'], length=21)
data['EMA_50'] = ta.ema(data['Close'], length=50)

# ADX for trend strength
adx_data = ta.adx(data['High'], data['Low'], data['Close'], length=14)
data['ADX'] = adx_data['ADX_14']
data['DI_plus'] = adx_data['DMP_14']
data['DI_minus'] = adx_data['DMN_14']

# Trend score (-100 to +100)
def calculate_trend_score(row):
    score = 0
    # EMA alignment
    if row['EMA_8'] > row['EMA_21'] > row['EMA_50']:
        score += 50
    elif row['EMA_8'] < row['EMA_21'] < row['EMA_50']:
        score -= 50
    # ADX strength
    if row['ADX'] > 25:
        if row['DI_plus'] > row['DI_minus']:
            score += row['ADX']
        else:
            score -= row['ADX']
    return score

data['Trend_Score'] = data.apply(calculate_trend_score, axis=1)

# Bollinger Bands
data['BB_Middle'] = data['Close'].rolling(20).mean()
data['BB_Std'] = data['Close'].rolling(20).std()
data['BB_Upper'] = data['BB_Middle'] + (data['BB_Std'] * 2)
data['BB_Lower'] = data['BB_Middle'] - (data['BB_Std'] * 2)
data['BB_Width'] = (data['BB_Upper'] - data['BB_Lower']) / data['BB_Middle']

print(f"✅ Loaded {len(data):,} 1-minute bars")
print(f"📅 Date range: {data.index.min()} → {data.index.max()}")


class SDZStatArbTrendStrategy(Strategy):
    """
    Statistical Arbitrage with Trend Filter Strategy

    Parameters:
    - lookback_period: Period for zone calculation
    - zscore_entry_ranging: Z-score for ranging markets
    - zscore_entry_trending: Z-score for trending markets
    - trend_threshold: Threshold for trend detection
    - trend_align_only: Only trade with trend in strong trends
    - take_profit: Profit target
    - stop_loss: Stop loss
    """

    # Optimizable parameters
    lookback_period = 8
    zscore_entry_ranging = 1.5  # Lower threshold for ranging
    zscore_entry_trending = 2.5  # Higher threshold for trending
    trend_threshold = 30  # Trend score threshold
    trend_align_only = True  # Only with-trend trades in trends
    take_profit = 0.004
    stop_loss = 0.0025

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

        # Trend indicators
        self.trend_score = self.I(lambda: self.data.Trend_Score)
        self.adx = self.I(lambda: self.data.ADX)
        self.ema_8 = self.I(lambda: self.data.EMA_8)
        self.ema_21 = self.I(lambda: self.data.EMA_21)

        # Bollinger Bands
        self.bb_middle = self.I(lambda: self.data.BB_Middle)
        self.bb_width = self.I(lambda: self.data.BB_Width)

        # Track entry conditions
        self.entry_zscore = 0
        self.entry_trend = 0

    def next(self):
        """Main strategy logic"""

        # Skip if insufficient data
        if len(self.data) < 50:
            return

        # Get current values
        current_price = self.data.Close[-1]
        z5 = self.zscore_5[-1] if self.zscore_5[-1] and not np.isnan(self.zscore_5[-1]) else 0
        z10 = self.zscore_10[-1] if self.zscore_10[-1] and not np.isnan(self.zscore_10[-1]) else 0
        z20 = self.zscore_20[-1] if self.zscore_20[-1] and not np.isnan(self.zscore_20[-1]) else 0
        current_trend = self.trend_score[-1] if self.trend_score[-1] else 0
        current_adx = self.adx[-1] if self.adx[-1] else 20
        current_bb_middle = self.bb_middle[-1] if self.bb_middle[-1] and not np.isnan(self.bb_middle[-1]) else current_price
        current_bb_width = self.bb_width[-1] if self.bb_width[-1] and not np.isnan(self.bb_width[-1]) else 0.02

        # Get zones
        demand_zone = self.support[-1]
        supply_zone = self.resistance[-1]

        # Determine market regime
        is_trending_up = current_trend > self.trend_threshold
        is_trending_down = current_trend < -self.trend_threshold
        is_ranging = abs(current_trend) <= self.trend_threshold

        # Exit logic
        if self.position:
            # Exit based on trend change
            if self.position.is_long:
                # Exit long if trend turns bearish
                if current_trend < -self.trend_threshold and self.entry_trend > 0:
                    self.position.close()
                    return
                # Normal z-score exit
                if z5 > -0.5 and self.position.pl_pct > 0:
                    self.position.close()
                    return
            else:
                # Exit short if trend turns bullish
                if current_trend > self.trend_threshold and self.entry_trend < 0:
                    self.position.close()
                    return
                # Normal z-score exit
                if z5 < 0.5 and self.position.pl_pct > 0:
                    self.position.close()
                    return

        # Entry logic
        if not self.position:

            # Zone proximity
            near_demand = abs(current_price - demand_zone) / demand_zone <= 0.005
            near_supply = abs(current_price - supply_zone) / supply_zone <= 0.005

            # Adaptive z-score threshold
            if is_ranging:
                zscore_thresh = self.zscore_entry_ranging
            else:
                zscore_thresh = self.zscore_entry_trending

            # BUY signals
            buy_signal = False

            if is_ranging:
                # Classic mean reversion in ranging market
                if z5 < -zscore_thresh and near_demand:
                    buy_signal = True
                # Multi-timeframe confirmation
                elif z5 < -zscore_thresh * 0.8 and z10 < -zscore_thresh * 0.7:
                    if near_demand:
                        buy_signal = True

            elif is_trending_up and not self.trend_align_only:
                # Pullback in uptrend
                if z5 < -zscore_thresh * 0.7 and near_demand:
                    buy_signal = True

            elif is_trending_down:
                # Counter-trend only at extreme oversold
                if z5 < -zscore_thresh * 1.5 and z10 < -zscore_thresh:
                    if near_demand:
                        buy_signal = True

            if buy_signal:
                # Dynamic targets based on market regime
                if is_trending_up:
                    tp_mult = self.take_profit * 1.5  # Larger target in trend
                else:
                    tp_mult = self.take_profit

                sl_price = current_price * (1 - self.stop_loss)
                # Ensure bb_middle is valid
                if not np.isnan(current_bb_middle):
                    tp_price = max(current_bb_middle, current_price * (1 + tp_mult))
                else:
                    tp_price = current_price * (1 + tp_mult)
                # Final check
                if tp_price <= current_price * 1.001:
                    tp_price = current_price * (1 + self.take_profit)

                self.buy(sl=sl_price, tp=tp_price)
                self.entry_zscore = z5
                self.entry_trend = current_trend

            # SELL signals
            else:
                sell_signal = False

                if is_ranging:
                    # Classic mean reversion in ranging market
                    if z5 > zscore_thresh and near_supply:
                        sell_signal = True
                    # Multi-timeframe confirmation
                    elif z5 > zscore_thresh * 0.8 and z10 > zscore_thresh * 0.7:
                        if near_supply:
                            sell_signal = True

                elif is_trending_down and not self.trend_align_only:
                    # Pullback in downtrend
                    if z5 > zscore_thresh * 0.7 and near_supply:
                        sell_signal = True

                elif is_trending_up:
                    # Counter-trend only at extreme overbought
                    if z5 > zscore_thresh * 1.5 and z10 > zscore_thresh:
                        if near_supply:
                            sell_signal = True

                if sell_signal:
                    # Dynamic targets based on market regime
                    if is_trending_down:
                        tp_mult = self.take_profit * 1.5  # Larger target in trend
                    else:
                        tp_mult = self.take_profit

                    sl_price = current_price * (1 + self.stop_loss)
                    # Ensure bb_middle is valid
                    if not np.isnan(current_bb_middle):
                        tp_price = min(current_bb_middle, current_price * (1 - tp_mult))
                    else:
                        tp_price = current_price * (1 - tp_mult)
                    # Final check
                    if tp_price >= current_price * 0.999:
                        tp_price = current_price * (1 - self.take_profit)

                    self.sell(sl=sl_price, tp=tp_price)
                    self.entry_zscore = z5
                    self.entry_trend = current_trend


# Run baseline backtest
print("\n" + "="*70)
print("RUNNING STAT ARB + TREND FILTER BACKTEST")
print("="*70)

bt = Backtest(
    data,
    SDZStatArbTrendStrategy,
    cash=1000000,
    commission=0.001,
    exclusive_orders=True
)

# Run baseline
baseline_stats = bt.run()

print(f"\n📊 BASELINE RESULTS:")
print(f"Lookback: {SDZStatArbTrendStrategy.lookback_period} bars")
print(f"Z-Score Ranging: {SDZStatArbTrendStrategy.zscore_entry_ranging}")
print(f"Z-Score Trending: {SDZStatArbTrendStrategy.zscore_entry_trending}")
print(f"Trend Threshold: {SDZStatArbTrendStrategy.trend_threshold}")
print(f"Take Profit: {SDZStatArbTrendStrategy.take_profit*100:.1f}%")
print(f"Stop Loss: {SDZStatArbTrendStrategy.stop_loss*100:.2f}%")
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
        zscore_entry_ranging=[1.2, 1.5, 1.8],
        zscore_entry_trending=[2.0, 2.5, 3.0],
        trend_threshold=[20, 30, 40],
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
    print(f"Sharpe: {optimization_results['Sharpe Ratio']:.2f}")
    print(f"Lookback Period: {optimization_results._strategy.lookback_period} bars")
    print(f"Z-Score Ranging: {optimization_results._strategy.zscore_entry_ranging}")
    print(f"Z-Score Trending: {optimization_results._strategy.zscore_entry_trending}")
    print(f"Trend Threshold: {optimization_results._strategy.trend_threshold}")
    print(f"Take Profit: {optimization_results._strategy.take_profit*100:.2f}%")
    print(f"Stop Loss: {optimization_results._strategy.stop_loss*100:.2f}%")

except Exception as e:
    print(f"\n⚠️ Optimization failed: {str(e)}")

# Show plot
print("\n📊 Generating plot...")
bt.plot()