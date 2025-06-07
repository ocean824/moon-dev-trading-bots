#!/usr/bin/env python3
"""
🌙 Moon Dev API Chunks - FIXED for Complete Data 🚀
Specialized for downloading ALL liquidation data including recent data
BETA VERSION: Now downloads from END of file first for recent data!
"""

import os
import requests
import pandas as pd
import time
import traceback
from pathlib import Path
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import datetime

# Load environment variables
load_dotenv()

class MoonDevChunkedAPI:
    """
    🌙 Moon Dev's specialized API client for complete liquidation data
    BETA: Gets recent data FIRST by reading from file END!
    """
    
    def __init__(self, api_key=None, base_url="http://api.moondev.com:8000"):
        self.api_key = api_key or os.getenv('MOONDEV_API_KEY')
        self.base_url = base_url
        
        # Create data directory
        self.base_dir = Path("moondev_api_data")
        self.base_dir.mkdir(exist_ok=True)
        
        # Setup robust session with retries
        self.session = self._create_robust_session()
        
        # Headers for API requests
        self.headers = {}
        if self.api_key:
            self.headers['Authorization'] = f'Bearer {self.api_key}'
        
        print("🚀 Moon Dev Chunked API BETA initialized!")
        print(f"📁 Data directory: {self.base_dir.absolute()}")
        print("🎯 BETA FEATURE: Downloads recent data FIRST from file END!")
        if self.api_key:
            print("🔑 API key loaded successfully")
            # Security check - never print the actual API key
            print("🔒 Moon Dev Security: API key is protected and will never be displayed")
        else:
            print("⚠️  No API key found - some endpoints may be limited")
            print("🔑 Set MOONDEV_API_KEY in your .env file")
        
        # Define column structure for headerless data
        self.column_names = [
            "symbol", "side", "order_type", "time_in_force",
            "original_quantity", "price", "average_price", "order_status",
            "order_last_filled_quantity", "order_filled_accumulated_quantity",
            "order_trade_time", "usd_size"
        ]
    
    def _create_robust_session(self):
        """Create a session with retry strategy for large downloads"""
        session = requests.Session()
        
        # Moon Dev's aggressive retry strategy 🌙
        retry_strategy = Retry(
            total=5,
            backoff_factor=2,  # Wait 2, 4, 8, 16, 32 seconds
            status_forcelist=[429, 500, 502, 503, 504, 520, 521, 522, 523, 524],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=20
        )
        
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def get_file_size(self, url):
        """Get total file size using range request"""
        try:
            headers = self.headers.copy()
            headers['Range'] = 'bytes=0-1'
            
            response = self.session.get(url, headers=headers, timeout=30)
            
            if response.status_code == 206:  # Partial Content
                content_range = response.headers.get('content-range')
                if content_range:
                    total_size = int(content_range.split('/')[-1])
                    return total_size
            
            # Fallback: Get content-length from full request
            response = self.session.get(url, headers=self.headers, stream=True, timeout=30)
            response.raise_for_status()
            
            content_length = response.headers.get('content-length')
            if content_length:
                response.close()
                return int(content_length)
            else:
                response.close()
                return None
                
        except Exception as e:
            print(f"💥 Moon Dev error getting file size: {e}")
            return None
    
    def download_chunk_range(self, url, start_byte, end_byte, chunk_number):
        """Download a specific byte range"""
        try:
            headers = self.headers.copy()
            headers['Range'] = f'bytes={start_byte}-{end_byte}'
            
            response = self.session.get(url, headers=headers, timeout=(30, 120))
            
            if response.status_code == 206:  # Partial Content
                return response.content
            elif response.status_code == 200:
                return response.content
            else:
                print(f"💥 Moon Dev unexpected status code: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"💥 Moon Dev error downloading chunk {chunk_number}: {e}")
            return None
    
    def parse_chunk_data(self, chunk_bytes):
        """Parse chunk bytes into list of liquidation records"""
        try:
            chunk_str = chunk_bytes.decode('utf-8')
            lines = [line.strip() for line in chunk_str.strip().split('\n') if line.strip()]
            
            records = []
            for line in lines:
                fields = line.split(',')
                if len(fields) >= 12:
                    try:
                        # Create record with proper column names
                        record = {}
                        for i, col_name in enumerate(self.column_names):
                            if i < len(fields):
                                record[col_name] = fields[i].strip()
                        
                        # Convert timestamp to int for sorting
                        if record.get('order_trade_time', '').isdigit():
                            record['order_trade_time'] = int(record['order_trade_time'])
                            records.append(record)
                    except Exception:
                        continue
            
            return records
            
        except Exception as e:
            print(f"💥 Moon Dev error parsing chunk: {e}")
            return []

    def _download_with_progress(self, url, filename, resume=True):
        """
        🌙 Moon Dev's robust download with progress tracking and resume capability
        LEGACY METHOD - kept for compatibility
        """
        file_path = self.base_dir / filename
        temp_path = self.base_dir / f"temp_{filename}"
        
        # Check if we can resume
        resume_pos = 0
        if resume and temp_path.exists():
            resume_pos = temp_path.stat().st_size
            print(f"🔄 Moon Dev resuming download from {resume_pos:,} bytes")
        
        headers = self.headers.copy()
        if resume_pos > 0:
            headers['Range'] = f'bytes={resume_pos}-'
        
        try:
            print(f"🚀 Moon Dev connecting to: {url}")
            response = self.session.get(
                url, 
                headers=headers, 
                stream=True, 
                timeout=(30, 600)  # 30s connect, 10min read
            )
            response.raise_for_status()
            
            # Get total size
            content_length = response.headers.get('content-length')
            if content_length:
                total_size = int(content_length)
                if resume_pos > 0:
                    total_size += resume_pos  # Add resumed bytes to total
            else:
                total_size = 0
            
            print(f"📊 Moon Dev download info:")
            print(f"   📁 File: {filename}")
            print(f"   📏 Size: {total_size:,} bytes ({total_size/1e9:.2f} GB)")
            if resume_pos > 0:
                print(f"   🔄 Resuming from: {resume_pos:,} bytes")
            
            # Open in append mode if resuming
            mode = 'ab' if resume_pos > 0 else 'wb'
            downloaded = resume_pos
            
            with open(temp_path, mode) as f:
                print("🌙 Moon Dev starting chunked download...")
                
                for chunk in response.iter_content(chunk_size=1024*1024):  # 1MB chunks
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Progress every 50MB or at completion
                        if (downloaded % (50*1024*1024) == 0 or 
                            (total_size > 0 and downloaded >= total_size)):
                            
                            if total_size > 0:
                                progress = downloaded / total_size
                                remaining_mb = (total_size - downloaded) / 1024**2
                                print(f"🌙 Progress: {downloaded:,}/{total_size:,} bytes ({progress:.1%}) - {remaining_mb:.1f}MB left")
                            else:
                                print(f"🌙 Downloaded: {downloaded:,} bytes")
            
            print(f"✅ Moon Dev download complete!")
            print(f"   📊 Total downloaded: {downloaded:,} bytes")
            
            # Move temp file to final location
            if file_path.exists():
                file_path.unlink()  # Remove existing file
            temp_path.rename(file_path)
            
            print(f"💾 File saved to: {file_path}")
            return file_path
            
        except Exception as e:
            print(f"💥 Moon Dev download error: {str(e)}")
            print(f"📋 Stack trace:\n{traceback.format_exc()}")
            
            if temp_path.exists():
                temp_size = temp_path.stat().st_size
                print(f"🔄 Partial download saved: {temp_size:,} bytes")
                print("   You can resume this download later!")
            
            return None
    
    def get_recent_liquidations(self, days_back=7, max_chunks=20):
        """
        🌙 BETA: Download RECENT liquidation data from END of file first!
        This solves the "22 days late" issue by reading from file end
        """
        url = f'{self.base_url}/files/liq_data.csv'
        
        print(f"🚀 Moon Dev BETA: Downloading RECENT liquidations from END of file!")
        print(f"🎯 Target: Last {days_back} days of data")
        print(f"📦 Max chunks to download: {max_chunks}")
        
        # Get file size
        total_size = self.get_file_size(url)
        if not total_size:
            print("💥 Moon Dev could not get file size!")
            return None
        
        print(f"📊 Total file size: {total_size:,} bytes ({total_size/1e9:.2f} GB)")
        
        chunk_size = 2 * 1024 * 1024  # 2MB chunks
        all_records = []
        chunks_downloaded = 0
        target_timestamp = int((datetime.now().timestamp() - (days_back * 24 * 3600)) * 1000)
        
        print(f"🕐 Target timestamp: {target_timestamp} ({datetime.fromtimestamp(target_timestamp/1000).strftime('%Y-%m-%d %H:%M')})")
        
        # Download chunks from END backwards
        for i in range(max_chunks):
            # Calculate chunk position from end
            end_byte = total_size - 1 - (i * chunk_size)
            start_byte = max(0, end_byte - chunk_size + 1)
            
            if start_byte < 0 or end_byte <= start_byte:
                break
            
            chunk_number = i + 1
            print(f"\n🧩 Moon Dev downloading chunk {chunk_number} from END")
            print(f"   📍 Byte range: {start_byte:,} - {end_byte:,}")
            
            # Download chunk
            chunk_bytes = self.download_chunk_range(url, start_byte, end_byte, chunk_number)
            if not chunk_bytes:
                print(f"💥 Moon Dev failed to download chunk {chunk_number}")
                continue
            
            # Parse chunk data
            records = self.parse_chunk_data(chunk_bytes)
            
            if records:
                # Check timestamp range in this chunk
                timestamps = [r['order_trade_time'] for r in records if 'order_trade_time' in r]
                if timestamps:
                    min_ts = min(timestamps)
                    max_ts = max(timestamps)
                    
                    min_date = datetime.fromtimestamp(min_ts / 1000)
                    max_date = datetime.fromtimestamp(max_ts / 1000)
                    
                    print(f"   📅 Chunk data: {min_date.strftime('%Y-%m-%d %H:%M')} → {max_date.strftime('%Y-%m-%d %H:%M')}")
                    print(f"   📊 Records: {len(records)}")
                    
                    # Add records to our collection
                    all_records.extend(records)
                    chunks_downloaded += 1
                    
                    # Check if we've gone back far enough
                    if min_ts < target_timestamp:
                        print(f"   🎯 Moon Dev reached target date! Downloaded enough recent data.")
                        break
                    
                    # Progress update
                    days_ago = (datetime.now().timestamp() - min_ts/1000) / (24*3600)
                    print(f"   🕐 Oldest in chunk: {days_ago:.1f} days ago")
                else:
                    print(f"   ⚠️  Moon Dev: No valid timestamps in chunk {chunk_number}")
            else:
                print(f"   ⚠️  Moon Dev: No valid records in chunk {chunk_number}")
        
        if not all_records:
            print("💥 Moon Dev: No liquidation records downloaded!")
            return None
        
        # Sort records by timestamp (OLDEST first - like OHLCV trading data)
        print(f"\n🔄 Moon Dev: Sorting {len(all_records):,} records by timestamp...")
        all_records.sort(key=lambda x: x.get('order_trade_time', 0), reverse=False)  # OLDEST FIRST
        
        # Convert to DataFrame
        df = pd.DataFrame(all_records)
        
        # Convert timestamp to readable datetime
        df['datetime'] = pd.to_datetime(df['order_trade_time'], unit='ms')
        
        print(f"\n✅ Moon Dev BETA SUCCESS! Downloaded liquidation data:")
        print(f"   📊 Total records: {len(df):,}")
        print(f"   📊 Chunks downloaded: {chunks_downloaded}")
        print(f"   📅 Date range: {df['datetime'].min()} → {df['datetime'].max()}")
        print(f"   💾 Memory usage: {df.memory_usage(deep=True).sum() / 1024**2:.1f} MB")
        
        # Save to specified directory path
        save_dir = Path("/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/moondev_api")
        save_dir.mkdir(parents=True, exist_ok=True)
        output_file = save_dir / "liq_data.csv"
        df.to_csv(output_file, index=False)
        print(f"💾 Moon Dev saved to: {output_file}")
        
        # Show data preview (trading data format - oldest first)
        print(f"\n📋 Moon Dev Liquidation Data Preview (Trading Data Format):")
        print(f"   📅 OLDEST liquidations (like OHLCV data):")
        for i in range(min(3, len(df))):
            row = df.iloc[i]
            print(f"     {i+1}. {row['datetime']} - {row['symbol']} {row['side']} ${row['usd_size']}")
        
        if len(df) > 3:
            print(f"   🔥 NEWEST liquidations:")
            for i in range(max(0, len(df)-3), len(df)):
                row = df.iloc[i]
                print(f"     {len(df)-i}. {row['datetime']} - {row['symbol']} {row['side']} ${row['usd_size']}")
        
        return df

    def get_complete_liquidation_data(self, max_attempts=5, recent_first=True):
        """
        🌙 Download COMPLETE liquidation data
        BETA: Option to get recent data first or use legacy full download
        """
        if recent_first:
            print("🌙 Moon Dev BETA MODE: Getting recent data first!")
            return self.get_recent_liquidations(days_back=30, max_chunks=50)
        
        # Legacy mode - full file download (kept for compatibility)
        print("🌙 Moon Dev LEGACY MODE: Full file download...")
        print("⚠️  This will download 1.5GB and start from June 2024!")
        print("🎯 Use recent_first=True for faster recent data download")
        
        filename = "liq_data.csv"
        
        # Strategy 1: No limit parameter at all
        urls_to_try = [
            f'{self.base_url}/files/liq_data.csv',  # No parameters
            f'{self.base_url}/files/liq_data.csv?limit=0',  # Limit 0 (sometimes means "no limit")
            f'{self.base_url}/files/liq_data.csv?all=true',  # All flag
            f'{self.base_url}/files/liq_data.csv?recent=true',  # Recent flag
            f'{self.base_url}/files/liq_data.csv?limit=999999999',  # Very high limit
        ]
        
        for i, url in enumerate(urls_to_try):
            print(f"\n🎯 Moon Dev Strategy {i+1}/{len(urls_to_try)}: {url}")
            
            for attempt in range(max_attempts):
                print(f"   🔄 Attempt {attempt + 1}/{max_attempts}")
                
                file_path = self._download_with_progress(url, f"strategy_{i+1}_{filename}", resume=True)
                
                if file_path:
                    print(f"✅ Strategy {i+1} successful!")
                    
                    # Check file size and load to verify
                    try:
                        df = pd.read_csv(file_path)
                        file_size_gb = file_path.stat().st_size / 1e9
                        
                        print(f"📊 Strategy {i+1} Results:")
                        print(f"   📏 File size: {file_size_gb:.2f} GB")
                        print(f"   📊 Rows: {len(df):,}")
                        print(f"   📊 Columns: {len(df.columns)}")
                        
                        # Check if we have recent data
                        if len(df) > 0 and 'timestamp' in df.columns:
                            try:
                                df['timestamp'] = pd.to_datetime(df['timestamp'])
                                latest_date = df['timestamp'].max()
                                days_ago = (pd.Timestamp.now() - latest_date).days
                                print(f"   📅 Latest data: {latest_date} ({days_ago} days ago)")
                                
                                # If this strategy gives us recent data (< 5 days old), use it!
                                if days_ago < 5:
                                    print(f"🎉 Found recent data! Using Strategy {i+1}")
                                    
                                    # Rename to final filename
                                    final_path = self.base_dir / filename
                                    if final_path.exists():
                                        final_path.unlink()
                                    file_path.rename(final_path)
                                    
                                    return df
                                else:
                                    print(f"⚠️  Data is {days_ago} days old - trying next strategy...")
                                    
                            except Exception as e:
                                print(f"⚠️  Could not parse timestamp: {e}")
                        
                        # If file size is significantly larger, it might be the complete dataset
                        if file_size_gb > 1.35:  # Larger than your current incomplete file
                            print(f"🎉 Found larger dataset ({file_size_gb:.2f} GB)! This might be complete.")
                            
                            # Rename to final filename
                            final_path = self.base_dir / filename
                            if final_path.exists():
                                final_path.unlink()
                            file_path.rename(final_path)
                            
                            return df
                        
                    except Exception as e:
                        print(f"⚠️  Could not verify file: {e}")
                
                if attempt < max_attempts - 1:
                    wait_time = 2 ** attempt
                    print(f"   🔄 Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
            
            print(f"💥 Strategy {i+1} failed after {max_attempts} attempts")
        
        print("💥 All strategies failed! You might need to contact the API provider.")
        return None

    def check_data_freshness(self, file_path):
        """
        🔍 Check how fresh the liquidation data is
        """
        try:
            print(f"🔍 Moon Dev: Checking data freshness for {file_path}")
            df = pd.read_csv(file_path)
            
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                latest_date = df['timestamp'].max()
                earliest_date = df['timestamp'].min()
                days_ago = (pd.Timestamp.now() - latest_date).days
                
                print(f"📅 Data range: {earliest_date} to {latest_date}")
                print(f"🕐 Latest data is {days_ago} days old")
                print(f"📊 Total records: {len(df):,}")
                
                if days_ago > 1:
                    print(f"⚠️  WARNING: Data might be missing recent liquidations!")
                else:
                    print("✅ Data looks fresh!")
                
                return days_ago
            else:
                print("⚠️  No timestamp column found")
                return None
                
        except Exception as e:
            print(f"💥 Error checking data freshness: {e}")
            return None

def main():
    """🌙 Moon Dev complete liquidation data download - BETA VERSION"""
    print("🌙 Moon Dev Chunked API - BETA VERSION WITH RECENT DATA FIRST! 🚀")
    print("=" * 80)
    print("🎯 BETA FEATURE: Downloads recent data from END of file first!")
    print("💡 Solves the '22 days late' issue by reading chunks in reverse order")
    
    # Initialize API
    api = MoonDevChunkedAPI()
    
    # BETA: Get COMPLETE liquidation data (full 1.5GB dataset)
    print("\n🌙 Moon Dev BETA: Getting COMPLETE liquidation data from file END...")
    print("   📊 This downloads the FULL 1.5GB dataset with recent data FIRST!")
    print("   🎯 Target: Complete 1-year dataset (~1.5GB)")
    print("   ⚡ Recent data comes first, then continues backwards in time")
    
    # Download the full dataset by going back 400 days and allowing 800 chunks
    # This should get the complete 1.5GB file
    df = api.get_recent_liquidations(days_back=400, max_chunks=800)
    
    if df is not None:
        print("\n🎉 Moon Dev BETA SUCCESS! Complete liquidation dataset downloaded!")
        print(f"   📊 Shape: {df.shape}")
        print(f"   💾 Memory: {df.memory_usage(deep=True).sum() / 1024**2:.1f} MB")
        
        # Calculate approximate file size
        approx_file_size = df.memory_usage(deep=True).sum() / 1024**3  # GB
        print(f"   📁 Approximate data size: {approx_file_size:.2f} GB")
        
        # Show data range
        if len(df) > 0:
            print(f"\n📋 Moon Dev Complete Dataset Info:")
            print(f"   📅 Date range: {df['datetime'].min()} → {df['datetime'].max()}")
            print(f"   📊 Total liquidations: {len(df):,}")
            
            # Show most recent liquidations
            print(f"   🥇 Most recent liquidations:")
            for i in range(min(3, len(df))):
                row = df.iloc[i]
                print(f"     {i+1}. {row['datetime']} - {row['symbol']} {row['side']} ${row['usd_size']}")
            
            # Show oldest liquidations  
            print(f"   📜 Oldest liquidations in dataset:")
            for i in range(max(0, len(df)-3), len(df)):
                row = df.iloc[i]
                print(f"     {len(df)-i}. {row['datetime']} - {row['symbol']} {row['side']} ${row['usd_size']}")
        
        print("\n🚀 Moon Dev BETA: Ready for ML training with COMPLETE liquidation data!")
        print("💡 Data is sorted with newest first, recent data downloaded immediately")
        
    else:
        print("\n💥 Moon Dev BETA: Could not get complete dataset!")
        print("🔍 You might need to contact the API provider")

if __name__ == "__main__":
    main() 