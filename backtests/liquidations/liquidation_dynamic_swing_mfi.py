"""
Liquidation + Dynamic Swing MFI Strategy
=========================================

Combines large liquidation events with Dynamic Swing VWAP analysis and MFI confirmation.

Strategy Logic:
1. Monitor for large liquidations (>$5M) as primary trigger
2. Use Dynamic Swing VWAP for trend direction and support/resistance
3. Add MFI for money flow confirmation
4. Trade when liquidations align with swing levels and money flow
"""

import pandas as pd
import numpy as np
import talib
import pandas_ta as ta
from backtesting import Backtest, Strategy
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Liquidation + Dynamic Swing MFI Strategy Loading... 🌙")

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
LOOKBACK_HOURS = 5  # Look for liquidations in past 5 hours
POSITION_SIZE = 0.90  # Use 90% of available capital



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
        data = data.tail(2000)  # More data for swing calculations
else:
    data = data.tail(2000)

print(f"✅ Price data ready! {len(data)} rows 🌙")


class LiquidationDynamicSwingMFIStrategy(Strategy):
    """
    Advanced strategy combining liquidations, swing VWAP, and MFI
    """

    # Strategy parameters
    liquidation_threshold = LARGE_LIQUIDATION_THRESHOLD
    lookback_hours = LOOKBACK_HOURS
    position_size = POSITION_SIZE

    # Dynamic Swing parameters
    swing_period = 50  # Period for swing detection
    base_apt = 20      # Adaptive Price Tracking
    atr_len = 50       # ATR length for adaptation

    # MFI parameters
    mfi_period = 14
    mfi_oversold = 30
    mfi_overbought = 70
    mfi_neutral_low = 45
    mfi_neutral_high = 55

    # Risk management
    take_profit = 0.04   # 4%
    stop_loss = 0.025    # 2.5%
    max_hold_hours = 10  # Maximum holding period

    def init(self):
        """Initialize strategy with swing, MFI and liquidation components"""
        print("🔧 Liquidation + Dynamic Swing MFI Strategy Initializing...")

        # Initialize swing point detection
        self.swing_high = self.I(self.calculate_swing_high)
        self.swing_low = self.I(self.calculate_swing_low)

        # ATR for adaptation
        self.atr = self.I(talib.ATR, self.data.High, self.data.Low, self.data.Close, self.atr_len)
        self.atr_avg = self.I(talib.SMA, self.atr, self.atr_len)

        # Calculate direction and dynamic VWAP
        self.direction = self.I(self.calculate_direction)
        self.vwap = self.I(self.calculate_dynamic_vwap)

        # Money Flow Index
        self.mfi = self.I(talib.MFI, self.data.High, self.data.Low, self.data.Close,
                         self.data.Volume, self.mfi_period)

        # Additional technical indicators
        self.ema_fast = self.I(talib.EMA, self.data.Close, 12)
        self.ema_slow = self.I(talib.EMA, self.data.Close, 26)

        print("📈 Dynamic Swing + MFI + Liquidation components ready! 🎯")

    def calculate_swing_high(self):
        """Calculate swing highs"""
        high_values = pd.Series(self.data.High)
        swing_highs = np.full(len(high_values), np.nan)

        for i in range(self.swing_period, len(high_values) - self.swing_period):
            window_start = max(0, i - self.swing_period)
            window_end = min(len(high_values), i + self.swing_period + 1)

            if high_values.iloc[i] == high_values.iloc[window_start:window_end].max():
                swing_highs[i] = high_values.iloc[i]

        # Forward fill to maintain last swing high
        return pd.Series(swing_highs).ffill().values

    def calculate_swing_low(self):
        """Calculate swing lows"""
        low_values = pd.Series(self.data.Low)
        swing_lows = np.full(len(low_values), np.nan)

        for i in range(self.swing_period, len(low_values) - self.swing_period):
            window_start = max(0, i - self.swing_period)
            window_end = min(len(low_values), i + self.swing_period + 1)

            if low_values.iloc[i] == low_values.iloc[window_start:window_end].min():
                swing_lows[i] = low_values.iloc[i]

        # Forward fill to maintain last swing low
        return pd.Series(swing_lows).ffill().values

    def calculate_direction(self):
        """Calculate current trend direction based on swing points"""
        direction = np.zeros(len(self.data))

        for i in range(1, len(self.data)):
            if i < len(self.swing_high) and i < len(self.swing_low):
                swing_h = self.swing_high[i] if not np.isnan(self.swing_high[i]) else self.swing_high[i-1]
                swing_l = self.swing_low[i] if not np.isnan(self.swing_low[i]) else self.swing_low[i-1]

                if not (np.isnan(swing_h) or np.isnan(swing_l)):
                    if swing_h > swing_l:
                        direction[i] = 1  # Upward bias
                    elif swing_h < swing_l:
                        direction[i] = -1  # Downward bias
                    else:
                        direction[i] = direction[i-1] if i > 0 else 0

        return direction

    def calculate_dynamic_vwap(self):
        """Calculate dynamic VWAP based on swing points and direction"""
        vwap_values = np.full(len(self.data), np.nan)
        cumulative_pv = 0
        cumulative_vol = 0

        for i in range(len(self.data)):
            if i == 0:
                vwap_values[i] = self.data.Close[i]
                cumulative_pv = self.data.Close[i] * self.data.Volume[i]
                cumulative_vol = self.data.Volume[i]
                continue

            # Check for direction change or swing point update
            direction_change = (i > 0 and
                               hasattr(self, 'direction') and
                               len(self.direction) > i and
                               self.direction[i] != self.direction[i-1])

            if direction_change or i % self.base_apt == 0:
                # Reset VWAP calculation
                cumulative_pv = self.data.Close[i] * self.data.Volume[i]
                cumulative_vol = self.data.Volume[i]
            else:
                # Continue cumulative calculation
                cumulative_pv += self.data.Close[i] * self.data.Volume[i]
                cumulative_vol += self.data.Volume[i]

            if cumulative_vol > 0:
                vwap_values[i] = cumulative_pv / cumulative_vol
            else:
                vwap_values[i] = vwap_values[i-1] if i > 0 else self.data.Close[i]

        return vwap_values

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

        if abs(net_pressure) < total_pressure * 0.25:
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
        """Main strategy logic with swing + MFI + liquidation confirmation"""
        if len(self.data) < max(self.swing_period, self.mfi_period) + 20:
            return

        current_time = self.data.index[-1]
        current_price = self.data.Close[-1]
        idx = len(self.data) - 1

        # Get recent liquidations
        recent_liqs = self.get_recent_liquidations(current_time)
        liq_analysis = self.analyze_liquidation_pressure(recent_liqs)

        # Get current indicator values
        mfi_val = self.mfi[-1] if not np.isnan(self.mfi[-1]) else 50
        vwap_val = self.vwap[-1] if not np.isnan(self.vwap[-1]) else current_price
        direction_val = self.direction[-1] if hasattr(self, 'direction') and len(self.direction) > idx else 0
        ema_fast = self.ema_fast[-1]
        ema_slow = self.ema_slow[-1]

        # Skip if insufficient liquidation pressure
        if liq_analysis['pressure'] < self.liquidation_threshold:
            return

        # Entry logic - combined confirmation required
        if not self.position:

            # Long entry conditions:
            # 1. Bearish liquidation pressure (contrarian)
            # 2. Price above dynamic VWAP or at swing low support
            # 3. MFI oversold or neutral rising
            # 4. EMA alignment supporting direction
            if (liq_analysis['direction'] == 'bearish' and
                liq_analysis['pressure'] >= self.liquidation_threshold and
                (current_price >= vwap_val * 0.998 or direction_val >= 0) and
                mfi_val < self.mfi_neutral_high and
                ema_fast >= ema_slow * 0.999):

                sl_price = current_price * (1 - self.stop_loss)
                tp_price = current_price * (1 + self.take_profit)

                self.buy(size=self.position_size, sl=sl_price, tp=tp_price)
                print(f"🟢 LONG: Liq ${liq_analysis['pressure']:,.0f} + MFI {mfi_val:.1f} + VWAP support")

            # Short entry conditions:
            # 1. Bullish liquidation pressure (contrarian)
            # 2. Price below dynamic VWAP or at swing high resistance
            # 3. MFI overbought or neutral falling
            # 4. EMA alignment supporting direction
            elif (liq_analysis['direction'] == 'bullish' and
                  liq_analysis['pressure'] >= self.liquidation_threshold and
                  (current_price <= vwap_val * 1.002 or direction_val <= 0) and
                  mfi_val > self.mfi_neutral_low and
                  ema_fast <= ema_slow * 1.001):

                sl_price = current_price * (1 + self.stop_loss)
                tp_price = current_price * (1 - self.take_profit)

                self.sell(size=self.position_size, sl=sl_price, tp=tp_price)
                print(f"🔴 SHORT: Liq ${liq_analysis['pressure']:,.0f} + MFI {mfi_val:.1f} + VWAP resistance")

        # Exit logic
        else:
            entry_time = self.trades[-1].entry_time if self.trades else current_time
            hours_held = (current_time - entry_time).total_seconds() / 3600

            # Time-based exit
            if hours_held >= self.max_hold_hours:
                self.position.close()
                print(f"⏰ TIME EXIT: Held for {hours_held:.1f} hours")

            # MFI reversal exit
            elif self.position.is_long and mfi_val > self.mfi_overbought:
                self.position.close()
                print(f"💰 MFI OVERBOUGHT EXIT: MFI {mfi_val:.1f}")

            elif self.position.is_short and mfi_val < self.mfi_oversold:
                self.position.close()
                print(f"💰 MFI OVERSOLD EXIT: MFI {mfi_val:.1f}")

            # VWAP break exit
            elif self.position.is_long and current_price < vwap_val * 0.995:
                self.position.close()
                print(f"📉 VWAP BREAK EXIT: Price broke below VWAP")

            elif self.position.is_short and current_price > vwap_val * 1.005:
                self.position.close()
                print(f"📈 VWAP BREAK EXIT: Price broke above VWAP")


# Run backtest
if len(data) > 200:
    bt = Backtest(data, LiquidationDynamicSwingMFIStrategy, cash=1000000, commission=0.001)

    print("\n🌙 ===== LIQUIDATION + DYNAMIC SWING MFI STRATEGY RESULTS ===== 🌙")
    print(f"Large Liquidation Threshold: ${LARGE_LIQUIDATION_THRESHOLD:,}")
    print(f"Swing Period: {LiquidationDynamicSwingMFIStrategy.swing_period}")
    print(f"MFI Period: {LiquidationDynamicSwingMFIStrategy.mfi_period}")
    print("-" * 60)

    stats = bt.run()

    print(f"\n📊 KEY METRICS:")
    print(f"Total Trades: {stats['# Trades']}")
    if stats['# Trades'] > 0:
        print(f"Win Rate: {stats['Win Rate [%]']:.2f}%")
        print(f"Return: {stats['Return [%]']:.2f}%")
        print(f"Sharpe: {stats['Sharpe Ratio']:.2f}" if not np.isnan(stats['Sharpe Ratio']) else "Sharpe: N/A")
        print(f"Max Drawdown: {stats['Max. Drawdown [%]']:.2f}%")

        print("\n✅ LIQUIDATION + DYNAMIC SWING MFI RESULTS:")
        print("="*60)
        print(stats)
    else:
        print("❌ No trades generated")

else:
    print("❌ Insufficient data for backtesting")