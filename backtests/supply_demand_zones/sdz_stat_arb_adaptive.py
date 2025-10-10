"""
Supply and Demand Zones STATISTICAL ARBITRAGE with ADAPTIVE Z-SCORE Strategy
=============================================================================

Machine learning inspired adaptive z-score thresholds based on market conditions.

Theory:
- Z-score thresholds should adapt to market volatility
- Use rolling performance metrics to adjust parameters
- Learn from recent trade outcomes
- Dynamic lookback periods based on volatility regime

Trading Logic:
- Calculate adaptive z-score thresholds based on recent volatility
- Adjust lookback periods dynamically
- Use win rate feedback to tighten/loosen entry criteria
- Volatility-scaled position sizing concept
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's SDZ STATISTICAL ARBITRAGE + ADAPTIVE Z-SCORE Strategy 🌙")
print("=" * 70)

# Load BTC 1-minute data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1m-4wks-data.csv'
print(f"📊 Loading BTC 1-minute data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)

# Rename columns
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Calculate adaptive indicators
# Volatility metrics
data['Returns'] = data['Close'].pct_change()
data['Volatility_5'] = data['Returns'].rolling(5).std()
data['Volatility_20'] = data['Returns'].rolling(20).std()
data['Volatility_60'] = data['Returns'].rolling(60).std()

# Volatility regime (percentile based)
data['Vol_Percentile'] = data['Volatility_20'].rolling(100).rank(pct=True) * 100

# Market efficiency (trending vs choppy)
def calculate_efficiency(close, period=10):
    net_change = abs(close - close.shift(period))
    total_change = abs(close - close.shift(1)).rolling(period).sum()
    return net_change / (total_change + 0.0001)

data['Efficiency'] = calculate_efficiency(data['Close'])

# Dynamic lookback based on volatility
def get_adaptive_lookback(vol_percentile):
    if vol_percentile < 30:
        return 5  # Low vol = shorter lookback
    elif vol_percentile < 70:
        return 10  # Medium vol = medium lookback
    else:
        return 20  # High vol = longer lookback

# Multiple adaptive z-scores
for lookback in [5, 10, 20]:
    mean = data['Close'].rolling(lookback).mean()
    std = data['Close'].rolling(lookback).std()
    data[f'ZScore_{lookback}'] = (data['Close'] - mean) / std

# Adaptive threshold calculation
data['Adaptive_Threshold'] = 1.5 + (data['Vol_Percentile'] / 100)  # 1.5 to 2.5 based on volatility

# Feature engineering for ML-like pattern recognition
data['High_Low_Ratio'] = data['High'] / data['Low']
data['Close_Open_Ratio'] = data['Close'] / data['Open']
data['Volume_Change'] = data['Volume'].pct_change()

# Bollinger Bands
data['BB_Middle'] = data['Close'].rolling(20).mean()
data['BB_Std'] = data['Close'].rolling(20).std()
data['BB_Upper'] = data['BB_Middle'] + (data['BB_Std'] * 2)
data['BB_Lower'] = data['BB_Middle'] - (data['BB_Std'] * 2)

print(f"✅ Loaded {len(data):,} 1-minute bars")
print(f"📅 Date range: {data.index.min()} → {data.index.max()}")


class SDZStatArbAdaptiveStrategy(Strategy):
    """
    Statistical Arbitrage with Adaptive Z-Score Strategy

    Parameters:
    - base_lookback: Base lookback period
    - base_zscore: Base z-score threshold
    - adapt_factor: How much to adapt based on volatility
    - efficiency_filter: Minimum efficiency for trades
    - vol_scale_positions: Scale positions by volatility
    - take_profit: Base profit target
    - stop_loss: Base stop loss
    """

    # Optimizable parameters
    base_lookback = 10
    base_zscore = 2.0
    adapt_factor = 0.5  # How much to adapt (0 = no adaptation, 1 = full)
    efficiency_filter = 0.2  # Minimum efficiency
    vol_scale_positions = True  # Adapt targets to volatility
    take_profit = 0.004
    stop_loss = 0.0025

    def init(self):
        """Initialize indicators"""
        # Calculate zones (using base lookback)
        self.support = self.I(lambda: pd.Series(self.data.Close).rolling(
            window=self.base_lookback, min_periods=1).min())
        self.resistance = self.I(lambda: pd.Series(self.data.Close).rolling(
            window=self.base_lookback, min_periods=1).max())

        # Adaptive indicators
        self.vol_percentile = self.I(lambda: self.data.Vol_Percentile)
        self.efficiency = self.I(lambda: self.data.Efficiency)
        self.adaptive_threshold = self.I(lambda: self.data.Adaptive_Threshold)

        # Z-scores
        self.zscore_5 = self.I(lambda: self.data.ZScore_5)
        self.zscore_10 = self.I(lambda: self.data.ZScore_10)
        self.zscore_20 = self.I(lambda: self.data.ZScore_20)

        # Volatility
        self.volatility_5 = self.I(lambda: self.data.Volatility_5)
        self.volatility_20 = self.I(lambda: self.data.Volatility_20)

        # Bollinger Bands
        self.bb_middle = self.I(lambda: self.data.BB_Middle)

        # Track performance for adaptation
        self.recent_trades = []
        self.adaptive_win_rate = 0.5
        self.entry_volatility = 0

    def get_adaptive_zscore(self):
        """Get the appropriate z-score based on current volatility"""
        if len(self.data) < 100:
            return self.zscore_10[-1] if self.zscore_10[-1] else 0

        vol_pct = self.vol_percentile[-1] if self.vol_percentile[-1] else 50

        # Choose z-score based on volatility
        if vol_pct < 30:
            return self.zscore_5[-1] if self.zscore_5[-1] and not np.isnan(self.zscore_5[-1]) else 0
        elif vol_pct < 70:
            return self.zscore_10[-1] if self.zscore_10[-1] and not np.isnan(self.zscore_10[-1]) else 0
        else:
            return self.zscore_20[-1] if self.zscore_20[-1] and not np.isnan(self.zscore_20[-1]) else 0

    def get_adaptive_threshold(self):
        """Calculate adaptive entry threshold"""
        base = self.base_zscore

        # Adjust based on volatility
        vol_adjustment = 0
        if self.vol_percentile[-1]:
            vol_adjustment = (self.vol_percentile[-1] - 50) / 100  # -0.5 to +0.5

        # Adjust based on recent performance
        performance_adjustment = 0
        if len(self.recent_trades) >= 10:
            recent_win_rate = sum(self.recent_trades[-10:]) / 10
            if recent_win_rate < 0.4:  # Losing streak - be more selective
                performance_adjustment = 0.3
            elif recent_win_rate > 0.7:  # Winning streak - can be less selective
                performance_adjustment = -0.2

        # Combine adjustments
        adaptive_threshold = base + (vol_adjustment + performance_adjustment) * self.adapt_factor

        return max(1.0, min(3.0, adaptive_threshold))  # Clamp between 1 and 3

    def next(self):
        """Main strategy logic"""

        # Skip if insufficient data
        if len(self.data) < 100:
            return

        # Get current values
        current_price = self.data.Close[-1]
        current_zscore = self.get_adaptive_zscore()
        current_threshold = self.get_adaptive_threshold()
        current_efficiency = self.efficiency[-1] if self.efficiency[-1] else 0.5
        current_volatility = self.volatility_20[-1] if self.volatility_20[-1] else 0.001
        current_bb_middle = self.bb_middle[-1] if self.bb_middle[-1] else current_price

        # Get zones
        demand_zone = self.support[-1]
        supply_zone = self.resistance[-1]

        # Exit logic
        if self.position:
            # Adaptive exit based on volatility
            exit_threshold = 0.5 * (1 + current_volatility / self.entry_volatility) if self.entry_volatility > 0 else 0.5

            if self.position.is_long:
                if current_zscore > -exit_threshold and self.position.pl_pct > 0:
                    # Track trade result before closing
                    self.recent_trades.append(1 if self.position.pl_pct > 0 else 0)
                    if len(self.recent_trades) > 20:
                        self.recent_trades.pop(0)
                    self.position.close()
                    return
            else:
                if current_zscore < exit_threshold and self.position.pl_pct > 0:
                    # Track trade result before closing
                    self.recent_trades.append(1 if self.position.pl_pct > 0 else 0)
                    if len(self.recent_trades) > 20:
                        self.recent_trades.pop(0)
                    self.position.close()
                    return

        # Entry logic
        if not self.position:

            # Skip if market is too choppy
            if current_efficiency < self.efficiency_filter:
                return

            # Zone proximity
            near_demand = abs(current_price - demand_zone) / demand_zone <= 0.005
            near_supply = abs(current_price - supply_zone) / supply_zone <= 0.005

            # BUY signals with adaptive threshold
            if current_zscore < -current_threshold and near_demand:

                # Adaptive targets based on volatility
                if self.vol_scale_positions:
                    vol_mult = max(0.5, min(2.0, current_volatility / 0.001))  # Scale based on vol
                    tp_mult = self.take_profit * vol_mult
                    sl_mult = self.stop_loss * vol_mult
                else:
                    tp_mult = self.take_profit
                    sl_mult = self.stop_loss

                sl_price = current_price * (1 - sl_mult)
                tp_price = max(current_bb_middle, current_price * (1 + tp_mult))
                if tp_price <= current_price * 1.001:
                    tp_price = current_price * (1 + tp_mult)

                self.buy(sl=sl_price, tp=tp_price)
                self.entry_volatility = current_volatility

            # SELL signals with adaptive threshold
            elif current_zscore > current_threshold and near_supply:

                # Adaptive targets based on volatility
                if self.vol_scale_positions:
                    vol_mult = max(0.5, min(2.0, current_volatility / 0.001))
                    tp_mult = self.take_profit * vol_mult
                    sl_mult = self.stop_loss * vol_mult
                else:
                    tp_mult = self.take_profit
                    sl_mult = self.stop_loss

                sl_price = current_price * (1 + sl_mult)
                tp_price = min(current_bb_middle, current_price * (1 - tp_mult))
                if tp_price >= current_price * 0.999:
                    tp_price = current_price * (1 - tp_mult)

                self.sell(sl=sl_price, tp=tp_price)
                self.entry_volatility = current_volatility


# Run baseline backtest
print("\n" + "="*70)
print("RUNNING ADAPTIVE Z-SCORE BACKTEST")
print("="*70)

bt = Backtest(
    data,
    SDZStatArbAdaptiveStrategy,
    cash=1000000,
    commission=0.001,
    exclusive_orders=True
)

# Run baseline
baseline_stats = bt.run()

print(f"\n📊 BASELINE RESULTS:")
print(f"Base Lookback: {SDZStatArbAdaptiveStrategy.base_lookback} bars")
print(f"Base Z-Score: {SDZStatArbAdaptiveStrategy.base_zscore}")
print(f"Adapt Factor: {SDZStatArbAdaptiveStrategy.adapt_factor}")
print(f"Efficiency Filter: {SDZStatArbAdaptiveStrategy.efficiency_filter}")
print(f"Take Profit: {SDZStatArbAdaptiveStrategy.take_profit*100:.1f}%")
print(f"Stop Loss: {SDZStatArbAdaptiveStrategy.stop_loss*100:.2f}%")
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
        base_lookback=[8, 10, 12],
        base_zscore=[1.5, 2.0, 2.5],
        adapt_factor=[0.3, 0.5, 0.7],
        efficiency_filter=[0.15, 0.2, 0.25],
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
    print(f"Base Lookback: {optimization_results._strategy.base_lookback} bars")
    print(f"Base Z-Score: {optimization_results._strategy.base_zscore}")
    print(f"Adapt Factor: {optimization_results._strategy.adapt_factor}")
    print(f"Efficiency Filter: {optimization_results._strategy.efficiency_filter}")
    print(f"Take Profit: {optimization_results._strategy.take_profit*100:.2f}%")
    print(f"Stop Loss: {optimization_results._strategy.stop_loss*100:.2f}%")

except Exception as e:
    print(f"\n⚠️ Optimization failed: {str(e)}")

# Show plot
print("\n📊 Generating plot...")
bt.plot()