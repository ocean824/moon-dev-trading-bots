"""
Statistical Arbitrage with MOMENTUM CONFIRMATION
=================================================

STRATEGY GOAL: Increase expectancy by only taking mean reversion trades
that have momentum confirmation, reducing false signals.

Key Improvements:
- Add momentum filter to confirm reversal has started
- Use RSI divergence for additional confirmation
- Trail stops when momentum is strong
- Exit early if momentum reverses

Target: 4000+ trades with >0.03% expectancy (double current)
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's STAT ARB + MOMENTUM CONFIRMATION Strategy 🌙")
print("=" * 70)

# Load data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1m-4wks-data.csv'
print(f"📊 Loading BTC 1-minute data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Calculate indicators
def calculate_zscore(series, period):
    mean = series.rolling(period).mean()
    std = series.rolling(period).std()
    zscore = (series - mean) / std
    return zscore

# Z-scores
data['ZScore_5'] = calculate_zscore(data['Close'], 5)
data['ZScore_10'] = calculate_zscore(data['Close'], 10)
data['ZScore_20'] = calculate_zscore(data['Close'], 20)

# Momentum indicators
data['Momentum'] = data['Close'].pct_change(3)
data['Momentum_Accel'] = data['Momentum'].diff()  # Acceleration
data['RSI'] = ta.rsi(data['Close'], length=6)  # Fast RSI

# Rate of change
data['ROC'] = ta.roc(data['Close'], length=5)

# Bollinger Bands
data['BB_Middle'] = data['Close'].rolling(20).mean()
data['BB_Std'] = data['Close'].rolling(20).std()
data['BB_Width'] = (data['BB_Std'] * 2) / data['BB_Middle']

# Price velocity
data['Velocity'] = data['Close'].diff(3) / 3

print(f"✅ Loaded {len(data):,} 1-minute bars")


class StatArbMomentumStrategy(Strategy):
    """
    Momentum-Confirmed Statistical Arbitrage

    Only enters when:
    1. Z-score is extreme
    2. Momentum confirms reversal has started
    3. RSI supports the direction
    """

    # Parameters
    lookback_period = 6
    zscore_entry = 1.2  # Lowered from 1.5
    zscore_exit = 0.3
    momentum_threshold = 0.0005  # Lowered from 0.001
    rsi_oversold = 35  # Raised from 30
    rsi_overbought = 65  # Lowered from 70
    take_profit = 0.006  # Larger TP for better expectancy
    stop_loss = 0.002
    bb_width_filter = 0.06  # Raised from 0.04

    def init(self):
        # Zones
        self.support = self.I(lambda: pd.Series(self.data.Close).rolling(
            window=self.lookback_period, min_periods=1).min())
        self.resistance = self.I(lambda: pd.Series(self.data.Close).rolling(
            window=self.lookback_period, min_periods=1).max())

        # Indicators
        self.zscore_5 = self.I(lambda: self.data.ZScore_5)
        self.zscore_10 = self.I(lambda: self.data.ZScore_10)
        self.momentum = self.I(lambda: self.data.Momentum)
        self.momentum_accel = self.I(lambda: self.data.Momentum_Accel)
        self.rsi = self.I(lambda: self.data.RSI)
        self.roc = self.I(lambda: self.data.ROC)
        self.bb_middle = self.I(lambda: self.data.BB_Middle)
        self.bb_width = self.I(lambda: self.data.BB_Width)
        self.velocity = self.I(lambda: self.data.Velocity)

    def check_momentum_confirmation(self, is_long):
        """Check if momentum confirms the trade direction"""
        current_momentum = self.momentum[-1] if self.momentum[-1] else 0
        current_accel = self.momentum_accel[-1] if self.momentum_accel[-1] else 0
        current_velocity = self.velocity[-1] if self.velocity[-1] else 0

        if is_long:
            # For longs: any positive sign or not too negative
            momentum_ok = current_momentum > -self.momentum_threshold * 3
            accel_ok = current_accel >= -0.0001
            velocity_ok = current_velocity >= -0.001
            # Need at least 1 of 3 conditions
            return sum([momentum_ok, accel_ok, velocity_ok]) >= 1
        else:
            # For shorts: any negative sign or not too positive
            momentum_ok = current_momentum < self.momentum_threshold * 3
            accel_ok = current_accel <= 0.0001
            velocity_ok = current_velocity <= 0.001
            # Need at least 1 of 3 conditions
            return sum([momentum_ok, accel_ok, velocity_ok]) >= 1

    def next(self):
        # Skip if insufficient data
        if len(self.data) < 50:
            return

        # Get current values
        current_price = self.data.Close[-1]
        z5 = self.zscore_5[-1] if self.zscore_5[-1] and not np.isnan(self.zscore_5[-1]) else 0
        z10 = self.zscore_10[-1] if self.zscore_10[-1] and not np.isnan(self.zscore_10[-1]) else 0
        current_rsi = self.rsi[-1] if self.rsi[-1] else 50
        current_bb_width = self.bb_width[-1] if self.bb_width[-1] else 0.02
        current_bb_middle = self.bb_middle[-1] if self.bb_middle[-1] and not np.isnan(self.bb_middle[-1]) else current_price

        # Get zones
        demand_zone = self.support[-1]
        supply_zone = self.resistance[-1]

        # Skip if volatility too high
        if current_bb_width > self.bb_width_filter:
            return

        # Exit logic - enhanced with momentum
        if self.position:
            if self.position.is_long:
                # Exit if momentum turns strongly negative
                if self.momentum[-1] < -self.momentum_threshold * 2:
                    self.position.close()
                    return
                # Normal exit
                if z5 > -self.zscore_exit and self.position.pl_pct > 0:
                    self.position.close()
                    return
            else:
                # Exit if momentum turns strongly positive
                if self.momentum[-1] > self.momentum_threshold * 2:
                    self.position.close()
                    return
                # Normal exit
                if z5 < self.zscore_exit and self.position.pl_pct > 0:
                    self.position.close()
                    return

        # Entry logic
        if not self.position:
            near_demand = abs(current_price - demand_zone) / demand_zone <= 0.005
            near_supply = abs(current_price - supply_zone) / supply_zone <= 0.005

            # BUY signal with momentum confirmation
            if (z5 < -self.zscore_entry and
                near_demand):

                # Check RSI and momentum (more relaxed)
                rsi_ok = current_rsi < self.rsi_oversold + 15
                very_oversold = z5 < -self.zscore_entry * 1.3
                momentum_ok = self.check_momentum_confirmation(True)

                if (rsi_ok and momentum_ok) or very_oversold:
                    # Dynamic TP based on momentum strength
                    current_momentum = self.momentum[-1] if self.momentum[-1] else 0
                    momentum_mult = min(abs(current_momentum) / self.momentum_threshold, 2) if current_momentum else 1
                    tp_price = max(current_bb_middle, current_price * (1 + self.take_profit * momentum_mult))
                    if tp_price <= current_price * 1.001:
                        tp_price = current_price * (1 + self.take_profit)

                    sl_price = current_price * (1 - self.stop_loss)
                    self.buy(sl=sl_price, tp=tp_price)

            # SELL signal with momentum confirmation
            elif (z5 > self.zscore_entry and
                  near_supply):

                # Check RSI and momentum (more relaxed)
                rsi_ok = current_rsi > self.rsi_overbought - 15
                very_overbought = z5 > self.zscore_entry * 1.3
                momentum_ok = self.check_momentum_confirmation(False)

                if (rsi_ok and momentum_ok) or very_overbought:
                    # Dynamic TP based on momentum strength
                    current_momentum = self.momentum[-1] if self.momentum[-1] else 0
                    momentum_mult = min(abs(current_momentum) / self.momentum_threshold, 2) if current_momentum else 1
                    tp_price = min(current_bb_middle, current_price * (1 - self.take_profit * momentum_mult))
                    if tp_price >= current_price * 0.999:
                        tp_price = current_price * (1 - self.take_profit)

                    sl_price = current_price * (1 + self.stop_loss)
                    self.sell(sl=sl_price, tp=tp_price)


# Run backtest
print("\n" + "="*70)
print("RUNNING MOMENTUM CONFIRMATION BACKTEST")
print("="*70)

bt = Backtest(
    data,
    StatArbMomentumStrategy,
    cash=1000000,
    commission=0.001,
    exclusive_orders=True
)

# Run baseline
baseline_stats = bt.run()

print(f"\n📊 BASELINE RESULTS:")
print(f"Take Profit: {StatArbMomentumStrategy.take_profit*100:.2f}%")
print(f"Stop Loss: {StatArbMomentumStrategy.stop_loss*100:.2f}%")
print("-" * 50)
print(baseline_stats)

# Optimization
print("\n" + "="*70)
print("OPTIMIZING FOR RETURN ON INVESTMENT")
print("="*70)

try:
    optimization_results = bt.optimize(
        lookback_period=[5, 6, 7],
        zscore_entry=[1.0, 1.2, 1.4],
        momentum_threshold=[0.0003, 0.0005, 0.0007],
        take_profit=[0.005, 0.006, 0.007],
        stop_loss=[0.0015, 0.002, 0.0025],
        maximize='Return [%]',
        return_heatmap=False
    )

    print(f"\n✨ OPTIMIZED RESULTS:")
    print(optimization_results)
    print(f"\n🎯 OPTIMIZED PARAMETERS:")
    print(f"Lookback Period: {optimization_results._strategy.lookback_period} bars")
    print(f"Z-Score Entry: {optimization_results._strategy.zscore_entry}")
    print(f"Momentum Threshold: {optimization_results._strategy.momentum_threshold*10000:.2f} bps")
    print(f"Take Profit: {optimization_results._strategy.take_profit*100:.2f}%")
    print(f"Stop Loss: {optimization_results._strategy.stop_loss*100:.2f}%")

except Exception as e:
    print(f"Optimization failed: {str(e)}")

bt.plot()