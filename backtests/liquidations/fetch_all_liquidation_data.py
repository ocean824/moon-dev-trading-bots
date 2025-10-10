"""
Fetch ALL Liquidation Data for Pure Liquidation Strategies
===========================================================
Pulls ALL available liquidation data using Moon Dev API for pure liquidation-based strategies.
"""

import sys
import os
sys.path.append('/Users/md/Dropbox/dev/github/moon-dev-trading-bots')

from api import MoonDevAPI
import pandas as pd
from datetime import datetime, timedelta
import numpy as np

print("🌙 Moon Dev's FULL Liquidation Data Fetcher 🚀")
print("=" * 60)

# Initialize API
api = MoonDevAPI()

print(f"📅 Fetching ALL available liquidation data...")
print("⏳ This may take several minutes...")

# Fetch ALL liquidation data (no limit parameter)
liquidation_data = api.get_liquidation_data()  # No limit = get all data

if liquidation_data is not None:
    print(f"✅ Successfully fetched {len(liquidation_data):,} liquidation records!")

    # Check date range
    if 'datetime' in liquidation_data.columns:
        date_range = liquidation_data['datetime'].max() - liquidation_data['datetime'].min()
        print(f"📅 Date range: {liquidation_data['datetime'].min()} → {liquidation_data['datetime'].max()}")
        print(f"📊 Total days: {date_range.days}")

    # Analyze the data structure
    print(f"\n📊 Data Structure:")
    print(f"Columns: {list(liquidation_data.columns)}")
    print(f"Shape: {liquidation_data.shape}")

    # Check for USD size column
    usd_columns = [col for col in liquidation_data.columns if 'usd' in col.lower() or 'size' in col.lower()]
    print(f"💰 USD/Size columns found: {usd_columns}")

    # Rename columns for clarity
    if len(liquidation_data.columns) >= 13:
        column_names = ['symbol', 'side', 'order_type', 'time_in_force', 'quantity',
                       'price', 'avg_price', 'status', 'filled_qty', 'total_qty',
                       'timestamp_ms', 'usd_value', 'datetime']
        liquidation_data.columns = column_names[:len(liquidation_data.columns)]

    # Convert usd_value to numeric if it exists
    if 'usd_value' in liquidation_data.columns:
        liquidation_data['usd_value'] = pd.to_numeric(liquidation_data['usd_value'], errors='coerce')

        # Analyze liquidation sizes
        print(f"\n💥 Liquidation Size Analysis:")
        print(f"Total liquidations: {len(liquidation_data):,}")

        # Different thresholds
        thresholds = [100_000, 500_000, 1_000_000, 5_000_000, 10_000_000]
        for threshold in thresholds:
            large_liqs = liquidation_data[liquidation_data['usd_value'] >= threshold]
            print(f"Liquidations ≥${threshold:,}: {len(large_liqs):,} ({len(large_liqs)/len(liquidation_data)*100:.2f}%)")

        # Overall statistics
        print(f"\n💰 Overall liquidation stats:")
        print(f"  Mean size: ${liquidation_data['usd_value'].mean():,.0f}")
        print(f"  Median size: ${liquidation_data['usd_value'].median():,.0f}")
        print(f"  Max size: ${liquidation_data['usd_value'].max():,.0f}")
        print(f"  Min size: ${liquidation_data['usd_value'].min():,.0f}")
        print(f"  Std dev: ${liquidation_data['usd_value'].std():,.0f}")

        # Analyze by side
        if 'side' in liquidation_data.columns:
            print(f"\n📊 Liquidations by side:")
            buy_liqs = liquidation_data[liquidation_data['side'].str.upper() == 'BUY']
            sell_liqs = liquidation_data[liquidation_data['side'].str.upper() == 'SELL']

            print(f"  Long liquidations (BUY): {len(buy_liqs):,} ({len(buy_liqs)/len(liquidation_data)*100:.1f}%)")
            print(f"  Short liquidations (SELL): {len(sell_liqs):,} ({len(sell_liqs)/len(liquidation_data)*100:.1f}%)")
            print(f"  Avg long liq size: ${buy_liqs['usd_value'].mean():,.0f}")
            print(f"  Avg short liq size: ${sell_liqs['usd_value'].mean():,.0f}")

    # Save data to results folder
    save_path = "/Users/md/Dropbox/dev/github/moon-dev-trading-bots/backtests/liquidations/results/all_liquidations.csv"

    # Create results folder if it doesn't exist
    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    liquidation_data.to_csv(save_path, index=False)

    file_size_mb = os.path.getsize(save_path) / (1024**2)
    print(f"\n💾 Data saved to: {save_path}")
    print(f"📁 File size: {file_size_mb:.2f} MB")

    # Display sample data
    print(f"\n📋 Sample Data:")
    print(liquidation_data.head())

    print(f"\n✅ ALL liquidation data fetch complete!")
    print(f"🎯 Ready for pure liquidation strategy testing!")

else:
    print("❌ Failed to fetch liquidation data!")
    print("🔍 Check your API key and internet connection")