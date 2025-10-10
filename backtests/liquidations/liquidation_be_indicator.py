"""
Liquidation + BE Indicator Strategy
===================================

Combines large liquidation events with BE-Indicator aggregator logic for enhanced signals.

Strategy Logic:
1. Monitor for large liquidations (>$5M) as primary trigger
2. Use BE-Indicator conditions for confirmation
3. Only trade when both liquidation pressure AND BE conditions align
4. Enhanced risk management with multiple exit conditions
"""

import pandas as pd
import numpy as np
import talib
import pandas_ta as ta
from backtesting import Backtest, Strategy
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Liquidation + BE Indicator Strategy Loading... 🌙")

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
LOOKBACK_HOURS = 6  # Look for liquidations in past 6 hours
POSITION_SIZE = 0.90  # Use 90% of available capital



# Load liquidation data


# Process liquidation data (same as base strategy)
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

# Prepare data (same overlap logic as base)
if len(large_liquidations) > 0:
    liq_start = large_liquidations['datetime'].min()
    liq_end = large_liquidations['datetime'].max()
    overlap_data = data[(data.index >= liq_start - timedelta(hours=24)) &
                       (data.index <= liq_end + timedelta(hours=24))]
    if len(overlap_data) > 0:
        data = overlap_data
    else:
        data = data.tail(2000)  # More data for BE indicators
else:
    data = data.tail(2000)

print(f"✅ Price data ready! {len(data)} rows 🌙")


class LiquidationBEIndicatorStrategy(Strategy):
    """
    Enhanced strategy combining liquidations with BE-Indicator logic
    """

    # Strategy parameters
    liquidation_threshold = LARGE_LIQUIDATION_THRESHOLD
    lookback_hours = LOOKBACK_HOURS
    position_size = POSITION_SIZE

    # BE-Indicator parameters
    es1_period = 14  # RSI
    es2_period = 20  # SMA
    es3_period = 50  # EMA
    es4_period = 12  # MACD fast
    es5_period = 26  # MACD slow
    es6_period = 9   # MACD signal

    # Risk management
    take_profit = 0.03   # 3%
    stop_loss = 0.02     # 2%
    max_hold_hours = 8   # Maximum holding period

    def init(self):
        """Initialize strategy with both liquidation and BE-Indicator components"""
        print("🔧 Liquidation + BE Indicator Strategy Initializing...")

        # Prepare data series for BE indicators
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        volume = pd.Series(self.data.Volume)

        # ES1: RSI (0-100 range)
        self.es1_rsi = ta.rsi(close, length=self.es1_period)
        self.es1_rsi = self.es1_rsi.fillna(50)

        # ES2: SMA vs Price (percentage difference)
        sma = ta.sma(close, length=self.es2_period)
        self.es2_sma_diff = ((close - sma) / sma * 100)
        self.es2_sma_diff = self.es2_sma_diff.fillna(0)

        # ES3: EMA vs Price (percentage difference)
        ema = ta.ema(close, length=self.es3_period)
        self.es3_ema_diff = ((close - ema) / ema * 100)
        self.es3_ema_diff = self.es3_ema_diff.fillna(0)

        # ES4: MACD components
        macd_result = ta.macd(close, fast=self.es4_period, slow=self.es5_period, signal=self.es6_period)
        if macd_result is not None and len(macd_result.columns) >= 3:
            self.es4_macd = macd_result.iloc[:, 0].fillna(0)  # MACD line
            self.es5_signal = macd_result.iloc[:, 2].fillna(0)  # Signal line
        else:
            self.es4_macd = pd.Series(np.zeros(len(close)), index=close.index)
            self.es5_signal = pd.Series(np.zeros(len(close)), index=close.index)

        # Additional technical indicators
        self.atr = self.I(talib.ATR, self.data.High, self.data.Low, self.data.Close, 14)
        self.volume_sma = self.I(talib.SMA, self.data.Volume, 20)

        print("📈 BE Indicator + Liquidation components ready! 🎯")

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

    def check_be_long_conditions(self, idx):
        """Check BE-Indicator long conditions"""
        try:
            # L-OR conditions: ES1 oversold OR price below SMA OR MACD bullish
            es1_condition = self.es1_rsi.iloc[idx] < 40  # RSI oversold
            es2_condition = self.es2_sma_diff.iloc[idx] < -2  # Price below SMA
            es4_condition = self.es4_macd.iloc[idx] > self.es5_signal.iloc[idx]  # MACD bullish

            # OR logic: At least one condition must be true
            or_conditions = es1_condition or es2_condition or es4_condition

            # Additional filters
            es3_filter = self.es3_ema_diff.iloc[idx] > -5  # Not too far below EMA

            return or_conditions and es3_filter

        except (IndexError, AttributeError):
            return False

    def check_be_short_conditions(self, idx):
        """Check BE-Indicator short conditions"""
        try:
            # S-OR conditions: ES1 overbought OR price above SMA OR MACD bearish
            es1_condition = self.es1_rsi.iloc[idx] > 60  # RSI overbought
            es2_condition = self.es2_sma_diff.iloc[idx] > 2  # Price above SMA
            es4_condition = self.es4_macd.iloc[idx] < self.es5_signal.iloc[idx]  # MACD bearish

            # OR logic: At least one condition must be true
            or_conditions = es1_condition or es2_condition or es4_condition

            # Additional filters
            es3_filter = self.es3_ema_diff.iloc[idx] < 5  # Not too far above EMA

            return or_conditions and es3_filter

        except (IndexError, AttributeError):
            return False

    def next(self):
        """Main strategy logic combining liquidations and BE indicators"""
        if len(self.data) < 100:  # Need enough data for all indicators
            return

        current_time = self.data.index[-1]
        current_price = self.data.Close[-1]
        current_idx = len(self.data) - 1

        # Get recent liquidations
        recent_liqs = self.get_recent_liquidations(current_time)
        liq_analysis = self.analyze_liquidation_pressure(recent_liqs)

        # Technical values
        atr = self.atr[-1]
        volume = self.data.Volume[-1]
        avg_volume = self.volume_sma[-1]

        # Skip if no significant liquidation pressure or invalid indicators
        if (liq_analysis['pressure'] < self.liquidation_threshold or
            np.isnan(atr) or current_idx < 0):
            return

        # Entry logic - combine liquidation pressure with BE conditions
        if not self.position:

            # Long entry: Bearish liquidation pressure + BE long conditions
            if (liq_analysis['direction'] == 'bearish' and
                liq_analysis['pressure'] >= self.liquidation_threshold and
                self.check_be_long_conditions(current_idx) and
                volume > avg_volume * 1.1):  # Volume confirmation

                sl_price = current_price * (1 - self.stop_loss)
                tp_price = current_price * (1 + self.take_profit)

                self.buy(size=self.position_size, sl=sl_price, tp=tp_price)
                print(f"🟢 LONG: Liq pressure ${liq_analysis['pressure']:,.0f} + BE signals at {current_time}")

            # Short entry: Bullish liquidation pressure + BE short conditions
            elif (liq_analysis['direction'] == 'bullish' and
                  liq_analysis['pressure'] >= self.liquidation_threshold and
                  self.check_be_short_conditions(current_idx) and
                  volume > avg_volume * 1.1):  # Volume confirmation

                sl_price = current_price * (1 + self.stop_loss)
                tp_price = current_price * (1 - self.take_profit)

                self.sell(size=self.position_size, sl=sl_price, tp=tp_price)
                print(f"🔴 SHORT: Liq pressure ${liq_analysis['pressure']:,.0f} + BE signals at {current_time}")

        # Exit logic - time-based and signal reversal
        else:
            entry_time = self.trades[-1].entry_time if self.trades else current_time
            hours_held = (current_time - entry_time).total_seconds() / 3600

            # Exit if held too long
            if hours_held >= self.max_hold_hours:
                self.position.close()
                print(f"⏰ TIME EXIT: Held for {hours_held:.1f} hours")

            # Exit on BE signal reversal
            elif self.position.is_long and self.check_be_short_conditions(current_idx):
                self.position.close()
                print(f"🔄 SIGNAL REVERSAL EXIT: BE conditions flipped")

            elif self.position.is_short and self.check_be_long_conditions(current_idx):
                self.position.close()
                print(f"🔄 SIGNAL REVERSAL EXIT: BE conditions flipped")


# Run backtest
if len(data) > 200:
    bt = Backtest(data, LiquidationBEIndicatorStrategy, cash=1000000, commission=0.001)

    print("\n🌙 ===== LIQUIDATION + BE INDICATOR STRATEGY RESULTS ===== 🌙")
    print(f"Large Liquidation Threshold: ${LARGE_LIQUIDATION_THRESHOLD:,}")
    print(f"Lookback Period: {LOOKBACK_HOURS} hours")
    print("-" * 60)

    stats = bt.run()

    print(f"\n📊 KEY METRICS:")
    print(f"Total Trades: {stats['# Trades']}")
    if stats['# Trades'] > 0:
        print(f"Win Rate: {stats['Win Rate [%]']:.2f}%")
        print(f"Return: {stats['Return [%]']:.2f}%")
        print(f"Sharpe: {stats['Sharpe Ratio']:.2f}" if not np.isnan(stats['Sharpe Ratio']) else "Sharpe: N/A")
        print(f"Max Drawdown: {stats['Max. Drawdown [%]']:.2f}%")

        print("\n✅ LIQUIDATION + BE INDICATOR RESULTS:")
        print("="*60)
        print(stats)
    else:
        print("❌ No trades generated")

else:
    print("❌ Insufficient data for backtesting")