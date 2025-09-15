"""
Debug script to test Volume by Time signal generation
"""

import pandas as pd
import numpy as np
import sys
import os

# Add parent directories to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Load data
data_path = "/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1d-100wks-data.csv"
data = pd.read_csv(data_path, index_col=0, parse_dates=True)

# Rename columns
if 'open' in data.columns:
    data = data.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low',
                               'close': 'Close', 'volume': 'Volume'})

print("Data shape:", data.shape)
print("Date range:", data.index[0], "to", data.index[-1])
print("\nFirst few rows:")
print(data.head())

# Calculate volume ratio
lookback_days = 20
volume_threshold = 1.1

volume_series = data['Volume']
volume_ratios = []

for i in range(len(volume_series)):
    if i < lookback_days:
        volume_ratios.append(1.0)
        continue

    # Get historical volumes for lookback period
    historical_volumes = volume_series[max(0, i-lookback_days):i]

    if len(historical_volumes) > 0:
        historical_avg = historical_volumes.mean()
        if historical_avg > 0:
            ratio = volume_series.iloc[i] / historical_avg
        else:
            ratio = 1.0
    else:
        ratio = 1.0

    volume_ratios.append(ratio)

data['VolumeRatio'] = volume_ratios

# Calculate price direction
data['PriceDir'] = np.where(data['Close'] > data['Open'], 1, -1)

# Calculate SMA20
data['SMA20'] = data['Close'].rolling(20).mean()

# Check for signals
data['LongSignal'] = (
    (data['VolumeRatio'] > volume_threshold) &
    (data['PriceDir'] > 0) &
    (data['Close'] > data['SMA20'])
)

data['ShortSignal'] = (
    (data['VolumeRatio'] > volume_threshold) &
    (data['PriceDir'] < 0) &
    (data['Close'] < data['SMA20'])
)

print("\n" + "="*60)
print("SIGNAL ANALYSIS")
print("="*60)
print(f"Total Long Signals: {data['LongSignal'].sum()}")
print(f"Total Short Signals: {data['ShortSignal'].sum()}")

print("\nVolume Ratio Statistics:")
print(f"  Min: {data['VolumeRatio'].min():.2f}")
print(f"  Max: {data['VolumeRatio'].max():.2f}")
print(f"  Mean: {data['VolumeRatio'].mean():.2f}")
print(f"  Median: {data['VolumeRatio'].median():.2f}")
print(f"  Std: {data['VolumeRatio'].std():.2f}")

print(f"\nVolume ratios > {volume_threshold}: {(data['VolumeRatio'] > volume_threshold).sum()}")
print(f"Bullish days: {(data['PriceDir'] > 0).sum()}")
print(f"Days above SMA20: {(data['Close'] > data['SMA20']).sum()}")

# Show some days with high volume ratios
high_volume_days = data[data['VolumeRatio'] > volume_threshold].sort_values('VolumeRatio', ascending=False)
print(f"\nTop 10 high volume ratio days:")
for idx in high_volume_days.head(10).index:
    row = data.loc[idx]
    print(f"  {idx.date()}: Ratio={row['VolumeRatio']:.2f}, Price={row['Close']:.2f}, Dir={'Bull' if row['PriceDir'] > 0 else 'Bear'}, Above SMA20={'Yes' if row['Close'] > row['SMA20'] else 'No'}")

# Check why signals might not be triggering
print("\n" + "="*60)
print("SIGNAL CONDITION BREAKDOWN")
print("="*60)

# Count conditions met
cond1 = (data['VolumeRatio'] > volume_threshold)
cond2 = (data['PriceDir'] > 0)
cond3 = (data['Close'] > data['SMA20'])

print(f"Volume spike days: {cond1.sum()}")
print(f"Volume spike + Bullish: {(cond1 & cond2).sum()}")
print(f"Volume spike + Bullish + Above SMA20: {(cond1 & cond2 & cond3).sum()}")

# Show some potential signal days
potential_signals = data[(cond1 & cond2)].head(10)
print("\nPotential signal days (volume spike + bullish):")
for idx in potential_signals.index:
    row = data.loc[idx]
    sma20_str = f"{row['SMA20']:.2f}" if not pd.isna(row['SMA20']) else "N/A"
    print(f"  {idx.date()}: Volume Ratio={row['VolumeRatio']:.2f}, Close={row['Close']:.2f}, SMA20={sma20_str}")