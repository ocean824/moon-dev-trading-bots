"""
TEST SIMPLE STRATEGY - DEBUG VERSION
Created by: Moon Dev
"""

import pandas as pd
import numpy as np
import pandas_ta as ta

print("🚀 Moon Dev's Debug Test Loading... 🌙")

# Load data
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()

print(f"✅ Data loaded! {len(data)} rows")
print(f"Date range: {data.index[0]} to {data.index[-1]}")
print(f"Price range: ${data['Close'].min():.2f} to ${data['Close'].max():.2f}")

# Calculate indicators
support = data['Low'].rolling(20).min()
resistance = data['High'].rolling(20).max()
rsi = ta.rsi(data['Close'], 14)
atr = ta.atr(data['High'], data['Low'], data['Close'], 14)

# Check conditions at various points
data['support'] = support
data['resistance'] = resistance
data['rsi'] = rsi
data['atr'] = atr

# Calculate zones
data['support_zone_upper'] = data['support'] + (data['atr'] * 0.5)
data['resistance_zone_lower'] = data['resistance'] - (data['atr'] * 0.5)

# Check long conditions
data['near_support'] = data['Close'] <= data['support_zone_upper']
data['rsi_oversold'] = data['rsi'] < 45
data['bullish_bar'] = data['Close'] > data['Open']
data['long_signal'] = data['near_support'] & data['rsi_oversold'] & data['bullish_bar']

# Check short conditions
data['near_resistance'] = data['Close'] >= data['resistance_zone_lower']
data['rsi_overbought'] = data['rsi'] > 55
data['bearish_bar'] = data['Close'] < data['Open']
data['short_signal'] = data['near_resistance'] & data['rsi_overbought'] & data['bearish_bar']

# Count signals
print(f"\n📊 Signal Analysis:")
print(f"Near support count: {data['near_support'].sum()}")
print(f"RSI oversold count: {data['rsi_oversold'].sum()}")
print(f"Bullish bar count: {data['bullish_bar'].sum()}")
print(f"Long signals (all conditions): {data['long_signal'].sum()}")
print(f"\nNear resistance count: {data['near_resistance'].sum()}")
print(f"RSI overbought count: {data['rsi_overbought'].sum()}")
print(f"Bearish bar count: {data['bearish_bar'].sum()}")
print(f"Short signals (all conditions): {data['short_signal'].sum()}")

# Show some examples where conditions are close
print("\n🔍 Sample data points where price is near support:")
near_support_samples = data[data['near_support'] == True].head(5)
if not near_support_samples.empty:
    print(near_support_samples[['Close', 'support', 'support_zone_upper', 'rsi', 'bullish_bar']])

print("\n🔍 Sample data points where RSI is oversold:")
rsi_samples = data[data['rsi'] < 30].head(5)
if not rsi_samples.empty:
    print(rsi_samples[['Close', 'support', 'rsi', 'near_support']])

# Try with more relaxed conditions
print("\n🎯 Testing with progressively more relaxed conditions:")
print(f"RSI < 50: {(data['rsi'] < 50).sum()} occurrences")
print(f"RSI < 50 AND bullish bar: {((data['rsi'] < 50) & data['bullish_bar']).sum()} occurrences")
print(f"Just bullish bars: {data['bullish_bar'].sum()} occurrences")
print(f"Just bearish bars: {data['bearish_bar'].sum()} occurrences")