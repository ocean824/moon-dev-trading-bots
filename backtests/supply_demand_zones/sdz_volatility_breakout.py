"""
Supply and Demand Zones VOLATILITY BREAKOUT Strategy
=====================================================

Ultra high frequency trading on volatility expansions from compressions.

Theory:
- Volatility cycles between compression and expansion
- Breakouts from low volatility are explosive
- ATR and Keltner channels show volatility state
- Trade the expansion with zone confirmation

Trading Logic:
- Identify volatility squeeze (Bollinger inside Keltner)
- Enter on volatility expansion at zones
- Use ATR for dynamic stops and targets
- Exit on volatility exhaustion
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Supply and Demand Zones VOLATILITY BREAKOUT Strategy 🌙")
print("=" * 70)

# Load BTC 1-minute data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1m-4wks-data.csv'
print(f"📊 Loading BTC 1-minute data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)

# Rename columns
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Calculate volatility indicators
# ATR
high = data['High']
low = data['Low']
close = data['Close']
tr1 = high - low
tr2 = abs(high - close.shift())
tr3 = abs(low - close.shift())
tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
data['ATR'] = tr.rolling(14).mean()
data['ATR_Ratio'] = data['ATR'] / close

# Bollinger Bands
data['BB_Middle'] = close.rolling(20).mean()
data['BB_Std'] = close.rolling(20).std()
data['BB_Upper'] = data['BB_Middle'] + (data['BB_Std'] * 2)
data['BB_Lower'] = data['BB_Middle'] - (data['BB_Std'] * 2)

# Keltner Channels
data['KC_Middle'] = close.ewm(span=20).mean()
data['KC_Upper'] = data['KC_Middle'] + (data['ATR'] * 1.5)
data['KC_Lower'] = data['KC_Middle'] - (data['ATR'] * 1.5)

# Squeeze indicator (Bollinger inside Keltner = squeeze)
data['Squeeze'] = ((data['BB_Upper'] < data['KC_Upper']) &
                   (data['BB_Lower'] > data['KC_Lower'])).astype(int)

# Volatility percentile
data['Vol_Percentile'] = data['ATR'].rolling(100).rank(pct=True) * 100

# Historical volatility
data['HV'] = close.pct_change().rolling(20).std() * np.sqrt(1440)  # Annualized

print(f"✅ Loaded {len(data):,} 1-minute bars")
print(f"📅 Date range: {data.index.min()} → {data.index.max()}")


class SDZVolatilityBreakoutStrategy(Strategy):
    """
    Volatility Breakout SDZ Strategy

    Parameters:
    - lookback_period: Period for zone calculation
    - squeeze_lookback: Bars to check for squeeze
    - vol_expansion_mult: ATR multiplier for expansion
    - vol_percentile_low: Low volatility threshold
    - atr_tp_mult: ATR multiplier for take profit
    - atr_sl_mult: ATR multiplier for stop loss
    - max_hold_bars: Maximum hold period
    """

    # Optimizable parameters
    lookback_period = 8  # Zone lookback
    squeeze_lookback = 5  # Check squeeze in last N bars
    vol_expansion_mult = 1.5  # ATR expansion multiplier
    vol_percentile_low = 30  # Low vol below 30th percentile
    atr_tp_mult = 2.0  # Take profit at 2x ATR
    atr_sl_mult = 1.0  # Stop loss at 1x ATR
    max_hold_bars = 20  # Hold max 20 minutes

    def init(self):
        """Initialize indicators"""
        # Calculate zones
        self.support = self.I(lambda: pd.Series(self.data.Close).rolling(
            window=self.lookback_period, min_periods=1).min())
        self.resistance = self.I(lambda: pd.Series(self.data.Close).rolling(
            window=self.lookback_period, min_periods=1).max())

        # Volatility indicators
        self.atr = self.I(lambda: self.data.ATR)
        self.atr_ratio = self.I(lambda: self.data.ATR_Ratio)
        self.squeeze = self.I(lambda: self.data.Squeeze)
        self.vol_percentile = self.I(lambda: self.data.Vol_Percentile)

        # Price channels
        self.bb_upper = self.I(lambda: self.data.BB_Upper)
        self.bb_lower = self.I(lambda: self.data.BB_Lower)
        self.kc_upper = self.I(lambda: self.data.KC_Upper)
        self.kc_lower = self.I(lambda: self.data.KC_Lower)

        # Track volatility state
        self.entry_atr = 0
        self.entry_bar = 0
        self.was_squeezed = False

    def next(self):
        """Main strategy logic - volatility breakout trading"""

        # Skip if insufficient data
        if len(self.data) < 30:
            return

        # Get current values
        current_price = self.data.Close[-1]
        current_atr = self.atr[-1] if self.atr[-1] else 0
        current_atr_ratio = self.atr_ratio[-1] if self.atr_ratio[-1] else 0.001
        current_squeeze = self.squeeze[-1]
        current_vol_percentile = self.vol_percentile[-1] if self.vol_percentile[-1] else 50

        # Skip if no ATR
        if current_atr == 0:
            return

        # Get zones
        demand_zone = self.support[-1]
        supply_zone = self.resistance[-1]

        # Check for recent squeeze
        recent_squeeze = any(self.squeeze[-i] == 1 for i in range(1, min(self.squeeze_lookback + 1, len(self.data))))

        # Detect volatility expansion
        vol_expanding = False
        if len(self.data) > 5:
            prev_atr = self.atr[-5] if self.atr[-5] else current_atr
            if current_atr > prev_atr * self.vol_expansion_mult:
                vol_expanding = True

        # Exit logic
        if self.position:
            bars_held = len(self.data) - self.entry_bar

            # Exit on max hold
            if bars_held >= self.max_hold_bars:
                self.position.close()
                return

            # Exit on volatility contraction
            if current_atr < self.entry_atr * 0.7:
                if self.position.pl_pct > 0:
                    self.position.close()
                    return

            # Exit on volatility expansion with profit
            if current_atr > self.entry_atr * 1.2:
                if self.position.pl_pct > self.atr_tp_mult * 0.3:  # Take partial profit on vol expansion
                    self.position.close()
                    return

        # Entry logic - only if no position
        if not self.position:

            # Zone proximity
            near_demand = abs(current_price - demand_zone) / demand_zone <= 0.005
            near_supply = abs(current_price - supply_zone) / supply_zone <= 0.005

            # BUY signals - Volatility breakout from demand
            buy_signal = False

            # Squeeze release at demand
            if recent_squeeze and not current_squeeze and near_demand:
                if vol_expanding or current_price > self.bb_upper[-1]:
                    buy_signal = True

            # Low volatility breakout
            elif current_vol_percentile < self.vol_percentile_low and near_demand:
                if vol_expanding:
                    buy_signal = True

            # Bollinger breakout from squeeze
            elif self.was_squeezed and current_price > self.bb_upper[-1]:
                if near_demand or current_price < (demand_zone + supply_zone) / 2:
                    buy_signal = True

            # ATR expansion at demand
            elif vol_expanding and near_demand:
                if current_price > self.kc_lower[-1]:
                    buy_signal = True

            # Keltner channel breakout
            elif current_price > self.kc_upper[-1] and near_demand:
                buy_signal = True

            if buy_signal:
                # Dynamic stops based on ATR
                sl_price = current_price - (current_atr * self.atr_sl_mult)
                tp_price = current_price + (current_atr * self.atr_tp_mult)

                self.buy(sl=sl_price, tp=tp_price)
                self.entry_atr = current_atr
                self.entry_bar = len(self.data)

            # SELL signals - Volatility breakout from supply
            else:
                sell_signal = False

                # Squeeze release at supply
                if recent_squeeze and not current_squeeze and near_supply:
                    if vol_expanding or current_price < self.bb_lower[-1]:
                        sell_signal = True

                # Low volatility breakout
                elif current_vol_percentile < self.vol_percentile_low and near_supply:
                    if vol_expanding:
                        sell_signal = True

                # Bollinger breakout from squeeze
                elif self.was_squeezed and current_price < self.bb_lower[-1]:
                    if near_supply or current_price > (demand_zone + supply_zone) / 2:
                        sell_signal = True

                # ATR expansion at supply
                elif vol_expanding and near_supply:
                    if current_price < self.kc_upper[-1]:
                        sell_signal = True

                # Keltner channel breakout
                elif current_price < self.kc_lower[-1] and near_supply:
                    sell_signal = True

                if sell_signal:
                    # Dynamic stops based on ATR
                    sl_price = current_price + (current_atr * self.atr_sl_mult)
                    tp_price = current_price - (current_atr * self.atr_tp_mult)

                    self.sell(sl=sl_price, tp=tp_price)
                    self.entry_atr = current_atr
                    self.entry_bar = len(self.data)

        # Update squeeze state
        self.was_squeezed = current_squeeze == 1


# Run baseline backtest
print("\n" + "="*70)
print("RUNNING VOLATILITY BREAKOUT BACKTEST")
print("="*70)

bt = Backtest(
    data,
    SDZVolatilityBreakoutStrategy,
    cash=1000000,  # $1M for BTC trading
    commission=0.001,
    exclusive_orders=True
)

# Run baseline
baseline_stats = bt.run()

print(f"\n📊 BASELINE RESULTS:")
print(f"Lookback Period: {SDZVolatilityBreakoutStrategy.lookback_period} bars")
print(f"Squeeze Lookback: {SDZVolatilityBreakoutStrategy.squeeze_lookback} bars")
print(f"Vol Expansion: {SDZVolatilityBreakoutStrategy.vol_expansion_mult}x")
print(f"ATR TP Mult: {SDZVolatilityBreakoutStrategy.atr_tp_mult}x")
print(f"ATR SL Mult: {SDZVolatilityBreakoutStrategy.atr_sl_mult}x")
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
print("OPTIMIZING FOR VOLATILITY PROFITS")
print("="*70)

try:
    optimization_results = bt.optimize(
        lookback_period=[6, 8, 10],
        squeeze_lookback=[3, 5, 7],
        vol_expansion_mult=[1.3, 1.5, 1.7],
        atr_tp_mult=[1.5, 2.0, 2.5],
        atr_sl_mult=[0.7, 1.0, 1.3],
        max_hold_bars=[15, 20, 25],
        maximize='Sharpe Ratio',
        constraint=lambda p: p['# Trades'] > 100,
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
    print(f"ATR TP: {optimization_results._strategy.atr_tp_mult}x")

except Exception as e:
    print(f"\n⚠️ Optimization failed: {str(e)}")

# Show plot
print("\n📊 Generating plot...")
bt.plot()