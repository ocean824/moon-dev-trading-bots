"""
🌙 Moon Dev's Tick Data Downloader
Downloads tick data CSV files from Moon Dev API

This script downloads:
- sol_tickdata.csv
- btc_tickdata.csv  
- eth_tickdata.csv
"""

import os
import sys
import requests
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path to import api module
sys.path.append(str(Path(__file__).parent.parent))
from api import MoonDevAPI

# Load environment variables
load_dotenv()

def download_tick_data():
    """Download tick data files from Moon Dev API"""
    
    # Initialize API client
    api = MoonDevAPI()
    
    if not api.api_key:
        print("❗ Error: MOONDEV_API_KEY not found in .env file")
        print("Please set your API key in the .env file")
        return
    
    # Set output directory to data/tick_data
    tick_data_dir = Path("/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/tick_data")
    tick_data_dir.mkdir(parents=True, exist_ok=True)
    
    # Files to download
    tick_files = [
        "sol_tickdata.csv",
        "btc_tickdata.csv",
        "eth_tickdata.csv"
    ]
    
    print("🌙 Moon Dev Tick Data Downloader")
    print("=" * 50)
    
    for filename in tick_files:
        print(f"\n📊 Downloading {filename}...")
        
        try:
            # Use the API's session and headers for authentication
            url = f"{api.base_url}/files/{filename}"
            response = api.session.get(url, headers=api.headers, stream=True)
            response.raise_for_status()
            
            # Save to TickData directory
            save_path = tick_data_dir / filename
            
            # Download with progress indication
            with open(save_path, 'wb') as f:
                total_size = 0
                for chunk in response.iter_content(chunk_size=8192*16):
                    if chunk:
                        f.write(chunk)
                        total_size += len(chunk)
                        # Show progress every 10MB
                        if total_size % (10 * 1024 * 1024) < (8192*16):
                            print(f"   Downloaded {total_size / (1024*1024):.1f} MB...")
            
            file_size_mb = save_path.stat().st_size / (1024**2)
            print(f"✅ Successfully downloaded {filename}")
            print(f"   💾 Size: {file_size_mb:.2f} MB")
            print(f"   📂 Saved to: {save_path}")
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                print(f"❌ File not found on server: {filename}")
            elif e.response.status_code == 403:
                print(f"❌ Access denied - check your API key permissions")
            else:
                print(f"❌ HTTP error downloading {filename}: {e}")
                
        except Exception as e:
            print(f"❌ Error downloading {filename}: {str(e)}")
    
    print("\n" + "=" * 50)
    print("✨ Tick data download complete!")

if __name__ == "__main__":
    download_tick_data()