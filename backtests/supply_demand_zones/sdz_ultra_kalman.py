"""
Supply and Demand Zones ULTRA HIGH FREQUENCY with Kalman Filter Strategy
=========================================================================

Ultra high frequency trading with Kalman filter for noise reduction and trend extraction.

Theory:
- Kalman filter removes market noise while preserving true price signals
- Provides smooth trend estimation with minimal lag
- Kalman deviation shows when price diverges from filtered trend
- Combine with SDZ for high-probability mean reversion trades

Trading Logic:
- Buy when price below Kalman AND at demand zone
- Sell when price above Kalman AND at supply zone
- Use Kalman slope for trend direction confirmation
- Trade divergences between price and Kalman estimate
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Supply and Demand Zones ULTRA HIGH FREQ + KALMAN Strategy 🌙")
print("=" * 70)

# Load BTC 1-minute data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1m-4wks-data.csv'
print(f"📊 Loading BTC 1-minute data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)

# Rename columns
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']


def kalman_filter(prices, process_variance=0.01, measurement_variance=0.1):
    """
    Simple 1D Kalman filter for price smoothing
    """
    n = len(prices)
    filtered_prices = np.zeros(n)
    prediction_errors = np.zeros(n)

    # Initial estimates
    x_hat = prices.iloc[0] if hasattr(prices, 'iloc') else prices[0]
    P = 1.0

    for i in range(n):
        # Prediction step
        x_hat_minus = x_hat
        P_minus = P + process_variance

        # Update step
        current_price = prices.iloc[i] if hasattr(prices, 'iloc') else prices[i]
        K = P_minus / (P_minus + measurement_variance)
        x_hat = x_hat_minus + K * (current_price - x_hat_minus)
        P = (1 - K) * P_minus

        filtered_prices[i] = x_hat
        prediction_errors[i] = current_price - x_hat

    return filtered_prices, prediction_errors


# Apply Kalman filter
kalman_prices, kalman_errors = kalman_filter(data['Close'],
                                             process_variance=0.01,
                                             measurement_variance=0.1)
data['Kalman'] = kalman_prices
data['Kalman_Error'] = kalman_errors

# Calculate Kalman slope (trend direction)
data['Kalman_Slope'] = data['Kalman'].diff(5) / data['Kalman'].shift(5)

# Kalman deviation bands
data['Kalman_StdDev'] = data['Kalman_Error'].rolling(window=20).std()
data['Kalman_Upper'] = data['Kalman'] + (data['Kalman_StdDev'] * 2)
data['Kalman_Lower'] = data['Kalman'] - (data['Kalman_StdDev'] * 2)

print(f"✅ Loaded {len(data):,} 1-minute bars")
print(f"📅 Date range: {data.index.min()} → {data.index.max()}")


class SDZUltraKalmanStrategy(Strategy):
    """
    Ultra High Frequency SDZ with Kalman Filter

    Parameters:
    - lookback_period: Period for SDZ calculation
    - zone_proximity: How close to zone to trigger
    - kalman_deviation: Max deviation from Kalman for trades
    - kalman_slope_threshold: Minimum slope for trend confirmation
    - take_profit: Small for quick exits
    - stop_loss: Tight stop
    - max_hold_bars: Maximum bars to hold
    """

    # Optimizable parameters
    lookback_period = 8  # SDZ lookback
    zone_proximity = 0.009  # 0.9% from zone
    kalman_deviation = 0.003  # Max 0.3% deviation from Kalman
    kalman_slope_threshold = 0.0001  # Minimum slope for trend
    take_profit = 0.0028  # 0.28% take profit
    stop_loss = 0.0018  # 0.18% stop loss
    max_hold_bars = 10  # Exit after 10 minutes max

    def init(self):
        """Initialize indicators"""
        # Calculate SDZ zones
        self.support = self.I(lambda: pd.Series(self.data.Close).rolling(
            window=self.lookback_period, min_periods=1).min())
        self.resistance = self.I(lambda: pd.Series(self.data.Close).rolling(
            window=self.lookback_period, min_periods=1).max())

        # Zone boundaries
        self.supp_lo = self.I(lambda: pd.Series(self.data.Low).rolling(
            window=self.lookback_period, min_periods=1).min())
        self.res_hi = self.I(lambda: pd.Series(self.data.High).rolling(
            window=self.lookback_period, min_periods=1).max())

        # Kalman filter indicators
        self.kalman = self.I(lambda: self.data.Kalman)
        self.kalman_error = self.I(lambda: self.data.Kalman_Error)
        self.kalman_slope = self.I(lambda: self.data.Kalman_Slope)
        self.kalman_upper = self.I(lambda: self.data.Kalman_Upper)
        self.kalman_lower = self.I(lambda: self.data.Kalman_Lower)

        # Track entry bar
        self.entry_bar = 0
        self.entry_kalman = 0

    def next(self):
        """Main strategy logic - high frequency with Kalman filter"""

        # Skip if insufficient data
        if len(self.data) < max(self.lookback_period, 25):
            return

        # Get current values
        current_price = self.data.Close[-1]
        current_kalman = self.kalman[-1] if self.kalman[-1] else current_price
        current_kalman_error = self.kalman_error[-1] if self.kalman_error[-1] else 0
        current_kalman_slope = self.kalman_slope[-1] if self.kalman_slope[-1] else 0
        current_kalman_upper = self.kalman_upper[-1] if self.kalman_upper[-1] else current_kalman * 1.01
        current_kalman_lower = self.kalman_lower[-1] if self.kalman_lower[-1] else current_kalman * 0.99

        # Get SDZ zones
        demand_zone = self.support[-1]
        supply_zone = self.resistance[-1]
        demand_low = self.supp_lo[-1]
        supply_high = self.res_hi[-1]

        # Calculate Kalman position
        kalman_deviation = (current_price - current_kalman) / current_kalman
        above_kalman = current_price > current_kalman
        below_kalman = current_price < current_kalman
        kalman_trending_up = current_kalman_slope > self.kalman_slope_threshold
        kalman_trending_down = current_kalman_slope < -self.kalman_slope_threshold

        # Exit existing positions
        if self.position:
            bars_held = len(self.data) - self.entry_bar

            # Exit after max hold
            if bars_held >= self.max_hold_bars:
                self.position.close()
                return

            # Exit at Kalman (mean reversion target)
            if self.position.is_long:
                if current_price >= current_kalman and self.position.pl_pct > 0:
                    self.position.close()
                    return
            else:
                if current_price <= current_kalman and self.position.pl_pct > 0:
                    self.position.close()
                    return

            # Quick profit exit
            if self.position.pl_pct >= self.take_profit * 0.25:
                self.position.close()
                return

        # Entry logic - only if no position
        if not self.position:

            # BUY signals - Price below Kalman with demand zone confluence
            buy_conditions = []

            # Classic mean reversion: Below Kalman at demand zone
            if below_kalman and abs(kalman_deviation) <= self.kalman_deviation * 2:
                if abs(current_price - demand_zone) / demand_zone <= self.zone_proximity:
                    buy_conditions.append("kalman_demand_reversion")

            # Extreme oversold at Kalman lower band
            if current_price <= current_kalman_lower:
                if abs(current_price - demand_low) / demand_low <= self.zone_proximity * 1.2:
                    buy_conditions.append("kalman_lower_extreme")

            # Kalman uptrend with zone support
            if kalman_trending_up:
                if abs(current_price - demand_zone) / demand_zone <= self.zone_proximity * 0.8:
                    if abs(kalman_deviation) <= self.kalman_deviation:
                        buy_conditions.append("kalman_uptrend_support")

            # Strong error reversal (price snapping back to Kalman)
            if current_kalman_error < -abs(current_kalman) * 0.002:  # Strong negative error
                if len(self.data) > 2:
                    prev_error = self.kalman_error[-2] if self.kalman_error[-2] else 0
                    if current_kalman_error > prev_error:  # Error reducing
                        buy_conditions.append("kalman_error_reversal")

            # Kalman filter convergence at demand
            if abs(kalman_deviation) < 0.001:  # Very close to Kalman
                if abs(current_price - demand_zone) / demand_zone <= self.zone_proximity:
                    if not kalman_trending_down:
                        buy_conditions.append("kalman_convergence_buy")

            if buy_conditions:
                # Target is Kalman or take profit
                kalman_target = min(current_kalman, current_price * (1 + self.take_profit))
                sl_price = current_price * (1 - self.stop_loss)
                tp_price = max(kalman_target, current_price * (1 + self.take_profit))

                self.buy(sl=sl_price, tp=tp_price)
                self.entry_bar = len(self.data)
                self.entry_kalman = current_kalman

            # SELL signals - Price above Kalman with supply zone confluence
            else:
                sell_conditions = []

                # Classic mean reversion: Above Kalman at supply zone
                if above_kalman and abs(kalman_deviation) <= self.kalman_deviation * 2:
                    if abs(current_price - supply_zone) / supply_zone <= self.zone_proximity:
                        sell_conditions.append("kalman_supply_reversion")

                # Extreme overbought at Kalman upper band
                if current_price >= current_kalman_upper:
                    if abs(current_price - supply_high) / supply_high <= self.zone_proximity * 1.2:
                        sell_conditions.append("kalman_upper_extreme")

                # Kalman downtrend with zone resistance
                if kalman_trending_down:
                    if abs(current_price - supply_zone) / supply_zone <= self.zone_proximity * 0.8:
                        if abs(kalman_deviation) <= self.kalman_deviation:
                            sell_conditions.append("kalman_downtrend_resistance")

                # Strong error reversal (price snapping back to Kalman)
                if current_kalman_error > abs(current_kalman) * 0.002:  # Strong positive error
                    if len(self.data) > 2:
                        prev_error = self.kalman_error[-2] if self.kalman_error[-2] else 0
                        if current_kalman_error < prev_error:  # Error reducing
                            sell_conditions.append("kalman_error_reversal")

                # Kalman filter convergence at supply
                if abs(kalman_deviation) < 0.001:  # Very close to Kalman
                    if abs(current_price - supply_zone) / supply_zone <= self.zone_proximity:
                        if not kalman_trending_up:
                            sell_conditions.append("kalman_convergence_sell")

                if sell_conditions:
                    # Target is Kalman or take profit
                    kalman_target = max(current_kalman, current_price * (1 - self.take_profit))
                    sl_price = current_price * (1 + self.stop_loss)
                    tp_price = min(kalman_target, current_price * (1 - self.take_profit))

                    self.sell(sl=sl_price, tp=tp_price)
                    self.entry_bar = len(self.data)
                    self.entry_kalman = current_kalman


# Run baseline backtest
print("\n" + "="*70)
print("RUNNING ULTRA HIGH FREQUENCY + KALMAN BACKTEST")
print("="*70)

bt = Backtest(
    data,
    SDZUltraKalmanStrategy,
    cash=1000000,  # $1M for BTC trading
    commission=0.001,
    exclusive_orders=True
)

# Run baseline
baseline_stats = bt.run()

print(f"\n📊 BASELINE RESULTS:")
print(f"SDZ Lookback: {SDZUltraKalmanStrategy.lookback_period} bars")
print(f"Zone Proximity: {SDZUltraKalmanStrategy.zone_proximity*100:.1f}%")
print(f"Kalman Deviation: {SDZUltraKalmanStrategy.kalman_deviation*100:.1f}%")
print(f"Kalman Slope Thresh: {SDZUltraKalmanStrategy.kalman_slope_threshold*100:.3f}%")
print(f"Take Profit: {SDZUltraKalmanStrategy.take_profit*100:.2f}%")
print(f"Stop Loss: {SDZUltraKalmanStrategy.stop_loss*100:.2f}%")
print(f"Max Hold: {SDZUltraKalmanStrategy.max_hold_bars} bars")
print("-" * 50)
print(f"🔥 Total Trades: {baseline_stats['# Trades']}")
print(f"Win Rate: {baseline_stats['Win Rate [%]']:.2f}%")
print(f"Return: {baseline_stats['Return [%]']:.2f}%")
print(f"Sharpe: {baseline_stats['Sharpe Ratio']:.2f}")
print(f"Max Drawdown: {baseline_stats['Max. Drawdown [%]']:.2f}%")

print("\n📈 FULL BASELINE STATS:")
print("="*70)
print(baseline_stats)

# Run optimization for high trades with better returns
print("\n" + "="*70)
print("OPTIMIZING FOR HIGH TRADES WITH PROFITABILITY")
print("="*70)

try:
    optimization_results = bt.optimize(
        lookback_period=[6, 8, 10],
        zone_proximity=[0.008, 0.009, 0.011],
        kalman_deviation=[0.002, 0.003, 0.004],
        kalman_slope_threshold=[0.00005, 0.0001, 0.0002],
        take_profit=[0.0025, 0.0028, 0.003],
        stop_loss=[0.0015, 0.0018, 0.002],
        max_hold_bars=[8, 10, 12],
        maximize='Return [%]',  # Optimize for returns
        constraint=lambda p: p['# Trades'] > 800,  # Keep high trade count
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
    print(f"Kalman Deviation: {optimization_results._strategy.kalman_deviation*100:.1f}%")
    print(f"Zone Proximity: {optimization_results._strategy.zone_proximity*100:.1f}%")

except Exception as e:
    print(f"\n⚠️ Optimization failed: {str(e)}")

# Show plot
print("\n📊 Generating plot...")
bt.plot()