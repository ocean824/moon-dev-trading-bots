"""
Liquidation + Delta Ladder ADX Strategy
========================================

Combines large liquidation events with Delta Ladder volume analysis and ADX trend strength.

Strategy Logic:
1. Monitor for large liquidations (>$5M) as primary signal
2. Use Delta Ladder for volume imbalance confirmation
3. Add ADX for trend strength validation
4. Only trade when liquidations + delta + trend align
"""

import pandas as pd
import numpy as np
import talib
import pandas_ta as ta
from backtesting import Backtest, Strategy
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Liquidation + Delta Ladder ADX Strategy Loading... 🌙")

# Data configuration
# Load preprocessed BTC data - choose between 1-minute and 5-minute
# Just comment/uncomment to switch between timeframes

# Option 1: 1-minute data
# data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/moondev_api/liq_data_BTC_1m_ohlcv.csv'
# timeframe = '1-minute'

# Option 2: 5-minute data (currently active)
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/moondev_api/liq_data_BTC_5m_ohlcv.csv'
timeframe = '5-minute'

print(f"📊 Loading preprocessed {timeframe} BTC liquidation data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)

# Data already has proper columns from preprocessing
print(f"✅ Loaded {len(data):,} {timeframe} bars")
print("Columns:", data.columns.tolist())


# Strategy parameters
LARGE_LIQUIDATION_THRESHOLD = 5_000_000  # $5M USD
LOOKBACK_HOURS = 4  # Look for liquidations in past 4 hours
POSITION_SIZE = 0.85  # Use 85% of available capital



# Load liquidation data


# Process liquidation data
def process_liquidation_data(liq_df):
    if len(liq_df.columns) >= 12:
        column_names = ['symbol', 'side', 'order_type', 'time_in_force', 'quantity',
                       'price', 'avg_price', 'status', 'filled_qty', 'total_qty',
                       'timestamp_ms', 'usd_value', 'datetime']

        liq_df.columns = column_names[:len(liq_df.columns)]

        if 'datetime' in liq_df.columns:
            liq_df['datetime'] = pd.to_datetime(liq_df['datetime'])
        if 'usd_value' in liq_df.columns:
            liq_df['usd_value'] = pd.to_numeric(liq_df['usd_value'], errors='coerce')

        large_liqs = liq_df[liq_df['usd_value'] >= LARGE_LIQUIDATION_THRESHOLD].copy()

        print(f"📊 Total liquidations: {len(liq_df):,}")
        print(f"💥 Large liquidations (≥${LARGE_LIQUIDATION_THRESHOLD:,}): {len(large_liqs):,}")

        return large_liqs
    else:
        return pd.DataFrame()

large_liquidations = process_liquidation_data(liq_data)

# Prepare data
if len(large_liquidations) > 0:
    liq_start = large_liquidations['datetime'].min()
    liq_end = large_liquidations['datetime'].max()
    overlap_data = data[(data.index >= liq_start - timedelta(hours=24)) &
                       (data.index <= liq_end + timedelta(hours=24))]
    if len(overlap_data) > 0:
        data = overlap_data
    else:
        data = data.tail(2000)  # More data for delta calculations
else:
    data = data.tail(2000)

print(f"✅ Price data ready! {len(data)} rows 🌙")


class LiquidationDeltaLadderADXStrategy(Strategy):
    """
    Triple confirmation strategy: Liquidations + Delta Ladder + ADX
    """

    # Strategy parameters
    liquidation_threshold = LARGE_LIQUIDATION_THRESHOLD
    lookback_hours = LOOKBACK_HOURS
    position_size = POSITION_SIZE

    # Delta Ladder parameters
    delta_rows = 10  # Number of price levels per bar
    volume_lookback = 20  # Lookback for average volume
    min_delta_ratio = 0.2  # Minimum delta ratio for signal

    # ADX parameters
    adx_period = 14
    adx_threshold = 25  # Minimum ADX for trend strength

    # Risk management
    take_profit = 0.035  # 3.5%
    stop_loss = 0.025   # 2.5%
    max_hold_hours = 6   # Maximum holding period

    def init(self):
        """Initialize all strategy components"""
        print("🔧 Liquidation + Delta Ladder ADX Strategy Initializing...")

        # Calculate delta ladder components
        self.delta_data = self.calculate_delta_ladder()

        # Volume average for expansion detection
        self.avg_volume = ta.sma(pd.Series(self.data.Volume), length=self.volume_lookback).values

        # Calculate ADX and DI indicators
        adx_result = ta.adx(
            pd.Series(self.data.High),
            pd.Series(self.data.Low),
            pd.Series(self.data.Close),
            length=self.adx_period
        )

        # Extract ADX, +DI, -DI values
        self.adx = adx_result[f'ADX_{self.adx_period}'].values
        self.plus_di = adx_result[f'DMP_{self.adx_period}'].values
        self.minus_di = adx_result[f'DMN_{self.adx_period}'].values

        # ATR for volatility analysis
        self.atr = ta.atr(
            pd.Series(self.data.High),
            pd.Series(self.data.Low),
            pd.Series(self.data.Close),
            length=14
        ).values

        print("📈 Delta Ladder + ADX + Liquidation components ready! 🎯")

    def calculate_delta_ladder(self):
        """Calculate delta ladder components for each bar"""
        delta_data = {
            'cumulative_delta': [],
            'delta_ratio': [],
            'delta_momentum': [],
            'volume_expansion': []
        }

        closes = self.data.Close
        opens = self.data.Open
        highs = self.data.High
        lows = self.data.Low
        volumes = self.data.Volume

        for i in range(len(closes)):
            if i == 0:
                delta_data['cumulative_delta'].append(0)
                delta_data['delta_ratio'].append(0)
                delta_data['delta_momentum'].append(0)
                delta_data['volume_expansion'].append(0)
                continue

            # Calculate bar range and level size
            bar_range = highs[i] - lows[i]
            if bar_range == 0:
                delta_data['cumulative_delta'].append(delta_data['cumulative_delta'][-1])
                delta_data['delta_ratio'].append(0)
                delta_data['delta_momentum'].append(0)
                delta_data['volume_expansion'].append(0)
                continue

            # Calculate delta based on close position and volume
            close_position = (closes[i] - lows[i]) / bar_range

            # Estimate buying vs selling pressure
            buying_pressure = close_position * volumes[i]
            selling_pressure = (1 - close_position) * volumes[i]

            bar_delta = buying_pressure - selling_pressure

            # Update cumulative delta
            prev_cumulative = delta_data['cumulative_delta'][-1]
            new_cumulative = prev_cumulative + bar_delta
            delta_data['cumulative_delta'].append(new_cumulative)

            # Calculate delta ratio (normalized)
            total_volume = buying_pressure + selling_pressure
            delta_ratio = bar_delta / total_volume if total_volume > 0 else 0
            delta_data['delta_ratio'].append(delta_ratio)

            # Calculate delta momentum (change in delta)
            if len(delta_data['delta_ratio']) > 1:
                prev_ratio = delta_data['delta_ratio'][-2]
                momentum = delta_ratio - prev_ratio
            else:
                momentum = 0
            delta_data['delta_momentum'].append(momentum)

            # Volume expansion check
            if i >= self.volume_lookback:
                recent_avg_vol = np.mean(volumes[i-self.volume_lookback:i])
                expansion = volumes[i] / recent_avg_vol if recent_avg_vol > 0 else 1
            else:
                expansion = 1
            delta_data['volume_expansion'].append(expansion)

        return delta_data

    def get_recent_liquidations(self, current_time):
        """Get liquidations in the lookback period"""
        if len(large_liquidations) == 0:
            return pd.DataFrame()

        cutoff_time = current_time - timedelta(hours=self.lookback_hours)
        recent_liqs = large_liquidations[
            (large_liquidations['datetime'] >= cutoff_time) &
            (large_liquidations['datetime'] <= current_time)
        ]

        return recent_liqs

    def analyze_liquidation_pressure(self, recent_liqs):
        """Analyze liquidation pressure and direction"""
        if len(recent_liqs) == 0:
            return {'pressure': 0, 'direction': 'neutral', 'total_value': 0}

        buy_liqs = recent_liqs[recent_liqs['side'].str.upper() == 'BUY']
        sell_liqs = recent_liqs[recent_liqs['side'].str.upper() == 'SELL']

        buy_pressure = buy_liqs['usd_value'].sum() if len(buy_liqs) > 0 else 0
        sell_pressure = sell_liqs['usd_value'].sum() if len(sell_liqs) > 0 else 0

        total_pressure = buy_pressure + sell_pressure
        net_pressure = sell_pressure - buy_pressure

        if abs(net_pressure) < total_pressure * 0.3:
            direction = 'neutral'
        elif net_pressure > 0:
            direction = 'bearish'
        else:
            direction = 'bullish'

        return {
            'pressure': abs(net_pressure),
            'direction': direction,
            'total_value': total_pressure
        }

    def next(self):
        """Main strategy logic with triple confirmation"""
        if len(self.data) < max(self.adx_period, self.volume_lookback) + 20:
            return

        current_time = self.data.index[-1]
        current_price = self.data.Close[-1]
        idx = len(self.data) - 1

        # Get recent liquidations
        recent_liqs = self.get_recent_liquidations(current_time)
        liq_analysis = self.analyze_liquidation_pressure(recent_liqs)

        # Get current indicator values
        adx_val = self.adx[idx] if idx < len(self.adx) else np.nan
        plus_di_val = self.plus_di[idx] if idx < len(self.plus_di) else np.nan
        minus_di_val = self.minus_di[idx] if idx < len(self.minus_di) else np.nan

        # Delta ladder values
        if idx < len(self.delta_data['delta_ratio']):
            delta_ratio = self.delta_data['delta_ratio'][idx]
            delta_momentum = self.delta_data['delta_momentum'][idx]
            volume_expansion = self.delta_data['volume_expansion'][idx]
        else:
            delta_ratio = 0
            delta_momentum = 0
            volume_expansion = 1

        # Skip if insufficient conditions
        if (liq_analysis['pressure'] < self.liquidation_threshold or
            np.isnan(adx_val) or adx_val < self.adx_threshold):
            return

        # Entry logic - triple confirmation required
        if not self.position:

            # Long entry conditions:
            # 1. Bearish liquidation pressure (contrarian)
            # 2. Positive delta ratio (buying pressure)
            # 3. ADX strong + bullish DI setup
            # 4. Volume expansion
            if (liq_analysis['direction'] == 'bearish' and
                liq_analysis['pressure'] >= self.liquidation_threshold and
                delta_ratio > self.min_delta_ratio and
                delta_momentum > 0 and
                adx_val >= self.adx_threshold and
                plus_di_val > minus_di_val and
                volume_expansion > 1.2):

                sl_price = current_price * (1 - self.stop_loss)
                tp_price = current_price * (1 + self.take_profit)

                self.buy(size=self.position_size, sl=sl_price, tp=tp_price)
                print(f"🟢 LONG: Liq ${liq_analysis['pressure']:,.0f} + Delta {delta_ratio:.3f} + ADX {adx_val:.1f}")

            # Short entry conditions:
            # 1. Bullish liquidation pressure (contrarian)
            # 2. Negative delta ratio (selling pressure)
            # 3. ADX strong + bearish DI setup
            # 4. Volume expansion
            elif (liq_analysis['direction'] == 'bullish' and
                  liq_analysis['pressure'] >= self.liquidation_threshold and
                  delta_ratio < -self.min_delta_ratio and
                  delta_momentum < 0 and
                  adx_val >= self.adx_threshold and
                  minus_di_val > plus_di_val and
                  volume_expansion > 1.2):

                sl_price = current_price * (1 + self.stop_loss)
                tp_price = current_price * (1 - self.take_profit)

                self.sell(size=self.position_size, sl=sl_price, tp=tp_price)
                print(f"🔴 SHORT: Liq ${liq_analysis['pressure']:,.0f} + Delta {delta_ratio:.3f} + ADX {adx_val:.1f}")

        # Exit logic
        else:
            entry_time = self.trades[-1].entry_time if self.trades else current_time
            hours_held = (current_time - entry_time).total_seconds() / 3600

            # Time-based exit
            if hours_held >= self.max_hold_hours:
                self.position.close()
                print(f"⏰ TIME EXIT: Held for {hours_held:.1f} hours")

            # Delta reversal exit
            elif self.position.is_long and delta_ratio < -self.min_delta_ratio:
                self.position.close()
                print(f"🔄 DELTA REVERSAL EXIT: Delta turned negative {delta_ratio:.3f}")

            elif self.position.is_short and delta_ratio > self.min_delta_ratio:
                self.position.close()
                print(f"🔄 DELTA REVERSAL EXIT: Delta turned positive {delta_ratio:.3f}")

            # ADX weakening exit
            elif adx_val < self.adx_threshold * 0.8:
                self.position.close()
                print(f"📉 ADX WEAKENING EXIT: ADX dropped to {adx_val:.1f}")


# Run backtest
if len(data) > 200:
    bt = Backtest(data, LiquidationDeltaLadderADXStrategy, cash=1000000, commission=0.001)

    print("\n🌙 ===== LIQUIDATION + DELTA LADDER ADX STRATEGY RESULTS ===== 🌙")
    print(f"Large Liquidation Threshold: ${LARGE_LIQUIDATION_THRESHOLD:,}")
    print(f"ADX Threshold: {LiquidationDeltaLadderADXStrategy.adx_threshold}")
    print(f"Min Delta Ratio: {LiquidationDeltaLadderADXStrategy.min_delta_ratio}")
    print("-" * 60)

    stats = bt.run()

    print(f"\n📊 KEY METRICS:")
    print(f"Total Trades: {stats['# Trades']}")
    if stats['# Trades'] > 0:
        print(f"Win Rate: {stats['Win Rate [%]']:.2f}%")
        print(f"Return: {stats['Return [%]']:.2f}%")
        print(f"Sharpe: {stats['Sharpe Ratio']:.2f}" if not np.isnan(stats['Sharpe Ratio']) else "Sharpe: N/A")
        print(f"Max Drawdown: {stats['Max. Drawdown [%]']:.2f}%")

        print("\n✅ LIQUIDATION + DELTA LADDER ADX RESULTS:")
        print("="*60)
        print(stats)
    else:
        print("❌ No trades generated - high selectivity by design")

else:
    print("❌ Insufficient data for backtesting")