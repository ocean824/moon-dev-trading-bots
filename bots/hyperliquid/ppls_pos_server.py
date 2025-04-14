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
import threading

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
LIQUIDATION_THRESHOLD_PCT = 2.0  # Positions within 2% of liquidation are high priority
HIGH_PRIORITY_UPDATE_INTERVAL = 5  # Update high priority positions every 5 seconds
BATCH_SIZE = 50  # Process high priority addresses in batches of 50
HIGH_PRIORITY_MAX_WORKERS = 20  # Use more workers for high priority monitoring

# Global storage for high priority addresses and current prices
high_priority_addresses = set()
current_prices = {}
run_high_priority_thread = True
last_full_scan_time = 0
high_priority_running = False  # Flag to avoid overlapping high priority runs
full_scan_running = False  # Flag to track if full scan is running

def ask_bid(symbol):
    """Get current ask and bid prices for a symbol"""
    try:
        url = 'https://api.hyperliquid.xyz/info'
        headers = {'Content-Type': 'application/json'}

        data = {
            'type': 'l2Book',
            'coin': symbol
        }

        # Add retries for API reliability
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(url, headers=headers, json=data)
                
                # Check if response is valid
                if response.status_code != 200:
                    print(f"🔴 MOON DEV API error for {symbol}: status code {response.status_code}")
                    if attempt < max_retries - 1:
                        time.sleep(0.5)
                        continue
                    return None, None, None
                
                # Try to parse JSON
                try:
                    l2_data = response.json()
                except ValueError as e:
                    print(f"🔴 MOON DEV JSON parse error for {symbol}: {str(e)}")
                    print(f"Response text: {response.text[:100]}...")
                    if attempt < max_retries - 1:
                        time.sleep(0.5)
                        continue
                    return None, None, None
                
                # Check if response has expected structure
                if 'levels' not in l2_data:
                    print(f"🔴 MOON DEV Unexpected API response for {symbol}: 'levels' not found")
                    print(f"Response: {str(l2_data)[:100]}...")
                    if attempt < max_retries - 1:
                        time.sleep(0.5)
                        continue
                    return None, None, None
                
                l2_data = l2_data['levels']
                
                # Check if we have both bid and ask data
                if len(l2_data) < 2 or not l2_data[0] or not l2_data[1]:
                    print(f"🔴 MOON DEV Incomplete order book data for {symbol}")
                    if attempt < max_retries - 1:
                        time.sleep(0.5)
                        continue
                    return None, None, None
                
                # get bid and ask
                bid = float(l2_data[0][0]['px'])
                ask = float(l2_data[1][0]['px'])
                
                return ask, bid, l2_data
                
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"⚠️ MOON DEV Retrying {symbol} (attempt {attempt+1}/{max_retries}): {str(e)}")
                    time.sleep(0.5)
                else:
                    raise
        
        return None, None, None
    except Exception as e:
        print(f"🔴 MOON DEV Error fetching ask/bid for {symbol}: {str(e)}")
        return None, None, None

def update_all_prices():
    """Update current prices for all major coins"""
    coins = ["BTC", "ETH", "SOL", "DOGE", "BNB", "XRP", "AVAX", "MATIC", "ARB", "OP", "SUI", "APT", "LINK", "NEAR"]
    prices = {}
    
    print("💰 MOON DEV Updating market prices...")
    success_count = 0
    
    for coin in coins:
        try:
            ask, bid, _ = ask_bid(coin)
            if bid:
                prices[coin] = bid
                print(f"🌙 MOON DEV Price Update: {coin} = ${bid:.2f}")
                success_count += 1
            else:
                print(f"⚠️ MOON DEV Failed to get price for {coin}")
        except Exception as e:
            print(f"⚠️ MOON DEV Error updating price for {coin}: {str(e)}")
    
    if success_count == 0:
        print("❌ MOON DEV Failed to fetch ANY prices! Check API connectivity.")
    else:
        print(f"✅ MOON DEV Successfully fetched {success_count}/{len(coins)} prices")
    
    return prices

def load_wallet_addresses():
    """Load wallet addresses from text file"""
    addresses_file = os.path.join(DATA_DIR, "whale_addresses.txt")
    try:
        with open(addresses_file, 'r') as f:
            addresses = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        print(f"🌙 MOON DEV Loaded {len(addresses)} addresses")
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

def is_near_liquidation(position, current_prices):
    """Check if position is close to liquidation price"""
    coin = position.get("coin")
    current_price = current_prices.get(coin)
    
    if not current_price or not position.get("liquidation_price"):
        return False
    
    liquidation_price = position.get("liquidation_price")
    is_long = position.get("is_long")
    
    if is_long:
        # For longs, liquidation price is below current price
        if liquidation_price <= 0:
            return False
        pct_to_liquidation = (current_price - liquidation_price) / current_price * 100
    else:
        # For shorts, liquidation price is above current price
        if liquidation_price <= 0:
            return False
        pct_to_liquidation = (liquidation_price - current_price) / current_price * 100
    
    return pct_to_liquidation <= LIQUIDATION_THRESHOLD_PCT

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
    print(f"✨ MOON DEV Saved {len(all_positions)} positions to {positions_file}")
    
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
    print(f"✨ MOON DEV Saved aggregated positions to {agg_file}")
    
    return df, agg_df

def fetch_addresses_batch(addresses_batch):
    """Fetch positions for a batch of addresses in parallel"""
    batch_positions = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=HIGH_PRIORITY_MAX_WORKERS) as executor:
        future_to_address = {executor.submit(process_address_data, address): address for address in addresses_batch}
        
        for future in concurrent.futures.as_completed(future_to_address):
            try:
                positions = future.result()
                if positions:
                    batch_positions.extend(positions)
            except Exception as e:
                print(f"❌ Error in batch processing: {str(e)}")
                
    return batch_positions

def high_priority_monitoring_thread():
    """Thread function to monitor high priority addresses more frequently"""
    global high_priority_addresses, current_prices, run_high_priority_thread, high_priority_running
    
    print("🚨 MOON DEV Starting high priority monitoring thread with faster updates")
    
    while run_high_priority_thread:
        if high_priority_addresses and not high_priority_running:
            try:
                high_priority_running = True
                
                # Update prices first (only coins we need)
                needed_coins = set()
                addresses_list = list(high_priority_addresses)
                
                # Process in batches to avoid memory issues
                all_priority_positions = []
                
                # Process addresses in batches
                for i in range(0, len(addresses_list), BATCH_SIZE):
                    batch = addresses_list[i:i+BATCH_SIZE]
                    print(f"🔍 MOON DEV Checking priority batch {i//BATCH_SIZE + 1}/{(len(addresses_list)-1)//BATCH_SIZE + 1} ({len(batch)} addresses)")
                    
                    batch_positions = fetch_addresses_batch(batch)
                    all_priority_positions.extend(batch_positions)
                    
                    # Note which coins we need prices for
                    for pos in batch_positions:
                        needed_coins.add(pos.get("coin", ""))
                
                # Update only prices we need
                for coin in needed_coins:
                    if coin:
                        try:
                            ask, bid, _ = ask_bid(coin)
                            if bid:
                                current_prices[coin] = bid
                                print(f"💲 MOON DEV Price: {coin} = ${bid:.2f}")
                        except Exception as e:
                            pass
                
                # Check which positions are still near liquidation
                still_near_liq = set()
                for position in all_priority_positions:
                    if is_near_liquidation(position, current_prices):
                        still_near_liq.add(position["address"])
                
                # Update the set of high priority addresses
                high_priority_addresses = still_near_liq
                
                if all_priority_positions:
                    # Update the priority positions in the CSV files
                    print(f"📊 MOON DEV Updating {len(all_priority_positions)} high priority positions")
                    
                    # Read existing positions file if it exists
                    positions_file = os.path.join(DATA_DIR, "positions_on_hlp.csv")
                    if os.path.exists(positions_file):
                        try:
                            df = pd.read_csv(positions_file)
                            
                            # Remove existing entries for the high priority addresses
                            priority_addrs = [p["address"] for p in all_priority_positions]
                            df = df[~df['address'].isin(priority_addrs)]
                            
                            # Add updated positions
                            new_positions_df = pd.DataFrame(all_priority_positions)
                            df = pd.concat([df, new_positions_df], ignore_index=True)
                            
                            # Save updated file
                            df.to_csv(positions_file, index=False, float_format='%.2f')
                            
                            # Update aggregated view
                            save_positions_to_csv(df.to_dict('records'))
                            
                            print(f"✅ MOON DEV Updated {len(all_priority_positions)} high priority positions from {len(priority_addrs)} addresses")
                            print(f"🔔 MOON DEV Still near liquidation: {len(still_near_liq)} addresses")
                        except Exception as e:
                            print(f"❌ Error updating high priority positions: {str(e)}")
            except Exception as e:
                print(f"❌ Error in high priority thread: {str(e)}")
            finally:
                high_priority_running = False
        
        # Short sleep to prevent CPU hogging, but keep very responsive
        time.sleep(0.5)

def fetch_all_positions_parallel(addresses):
    """Fetch positions for all addresses in parallel"""
    global high_priority_addresses, current_prices, last_full_scan_time, full_scan_running
    
    full_scan_running = True
    start_time = time.time()
    total_addresses = len(addresses)
    print(f"🚀 MOON DEV Processing {total_addresses} addresses with {MAX_WORKERS} workers")
    
    # Update current prices before scanning - do this for all major coins
    current_prices = update_all_prices()
    
    all_positions = []
    # Process in batches to avoid memory issues
    for i in range(0, len(addresses), BATCH_SIZE):
        batch = addresses[i:i+BATCH_SIZE]
        print(f"📦 MOON DEV Processing address batch {i//BATCH_SIZE + 1}/{(len(addresses)-1)//BATCH_SIZE + 1}")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_address = {executor.submit(process_address_data, address): address for address in batch}
            
            for future in concurrent.futures.as_completed(future_to_address):
                try:
                    positions = future.result()
                    if positions:
                        all_positions.extend(positions)
                except Exception as e:
                    print(f"❌ Error processing address: {str(e)}")
    
    # Update high priority addresses
    new_high_priority = set()
    for position in all_positions:
        if is_near_liquidation(position, current_prices):
            new_high_priority.add(position["address"])
    
    # Merge with existing high priority addresses
    high_priority_addresses = new_high_priority
    
    last_full_scan_time = time.time()
    scan_duration = last_full_scan_time - start_time
    print(f"✅ MOON DEV Found {len(all_positions)} total positions in {scan_duration:.1f} seconds")
    print(f"🔥 Identified {len(high_priority_addresses)} high priority addresses near liquidation")
    
    full_scan_running = False
    return all_positions

def main():
    """Main function to run the position tracker"""
    global API_REQUEST_DELAY, run_high_priority_thread, LIQUIDATION_THRESHOLD_PCT, HIGH_PRIORITY_UPDATE_INTERVAL

    parser = argparse.ArgumentParser(description="HyperLiquid Position Tracker")
    parser.add_argument('--delay', type=float, default=0.1, help='Delay between API requests in seconds (default: 0.1)')
    parser.add_argument('--threshold', type=float, default=2.0, help='Liquidation threshold percentage (default: 2.0)')
    parser.add_argument('--priority-interval', type=float, default=5.0, help='High priority update interval in seconds (default: 5)')
    args = parser.parse_args()
    
    API_REQUEST_DELAY = args.delay
    LIQUIDATION_THRESHOLD_PCT = args.threshold
    HIGH_PRIORITY_UPDATE_INTERVAL = args.priority_interval
    
    if not ensure_data_dir():
        return
    
    addresses = load_wallet_addresses()
    if not addresses:
        print("⚠️ No addresses loaded! Exiting...")
        return
    
    try:
        # Start high priority monitoring thread
        high_priority_thread = threading.Thread(target=high_priority_monitoring_thread)
        high_priority_thread.daemon = True
        high_priority_thread.start()
        
        # Main loop to continually scan all addresses
        while True:
            if not full_scan_running:
                print(f"\n🔄 MOON DEV Starting full scan of {len(addresses)} addresses")
                all_positions = fetch_all_positions_parallel(addresses)
                save_positions_to_csv(all_positions)
            else:
                # Wait a short time if a full scan is already running
                time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 MOON DEV shutting down gracefully...")
        run_high_priority_thread = False
        time.sleep(1)  # Give thread time to terminate
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
    finally:
        run_high_priority_thread = False

if __name__ == "__main__":
    main()