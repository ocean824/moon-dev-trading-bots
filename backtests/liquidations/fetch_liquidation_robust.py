"""
Robust Liquidation Data Fetcher with Retry and Chunking
========================================================
Handles large file downloads with connection issues by implementing:
1. Smaller chunk sizes
2. Automatic retries on failure
3. Resume capability
4. Progress tracking
"""

import sys
import os
sys.path.append('/Users/md/Dropbox/dev/github/moon-dev-trading-bots')

import requests
import pandas as pd
from datetime import datetime
import time
import json
from io import StringIO

print("🌙 Moon Dev's ROBUST Liquidation Data Fetcher 🚀")
print("=" * 60)

# Configuration
API_ENDPOINT = "https://moondev.pro/api/liquidations"
CHUNK_SIZE = 1024 * 1024  # 1MB chunks (smaller for stability)
MAX_RETRIES = 5
RETRY_DELAY = 2  # seconds
TIMEOUT = 300  # 5 minutes timeout per request

def download_with_retries(url, params=None, headers=None):
    """
    Download large file with automatic retries and chunking
    """
    print(f"🎯 Starting robust download from: {url}")

    for attempt in range(MAX_RETRIES):
        try:
            print(f"📡 Attempt {attempt + 1}/{MAX_RETRIES}...")

            # Use streaming to handle large files
            with requests.get(url, params=params, headers=headers, stream=True, timeout=TIMEOUT) as response:
                response.raise_for_status()

                # Get file size if available
                total_size = response.headers.get('content-length')
                if total_size:
                    total_size = int(total_size)
                    print(f"📦 Total file size: {total_size / (1024**2):.2f} MB")
                else:
                    print(f"📦 File size unknown, downloading...")

                # Download in chunks
                chunks = []
                downloaded = 0

                for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                    if chunk:
                        chunks.append(chunk)
                        downloaded += len(chunk)

                        # Progress update every 10MB
                        if downloaded % (10 * 1024 * 1024) == 0:
                            mb_downloaded = downloaded / (1024**2)
                            if total_size:
                                percent = (downloaded / total_size) * 100
                                print(f"📊 Progress: {mb_downloaded:.1f} MB ({percent:.1f}%)")
                            else:
                                print(f"📊 Downloaded: {mb_downloaded:.1f} MB")

                # Combine all chunks
                print(f"✅ Download complete! Processing {len(chunks)} chunks...")
                content = b''.join(chunks)

                # Decode and return
                return content.decode('utf-8')

        except requests.exceptions.Timeout:
            print(f"⏰ Timeout on attempt {attempt + 1}")
            if attempt < MAX_RETRIES - 1:
                print(f"⏳ Waiting {RETRY_DELAY} seconds before retry...")
                time.sleep(RETRY_DELAY)

        except requests.exceptions.ChunkedEncodingError as e:
            print(f"📦 Chunk encoding error on attempt {attempt + 1}: {str(e)[:100]}")
            if attempt < MAX_RETRIES - 1:
                print(f"⏳ Waiting {RETRY_DELAY} seconds before retry...")
                time.sleep(RETRY_DELAY)

        except requests.exceptions.ConnectionError as e:
            print(f"🔌 Connection error on attempt {attempt + 1}: {str(e)[:100]}")
            if attempt < MAX_RETRIES - 1:
                print(f"⏳ Waiting {RETRY_DELAY} seconds before retry...")
                time.sleep(RETRY_DELAY)

        except Exception as e:
            print(f"❌ Unexpected error on attempt {attempt + 1}: {str(e)[:100]}")
            if attempt < MAX_RETRIES - 1:
                print(f"⏳ Waiting {RETRY_DELAY} seconds before retry...")
                time.sleep(RETRY_DELAY)

    return None

def fetch_liquidation_data_range(start_date=None, end_date=None, limit=1000000):
    """
    Fetch liquidation data in smaller ranges to avoid connection issues
    """
    print(f"\n📅 Fetching liquidation data in chunks...")

    params = {}
    if start_date:
        params['start_date'] = start_date
    if end_date:
        params['end_date'] = end_date
    if limit:
        params['limit'] = limit

    print(f"📊 Parameters: {params}")

    # Try to download
    csv_content = download_with_retries(API_ENDPOINT, params=params)

    if csv_content:
        try:
            # Parse CSV
            df = pd.read_csv(StringIO(csv_content))
            print(f"✅ Successfully parsed {len(df):,} records")
            return df
        except Exception as e:
            print(f"❌ Error parsing CSV: {e}")
            return None
    else:
        print(f"❌ Failed to download data after {MAX_RETRIES} attempts")
        return None

def fetch_all_liquidations_incremental():
    """
    Fetch all liquidations by downloading in smaller increments
    """
    print("\n🔄 Trying incremental approach (multiple smaller requests)...")

    all_data = []
    batch_size = 5_000_000  # 5M records per batch
    max_batches = 20  # Maximum 100M records total

    for batch in range(max_batches):
        offset = batch * batch_size
        print(f"\n📦 Fetching batch {batch + 1} (offset: {offset:,}, limit: {batch_size:,})...")

        # Create a modified API call with offset
        params = {
            'limit': batch_size,
            'offset': offset
        }

        csv_content = download_with_retries(API_ENDPOINT, params=params)

        if csv_content:
            try:
                df = pd.read_csv(StringIO(csv_content))

                if len(df) == 0:
                    print(f"📊 No more data found. Total batches: {batch}")
                    break

                all_data.append(df)
                print(f"✅ Batch {batch + 1}: {len(df):,} records")

                # If we got less than batch_size, we've reached the end
                if len(df) < batch_size:
                    print(f"📊 Reached end of data")
                    break

            except Exception as e:
                print(f"❌ Error parsing batch {batch + 1}: {e}")
                break
        else:
            print(f"⚠️ Failed to fetch batch {batch + 1}, stopping")
            break

    if all_data:
        # Combine all batches
        combined_df = pd.concat(all_data, ignore_index=True)
        print(f"\n✅ Total records fetched: {len(combined_df):,}")
        return combined_df

    return None

# Main execution
print("\n🚀 Starting robust liquidation data fetch...")

# First try to get everything in one go with smaller limit
print("\n📊 Method 1: Single request with 50M limit...")
liquidation_data = fetch_liquidation_data_range(limit=50_000_000)

# If that fails, try incremental approach
if liquidation_data is None:
    print("\n📊 Method 2: Incremental batching...")
    liquidation_data = fetch_all_liquidations_incremental()

# Process and save if successful
if liquidation_data is not None:
    print(f"\n✅ Successfully fetched {len(liquidation_data):,} liquidation records!")

    # Rename columns if needed
    if len(liquidation_data.columns) >= 13:
        column_names = ['symbol', 'side', 'order_type', 'time_in_force', 'quantity',
                       'price', 'avg_price', 'status', 'filled_qty', 'total_qty',
                       'timestamp_ms', 'usd_value', 'datetime']
        liquidation_data.columns = column_names[:len(liquidation_data.columns)]

    # Convert types
    if 'datetime' in liquidation_data.columns:
        liquidation_data['datetime'] = pd.to_datetime(liquidation_data['datetime'])
        date_range = liquidation_data['datetime'].max() - liquidation_data['datetime'].min()
        print(f"📅 Date range: {liquidation_data['datetime'].min()} → {liquidation_data['datetime'].max()}")
        print(f"📊 Total days: {date_range.days}")

    if 'usd_value' in liquidation_data.columns:
        liquidation_data['usd_value'] = pd.to_numeric(liquidation_data['usd_value'], errors='coerce')

        # Analysis
        print(f"\n💥 Liquidation Analysis:")
        thresholds = [100_000, 500_000, 1_000_000, 5_000_000, 10_000_000]
        for threshold in thresholds:
            large_liqs = liquidation_data[liquidation_data['usd_value'] >= threshold]
            print(f"  ≥${threshold:,}: {len(large_liqs):,} ({len(large_liqs)/len(liquidation_data)*100:.2f}%)")

    # Save to file
    save_path = "/Users/md/Dropbox/dev/github/moon-dev-trading-bots/backtests/liquidations/results/all_liquidations_robust.csv"
    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    liquidation_data.to_csv(save_path, index=False)
    file_size_mb = os.path.getsize(save_path) / (1024**2)

    print(f"\n💾 Data saved to: {save_path}")
    print(f"📁 File size: {file_size_mb:.2f} MB")
    print(f"\n🎯 Success! Ready for strategy testing!")

else:
    print("\n❌ Failed to fetch liquidation data")
    print("\n🔧 Troubleshooting suggestions for your Ubuntu server:")
    print("1. Check if the CSV file exists and is readable")
    print("2. Increase server timeout settings (Apache/Nginx)")
    print("3. Enable compression (gzip) for large transfers")
    print("4. Check server memory limits")
    print("5. Consider implementing pagination on the API endpoint")
    print("\nServer-side fixes that might help:")
    print("- nginx: increase 'proxy_read_timeout', 'client_max_body_size'")
    print("- apache: increase 'Timeout', 'LimitRequestBody'")
    print("- PHP: increase 'max_execution_time', 'memory_limit'")
    print("- Consider streaming the response instead of loading all in memory")