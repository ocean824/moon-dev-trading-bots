"""
Supply and Demand Zones STATISTICAL ARBITRAGE with VOLUME CONFIRMATION Strategy
================================================================================

Enhanced stat arb that requires volume confirmation for all trades.

Theory:
- High volume at extremes confirms genuine reversals
- Low volume extremes are often false signals
- Volume precedes price in reversals
- OBV divergences show hidden accumulation/distribution

Trading Logic:
- Enter only when z-score extreme coincides with volume spike
- Use OBV divergence for additional confirmation
- Track volume profile at each zone
- Exit when volume dries up
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's SDZ STATISTICAL ARBITRAGE + VOLUME Strategy 🌙")
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

# Z-scores
data['ZScore_5'] = calculate_zscore(data['Close'], 5)
data['ZScore_10'] = calculate_zscore(data['Close'], 10)
data['ZScore_20'] = calculate_zscore(data['Close'], 20)

# Volume indicators
data['Volume_MA'] = data['Volume'].rolling(20).mean()
data['Volume_Ratio'] = data['Volume'] / data['Volume_MA']
data['Volume_ZScore'] = calculate_zscore(data['Volume'], 20)

# OBV (On-Balance Volume)
data['OBV'] = ta.obv(data['Close'], data['Volume'])
data['OBV_MA'] = data['OBV'].rolling(20).mean()

# Volume-Weighted Average Price
data['VWAP'] = ta.vwap(data['High'], data['Low'], data['Close'], data['Volume'])

# Accumulation/Distribution Line
data['AD'] = ta.ad(data['High'], data['Low'], data['Close'], data['Volume'])
data['AD_MA'] = data['AD'].rolling(20).mean()

# Bollinger Bands
data['BB_Middle'] = data['Close'].rolling(20).mean()
data['BB_Std'] = data['Close'].rolling(20).std()
data['BB_Upper'] = data['BB_Middle'] + (data['BB_Std'] * 2)
data['BB_Lower'] = data['BB_Middle'] - (data['BB_Std'] * 2)

print(f"✅ Loaded {len(data):,} 1-minute bars")
print(f"📅 Date range: {data.index.min()} → {data.index.max()}")


class SDZStatArbVolumeStrategy(Strategy):
    """
    Statistical Arbitrage with Volume Confirmation Strategy

    Parameters:
    - lookback_period: Period for zone calculation
    - zscore_entry: Z-score threshold for entry
    - volume_multiplier: Minimum volume spike for confirmation
    - volume_zscore_min: Minimum volume z-score
    - obv_divergence_bars: Bars to check for OBV divergence
    - take_profit: Profit target
    - stop_loss: Stop loss
    """

    # Optimizable parameters
    lookback_period = 8
    zscore_entry = 2.0
    volume_multiplier = 1.5  # Need 1.5x average volume
    volume_zscore_min = 1.0  # Volume must be 1 std above mean
    obv_divergence_bars = 10  # Look back for OBV divergence
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

        # Volume indicators
        self.volume_ratio = self.I(lambda: self.data.Volume_Ratio)
        self.volume_zscore = self.I(lambda: self.data.Volume_ZScore)
        self.obv = self.I(lambda: self.data.OBV)
        self.obv_ma = self.I(lambda: self.data.OBV_MA)
        self.ad = self.I(lambda: self.data.AD)
        self.ad_ma = self.I(lambda: self.data.AD_MA)
        self.vwap = self.I(lambda: self.data.VWAP)

        # Bollinger Bands
        self.bb_middle = self.I(lambda: self.data.BB_Middle)

        # Track entry volume
        self.entry_volume_ratio = 1.0

    def check_obv_divergence(self, lookback):
        """Check for OBV divergence"""
        if len(self.data) < lookback + 1:
            return None

        # Price trend
        price_change = (self.data.Close[-1] - self.data.Close[-lookback]) / self.data.Close[-lookback]

        # OBV trend
        obv_change = (self.obv[-1] - self.obv[-lookback]) / abs(self.obv[-lookback]) if self.obv[-lookback] != 0 else 0

        # Bullish divergence: price down, OBV up
        if price_change < -0.002 and obv_change > 0.01:
            return "bullish"
        # Bearish divergence: price up, OBV down
        elif price_change > 0.002 and obv_change < -0.01:
            return "bearish"

        return None

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

        current_volume_ratio = self.volume_ratio[-1] if self.volume_ratio[-1] else 1
        current_volume_zscore = self.volume_zscore[-1] if self.volume_zscore[-1] and not np.isnan(self.volume_zscore[-1]) else 0
        current_vwap = self.vwap[-1] if self.vwap[-1] else current_price
        current_bb_middle = self.bb_middle[-1] if self.bb_middle[-1] else current_price

        # Get zones
        demand_zone = self.support[-1]
        supply_zone = self.resistance[-1]

        # Check OBV divergence
        obv_divergence = self.check_obv_divergence(self.obv_divergence_bars)

        # Check AD trend
        ad_rising = self.ad[-1] > self.ad_ma[-1] if self.ad[-1] and self.ad_ma[-1] else False
        ad_falling = self.ad[-1] < self.ad_ma[-1] if self.ad[-1] and self.ad_ma[-1] else False

        # Exit logic
        if self.position:
            # Exit on volume dry up
            if current_volume_ratio < 0.5:  # Volume dropped significantly
                if self.position.pl_pct > 0:
                    self.position.close()
                    return

            # Normal z-score exit
            if self.position.is_long:
                if z5 > -0.5 and self.position.pl_pct > 0:
                    self.position.close()
                    return
            else:
                if z5 < 0.5 and self.position.pl_pct > 0:
                    self.position.close()
                    return

        # Entry logic
        if not self.position:

            # Zone proximity
            near_demand = abs(current_price - demand_zone) / demand_zone <= 0.005
            near_supply = abs(current_price - supply_zone) / supply_zone <= 0.005

            # Volume confirmation required
            volume_confirmed = (current_volume_ratio >= self.volume_multiplier or
                               current_volume_zscore >= self.volume_zscore_min)

            # BUY signals
            buy_signal = False

            # Oversold with volume spike
            if z5 < -self.zscore_entry and near_demand and volume_confirmed:
                buy_signal = True

            # OBV bullish divergence with moderate z-score
            elif obv_divergence == "bullish" and z5 < -self.zscore_entry * 0.7:
                if near_demand and current_volume_ratio > 1.2:
                    buy_signal = True

            # Multi-timeframe with volume
            elif z5 < -self.zscore_entry * 0.8 and z10 < -self.zscore_entry * 0.7:
                if volume_confirmed and near_demand:
                    buy_signal = True

            # AD accumulation signal
            elif ad_rising and z5 < -self.zscore_entry * 0.9:
                if near_demand and current_volume_zscore > 0.5:
                    buy_signal = True

            # VWAP support with volume
            elif current_price < current_vwap * 0.995 and z5 < -1.5:
                if near_demand and volume_confirmed:
                    buy_signal = True

            if buy_signal:
                # Dynamic targets based on volume strength
                volume_strength = min(current_volume_ratio / self.volume_multiplier, 1.5)
                tp_mult = self.take_profit * volume_strength

                sl_price = current_price * (1 - self.stop_loss)
                tp_price = max(current_bb_middle, current_price * (1 + tp_mult))
                if tp_price <= current_price * 1.001:
                    tp_price = current_price * (1 + self.take_profit)

                self.buy(sl=sl_price, tp=tp_price)
                self.entry_volume_ratio = current_volume_ratio

            # SELL signals
            else:
                sell_signal = False

                # Overbought with volume spike
                if z5 > self.zscore_entry and near_supply and volume_confirmed:
                    sell_signal = True

                # OBV bearish divergence with moderate z-score
                elif obv_divergence == "bearish" and z5 > self.zscore_entry * 0.7:
                    if near_supply and current_volume_ratio > 1.2:
                        sell_signal = True

                # Multi-timeframe with volume
                elif z5 > self.zscore_entry * 0.8 and z10 > self.zscore_entry * 0.7:
                    if volume_confirmed and near_supply:
                        sell_signal = True

                # AD distribution signal
                elif ad_falling and z5 > self.zscore_entry * 0.9:
                    if near_supply and current_volume_zscore > 0.5:
                        sell_signal = True

                # VWAP resistance with volume
                elif current_price > current_vwap * 1.005 and z5 > 1.5:
                    if near_supply and volume_confirmed:
                        sell_signal = True

                if sell_signal:
                    # Dynamic targets based on volume strength
                    volume_strength = min(current_volume_ratio / self.volume_multiplier, 1.5)
                    tp_mult = self.take_profit * volume_strength

                    sl_price = current_price * (1 + self.stop_loss)
                    tp_price = min(current_bb_middle, current_price * (1 - tp_mult))
                    if tp_price >= current_price * 0.999:
                        tp_price = current_price * (1 - self.take_profit)

                    self.sell(sl=sl_price, tp=tp_price)
                    self.entry_volume_ratio = current_volume_ratio


# Run baseline backtest
print("\n" + "="*70)
print("RUNNING STAT ARB + VOLUME BACKTEST")
print("="*70)

bt = Backtest(
    data,
    SDZStatArbVolumeStrategy,
    cash=1000000,
    commission=0.001,
    exclusive_orders=True
)

# Run baseline
baseline_stats = bt.run()

print(f"\n📊 BASELINE RESULTS:")
print(f"Lookback: {SDZStatArbVolumeStrategy.lookback_period} bars")
print(f"Z-Score Entry: {SDZStatArbVolumeStrategy.zscore_entry}")
print(f"Volume Multiplier: {SDZStatArbVolumeStrategy.volume_multiplier}x")
print(f"Volume Z-Score Min: {SDZStatArbVolumeStrategy.volume_zscore_min}")
print(f"Take Profit: {SDZStatArbVolumeStrategy.take_profit*100:.1f}%")
print(f"Stop Loss: {SDZStatArbVolumeStrategy.stop_loss*100:.2f}%")
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
        volume_multiplier=[1.2, 1.5, 2.0],
        volume_zscore_min=[0.5, 1.0, 1.5],
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
    print(f"Z-Score Entry: {optimization_results._strategy.zscore_entry}")
    print(f"Volume Multiplier: {optimization_results._strategy.volume_multiplier}x")
    print(f"Volume Z-Score Min: {optimization_results._strategy.volume_zscore_min}")
    print(f"Take Profit: {optimization_results._strategy.take_profit*100:.2f}%")
    print(f"Stop Loss: {optimization_results._strategy.stop_loss*100:.2f}%")

except Exception as e:
    print(f"\n⚠️ Optimization failed: {str(e)}")

# Show plot
print("\n📊 Generating plot...")
bt.plot()