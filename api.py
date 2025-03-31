"""
🌙 Moon Dev's API Handler
Built with love by Moon Dev 🚀

disclaimer: this is not financial advice and there is no guarantee of any kind. use at your own risk.

Quick Start Guide:
-----------------
1. Install required packages:
   ```
   pip install requests pandas python-dotenv
   ```

2. Create a .env file in your project root:
   ```
   MOONDEV_API_KEY=your_api_key_here
   ```

3. Basic Usage:
   ```python
   from agents.api import MoonDevAPI
   
   # Initialize with env variable (recommended)
   api = MoonDevAPI()
   
   # Or initialize with direct key
   api = MoonDevAPI(api_key="your_key_here")
   
   # Get data
   liquidations = api.get_liquidation_data(limit=1000)  # Last 1000 rows
   funding = api.get_funding_data()
   oi = api.get_oi_data()
   ```

Available Methods:
----------------
- get_liquidation_data(limit=None): Get historical liquidation data. Use limit parameter for most recent data
- get_funding_data(): Get current funding rate data for various tokens
- get_token_addresses(): Get new Solana token launches and their addresses
- get_oi_data(): Get detailed open interest data for ETH or BTC individually
- get_oi_total(): Get total open interest data for ETH & BTC combined
- get_copybot_follow_list(): Get Moon Dev's personal copy trading follow list (for reference only - DYOR!)
- get_copybot_recent_transactions(): Get recent transactions from the followed wallets above
- get_agg_positions_hlp(): Get aggregated positions on HLP data
- get_positions_hlp(): Get detailed positions on HLP data
- get_whale_addresses(): Get list of whale addresses



Data Details:
------------
- Liquidation Data: Historical liquidation events with timestamps and amounts
- Funding Rates: Current funding rates across different tokens
- Token Addresses: New token launches on Solana with contract addresses
- Open Interest: Both detailed (per-token) and combined OI metrics
- CopyBot Data: Moon Dev's personal trading signals (use as reference only, always DYOR!)

Rate Limits:
-----------
- 100 requests per minute per API key
- Larger datasets (like liquidations) recommended to use limit parameter

⚠️ Important Notes:
-----------------
1. This is not financial advice
2. There are no guarantees of any kind
3. Use at your own risk
4. Always do your own research (DYOR)
5. The copybot follow list is Moon Dev's personal list and should not be used alone

Need an API key? for a limited time, bootcamp members get free api keys for claude, openai, helius, birdeye & quant elite gets access to the moon dev api. join here: https://algotradecamp.com
"""

import os
import pandas as pd
import requests
from datetime import datetime
import time
from pathlib import Path
import numpy as np
import traceback
import json
import io
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get the project root directory
PROJECT_ROOT = Path("/Users/md/Dropbox/dev/github/moon-dev-trading-bots")

class MoonDevAPI:
    def __init__(self, api_key=None, base_url="http://api.moondev.com:8000"):
        """Initialize the API handler"""
        # Simplified data directory path
        self.base_dir = PROJECT_ROOT / "data" / "moondev_api"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.api_key = api_key or os.getenv('MOONDEV_API_KEY')
        self.base_url = base_url
        self.headers = {'X-API-Key': self.api_key} if self.api_key else {}
        self.session = requests.Session()
        self.max_retries = 3
        self.chunk_size = 8192  # Smaller chunk size for more reliable downloads

    def _fetch_csv(self, filename, limit=None):
        """Fetch CSV data from the API with retry logic"""
        max_retries = 3
        retry_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                url = f'{self.base_url}/files/{filename}'
                if limit:
                    url += f'?limit={limit}'
                
                # Use stream=True for better handling of large files
                response = self.session.get(url, headers=self.headers, stream=True)
                response.raise_for_status()
                
                # Save streamed content to a temporary file first
                temp_file = self.base_dir / f"temp_{filename}"
                with open(temp_file, 'wb') as f:
                    # Use a larger chunk size for better performance
                    for chunk in response.iter_content(chunk_size=8192*16):
                        if chunk:
                            f.write(chunk)
                
                # Once download is complete, read the file
                df = pd.read_csv(temp_file)
                
                # Move temp file to final location
                final_file = self.base_dir / filename
                temp_file.rename(final_file)
                
                return df
                
            except (requests.exceptions.ChunkedEncodingError, 
                    requests.exceptions.ConnectionError,
                    requests.exceptions.RequestException) as e:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    print(f"💥 Error fetching {filename} after {max_retries} attempts: {str(e)}")
                    print(f"📋 Stack trace:\n{traceback.format_exc()}")
                    return None
                    
            except Exception as e:
                print(f"💥 Unexpected error fetching {filename}: {str(e)}")
                print(f"📋 Stack trace:\n{traceback.format_exc()}")
                return None

    def get_liquidation_data(self, limit=10000):
        """Get liquidation data from API, limited to last N rows by default"""
        return self._fetch_csv("liq_data.csv", limit=limit)

    def get_funding_data(self):
        """Get funding data from API"""
        return self._fetch_csv("funding.csv")

    def get_token_addresses(self):
        """Get token addresses from API"""
        return self._fetch_csv("new_token_addresses.csv")

    def get_oi_total(self):
        """Get total open interest data from API"""
        return self._fetch_csv("oi_total.csv")

    def get_oi_data(self):
        """Get detailed open interest data from API"""
        max_retries = 3
        retry_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                url = f'{self.base_url}/files/oi.csv'
                
                # Use stream=True and a larger chunk size
                response = self.session.get(url, headers=self.headers, stream=True)
                response.raise_for_status()
                
                # Save streamed content to a temporary file first
                temp_file = self.base_dir / "temp_oi.csv"
                with open(temp_file, 'wb') as f:
                    # Use a larger chunk size for better performance
                    for chunk in response.iter_content(chunk_size=8192*16):
                        if chunk:
                            f.write(chunk)
                
                # Once download is complete, read the file
                df = pd.read_csv(temp_file)
                
                # Move temp file to final location
                final_file = self.base_dir / "oi.csv"
                temp_file.rename(final_file)
                
                return df
                
            except (requests.exceptions.ChunkedEncodingError, 
                    requests.exceptions.ConnectionError,
                    requests.exceptions.RequestException) as e:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    print(f"💥 Error fetching oi.csv after {max_retries} attempts: {str(e)}")
                    print(f"📋 Stack trace:\n{traceback.format_exc()}")
                    return None
                    
            except Exception as e:
                print(f"💥 Unexpected error fetching oi.csv: {str(e)}")
                print(f"📋 Stack trace:\n{traceback.format_exc()}")
                return None

    def get_copybot_follow_list(self):
        """Get current copy trading follow list"""
        try:
            print("📋 Moon Dev CopyBot: Fetching follow list...")
            if not self.api_key:
                print("❗ API key is required for copybot endpoints")
                return None
                
            response = self.session.get(
                f"{self.base_url}/copybot/data/follow_list",
                headers=self.headers
            )
            
            if response.status_code == 403:
                print("❗ Invalid API key or insufficient permissions")
                print(f"🔑 Current API key: {self.api_key}")
                return None
                
            response.raise_for_status()
            
            # Save to cache and read
            save_path = self.base_dir / "follow_list.csv"
            with open(save_path, 'wb') as f:
                f.write(response.content)
            
            df = pd.read_csv(save_path)
            print(f"✨ Successfully loaded {len(df)} rows from follow list")
            return df
                
        except Exception as e:
            print(f"💥 Error fetching follow list: {str(e)}")
            if "403" in str(e):
                print("❗ Make sure your API key is set in the .env file and has the correct permissions")
            return None

    def get_copybot_recent_transactions(self):
        """Get recent copy trading transactions"""
        try:
            print("🔄 Moon Dev CopyBot: Fetching recent transactions...")
            if not self.api_key:
                print("❗ API key is required for copybot endpoints")
                return None
                
            response = self.session.get(
                f"{self.base_url}/copybot/data/recent_txs",
                headers=self.headers
            )
            
            if response.status_code == 403:
                print("❗ Invalid API key or insufficient permissions")
                print(f"🔑 Current API key: {self.api_key}")
                return None
                
            response.raise_for_status()
            
            # Save directly to moondev_api data directory
            save_path = self.base_dir / "recent_txs.csv"
            with open(save_path, 'wb') as f:
                f.write(response.content)
            
            df = pd.read_csv(save_path)
            print(f"✨ Successfully loaded {len(df)} rows from recent transactions")
            print(f"💾 Data saved to: {save_path}")
            return df
                
        except Exception as e:
            print(f"💥 Error fetching recent transactions: {str(e)}")
            if "403" in str(e):
                print("❗ Make sure your API key is set in the .env file and has the correct permissions")
            return None

    def get_agg_positions_hlp(self):
        """Get aggregated positions on HLP data"""
        return self._fetch_csv("agg_positions_on_hlp.csv")

    def get_positions_hlp(self):
        """Get detailed positions on HLP data"""
        return self._fetch_csv("positions_on_hlp.csv")

    def get_whale_addresses(self):
        """Get list of whale addresses"""
        try:
            print("🐋 Moon Dev API: Fetching whale addresses...")
            
            url = f'{self.base_url}/files/whale_addresses.txt'
            response = self.session.get(url, headers=self.headers)
            response.raise_for_status()
            
            # Save directly to moondev_api data directory
            save_path = self.base_dir / "whale_addresses.txt"
            with open(save_path, 'wb') as f:
                f.write(response.content)
            
            # Read the text file
            with open(save_path, 'r') as f:
                addresses = f.read().splitlines()
            
            print(f"✨ Successfully loaded {len(addresses)} whale addresses")
            print(f"💾 Data saved to: {save_path}")
            return addresses
                
        except Exception as e:
            print(f"💥 Error fetching whale addresses: {str(e)}")
            return None

if __name__ == "__main__":
    print("🌙 Moon Dev API Test Suite 🚀")
    print("=" * 50)
    
    # Initialize API
    api = MoonDevAPI()
    
    # print("\n📊 Testing Data Storage...")
    # print(f"📂 Data will be saved to: {api.base_dir}")
    
    # # Test Historical Liquidation Data
    # print("\n💥 Testing Liquidation Data...")
    # liq_data = api.get_liquidation_data(limit=10000)
    # if liq_data is not None:
    #     print(f"✨ Latest Liquidation Data Preview:\n{liq_data.head()}")
    
    # # Test Funding Rate Data
    # print("\n💰 Testing Funding Data...")
    # funding_data = api.get_funding_data()
    # if funding_data is not None:
    #     print(f"✨ Latest Funding Data Preview:\n{funding_data.head()}")
    
    # # Test Token Addresses
    # print("\n🔑 Testing Token Addresses...")
    # token_data = api.get_token_addresses()
    # if token_data is not None:
    #     print(f"✨ Token Addresses Preview:\n{token_data.head()}")
    
    # # Test Total OI Data for ETH & BTC combined
    # print("\n📈 Testing Total OI Data...")
    # oi_total = api.get_oi_total()
    # if oi_total is not None:
    #     print(f"✨ Total OI Data Preview:\n{oi_total.head()}")
    
    # # Test Detailed OI Data for ETH or BTC
    # print("\n📊 Testing Detailed OI Data...")
    # oi_data = api.get_oi_data()
    # if oi_data is not None:
    #     print(f"✨ Detailed OI Data Preview:\n{oi_data.head()}")
    
    # # Test CopyBot Follow List
    # print("\n👥 Testing CopyBot Follow List...")
    # follow_list = api.get_copybot_follow_list()
    # if follow_list is not None:
    #     print(f"✨ Follow List Preview:\n{follow_list.head()}")
    
    # # Test CopyBot Recent Transactions
    # print("\n💸 Testing CopyBot Recent Transactions...")
    # recent_txs = api.get_copybot_recent_transactions()
    # if recent_txs is not None:
    #     print(f"✨ Recent Transactions Preview:\n{recent_txs.head()}")
    
    # Test Aggregated Positions on HLP
    print("\n📊 Testing Aggregated HLP Positions...")
    agg_positions = api.get_agg_positions_hlp()
    if agg_positions is not None:
        print(f"✨ Aggregated HLP Positions Preview:\n{agg_positions.head()}")

    # Test Detailed Positions on HLP
    print("\n📊 Testing Detailed HLP Positions...")
    positions = api.get_positions_hlp()
    if positions is not None:
        print(f"✨ Detailed HLP Positions Preview:\n{positions.head()}")

    # Test Whale Addresses
    print("\n🐋 Testing Whale Addresses...")
    whale_addresses = api.get_whale_addresses()
    if whale_addresses is not None:
        print(f"✨ First few whale addresses:\n{whale_addresses[:5]}")
    
    print("\n✨ Moon Dev API Test Complete! ✨")
    print("\n💡 Note: Make sure to set MOONDEV_API_KEY in your .env file")
