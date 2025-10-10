"""
Supply and Demand Zones ULTRA HIGH FREQUENCY with MFI Strategy
================================================================

Ultra high frequency trading with Money Flow Index for volume-price confirmation.

Theory:
- MFI combines price and volume to identify overbought/oversold
- MFI > 80 = overbought, MFI < 20 = oversold
- Zone touches with MFI divergence are high probability
- Money flow confirms real buying/selling pressure

Trading Logic:
- Buy at demand zones when MFI shows oversold
- Sell at supply zones when MFI shows overbought
- Use MFI divergences for stronger signals
- Quick scalps with volume-price confirmation
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Supply and Demand Zones ULTRA HIGH FREQ + MFI Strategy 🌙")
print("=" * 70)

# Load BTC 1-minute data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1m-4wks-data.csv'
print(f"📊 Loading BTC 1-minute data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)

# Rename columns
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Calculate MFI
data['MFI'] = ta.mfi(data['High'], data['Low'], data['Close'], data['Volume'], length=14)

# Calculate MFI rate of change for divergence detection
data['MFI_ROC'] = data['MFI'].pct_change(5)

print(f"✅ Loaded {len(data):,} 1-minute bars")
print(f"📅 Date range: {data.index.min()} → {data.index.max()}")


class SDZUltraMFIStrategy(Strategy):
    """
    Ultra High Frequency SDZ with Money Flow Index

    Parameters:
    - lookback_period: Very short period for rapid zone updates
    - zone_proximity: How close to zone to trigger
    - mfi_oversold: MFI level for oversold condition
    - mfi_overbought: MFI level for overbought condition
    - mfi_neutral_low: Lower bound of neutral zone
    - mfi_neutral_high: Upper bound of neutral zone
    - take_profit: Small for quick exits
    - stop_loss: Tight stop
    - max_hold_bars: Maximum bars to hold
    """

    # Optimizable parameters
    lookback_period = 8  # Very short lookback
    zone_proximity = 0.009  # 0.9% proximity
    mfi_oversold = 25  # Oversold threshold
    mfi_overbought = 75  # Overbought threshold
    mfi_neutral_low = 40  # Neutral zone lower
    mfi_neutral_high = 60  # Neutral zone upper
    take_profit = 0.0028  # 0.28% take profit
    stop_loss = 0.0018  # 0.18% stop loss
    max_hold_bars = 12  # Exit after 12 minutes max

    def init(self):
        """Initialize indicators"""
        # Calculate zones
        self.support = self.I(lambda: pd.Series(self.data.Close).rolling(
            window=self.lookback_period, min_periods=1).min())
        self.resistance = self.I(lambda: pd.Series(self.data.Close).rolling(
            window=self.lookback_period, min_periods=1).max())

        # Zone boundaries
        self.supp_lo = self.I(lambda: pd.Series(self.data.Low).rolling(
            window=self.lookback_period, min_periods=1).min())
        self.res_hi = self.I(lambda: pd.Series(self.data.High).rolling(
            window=self.lookback_period, min_periods=1).max())

        # MFI indicators
        self.mfi = self.I(lambda: self.data.MFI)
        self.mfi_roc = self.I(lambda: self.data.MFI_ROC)

        # Track entry bar and last MFI
        self.entry_bar = 0
        self.entry_mfi = 50

    def next(self):
        """Main strategy logic - high frequency with MFI filter"""

        # Skip if insufficient data
        if len(self.data) < max(self.lookback_period, 20):
            return

        # Get current values
        current_price = self.data.Close[-1]
        current_mfi = self.mfi[-1] if self.mfi[-1] else 50
        current_mfi_roc = self.mfi_roc[-1] if self.mfi_roc[-1] else 0

        # Get zones
        demand_zone = self.support[-1]
        supply_zone = self.resistance[-1]
        demand_low = self.supp_lo[-1]
        supply_high = self.res_hi[-1]

        # Exit existing positions
        if self.position:
            bars_held = len(self.data) - self.entry_bar

            # Exit after max hold
            if bars_held >= self.max_hold_bars:
                self.position.close()
                return

            # Exit on MFI reversal
            if self.position.is_long:
                # Exit long if MFI turns overbought or drops significantly
                if current_mfi > self.mfi_overbought or (current_mfi < self.entry_mfi - 10):
                    if self.position.pl_pct > 0:
                        self.position.close()
                        return
            else:
                # Exit short if MFI turns oversold or rises significantly
                if current_mfi < self.mfi_oversold or (current_mfi > self.entry_mfi + 10):
                    if self.position.pl_pct > 0:
                        self.position.close()
                        return

            # Quick profit exit
            if self.position.pl_pct >= self.take_profit * 0.3:
                self.position.close()
                return

        # Entry logic - only if no position
        if not self.position:

            # MFI conditions
            is_oversold = current_mfi < self.mfi_oversold
            is_overbought = current_mfi > self.mfi_overbought
            is_neutral = self.mfi_neutral_low <= current_mfi <= self.mfi_neutral_high
            mfi_rising = current_mfi_roc > 0
            mfi_falling = current_mfi_roc < 0

            # BUY signals with MFI confirmation
            buy_conditions = []

            # Classic oversold bounce at demand zone
            if abs(current_price - demand_zone) / demand_zone <= self.zone_proximity:
                if is_oversold or (current_mfi < 35 and mfi_rising):
                    buy_conditions.append("oversold_demand")

            # Extreme demand with any low MFI
            if abs(current_price - demand_low) / demand_low <= self.zone_proximity:
                if current_mfi < 40:
                    buy_conditions.append("extreme_low_mfi")

            # MFI divergence buy (price lower, MFI higher)
            if len(self.data) > 10:
                price_trend = current_price < self.data.Close[-10]
                mfi_trend = current_mfi > self.mfi[-10] if self.mfi[-10] else False
                if price_trend and mfi_trend and current_mfi < 50:
                    if abs(current_price - demand_zone) / demand_zone <= self.zone_proximity * 1.5:
                        buy_conditions.append("bullish_divergence")

            # Neutral MFI at strong support
            if is_neutral and mfi_rising:
                if abs(current_price - demand_zone) / demand_zone <= self.zone_proximity * 0.8:
                    buy_conditions.append("neutral_support")

            # Money flow reversal
            if current_mfi < 30 and current_mfi_roc > 0.1:  # Strong MFI increase
                if current_price < (demand_zone + supply_zone) / 2:
                    buy_conditions.append("mfi_reversal")

            if buy_conditions:
                sl_price = current_price * (1 - self.stop_loss)
                tp_price = current_price * (1 + self.take_profit)
                self.buy(sl=sl_price, tp=tp_price)
                self.entry_bar = len(self.data)
                self.entry_mfi = current_mfi

            # SELL signals with MFI confirmation
            else:
                sell_conditions = []

                # Classic overbought reversal at supply zone
                if abs(current_price - supply_zone) / supply_zone <= self.zone_proximity:
                    if is_overbought or (current_mfi > 65 and mfi_falling):
                        sell_conditions.append("overbought_supply")

                # Extreme supply with any high MFI
                if abs(current_price - supply_high) / supply_high <= self.zone_proximity:
                    if current_mfi > 60:
                        sell_conditions.append("extreme_high_mfi")

                # MFI divergence sell (price higher, MFI lower)
                if len(self.data) > 10:
                    price_trend = current_price > self.data.Close[-10]
                    mfi_trend = current_mfi < self.mfi[-10] if self.mfi[-10] else False
                    if price_trend and mfi_trend and current_mfi > 50:
                        if abs(current_price - supply_zone) / supply_zone <= self.zone_proximity * 1.5:
                            sell_conditions.append("bearish_divergence")

                # Neutral MFI at strong resistance
                if is_neutral and mfi_falling:
                    if abs(current_price - supply_zone) / supply_zone <= self.zone_proximity * 0.8:
                        sell_conditions.append("neutral_resistance")

                # Money flow reversal
                if current_mfi > 70 and current_mfi_roc < -0.1:  # Strong MFI decrease
                    if current_price > (demand_zone + supply_zone) / 2:
                        sell_conditions.append("mfi_reversal")

                if sell_conditions:
                    sl_price = current_price * (1 + self.stop_loss)
                    tp_price = current_price * (1 - self.take_profit)
                    self.sell(sl=sl_price, tp=tp_price)
                    self.entry_bar = len(self.data)
                    self.entry_mfi = current_mfi


# Run baseline backtest
print("\n" + "="*70)
print("RUNNING ULTRA HIGH FREQUENCY + MFI BACKTEST")
print("="*70)

bt = Backtest(
    data,
    SDZUltraMFIStrategy,
    cash=1000000,  # $1M for BTC trading
    commission=0.001,
    exclusive_orders=True
)

# Run baseline
baseline_stats = bt.run()

print(f"\n📊 BASELINE RESULTS:")
print(f"Lookback Period: {SDZUltraMFIStrategy.lookback_period} bars")
print(f"Zone Proximity: {SDZUltraMFIStrategy.zone_proximity*100:.1f}%")
print(f"MFI Oversold: {SDZUltraMFIStrategy.mfi_oversold}")
print(f"MFI Overbought: {SDZUltraMFIStrategy.mfi_overbought}")
print(f"Take Profit: {SDZUltraMFIStrategy.take_profit*100:.2f}%")
print(f"Stop Loss: {SDZUltraMFIStrategy.stop_loss*100:.2f}%")
print(f"Max Hold: {SDZUltraMFIStrategy.max_hold_bars} bars")
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
        mfi_oversold=[20, 25, 30],
        mfi_overbought=[70, 75, 80],
        take_profit=[0.0025, 0.0028, 0.003],
        stop_loss=[0.0015, 0.0018, 0.002],
        max_hold_bars=[10, 12, 15],
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
    print(f"MFI Oversold: {optimization_results._strategy.mfi_oversold}")
    print(f"MFI Overbought: {optimization_results._strategy.mfi_overbought}")

except Exception as e:
    print(f"\n⚠️ Optimization failed: {str(e)}")

# Show plot
print("\n📊 Generating plot...")
bt.plot()