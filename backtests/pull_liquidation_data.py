import pandas as pd
from pathlib import Path
import os
import sys
from datetime import datetime

# Add the project root to the Python path to find the api module
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from api import MoonDevAPI

# Set up data paths
DATA_DIR = Path("/Users/md/Dropbox/dev/github/moon-dev-trading-bots/bots/hyperliquid/data/liqs")
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Define symbols we're interested in
SYMBOLS_OF_INTEREST = ['BTC', 'ETH', 'SOL']

def process_raw_data(raw_data_path):
    """Process raw data with proper column names"""
    # Define column names based on the data structure
    columns = [
        'symbol', 'side', 'order_type', 'time_in_force', 
        'size', 'price_1', 'price_2', 'status', 
        'filled_size', 'total_size', 'timestamp', 'usd_amount'
    ]
    
    # Read the CSV with proper column names
    data = pd.read_csv(raw_data_path, names=columns)
    return data

def process_and_save_by_symbol(raw_data_path):
    """Process raw data and save separate files for each symbol"""
    print("\n🌙 Moon Dev Processing Liquidation Data by Symbol 🚀")
    
    # Process raw data with proper column names
    processed_data = process_raw_data(raw_data_path)
    
    print("\n📊 Raw Data Sample:")
    print(processed_data.head().to_string())
    
    # Create a clean version with required columns
    clean_data = pd.DataFrame({
        'symbol': processed_data['symbol'],
        'side': processed_data['side'],
        'price': processed_data['price_1'].astype(float),
        'timestamp': processed_data['timestamp'],
        'amount': processed_data['usd_amount'].astype(float)
    })
    
    print("\n🔍 Processed Data Sample:")
    print(clean_data.head().to_string())
    
    # Convert timestamp to datetime for analysis
    clean_data['datetime'] = pd.to_datetime(clean_data['timestamp'], unit='ms')
    
    # Process each symbol
    for symbol in SYMBOLS_OF_INTEREST:
        # Filter data for this symbol - exact match only
        symbol_data = clean_data[clean_data['symbol'] == symbol]
        
        if len(symbol_data) > 0:
            # Sort by timestamp
            symbol_data = symbol_data.sort_values('timestamp')
            
            # Rename columns to match backtest requirements
            symbol_data = symbol_data.rename(columns={
                'side': 'LIQ_SIDE',
                'amount': 'usd_size'
            })
            
            # Add OHLC columns based on price
            symbol_data['Open'] = symbol_data['price']
            symbol_data['High'] = symbol_data['price']
            symbol_data['Low'] = symbol_data['price']
            symbol_data['Close'] = symbol_data['price']
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{symbol}_liquidations_{timestamp}.csv"
            filepath = DATA_DIR / filename
            
            # Print data verification before saving
            print(f"\n🔍 Verifying {symbol} Data Structure:")
            print("=" * 60)
            print("\n📊 First few rows with key columns:")
            print(symbol_data[['datetime', 'price', 'LIQ_SIDE', 'usd_size']].head().to_string())
            
            # Save to CSV
            symbol_data.to_csv(filepath, index=False)
            
            # Print analysis
            print(f"\n🪙 {symbol} Liquidation Analysis:")
            print("=" * 60)
            print(f"Total records: {len(symbol_data):,}")
            print(f"Date range: {symbol_data['datetime'].min()} to {symbol_data['datetime'].max()}")
            print(f"Price range: ${symbol_data['price'].min():,.2f} to ${symbol_data['price'].max():,.2f}")
            print(f"Total liquidation amount: ${symbol_data['usd_size'].sum():,.2f}")
            print(f"Average liquidation size: ${symbol_data['usd_size'].mean():,.2f}")
            print(f"Largest liquidation: ${symbol_data['usd_size'].max():,.2f}")
            print(f"File saved to: {filepath}")
            
            # Print sample liquidations
            print(f"\n🔥 First 3 {symbol} liquidations:")
            print(symbol_data.head(3)[['datetime', 'LIQ_SIDE', 'price', 'usd_size']].to_string())
            print(f"\n🌟 Most recent 3 {symbol} liquidations:")
            print(symbol_data.tail(3)[['datetime', 'LIQ_SIDE', 'price', 'usd_size']].to_string())
        else:
            print(f"\n⚠️ No liquidations found for {symbol}")

def pull_and_save_liquidation_data():
    print("🌙 Moon Dev Liquidation Data Puller 🚀")
    print("=" * 60)
    
    # Initialize API
    api = MoonDevAPI()
    
    # Pull raw data
    print("🔄 Fetching liquidation data from Moon Dev API...")
    raw_data = api.get_liquidation_data(limit=17000000)
    
    if raw_data is None:
        print("❌ Failed to fetch liquidation data. Please check your API key and connection.")
        return None
        
    print(f"✅ Successfully fetched {len(raw_data):,} liquidation records!")
    
    # Save raw data with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_filename = f"raw_liquidation_data_{timestamp}.csv"
    raw_path = DATA_DIR / raw_filename
    
    # Save raw data exactly as received
    raw_data.to_csv(raw_path, index=False, header=False)
    print(f"\n💾 Raw data saved to: {raw_path}")
    
    # Process and save data by symbol
    process_and_save_by_symbol(raw_path)
    
    return raw_data

if __name__ == "__main__":
    raw_data = pull_and_save_liquidation_data() 