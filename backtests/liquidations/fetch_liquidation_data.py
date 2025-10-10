"""
Fetch Liquidation Data for Strategy Testing
===========================================
Pulls 120 days of liquidation data using Moon Dev API for use in liquidation strategies.
"""

import sys
import os
sys.path.append('/Users/md/Dropbox/dev/github/moon-dev-trading-bots')

from api import MoonDevAPI
import pandas as pd
from datetime import datetime, timedelta
import numpy as np

print("🌙 Moon Dev's Liquidation Data Fetcher 🚀")
print("=" * 60)

# Initialize API
api = MoonDevAPI()

# Calculate approximate number of records for 90 days
# Based on initial test: 120,000 records = ~1 day
# So for 90 days: 120,000 * 90 = 10,800,000 records
# Let's pull 12 million to be safe
estimated_records = 12_000_000  # 12 million records for ~90-100 days

print(f"📅 Fetching liquidation data for approximately 90 days...")
print(f"🎯 Estimated records needed: ~{estimated_records:,}")
print("⏳ This may take a few minutes...")

# Fetch liquidation data
liquidation_data = api.get_liquidation_data(limit=estimated_records)

if liquidation_data is not None:
    print(f"✅ Successfully fetched {len(liquidation_data):,} liquidation records!")

    # Check date range
    if 'datetime' in liquidation_data.columns:
        date_range = liquidation_data['datetime'].max() - liquidation_data['datetime'].min()
        print(f"📅 Date range: {liquidation_data['datetime'].min()} → {liquidation_data['datetime'].max()}")
        print(f"📊 Total days: {date_range.days}")

        # Filter to last 90 days if we have more
        cutoff_date = liquidation_data['datetime'].max() - timedelta(days=90)
        recent_data = liquidation_data[liquidation_data['datetime'] >= cutoff_date]

        print(f"🎯 Filtered to last 90 days: {len(recent_data):,} records")
        print(f"📅 Final range: {recent_data['datetime'].min()} → {recent_data['datetime'].max()}")

        liquidation_data = recent_data

    # Analyze the data structure
    print(f"\n📊 Data Structure:")
    print(f"Columns: {list(liquidation_data.columns)}")
    print(f"Shape: {liquidation_data.shape}")

    # Check for USD size column
    usd_columns = [col for col in liquidation_data.columns if 'usd' in col.lower() or 'size' in col.lower()]
    print(f"💰 USD/Size columns found: {usd_columns}")

    # Convert usd_size to numeric if it exists
    if 'usd_size' in liquidation_data.columns:
        liquidation_data['usd_size'] = pd.to_numeric(liquidation_data['usd_size'], errors='coerce')

        # Analyze liquidation sizes
        large_liq_threshold = 5_000_000  # $5M threshold
        large_liquidations = liquidation_data[liquidation_data['usd_size'] >= large_liq_threshold]

        print(f"\n💥 Liquidation Analysis:")
        print(f"Total liquidations: {len(liquidation_data):,}")
        print(f"Large liquidations (≥$5M): {len(large_liquidations):,}")
        print(f"Percentage of large liquidations: {len(large_liquidations)/len(liquidation_data)*100:.2f}%")

        if len(large_liquidations) > 0:
            print(f"💰 Large liquidation stats:")
            print(f"  Average size: ${large_liquidations['usd_size'].mean():,.0f}")
            print(f"  Median size: ${large_liquidations['usd_size'].median():,.0f}")
            print(f"  Max size: ${large_liquidations['usd_size'].max():,.0f}")
            print(f"  Min size: ${large_liquidations['usd_size'].min():,.0f}")

    # Save data to CSV
    save_path = "/Users/md/Dropbox/dev/github/moon-dev-trading-bots/backtests/liquidations/data/liquidations_90days.csv"
    liquidation_data.to_csv(save_path, index=False)

    file_size_mb = os.path.getsize(save_path) / (1024**2)
    print(f"\n💾 Data saved to: {save_path}")
    print(f"📁 File size: {file_size_mb:.2f} MB")

    # Display sample data
    print(f"\n📋 Sample Data:")
    print(liquidation_data.head())

    print(f"\n✅ Liquidation data fetch complete!")
    print(f"🎯 Ready for strategy testing!")

else:
    print("❌ Failed to fetch liquidation data!")
    print("🔍 Check your API key and internet connection")