"""
Supply and Demand Zones STATISTICAL ARBITRAGE with REGIME DETECTION Strategy
=============================================================================

Market regime detection to switch between different z-score strategies.

Theory:
- Markets cycle through different regimes (trending, ranging, volatile, calm)
- Each regime requires different statistical approaches
- Use Hidden Markov Model concept for regime detection
- Switch strategies based on detected regime

Trading Logic:
- Identify current market regime using multiple metrics
- Apply regime-specific z-score thresholds and exits
- Use regime transitions as additional signals
- Adapt position sizing to regime volatility
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's SDZ STATISTICAL ARBITRAGE + REGIME DETECTION Strategy 🌙")
print("=" * 70)

# Load BTC 1-minute data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1m-4wks-data.csv'
print(f"📊 Loading BTC 1-minute data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)

# Rename columns
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Calculate regime detection indicators
# Returns and volatility
data['Returns'] = data['Close'].pct_change()
data['Volatility'] = data['Returns'].rolling(20).std()
data['Volatility_MA'] = data['Volatility'].rolling(50).mean()

# Trend strength (ADX)
adx_data = ta.adx(data['High'], data['Low'], data['Close'], length=14)
data['ADX'] = adx_data['ADX_14']

# Mean reversion tendency (Hurst exponent proxy)
def hurst_proxy(series, period=20):
    """Simple Hurst exponent proxy"""
    if len(series) < period:
        return 0.5

    mean_returns = []
    for lag in range(1, min(5, len(series))):
        mean_returns.append(np.mean(np.abs(series.diff(lag).dropna())))

    if len(mean_returns) > 1:
        hurst = np.polyfit(np.log(range(1, len(mean_returns) + 1)),
                          np.log(mean_returns), 1)[0]
        return min(1, max(0, hurst))
    return 0.5

data['Hurst'] = data['Returns'].rolling(50).apply(hurst_proxy, raw=False)

# Regime classification
def classify_regime(row):
    """
    Classify market regime:
    0: Low Volatility Ranging
    1: High Volatility Ranging
    2: Trending Up
    3: Trending Down
    4: Volatile Breakout
    """
    vol_high = row['Volatility'] > row['Volatility_MA'] * 1.2
    trending = row['ADX'] > 25
    mean_reverting = row['Hurst'] < 0.5

    if trending:
        if row['Returns'] > 0:
            return 2  # Trending Up
        else:
            return 3  # Trending Down
    elif vol_high:
        if mean_reverting:
            return 1  # High Vol Ranging
        else:
            return 4  # Volatile Breakout
    else:
        return 0  # Low Vol Ranging

data['Regime'] = data.apply(classify_regime, axis=1)

# Regime change detection
data['Regime_Change'] = (data['Regime'] != data['Regime'].shift(1)).astype(int)

# Z-scores
def calculate_zscore(series, period):
    mean = series.rolling(period).mean()
    std = series.rolling(period).std()
    zscore = (series - mean) / std
    return zscore

data['ZScore_5'] = calculate_zscore(data['Close'], 5)
data['ZScore_10'] = calculate_zscore(data['Close'], 10)
data['ZScore_20'] = calculate_zscore(data['Close'], 20)

# Bollinger Bands
data['BB_Middle'] = data['Close'].rolling(20).mean()
data['BB_Std'] = data['Close'].rolling(20).std()

print(f"✅ Loaded {len(data):,} 1-minute bars")
print(f"📅 Date range: {data.index.min()} → {data.index.max()}")


class SDZStatArbRegimeStrategy(Strategy):
    """
    Statistical Arbitrage with Regime Detection Strategy

    Parameters by regime:
    - zscore_low_vol: Z-score for low volatility ranging
    - zscore_high_vol: Z-score for high volatility ranging
    - zscore_trending: Z-score for trending markets
    - zscore_breakout: Z-score for breakout regime
    - regime_transition_trade: Trade on regime changes
    - take_profit: Base profit target
    - stop_loss: Base stop loss
    """

    # Optimizable parameters
    lookback_period = 8
    zscore_low_vol = 1.5  # Low vol = tighter threshold
    zscore_high_vol = 2.5  # High vol = wider threshold
    zscore_trending = 2.0  # Trending = medium threshold
    zscore_breakout = 3.0  # Breakout = widest threshold
    regime_transition_trade = True
    take_profit = 0.004
    stop_loss = 0.0025

    def init(self):
        """Initialize indicators"""
        # Calculate zones
        self.support = self.I(lambda: pd.Series(self.data.Close).rolling(
            window=self.lookback_period, min_periods=1).min())
        self.resistance = self.I(lambda: pd.Series(self.data.Close).rolling(
            window=self.lookback_period, min_periods=1).max())

        # Regime indicators
        self.regime = self.I(lambda: self.data.Regime)
        self.regime_change = self.I(lambda: self.data.Regime_Change)
        self.volatility = self.I(lambda: self.data.Volatility)
        self.adx = self.I(lambda: self.data.ADX)

        # Z-scores
        self.zscore_5 = self.I(lambda: self.data.ZScore_5)
        self.zscore_10 = self.I(lambda: self.data.ZScore_10)
        self.zscore_20 = self.I(lambda: self.data.ZScore_20)

        # Bollinger Bands
        self.bb_middle = self.I(lambda: self.data.BB_Middle)

        # Track entry regime
        self.entry_regime = 0

    def get_regime_params(self, regime):
        """Get parameters for current regime"""
        regime_params = {
            0: {'zscore': self.zscore_low_vol, 'tp_mult': 0.8, 'sl_mult': 0.8},   # Low Vol
            1: {'zscore': self.zscore_high_vol, 'tp_mult': 1.2, 'sl_mult': 1.2},  # High Vol
            2: {'zscore': self.zscore_trending, 'tp_mult': 1.5, 'sl_mult': 1.0},  # Trend Up
            3: {'zscore': self.zscore_trending, 'tp_mult': 1.5, 'sl_mult': 1.0},  # Trend Down
            4: {'zscore': self.zscore_breakout, 'tp_mult': 2.0, 'sl_mult': 1.5},  # Breakout
        }
        return regime_params.get(regime, {'zscore': 2.0, 'tp_mult': 1.0, 'sl_mult': 1.0})

    def next(self):
        """Main strategy logic"""

        # Skip if insufficient data
        if len(self.data) < 50:
            return

        # Get current values
        current_price = self.data.Close[-1]
        current_regime = int(self.regime[-1]) if self.regime[-1] else 0
        regime_changed = self.regime_change[-1] == 1
        current_volatility = self.volatility[-1] if self.volatility[-1] else 0.001
        current_bb_middle = self.bb_middle[-1] if self.bb_middle[-1] else current_price

        # Get regime-appropriate z-score
        if current_regime in [0, 1]:  # Ranging regimes use shorter z-score
            current_zscore = self.zscore_5[-1] if self.zscore_5[-1] and not np.isnan(self.zscore_5[-1]) else 0
        elif current_regime in [2, 3]:  # Trending regimes use medium z-score
            current_zscore = self.zscore_10[-1] if self.zscore_10[-1] and not np.isnan(self.zscore_10[-1]) else 0
        else:  # Breakout regime uses longer z-score
            current_zscore = self.zscore_20[-1] if self.zscore_20[-1] and not np.isnan(self.zscore_20[-1]) else 0

        # Get zones
        demand_zone = self.support[-1]
        supply_zone = self.resistance[-1]

        # Get regime parameters
        regime_params = self.get_regime_params(current_regime)
        zscore_threshold = regime_params['zscore']
        tp_multiplier = regime_params['tp_mult']
        sl_multiplier = regime_params['sl_mult']

        # Exit logic
        if self.position:
            # Exit on adverse regime change
            if regime_changed:
                # Exit longs if switching to strong downtrend
                if self.position.is_long and current_regime == 3:
                    self.position.close()
                    return
                # Exit shorts if switching to strong uptrend
                elif self.position.is_short and current_regime == 2:
                    self.position.close()
                    return

            # Regime-specific exits
            if current_regime in [0, 1]:  # Ranging - tight exits
                exit_threshold = 0.3
            elif current_regime in [2, 3]:  # Trending - let profits run
                exit_threshold = 0.0
            else:  # Breakout - normal exit
                exit_threshold = 0.5

            if self.position.is_long:
                if current_zscore > -exit_threshold and self.position.pl_pct > 0:
                    self.position.close()
                    return
            else:
                if current_zscore < exit_threshold and self.position.pl_pct > 0:
                    self.position.close()
                    return

        # Entry logic
        if not self.position:

            # Zone proximity
            near_demand = abs(current_price - demand_zone) / demand_zone <= 0.005
            near_supply = abs(current_price - supply_zone) / supply_zone <= 0.005

            # BUY signals
            buy_signal = False

            # Standard oversold entry
            if current_zscore < -zscore_threshold and near_demand:
                buy_signal = True

            # Regime transition opportunity
            elif self.regime_transition_trade and regime_changed:
                # Transition to ranging from downtrend (bottom forming)
                if current_regime in [0, 1] and self.regime[-2] == 3:
                    if near_demand:
                        buy_signal = True
                # Transition to uptrend
                elif current_regime == 2 and near_demand:
                    buy_signal = True

            # Regime-specific entries
            elif current_regime == 0:  # Low vol ranging - aggressive mean reversion
                if current_zscore < -zscore_threshold * 0.7 and near_demand:
                    buy_signal = True
            elif current_regime == 2:  # Uptrend - buy dips
                if current_zscore < -zscore_threshold * 0.5 and near_demand:
                    buy_signal = True

            if buy_signal:
                sl_price = current_price * (1 - self.stop_loss * sl_multiplier)
                tp_price = max(current_bb_middle, current_price * (1 + self.take_profit * tp_multiplier))
                if tp_price <= current_price * 1.001:
                    tp_price = current_price * (1 + self.take_profit * tp_multiplier)

                self.buy(sl=sl_price, tp=tp_price)
                self.entry_regime = current_regime

            # SELL signals
            else:
                sell_signal = False

                # Standard overbought entry
                if current_zscore > zscore_threshold and near_supply:
                    sell_signal = True

                # Regime transition opportunity
                elif self.regime_transition_trade and regime_changed:
                    # Transition to ranging from uptrend (top forming)
                    if current_regime in [0, 1] and self.regime[-2] == 2:
                        if near_supply:
                            sell_signal = True
                    # Transition to downtrend
                    elif current_regime == 3 and near_supply:
                        sell_signal = True

                # Regime-specific entries
                elif current_regime == 0:  # Low vol ranging - aggressive mean reversion
                    if current_zscore > zscore_threshold * 0.7 and near_supply:
                        sell_signal = True
                elif current_regime == 3:  # Downtrend - sell rallies
                    if current_zscore > zscore_threshold * 0.5 and near_supply:
                        sell_signal = True

                if sell_signal:
                    sl_price = current_price * (1 + self.stop_loss * sl_multiplier)
                    tp_price = min(current_bb_middle, current_price * (1 - self.take_profit * tp_multiplier))
                    if tp_price >= current_price * 0.999:
                        tp_price = current_price * (1 - self.take_profit * tp_multiplier)

                    self.sell(sl=sl_price, tp=tp_price)
                    self.entry_regime = current_regime


# Run baseline backtest
print("\n" + "="*70)
print("RUNNING REGIME DETECTION BACKTEST")
print("="*70)

bt = Backtest(
    data,
    SDZStatArbRegimeStrategy,
    cash=1000000,
    commission=0.001,
    exclusive_orders=True
)

# Run baseline
baseline_stats = bt.run()

print(f"\n📊 BASELINE RESULTS:")
print(f"Lookback: {SDZStatArbRegimeStrategy.lookback_period} bars")
print(f"Z-Score Low Vol: {SDZStatArbRegimeStrategy.zscore_low_vol}")
print(f"Z-Score High Vol: {SDZStatArbRegimeStrategy.zscore_high_vol}")
print(f"Z-Score Trending: {SDZStatArbRegimeStrategy.zscore_trending}")
print(f"Take Profit: {SDZStatArbRegimeStrategy.take_profit*100:.1f}%")
print(f"Stop Loss: {SDZStatArbRegimeStrategy.stop_loss*100:.2f}%")
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
        zscore_low_vol=[1.2, 1.5, 1.8],
        zscore_high_vol=[2.0, 2.5, 3.0],
        zscore_trending=[1.5, 2.0, 2.5],
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
    print(f"Z-Score Low Vol: {optimization_results._strategy.zscore_low_vol}")
    print(f"Z-Score High Vol: {optimization_results._strategy.zscore_high_vol}")
    print(f"Z-Score Trending: {optimization_results._strategy.zscore_trending}")
    print(f"Take Profit: {optimization_results._strategy.take_profit*100:.2f}%")
    print(f"Stop Loss: {optimization_results._strategy.stop_loss*100:.2f}%")

except Exception as e:
    print(f"\n⚠️ Optimization failed: {str(e)}")

# Show plot
print("\n📊 Generating plot...")
bt.plot()