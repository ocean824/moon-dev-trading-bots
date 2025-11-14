"""
CHECK ACTUAL RSI VALUES
Created by: Moon Dev
"""

import pandas as pd
import pandas_ta as ta

# Load data
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Calculate RSI
rsi = ta.rsi(data['Close'], 14)

print(f"RSI Statistics:")
print(f"Min RSI: {rsi.min():.2f}")
print(f"Max RSI: {rsi.max():.2f}")
print(f"Mean RSI: {rsi.mean():.2f}")
print(f"Median RSI: {rsi.median():.2f}")

print(f"\nRSI Distribution:")
print(f"RSI < 20: {(rsi < 20).sum()} occurrences ({(rsi < 20).sum() / len(rsi) * 100:.1f}%)")
print(f"RSI < 30: {(rsi < 30).sum()} occurrences ({(rsi < 30).sum() / len(rsi) * 100:.1f}%)")
print(f"RSI < 40: {(rsi < 40).sum()} occurrences ({(rsi < 40).sum() / len(rsi) * 100:.1f}%)")
print(f"RSI > 60: {(rsi > 60).sum()} occurrences ({(rsi > 60).sum() / len(rsi) * 100:.1f}%)")
print(f"RSI > 70: {(rsi > 70).sum()} occurrences ({(rsi > 70).sum() / len(rsi) * 100:.1f}%)")
print(f"RSI > 80: {(rsi > 80).sum()} occurrences ({(rsi > 80).sum() / len(rsi) * 100:.1f}%)")

print(f"\nSample RSI values < 30:")
low_rsi = data[rsi < 30].head(10)
if not low_rsi.empty:
    low_rsi['RSI'] = rsi[rsi < 30].head(10)
    print(low_rsi[['Close', 'RSI']])

print(f"\nSample RSI values > 70:")
high_rsi = data[rsi > 70].head(10)
if not high_rsi.empty:
    high_rsi['RSI'] = rsi[rsi > 70].head(10)
    print(high_rsi[['Close', 'RSI']])