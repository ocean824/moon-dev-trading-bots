"""
Base Liquidation Strategy - Medium Liquidations (>$1M)
======================================================

This strategy monitors for medium liquidations (over $1M) and trades based on the assumption
that medium-large liquidations create temporary price distortions that can be exploited.

Strategy Logic:
1. Monitor liquidation events from liquidation data
2. Identify medium liquidations (>$1M USD value)
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

print("🚀 Moon Dev's Medium Liquidation Strategy (>$1M) Loading... 🌙")

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


# Strategy parameters - LOWERED THRESHOLD
MEDIUM_LIQUIDATION_THRESHOLD = 1_000_000  # $1M USD (lowered from $5M)
LOOKBACK_HOURS = 6  # Look for liquidations in past 6 hours
POSITION_SIZE = 0.95  # Use 95% of available capital



# Load liquidation data


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

        # Filter for medium liquidations with lower threshold
        medium_liqs = liq_df[liq_df['usd_value'] >= MEDIUM_LIQUIDATION_THRESHOLD].copy()

        print(f"📊 Total liquidations: {len(liq_df):,}")
        print(f"💥 Medium liquidations (≥${MEDIUM_LIQUIDATION_THRESHOLD:,}): {len(medium_liqs):,}")

        if len(medium_liqs) > 0:
            print(f"💰 Medium liquidation stats:")
            print(f"  Average size: ${medium_liqs['usd_value'].mean():,.0f}")
            print(f"  Max size: ${medium_liqs['usd_value'].max():,.0f}")
            print(f"  Date range: {medium_liqs['datetime'].min()} → {medium_liqs['datetime'].max()}")

        return medium_liqs
    else:
        print(f"⚠️ Unexpected liquidation data structure: {len(liq_df.columns)} columns")
        return pd.DataFrame()

# Process liquidation data
medium_liquidations = process_liquidation_data(liq_data)

# For now, use the most recent data we have
# Since liquidations are from June-Sept 2025 but price data is older,
# we'll use the most recent price data available
data = data.tail(2160)  # 90 days of hourly data

print(f"✅ Price data ready! {len(data)} rows from {data.index.min()} to {data.index.max()} 🌙")
print(f"📊 Using price data for backtesting (actual liquidations would occur in future)")


class MediumLiquidationStrategy(Strategy):
    """
    Medium liquidation strategy that trades on $1M+ liquidation events

    Logic:
    1. Monitor for medium liquidation events in recent hours
    2. Trade opposite to liquidation direction (contrarian)
    3. Use technical indicators for confirmation
    4. Exit based on time or profit/loss targets
    """

    # Strategy parameters
    liquidation_threshold = MEDIUM_LIQUIDATION_THRESHOLD
    lookback_hours = LOOKBACK_HOURS
    position_size = POSITION_SIZE

    # Risk management
    take_profit = 0.02   # 2% (reduced from 2.5%)
    stop_loss = 0.012    # 1.2% (tighter stop)
    max_hold_hours = 8   # Maximum holding period

    def init(self):
        """Initialize strategy components"""
        print("🔧 Medium Liquidation Strategy Initializing...")

        # Technical indicators for confirmation
        self.rsi = self.I(talib.RSI, self.data.Close, 14)
        self.ema_fast = self.I(talib.EMA, self.data.Close, 12)
        self.ema_slow = self.I(talib.EMA, self.data.Close, 26)
        self.atr = self.I(talib.ATR, self.data.High, self.data.Low, self.data.Close, 14)

        # Volume indicators
        self.volume_sma = self.I(talib.SMA, self.data.Volume, 20)

        # Bollinger Bands for mean reversion
        self.bb_upper, self.bb_middle, self.bb_lower = self.I(
            talib.BBANDS, self.data.Close, timeperiod=20, nbdevup=2, nbdevdn=2
        )

        print("📈 Technical indicators calculated! Ready to hunt medium liquidations! 🎯")

    def get_recent_liquidations(self, current_time):
        """Get liquidations in the lookback period"""
        if len(medium_liquidations) == 0:
            return pd.DataFrame()

        # For backtesting, simulate liquidations throughout the price data period
        # This is a simulation since actual liquidations are from the future
        # In production, this would look for actual recent liquidations

        # Create synthetic liquidation signals based on volatility
        # This simulates what liquidations might have looked like during this period
        return self.simulate_liquidations(current_time)

    def simulate_liquidations(self, current_time):
        """Simulate liquidations based on price volatility for backtesting"""
        # Get current index position
        current_idx = None
        for i, timestamp in enumerate(self.data.index):
            if timestamp == current_time:
                current_idx = i
                break

        if current_idx is None or current_idx < 20:
            return pd.DataFrame()

        # Check for significant price movement (simulating liquidation events)
        price_change = (self.data.Close[current_idx] - self.data.Close[current_idx-1]) / self.data.Close[current_idx-1]
        volume_ratio = self.data.Volume[current_idx] / self.volume_sma[current_idx] if self.volume_sma[current_idx] > 0 else 1

        # Simulate liquidation if there's significant price movement and volume
        if abs(price_change) > 0.01 and volume_ratio > 1.5:  # 1% price move and 50% above avg volume
            # Create synthetic liquidation event
            side = 'SELL' if price_change < 0 else 'BUY'
            usd_value = abs(price_change) * 100_000_000 * volume_ratio  # Scale by price move and volume

            if usd_value >= self.liquidation_threshold:
                return pd.DataFrame([{
                    'side': side,
                    'usd_value': usd_value,
                    'datetime': current_time
                }])

        return pd.DataFrame()

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

        # Get recent liquidations (simulated for backtesting)
        recent_liqs = self.get_recent_liquidations(current_time)
        liq_analysis = self.analyze_liquidation_pressure(recent_liqs)

        # Technical indicator values
        rsi = self.rsi[-1]
        ema_fast = self.ema_fast[-1]
        ema_slow = self.ema_slow[-1]
        atr = self.atr[-1]
        volume = self.data.Volume[-1]
        avg_volume = self.volume_sma[-1]

        # Bollinger Band position
        bb_upper = self.bb_upper[-1]
        bb_lower = self.bb_lower[-1]

        # Skip if no liquidation pressure or invalid indicators
        if (liq_analysis['pressure'] < self.liquidation_threshold or
            np.isnan(rsi) or np.isnan(atr)):
            return

        # Entry logic - trade opposite to liquidation pressure (contrarian)
        if not self.position:

            # Long entry: Heavy sell liquidations (bearish pressure) + oversold conditions
            if (liq_analysis['direction'] == 'bearish' and
                liq_analysis['pressure'] >= self.liquidation_threshold and
                (rsi < 40 or current_price < bb_lower) and  # Oversold or below BB
                volume > avg_volume * 1.2):  # Above average volume

                # Calculate dynamic stop loss and take profit based on ATR
                sl_price = current_price * (1 - self.stop_loss)
                tp_price = current_price * (1 + self.take_profit)

                self.buy(size=self.position_size, sl=sl_price, tp=tp_price)
                print(f"🟢 LONG: Liquidation pressure ${liq_analysis['pressure']:,.0f} at {current_time}")

            # Short entry: Heavy buy liquidations (bullish pressure) + overbought conditions
            elif (liq_analysis['direction'] == 'bullish' and
                  liq_analysis['pressure'] >= self.liquidation_threshold and
                  (rsi > 60 or current_price > bb_upper) and  # Overbought or above BB
                  volume > avg_volume * 1.2):  # Above average volume

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

            # Exit on technical reversal
            elif self.position.is_long and (rsi > 70 or current_price > bb_upper):
                self.position.close()
                print(f"📈 OVERBOUGHT EXIT: RSI {rsi:.1f}")

            elif self.position.is_short and (rsi < 30 or current_price < bb_lower):
                self.position.close()
                print(f"📉 OVERSOLD EXIT: RSI {rsi:.1f}")


# Run backtest
if len(data) > 100:  # Ensure we have enough data
    bt = Backtest(data, MediumLiquidationStrategy, cash=1000000, commission=0.001)

    print("\n🌙 ===== MEDIUM LIQUIDATION STRATEGY RESULTS ===== 🌙")
    print(f"Medium Liquidation Threshold: ${MEDIUM_LIQUIDATION_THRESHOLD:,}")
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

        print("\n✅ MEDIUM LIQUIDATION STRATEGY RESULTS:")
        print("="*60)
        print(stats)
    else:
        print("❌ No trades generated - try adjusting parameters")

else:
    print("❌ Insufficient data for backtesting")