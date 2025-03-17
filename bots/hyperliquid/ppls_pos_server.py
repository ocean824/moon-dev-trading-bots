'''
We're building a bot that looks at all of the open positions here on Hyperliquid. 

The tricky part is going to be getting the addresses of the whales. 
Because I know how to get positions for anybody. That's easy money. 
It's just, who are those whales and how do we identify them? 

todo 
- Make a list of people with big deposits and then follow those or see what they're up to and see their position. 

list of adderess of potentional whales
https://dune.com/x3research/hyperliquid
    - i got stopped at the start of the 4th page here
https://dune.com/kouei/hyperliquid-usdc-deposit
    - i put the first 500 on the list
    

all hyperliquid protocols
https://data.asxn.xyz/dashboard/hyperliquid-ecosystem
https://hyperdash.info/ -- this is a good one
'''

import os
import json
import time
import pandas as pd
import requests
from datetime import datetime
import numpy as np
import concurrent.futures
from tqdm import tqdm
import colorama
from colorama import Fore
import argparse

# Initialize colorama for terminal colors
colorama.init(autoreset=True)

# Configure pandas display options
pd.set_option('display.float_format', '{:.2f}'.format)

# Configuration
API_URL = "https://api.hyperliquid.xyz/info"
DATA_DIR = "bots/hyperliquid/data/ppls_positions"
HEADERS = {"Content-Type": "application/json"}
MIN_POSITION_VALUE = 25000
MAX_WORKERS = 10
API_REQUEST_DELAY = 0.1

def load_wallet_addresses():
    """Load wallet addresses from text file"""
    addresses_file = os.path.join(DATA_DIR, "whale_addresses.txt")
    try:
        with open(addresses_file, 'r') as f:
            addresses = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        print(f"🌙 Loaded {len(addresses)} addresses")
        return addresses
    except Exception as e:
        print(f"⚠️ Error loading addresses: {str(e)}")
        return []

def ensure_data_dir():
    """Ensure the data directory exists"""
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        return True
    except Exception as e:
        print(f"⚠️ Error creating directory: {str(e)}")
        return False

def get_positions_for_address(address):
    """Fetch positions for a specific wallet address"""
    max_retries = 3
    base_delay = 0.5
    
    for retry in range(max_retries):
        try:
            payload = {
                "type": "clearinghouseState",
                "user": address
            }
            
            response = requests.post(API_URL, headers=HEADERS, json=payload)
            
            if response.status_code == 429:
                delay = base_delay * (2 ** retry)
                time.sleep(delay)
                continue
                
            response.raise_for_status()
            return response.json(), address
            
        except Exception as e:
            if retry == max_retries - 1:
                print(f"❌ Error fetching positions for {address[:6]}...{address[-4:]}: {str(e)}")
            
    return None, address

def process_positions(data, address):
    """Process the position data"""
    if not data or "assetPositions" not in data:
        return []
    
    positions = []
    for pos in data["assetPositions"]:
        if "position" in pos:
            p = pos["position"]
            
            try:
                size = float(p.get("szi", "0"))
                position_value = float(p.get("positionValue", "0"))
                
                if position_value < MIN_POSITION_VALUE:
                    continue
                    
                position_info = {
                    "address": address,
                    "coin": p.get("coin", ""),
                    "entry_price": float(p.get("entryPx", "0")),
                    "leverage": p.get("leverage", {}).get("value", 0),
                    "position_value": position_value,
                    "unrealized_pnl": float(p.get("unrealizedPnl", "0")),
                    "liquidation_price": float(p.get("liquidationPx", "0") or 0),
                    "is_long": size > 0,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                positions.append(position_info)
                
            except Exception as e:
                continue
    
    return positions

def process_address_data(address):
    """Process a single address - for parallel execution"""
    time.sleep(API_REQUEST_DELAY)
    data, address = get_positions_for_address(address)
    if data:
        return process_positions(data, address)
    return []

def save_positions_to_csv(all_positions):
    """Save positions to CSV files"""
    if not all_positions:
        print("No positions found to save!")
        return None, None
    
    # Create DataFrame
    df = pd.DataFrame(all_positions)
    
    # Format numeric columns
    numeric_cols = ['entry_price', 'position_value', 'unrealized_pnl', 'liquidation_price']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = df[col].astype(float)
    
    # Save all positions
    positions_file = os.path.join(DATA_DIR, "positions_on_hlp.csv")
    df.to_csv(positions_file, index=False, float_format='%.2f')
    print(f"✨ Saved {len(all_positions)} positions to {positions_file}")
    
    # Create and save aggregated view
    agg_df = df.groupby(['coin', 'is_long']).agg({
        'position_value': 'sum',
        'unrealized_pnl': 'sum',
        'address': 'count',
        'leverage': 'mean',
        'liquidation_price': lambda x: np.nan if all(pd.isna(x)) else np.nanmean(x)
    }).reset_index()
    
    # Add direction and rename columns
    agg_df['direction'] = agg_df['is_long'].apply(lambda x: 'LONG' if x else 'SHORT')
    agg_df = agg_df.rename(columns={
        'address': 'num_traders',
        'position_value': 'total_value',
        'unrealized_pnl': 'total_pnl',
        'leverage': 'avg_leverage'
    })
    
    # Sort by total value
    agg_df = agg_df.sort_values('total_value', ascending=False)
    
    # Save aggregated view
    agg_file = os.path.join(DATA_DIR, "agg_positions_on_hlp.csv")
    agg_df.to_csv(agg_file, index=False, float_format='%.2f')
    print(f"✨ Saved aggregated positions to {agg_file}")
    
    return df, agg_df

def fetch_all_positions_parallel(addresses):
    """Fetch positions for all addresses in parallel"""
    total_addresses = len(addresses)
    print(f"🚀 Processing {total_addresses} addresses with {MAX_WORKERS} workers")
    
    all_positions = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_address = {executor.submit(process_address_data, address): address for address in addresses}
        
        with tqdm(total=total_addresses, desc="Fetching positions") as progress_bar:
            for future in concurrent.futures.as_completed(future_to_address):
                try:
                    positions = future.result()
                    if positions:
                        all_positions.extend(positions)
                except Exception as e:
                    print(f"❌ Error processing address: {str(e)}")
                progress_bar.update(1)
                
    print(f"✅ Found {len(all_positions)} total positions")
    return all_positions

def main():
    """Main function to run the position tracker"""
    parser = argparse.ArgumentParser(description="HyperLiquid Position Tracker")
    parser.add_argument('--delay', type=float, default=0.1, help='Delay between API requests in seconds (default: 0.1)')
    args = parser.parse_args()
    
    global API_REQUEST_DELAY
    API_REQUEST_DELAY = args.delay
    
    ensure_data_dir()
    addresses = load_wallet_addresses()
    if not addresses:
        print("⚠️ No addresses loaded! Exiting...")
        return
    
    all_positions = fetch_all_positions_parallel(addresses)
    positions_df, agg_df = save_positions_to_csv(all_positions)
    return positions_df, agg_df

if __name__ == "__main__":
    main()