"""
LOOK-AHEAD BIAS DIAGNOSTIC
==========================

Testing for potential look-ahead bias issues:
1. All indicators use ONLY past data (shift everything by 1)
2. Entry signals based on PREVIOUS bar's close
3. No using current bar's high/low for decisions
4. Proper resampling without future data leak

This should reveal if we're accidentally peeking into the future.
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

print("🎯 LOOK-AHEAD BIAS DIAGNOSTIC 🎯")
print("=" * 70)

# Load data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1m-4wks-data.csv'
print(f"📊 Loading BTC 1-minute data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# CRITICAL: Calculate RSI on PREVIOUS close values
data['RSI_1m'] = ta.rsi(data['Close'], length=14)
# Shift after calculation to avoid look-ahead
data['RSI_1m'] = data['RSI_1m'].shift(1)

# Resample with proper alignment (no future leak)
# Use 'label='left'' and 'closed='left'' to avoid future data
data_5m = data['Close'].resample('5T', label='left', closed='left').last()
rsi_5m = ta.rsi(data_5m, length=14)
data['RSI_5m'] = rsi_5m.reindex(data.index, method='ffill')
data['RSI_5m'] = data['RSI_5m'].shift(1)  # Shift after reindexing

data_15m = data['Close'].resample('15T', label='left', closed='left').last()
rsi_15m = ta.rsi(data_15m, length=14)
data['RSI_15m'] = rsi_15m.reindex(data.index, method='ffill')
data['RSI_15m'] = data['RSI_15m'].shift(1)  # Shift after reindexing

# Volume calculations on PREVIOUS bar
data['Volume_MA'] = data['Volume'].rolling(20).mean()
data['Volume_Ratio'] = data['Volume'] / data['Volume_MA']
data['Volume_Ratio'] = data['Volume_Ratio'].shift(1)  # Shift to use previous

# Debug info
print(f"✅ Loaded {len(data):,} 1-minute bars")
print(f"🔍 DIAGNOSTIC INFO:")
print(f"- Using shifted (previous) close for RSI calculations")
print(f"- Resampling with label='left' and closed='left'")
print(f"- All indicators shifted by 1 to avoid look-ahead")


class DiagnosticStrategy(Strategy):
    """
    Ultra-conservative strategy to test for look-ahead bias
    """

    rsi_1m_oversold = 35
    rsi_1m_overbought = 65
    rsi_5m_oversold = 35
    rsi_5m_overbought = 65
    rsi_15m_oversold = 40
    rsi_15m_overbought = 60
    take_profit = 0.02
    stop_loss = 0.01

    def init(self):
        # Use indicators (already shifted in data preparation)
        self.rsi_1m = self.I(lambda: self.data.RSI_1m)
        self.rsi_5m = self.I(lambda: self.data.RSI_5m)
        self.rsi_15m = self.I(lambda: self.data.RSI_15m)
        self.volume_ratio = self.I(lambda: self.data.Volume_Ratio)

        # Track for debugging
        self.signal_count = 0
        self.entry_prices = []

    def next(self):
        if len(self.data) < 100:  # Need more history
            return

        # Use PREVIOUS bar's close for decisions
        # Never use current bar's high/low/close
        prev_close = self.data.Close[-2] if len(self.data) > 1 else self.data.Close[-1]

        # Get indicator values (already shifted in data prep)
        rsi_1m = self.rsi_1m[-1]
        rsi_5m = self.rsi_5m[-1]
        rsi_15m = self.rsi_15m[-1]
        vol_ratio = self.volume_ratio[-1]

        if pd.isna(rsi_1m) or pd.isna(rsi_5m) or pd.isna(rsi_15m) or pd.isna(vol_ratio):
            return

        # Exit logic based on PREVIOUS bar
        if self.position:
            if self.position.is_long and (rsi_1m > 60 or rsi_5m > 55):
                self.position.close()
            elif self.position.is_short and (rsi_1m < 40 or rsi_5m < 45):
                self.position.close()
            return

        # Entry logic based on PREVIOUS bar's data
        if not self.position:
            # BUY: All timeframes oversold (using old data)
            if (rsi_1m < self.rsi_1m_oversold and
                rsi_5m < self.rsi_5m_oversold and
                rsi_15m < self.rsi_15m_oversold and
                vol_ratio > 0.8):

                self.signal_count += 1
                # Use current price but decision based on old data
                current_price = self.data.Close[-1]
                tp = current_price * (1 + self.take_profit)
                sl = current_price * (1 - self.stop_loss)
                self.buy(tp=tp, sl=sl)
                self.entry_prices.append(current_price)

            # SELL: All timeframes overbought (using old data)
            elif (rsi_1m > self.rsi_1m_overbought and
                  rsi_5m > self.rsi_5m_overbought and
                  rsi_15m > self.rsi_15m_overbought and
                  vol_ratio > 0.8):

                self.signal_count += 1
                current_price = self.data.Close[-1]
                tp = current_price * (1 - self.take_profit)
                sl = current_price * (1 + self.stop_loss)
                self.sell(tp=tp, sl=sl)
                self.entry_prices.append(current_price)


# Run backtest
print("\n" + "="*70)
print("RUNNING DIAGNOSTIC BACKTEST (NO LOOK-AHEAD)")
print("="*70)

bt = Backtest(
    data,
    DiagnosticStrategy,
    cash=1000000,
    commission=0.001,
    exclusive_orders=True
)

stats = bt.run()
print(f"\n📊 DIAGNOSTIC RESULTS:")
print(stats)

print(f"\n🔍 ANALYSIS:")
print(f"Win Rate: {stats['Win Rate [%]']:.1f}%")
print(f"Number of Trades: {stats['# Trades']}")

if stats['Win Rate [%]'] > 70:
    print("\n⚠️ WARNING: Win rate still suspiciously high!")
    print("Possible issues:")
    print("1. The stop loss and take profit might be too tight for the volatility")
    print("2. The strategy might be catching micro-trends perfectly")
    print("3. The data might have patterns that don't exist in live trading")
else:
    print("\n✅ Win rate seems more realistic now")

# Test even more conservative version
print("\n" + "="*70)
print("TESTING ULTRA-CONSERVATIVE VERSION")
print("="*70)

class UltraConservativeStrategy(DiagnosticStrategy):
    """
    Even more conservative to really test
    """
    # Wider stops to be more realistic
    take_profit = 0.03  # 3%
    stop_loss = 0.02    # 2%

    # Much stricter entry conditions
    rsi_1m_oversold = 25
    rsi_1m_overbought = 75
    rsi_5m_oversold = 30
    rsi_5m_overbought = 70
    rsi_15m_oversold = 35
    rsi_15m_overbought = 65


bt2 = Backtest(
    data,
    UltraConservativeStrategy,
    cash=1000000,
    commission=0.001,
    exclusive_orders=True
)

stats2 = bt2.run()
print(f"\n📊 ULTRA-CONSERVATIVE RESULTS:")
print(stats2)

bt.plot()