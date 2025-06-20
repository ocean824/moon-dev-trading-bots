'''
STEPS TO USE
1. create a .env file that contains:
    BIRDEYE_KEY=your_api_key_here
2. select the contract address you want to fetch data for
3. select the timeframe (e.g., '15m', '1H', '4H', '1D')
4. select the number of days of data to fetch
5. run the script
'''

# ====== Moon Dev's Configuration 🌙 ======
CONTRACT_ADDRESS = 'DitHyRMQiSDhn5cnKMJV2CDDt6sVct96YrECiM49pump'  # USDC contract address as example
TIMEFRAME = '1D'          # Timeframe (e.g., '15m', '1H', '4H', '1D')
DAYS_BACK = 300           # How many days of data to fetch
SAVE_DIR = 'data/birdeye'  # Directory to save the data files

# ====== Imports ======
import pandas as pd
import datetime
import os
from dotenv import load_dotenv
from pathlib import Path
import requests
import time

# Create save directory if it doesn't exist
os.makedirs(SAVE_DIR, exist_ok=True)
print(f"📂 Moon Dev's save directory ready: {SAVE_DIR}")

# Get the project root directory (2 levels up from this file)
project_root = Path(__file__).parent.parent
env_path = project_root / '.env'

print(f"🔍 Looking for .env file in: {project_root}")
print(f"📁 .env file exists: {'✅' if env_path.exists() else '❌'}")

# Load environment variables from the specific path
load_dotenv(env_path)

# Get API key
birdeye_key = os.getenv('BIRDEYE_KEY')
print("🔑 BirdEye API Key loaded:", "✅" if birdeye_key else "❌")

if not birdeye_key:
    print("❌ Error: BirdEye API key not found in .env file")
    print("💡 Make sure your .env file exists and contains:")
    print("   BIRDEYE_KEY=your_api_key_here")
    raise ValueError("Missing BirdEye API key")

print("🌙 Moon Dev's BirdEye Data Fetcher Initialized! 🚀")

def get_time_range(days_back):
    """Calculate time range based on days back from current time"""
    time_to = int(time.time())
    time_from = time_to - (days_back * 24 * 60 * 60)
    return time_from, time_to

def get_birdeye_data(contract_address, timeframe, days_back):
    """Fetch historical data from BirdEye API"""
    print(f"🔍 Moon Dev is fetching {days_back} days of {timeframe} data for contract {contract_address}")
    
    output_file = os.path.join(SAVE_DIR, f'{contract_address}-{timeframe}-{days_back}days-data.csv')
    if os.path.exists(output_file):
        print("📂 Found existing data file!")
        return pd.read_csv(output_file)

    try:
        time_from, time_to = get_time_range(days_back)
        
        url = f"https://public-api.birdeye.so/defi/ohlcv"
        params = {
            "address": contract_address,
            "type": timeframe,
            "time_from": time_from,
            "time_to": time_to
        }
        
        headers = {
            "X-API-KEY": birdeye_key
        }
        
        print(f"🚀 Moon Dev making API request for {timeframe} data...")
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            print(f"❌ Error: API returned status code {response.status_code}")
            print(f"❌ Response: {response.text}")
            return pd.DataFrame()
            
        json_response = response.json()
        items = json_response.get('data', {}).get('items', [])
        
        if not items:
            print("⚠️ No data returned from API")
            return pd.DataFrame()
            
        # Process the data - only OHLCV
        processed_data = [{
            'datetime': datetime.datetime.utcfromtimestamp(item['unixTime']).strftime('%Y-%m-%d %H:%M:%S'),
            'open': item['o'],
            'high': item['h'],
            'low': item['l'],
            'close': item['c'],
            'volume': item['v']
        } for item in items]
        
        # Create DataFrame
        df = pd.DataFrame(processed_data)
        df['datetime'] = pd.to_datetime(df['datetime'])
        df = df.set_index('datetime')
        
        # Save to file
        df.to_csv(output_file)
        print(f"💾 Moon Dev saved {len(df)} candles to {output_file}")
        
        return df
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print("💡 Tips:")
        print("   1. Check if your BirdEye API key is valid")
        print("   2. Verify the contract address exists")
        print("   3. Make sure the timeframe is valid (e.g., '15m', '1H', '4H', '1D')")
        return pd.DataFrame()

# Get the data
if __name__ == "__main__":
    print("🌙 Moon Dev is starting the data fetch...")
    df = get_birdeye_data(CONTRACT_ADDRESS, TIMEFRAME, DAYS_BACK)
    print(df)
