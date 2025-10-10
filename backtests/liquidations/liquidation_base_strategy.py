"""
Base Liquidation Strategy - Large Liquidations (>$5M)
======================================================

This strategy monitors for large liquidations (over $5M) and trades based on the assumption
that large liquidations create temporary price distortions that can be exploited.

Strategy Logic:
1. Monitor liquidation events from liquidation data
2. Identify large liquidations (>$5M USD value)
3. Trade in the opposite direction of the liquidation
4. Use standard OHLCV data for backtesting framework
5. Combine liquidation events with price action

"""

import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Base Liquidation Strategy (>$5M) Loading... 🌙")

# Data configuration
# Load preprocessed BTC data - choose between 1-minute and 5-minute
# Just comment/uncomment to switch between timeframes

#Option 1: 1-minute data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/moondev_api/liq_data_BTC_1m_ohlcv.csv'
timeframe = '1-minute'

# # Option 2: 5-minute data (currently active)
# data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/moondev_api/liq_data_BTC_5m_ohlcv.csv'
# timeframe = '5-minute'

print(f"📊 Loading preprocessed {timeframe} BTC liquidation data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)

# Data already has proper columns from preprocessing
print(f"✅ Loaded {len(data):,} {timeframe} bars")
print("Columns:", data.columns.tolist())


# Strategy parameters
LARGE_LIQUIDATION_THRESHOLD = 5_000_000  # $5M USD
LOOKBACK_HOURS = 4  # Look for liquidations in past 4 hours
POSITION_SIZE = 0.95  # Use 95% of available capital

# Data is already loaded with liquidations included
print(f"✅ Data includes liquidation columns: long_liquidations, short_liquidations, total_liquidations")

# Process liquidation data
def process_liquidation_data(liq_df):
    """Process liquidation data to extract relevant information"""
    # Parse column structure - appears to be:
    # Symbol, Side, Type, TimeInForce, Quantity, Price, AvgPrice, Status, FilledQty, TotalQty, Timestamp, UsdValue, Datetime

    if len(liq_df.columns) >= 12:
        # Rename columns based on expected structure
        column_names = ['symbol', 'side', 'order_type', 'time_in_force', 'quantity',
                       'price', 'avg_price', 'status', 'filled_qty', 'total_qty',
                       'timestamp_ms', 'usd_value', 'datetime']

        # Take only the number of columns we have names for
        liq_df.columns = column_names[:len(liq_df.columns)]

        # Convert datetime
        if 'datetime' in liq_df.columns:
            liq_df['datetime'] = pd.to_datetime(liq_df['datetime'])

        # Convert USD value to numeric
        if 'usd_value' in liq_df.columns:
            liq_df['usd_value'] = pd.to_numeric(liq_df['usd_value'], errors='coerce')

        # Filter for large liquidations
        large_liqs = liq_df[liq_df['usd_value'] >= LARGE_LIQUIDATION_THRESHOLD].copy()

        print(f"📊 Total liquidations: {len(liq_df):,}")
        print(f"💥 Large liquidations (≥${LARGE_LIQUIDATION_THRESHOLD:,}): {len(large_liqs):,}")

        if len(large_liqs) > 0:
            print(f"💰 Large liquidation stats:")
            print(f"  Average size: ${large_liqs['usd_value'].mean():,.0f}")
            print(f"  Max size: ${large_liqs['usd_value'].max():,.0f}")
            print(f"  Date range: {large_liqs['datetime'].min()} → {large_liqs['datetime'].max()}")

        return large_liqs
    else:
        print(f"⚠️ Unexpected liquidation data structure: {len(liq_df.columns)} columns")
        return pd.DataFrame()

# Create liquidation dataframe from the existing data columns for strategy compatibility
large_liquidations = pd.DataFrame()

# Use recent data that overlaps with liquidations
if len(large_liquidations) > 0:
    # Get date range from liquidations
    liq_start = large_liquidations['datetime'].min()
    liq_end = large_liquidations['datetime'].max()

    # Filter price data to overlap with liquidation period
    overlap_data = data[(data.index >= liq_start - timedelta(hours=24)) &
                       (data.index <= liq_end + timedelta(hours=24))]

    if len(overlap_data) > 0:
        data = overlap_data
        print(f"✅ Using overlapping data: {len(data)} rows from {data.index.min()} to {data.index.max()}")
    else:
        print(f"⚠️ No overlapping data found, using last 1000 rows")
        data = data.tail(1000)
else:
    print(f"⚠️ No large liquidations found, using last 1000 rows")
    data = data.tail(1000)

print(f"✅ Price data ready! {len(data)} rows 🌙")


class LiquidationBaseStrategy(Strategy):
    """
    Base strategy that trades on large liquidation events

    Logic:
    1. Monitor for large liquidation events in recent hours
    2. Trade opposite to liquidation direction (contrarian)
    3. Use technical indicators for confirmation
    4. Exit based on time or profit/loss targets
    """

    # Strategy parameters
    liquidation_threshold = LARGE_LIQUIDATION_THRESHOLD
    lookback_hours = LOOKBACK_HOURS
    position_size = POSITION_SIZE

    # Risk management
    take_profit = 0.025  # 2.5%
    stop_loss = 0.015   # 1.5%
    max_hold_hours = 12  # Maximum holding period

    def init(self):
        """Initialize strategy components"""
        print("🔧 Liquidation Base Strategy Initializing...")

        # Technical indicators for confirmation
        self.rsi = self.I(talib.RSI, self.data.Close, 14)
        self.ema_fast = self.I(talib.EMA, self.data.Close, 12)
        self.ema_slow = self.I(talib.EMA, self.data.Close, 26)
        self.atr = self.I(talib.ATR, self.data.High, self.data.Low, self.data.Close, 14)

        # Volume indicators
        self.volume_sma = self.I(talib.SMA, self.data.Volume, 20)

        print("📈 Technical indicators calculated! Ready to hunt liquidations! 🎯")

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

        # Calculate total liquidation values by side
        buy_liqs = recent_liqs[recent_liqs['side'].str.upper() == 'BUY']
        sell_liqs = recent_liqs[recent_liqs['side'].str.upper() == 'SELL']

        buy_pressure = buy_liqs['usd_value'].sum() if len(buy_liqs) > 0 else 0
        sell_pressure = sell_liqs['usd_value'].sum() if len(sell_liqs) > 0 else 0

        total_pressure = buy_pressure + sell_pressure
        net_pressure = sell_pressure - buy_pressure  # Positive = more sells liquidated

        # Determine dominant direction
        if abs(net_pressure) < total_pressure * 0.2:  # Less than 20% difference
            direction = 'neutral'
        elif net_pressure > 0:
            direction = 'bearish'  # More sell liquidations = bearish pressure
        else:
            direction = 'bullish'  # More buy liquidations = bullish pressure

        return {
            'pressure': abs(net_pressure),
            'direction': direction,
            'total_value': total_pressure,
            'buy_pressure': buy_pressure,
            'sell_pressure': sell_pressure
        }

    def next(self):
        """Main strategy logic"""
        if len(self.data) < 50:  # Need enough data for indicators
            return

        current_time = self.data.index[-1]
        current_price = self.data.Close[-1]

        # Get recent liquidations
        recent_liqs = self.get_recent_liquidations(current_time)
        liq_analysis = self.analyze_liquidation_pressure(recent_liqs)

        # Technical indicator values
        rsi = self.rsi[-1]
        ema_fast = self.ema_fast[-1]
        ema_slow = self.ema_slow[-1]
        atr = self.atr[-1]
        volume = self.data.Volume[-1]
        avg_volume = self.volume_sma[-1]

        # Skip if no liquidation pressure or invalid indicators
        if (liq_analysis['pressure'] < self.liquidation_threshold or
            np.isnan(rsi) or np.isnan(atr)):
            return

        # Entry logic - trade opposite to liquidation pressure (contrarian)
        if not self.position:

            # Long entry: Heavy sell liquidations (bearish pressure) + oversold conditions
            if (liq_analysis['direction'] == 'bearish' and
                liq_analysis['pressure'] >= self.liquidation_threshold and
                rsi < 45 and  # Somewhat oversold
                volume > avg_volume * 1.2 and  # Above average volume
                current_price < ema_slow):  # Below slower EMA

                # Calculate dynamic stop loss and take profit based on ATR
                sl_price = current_price * (1 - self.stop_loss)
                tp_price = current_price * (1 + self.take_profit)

                self.buy(size=self.position_size, sl=sl_price, tp=tp_price)
                print(f"🟢 LONG: Liquidation pressure ${liq_analysis['pressure']:,.0f} at {current_time}")

            # Short entry: Heavy buy liquidations (bullish pressure) + overbought conditions
            elif (liq_analysis['direction'] == 'bullish' and
                  liq_analysis['pressure'] >= self.liquidation_threshold and
                  rsi > 55 and  # Somewhat overbought
                  volume > avg_volume * 1.2 and  # Above average volume
                  current_price > ema_slow):  # Above slower EMA

                # Calculate dynamic stop loss and take profit based on ATR
                sl_price = current_price * (1 + self.stop_loss)
                tp_price = current_price * (1 - self.take_profit)

                self.sell(size=self.position_size, sl=sl_price, tp=tp_price)
                print(f"🔴 SHORT: Liquidation pressure ${liq_analysis['pressure']:,.0f} at {current_time}")

        # Exit logic - time-based exit
        else:
            entry_time = self.trades[-1].entry_time if self.trades else current_time
            hours_held = (current_time - entry_time).total_seconds() / 3600

            # Exit if held too long
            if hours_held >= self.max_hold_hours:
                self.position.close()
                print(f"⏰ TIME EXIT: Held for {hours_held:.1f} hours")


# Run backtest
if len(data) > 100:  # Ensure we have enough data
    bt = Backtest(data, LiquidationBaseStrategy, cash=1000000, commission=0.001)

    print("\n🌙 ===== LIQUIDATION BASE STRATEGY RESULTS ===== 🌙")
    print(f"Large Liquidation Threshold: ${LARGE_LIQUIDATION_THRESHOLD:,}")
    print(f"Lookback Period: {LOOKBACK_HOURS} hours")
    print(f"Data Period: {data.index.min()} → {data.index.max()}")
    print("-" * 60)

    stats = bt.run()

    # Display key metrics
    print(f"\n📊 KEY METRICS:")
    print(f"Total Trades: {stats['# Trades']}")
    if stats['# Trades'] > 0:
        print(f"Win Rate: {stats['Win Rate [%]']:.2f}%")
        print(f"Return: {stats['Return [%]']:.2f}%")
        print(f"Sharpe: {stats['Sharpe Ratio']:.2f}" if not np.isnan(stats['Sharpe Ratio']) else "Sharpe: N/A")
        print(f"Max Drawdown: {stats['Max. Drawdown [%]']:.2f}%")
        print(f"Exposure Time: {stats['Exposure Time [%]']:.2f}%")

        print("\n✅ LIQUIDATION STRATEGY RESULTS:")
        print("="*60)
        print(stats)
    else:
        print("❌ No trades generated - try adjusting parameters or getting more liquidation data")

else:
    print("❌ Insufficient data for backtesting")