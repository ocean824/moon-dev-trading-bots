"""
DEBUG DATA ISSUE
Created by: Moon Dev
"""

import pandas as pd

# Load data
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
print(f"Column names: {data.columns.tolist()}")
print(f"\nFirst 5 rows:")
print(data.head())

# Check Open vs Close
print(f"\nData statistics:")
print(f"Open == Close: {(data['open'] == data['close']).sum()} rows")
print(f"Open > Close: {(data['open'] > data['close']).sum()} rows")
print(f"Open < Close: {(data['open'] < data['close']).sum()} rows")

# Sample where open != close
diff_samples = data[data['open'] != data['close']].head(10)
print(f"\nSample rows where Open != Close:")
print(diff_samples)