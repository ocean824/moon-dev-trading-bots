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
from tqdm import tqdm  # For progress bars
import colorama
from colorama import Fore, Back, Style
import nice_funcs as n  # Import directly from the same directory
import argparse

# Initialize colorama for terminal colors
colorama.init(autoreset=True)

# Configure pandas to display numbers with commas and no scientific notation
pd.set_option('display.float_format', '{:.2f}'.format)  # No dollar sign
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)

# ===== CONFIGURATION =====
API_URL = "https://api.hyperliquid.xyz/info"
DATA_DIR = "bots/hyperliquid/data/ppls_positions"  # Directory path, not file path
HEADERS = {"Content-Type": "application/json"}
MIN_POSITION_VALUE = 25000  # Only track positions with value >= $25,000
MAX_WORKERS = 10  # Reduced to 5 to avoid rate limiting
DUMP_RAW_DATA = False  # Set to True to dump raw API response data (one-time operation)
TOP_N_POSITIONS = 25  # Number of top positions to display

# Add a global variable for the delay
API_REQUEST_DELAY = 0.1  # Default delay in seconds

def load_wallet_addresses():
    """Load wallet addresses from text file"""
    addresses_file = os.path.join(DATA_DIR, "whale_addresses.txt")
    try:
        with open(addresses_file, 'r') as f:
            # Read lines and filter out empty lines and comments
            addresses = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        print(f"{Fore.CYAN}🌙 Moon Dev says: {Fore.GREEN}Loaded {len(addresses)} addresses from {addresses_file} 🚀")
        return addresses
    except Exception as e:
        print(f"{Fore.RED}⚠️ Error loading addresses: {str(e)}")
        return []

def ensure_data_dir():
    """Ensure the data directory exists"""
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        print(f"{Fore.CYAN}🌙 Moon Dev says: {Fore.GREEN}Data directory ready at {DATA_DIR} 🚀")
    except Exception as e:
        print(f"{Fore.RED}⚠️ Error creating directory: {str(e)}")
        return False
    return True

def dump_raw_api_data(data, address):
    """Dump raw API response data to a JSON file for analysis"""
    if not data:
        return
    
    try:
        # Create a filename with the address
        filename = os.path.join(DATA_DIR, f"raw_data_{address[:8]}.json")
        
        # Write the data to a JSON file with pretty formatting
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)
        
        print(f"{Fore.MAGENTA}💾 Dumped raw API data for analysis to {filename}")
        
        # Also create a human-readable analysis file
        analyze_raw_data(data, address)
        
        # Set the flag to False to prevent further dumps
        global DUMP_RAW_DATA
        DUMP_RAW_DATA = False
    except Exception as e:
        print(f"{Fore.RED}⚠️ Error dumping raw data: {str(e)}")

def analyze_raw_data(data, address):
    """Analyze the raw API data and create a human-readable summary"""
    try:
        # Create a filename for the analysis
        filename = os.path.join(DATA_DIR, f"data_analysis_{address[:8]}.txt")
        
        with open(filename, 'w') as f:
            f.write(f"=== HYPERLIQUID API DATA ANALYSIS ===\n")
            f.write(f"Address: {address}\n")
            f.write(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Write the top-level keys
            f.write("=== TOP LEVEL KEYS ===\n")
            for key in data.keys():
                f.write(f"- {key}\n")
            f.write("\n")
            
            # Analyze asset positions if available
            if "assetPositions" in data:
                f.write("=== ASSET POSITIONS STRUCTURE ===\n")
                if data["assetPositions"]:
                    # Get the first position as an example
                    example_pos = data["assetPositions"][0]
                    f.write(f"Position keys: {list(example_pos.keys())}\n\n")
                    
                    if "position" in example_pos:
                        position = example_pos["position"]
                        f.write("Position data keys:\n")
                        for key in position.keys():
                            f.write(f"- {key}: {type(position[key]).__name__}\n")
                            
                            # For nested objects, show their structure too
                            if isinstance(position[key], dict):
                                f.write(f"  Nested keys: {list(position[key].keys())}\n")
                else:
                    f.write("No positions found for this address.\n")
            
            # Analyze other interesting data
            if "marginSummary" in data:
                f.write("\n=== MARGIN SUMMARY ===\n")
                for key, value in data["marginSummary"].items():
                    f.write(f"- {key}: {value}\n")
            
            # Add any other sections that might be interesting
            f.write("\n=== POTENTIAL DATA POINTS FOR DISPLAY ===\n")
            f.write("1. Position size and value (already implemented)\n")
            f.write("2. Entry price and liquidation price (already implemented)\n")
            f.write("3. Leverage used (partially implemented)\n")
            f.write("4. Unrealized PnL (already implemented)\n")
            f.write("5. Margin information\n")
            f.write("6. Account equity\n")
            f.write("7. Funding payments\n")
            f.write("8. Position health/risk metrics\n")
            
        print(f"{Fore.GREEN}📝 Created human-readable analysis at {filename}")
    except Exception as e:
        print(f"{Fore.RED}⚠️ Error analyzing raw data: {str(e)}")

def get_positions_for_address(address):
    """
    Fetch positions for a specific wallet address using Hyperliquid API
    with exponential backoff for rate limiting
    """
    max_retries = 3
    base_delay = 0.5  # Start with 0.5 second delay
    
    for retry in range(max_retries):
        try:
            payload = {
                "type": "clearinghouseState",
                "user": address
            }
            
            # Debug message removed for cleaner parallel output
            response = requests.post(API_URL, headers=HEADERS, json=payload)
            
            # Check for rate limiting
            if response.status_code == 429:
                # Calculate exponential backoff delay
                delay = base_delay * (2 ** retry)
                print(f"{Fore.YELLOW}⚠️ Rate limited for {address[:6]}...{address[-4:]} - retrying in {delay:.2f}s (attempt {retry+1}/{max_retries})")
                time.sleep(delay)
                continue  # Retry the request
                
            response.raise_for_status()
            
            data = response.json()
            
            # Dump raw data for analysis (only once)
            global DUMP_RAW_DATA
            if DUMP_RAW_DATA and "assetPositions" in data and data["assetPositions"]:
                dump_raw_api_data(data, address)
            
            return data, address
            
        except requests.exceptions.HTTPError as e:
            if response.status_code == 429 and retry == max_retries - 1:
                # If we've exhausted our retries on rate limiting
                print(f"{Fore.RED}❌ Rate limit exceeded for {address[:6]}...{address[-4:]} after {max_retries} retries")
            else:
                print(f"{Fore.RED}❌ Error fetching positions for {address[:6]}...{address[-4:]}: {str(e)}")
            
            # If we've tried max_retries times, give up
            if retry == max_retries - 1:
                break
                
        except Exception as e:
            print(f"{Fore.RED}❌ Error fetching positions for {address[:6]}...{address[-4:]}: {str(e)}")
            # If we've tried max_retries times, give up
            if retry == max_retries - 1:
                break
            
    return None, address

def process_positions(data, address):
    """
    Process the position data into a more usable format
    """
    if not data or "assetPositions" not in data:
        return []
    
    positions = []
    position_count = len(data["assetPositions"])
    
    if position_count > 0:
        print(f"{Fore.YELLOW}🔍 Processing {position_count} positions for {address[:6]}...{address[-4:]}")
    
    for pos in data["assetPositions"]:
        if "position" in pos:
            p = pos["position"]
            
            try:
                size = float(p.get("szi", "0"))
                position_value = float(p.get("positionValue", "0"))
                
                # Skip positions below minimum value threshold
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
                
            except (TypeError, ValueError) as e:
                print(f"{Fore.RED}⚠️ Error processing position for {address[:6]}...{address[-4:]}: {str(e)}")
                continue
    
    return positions

def display_top_individual_positions(df, n=TOP_N_POSITIONS):
    """
    Display top individual long and short positions
    """
    if df is None or df.empty:
        print(f"{Fore.RED}No positions to display!")
        return None, None
    
    # Create a copy to avoid modifying the original
    display_df = df.copy()
    
    # Sort by position value
    longs = display_df[display_df['is_long']].sort_values('position_value', ascending=False)
    shorts = display_df[~display_df['is_long']].sort_values('position_value', ascending=False)
    
    # Print header with fancy box
    print(f"\n{Fore.CYAN}{'='*120}")
    print(f"{Fore.CYAN}{'='*35} 🐳 TOP INDIVIDUAL WHALE POSITIONS 🐳 {'='*35}")
    print(f"{Fore.CYAN}{'='*120}")
    
    # Display top long positions
    print(f"\n{Fore.GREEN}{Style.BRIGHT}🚀 TOP {n} INDIVIDUAL LONG POSITIONS 📈")
    print(f"{Fore.GREEN}{'-'*120}")
    
    if len(longs) > 0:
        for i, (_, row) in enumerate(longs.head(n).iterrows(), 1):
            liq_price = row['liquidation_price'] if row['liquidation_price'] > 0 else "N/A"
            liq_display = f"${liq_price:,.2f}" if liq_price != "N/A" else "N/A"
            
            print(f"{Fore.GREEN}#{i} {Fore.YELLOW}{row['coin']} {Fore.GREEN}${row['position_value']:,.2f} " + 
                  f"{Fore.BLUE}| Entry: ${row['entry_price']:,.2f} " +
                  f"{Fore.MAGENTA}| PnL: ${row['unrealized_pnl']:,.2f} " +
                  f"{Fore.CYAN}| Leverage: {row['leverage']}x " +
                  f"{Fore.RED}| Liq: {liq_display}")
            print(f"{Fore.CYAN}   Address: {row['address']}")
    else:
        print(f"{Fore.YELLOW}No long positions found!")
    
    # Display top short positions
    print(f"\n{Fore.RED}{Style.BRIGHT}💥 TOP {n} INDIVIDUAL SHORT POSITIONS 📉")
    print(f"{Fore.RED}{'-'*120}")
    
    if len(shorts) > 0:
        for i, (_, row) in enumerate(shorts.head(n).iterrows(), 1):
            liq_price = row['liquidation_price'] if row['liquidation_price'] > 0 else "N/A"
            liq_display = f"${liq_price:,.2f}" if liq_price != "N/A" else "N/A"
            
            print(f"{Fore.RED}#{i} {Fore.YELLOW}{row['coin']} {Fore.RED}${row['position_value']:,.2f} " + 
                  f"{Fore.BLUE}| Entry: ${row['entry_price']:,.2f} " +
                  f"{Fore.MAGENTA}| PnL: ${row['unrealized_pnl']:,.2f} " +
                  f"{Fore.CYAN}| Leverage: {row['leverage']}x " +
                  f"{Fore.RED}| Liq: {liq_display}")
            print(f"{Fore.CYAN}   Address: {row['address']}")
    else:
        print(f"{Fore.YELLOW}No short positions found!")
    
    # Print footer
    print(f"\n{Fore.CYAN}{'='*120}")
    print(f"{Fore.CYAN}{'='*30} 🌙 Moon Dev Whale Tracker - Happy Trading! 🚀 {'='*30}")
    print(f"{Fore.CYAN}{'='*120}")
    
    return longs.head(n), shorts.head(n)

def display_risk_metrics(df):
    """
    Display metrics for positions closest to liquidation
    """
    if df is None or df.empty:
        return None, None
    
    print(f"\n{Fore.CYAN}{'='*120}")
    print(f"{Fore.CYAN}{'='*35} 🔥 POSITIONS CLOSEST TO LIQUIDATION 🔥 {'='*35}")
    print(f"{Fore.CYAN}{'='*120}")
    
    # Create a copy to avoid modifying the original
    risk_df = df.copy()
    
    # Filter out positions with invalid liquidation prices
    risk_df = risk_df[risk_df['liquidation_price'] > 0]
    
    if risk_df.empty:
        print(f"{Fore.YELLOW}No positions with valid liquidation prices found!")
        return None, None
    
    # Calculate distance to liquidation as a percentage
    # For longs: (current_price - liquidation_price) / current_price * 100
    # For shorts: (liquidation_price - current_price) / current_price * 100
    
    # Since we don't have current price directly, we'll use entry price as a proxy
    # This is not ideal but gives a rough estimate
    risk_df['distance_to_liq_pct'] = np.where(
        risk_df['is_long'],
        (risk_df['entry_price'] - risk_df['liquidation_price']) / risk_df['entry_price'] * 100,
        (risk_df['liquidation_price'] - risk_df['entry_price']) / risk_df['entry_price'] * 100
    )
    
    # Sort by distance to liquidation (ascending)
    risk_df = risk_df.sort_values('distance_to_liq_pct')
    
    # Split into longs and shorts
    risky_longs = risk_df[risk_df['is_long']].sort_values('distance_to_liq_pct')
    risky_shorts = risk_df[~risk_df['is_long']].sort_values('distance_to_liq_pct')
    
    # Display positions closest to liquidation - LONGS
    print(f"\n{Fore.GREEN}{Style.BRIGHT}🚀 TOP {TOP_N_POSITIONS} LONG POSITIONS CLOSEST TO LIQUIDATION 📈")
    print(f"{Fore.GREEN}{'-'*120}")
    
    if len(risky_longs) > 0:
        for i, (_, row) in enumerate(risky_longs.head(TOP_N_POSITIONS).iterrows(), 1):
            print(f"{Fore.GREEN}#{i} {Fore.YELLOW}{row['coin']} {Fore.GREEN}${row['position_value']:,.2f} " + 
                  f"{Fore.BLUE}| Entry: ${row['entry_price']:,.2f} " +
                  f"{Fore.RED}| Liq: ${row['liquidation_price']:,.2f} " +
                  f"{Fore.MAGENTA}| Distance: {row['distance_to_liq_pct']:.2f}% " +
                  f"{Fore.CYAN}| Leverage: {row['leverage']}x")
            print(f"{Fore.CYAN}   Address: {row['address']}")
    else:
        print(f"{Fore.YELLOW}No long positions with liquidation prices found!")
    
    # Display positions closest to liquidation - SHORTS
    print(f"\n{Fore.RED}{Style.BRIGHT}💥 TOP {TOP_N_POSITIONS} SHORT POSITIONS CLOSEST TO LIQUIDATION 📉")
    print(f"{Fore.RED}{'-'*120}")
    
    if len(risky_shorts) > 0:
        for i, (_, row) in enumerate(risky_shorts.head(TOP_N_POSITIONS).iterrows(), 1):
            print(f"{Fore.RED}#{i} {Fore.YELLOW}{row['coin']} {Fore.RED}${row['position_value']:,.2f} " + 
                  f"{Fore.BLUE}| Entry: ${row['entry_price']:,.2f} " +
                  f"{Fore.RED}| Liq: ${row['liquidation_price']:,.2f} " +
                  f"{Fore.MAGENTA}| Distance: {row['distance_to_liq_pct']:.2f}% " +
                  f"{Fore.CYAN}| Leverage: {row['leverage']}x")
            print(f"{Fore.CYAN}   Address: {row['address']}")
    else:
        print(f"{Fore.YELLOW}No short positions with liquidation prices found!")
    
    # Print footer
    print(f"\n{Fore.CYAN}{'='*120}")
    print(f"{Fore.CYAN}{'='*30} 🌙 Moon Dev Liquidation Tracker - Trade Safely! 🚀 {'='*30}")
    print(f"{Fore.CYAN}{'='*120}")
    
    return risky_longs.head(TOP_N_POSITIONS), risky_shorts.head(TOP_N_POSITIONS)

def save_liquidation_risk_to_csv(risky_longs_df, risky_shorts_df):
    """
    Save positions closest to liquidation to a CSV file
    """
    if risky_longs_df is None and risky_shorts_df is None:
        print(f"{Fore.RED}🌙 Moon Dev says: No positions with liquidation data to save! 😢")
        return
    
    # Save risky long positions
    if risky_longs_df is not None and not risky_longs_df.empty:
        # Add a direction column
        risky_longs_df = risky_longs_df.copy()
        risky_longs_df['direction'] = 'LONG'
        
        # Save to CSV
        longs_file = os.path.join(DATA_DIR, "liquidation_closest_long_positions.csv")
        risky_longs_df.to_csv(longs_file, index=False, float_format='%.2f')
        print(f"{Fore.GREEN}🌙 Moon Dev says: Saved {len(risky_longs_df)} long positions closest to liquidation to {longs_file} 🚀")
    
    # Save risky short positions
    if risky_shorts_df is not None and not risky_shorts_df.empty:
        # Add a direction column
        risky_shorts_df = risky_shorts_df.copy()
        risky_shorts_df['direction'] = 'SHORT'
        
        # Save to CSV
        shorts_file = os.path.join(DATA_DIR, "liquidation_closest_short_positions.csv")
        risky_shorts_df.to_csv(shorts_file, index=False, float_format='%.2f')
        print(f"{Fore.GREEN}🌙 Moon Dev says: Saved {len(risky_shorts_df)} short positions closest to liquidation to {shorts_file} 🚀")
    
    # Combine risky long and short positions into a single file
    if (risky_longs_df is not None and not risky_longs_df.empty) or (risky_shorts_df is not None and not risky_shorts_df.empty):
        # Create combined DataFrame
        combined_df = pd.concat([risky_longs_df, risky_shorts_df]) if risky_longs_df is not None and risky_shorts_df is not None else (risky_longs_df if risky_longs_df is not None else risky_shorts_df)
        
        # Sort by distance to liquidation
        combined_df = combined_df.sort_values('distance_to_liq_pct')
        
        # Save to CSV
        combined_file = os.path.join(DATA_DIR, "liquidation_closest_positions.csv")
        combined_df.to_csv(combined_file, index=False, float_format='%.2f')
        print(f"{Fore.GREEN}🌙 Moon Dev says: Saved {len(combined_df)} positions closest to liquidation to {combined_file} 🚀")

def save_positions_to_csv(all_positions):
    """
    Save all positions to a CSV file
    """
    if not all_positions:
        print(f"{Fore.RED}🌙 Moon Dev says: No positions found to save! 😢")
        return None, None
    
    df = pd.DataFrame(all_positions)
    
    # Format numeric columns
    numeric_cols = ['entry_price', 'position_value', 'unrealized_pnl', 'liquidation_price']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = df[col].astype(float)
    
    # Save all positions
    positions_file = os.path.join(DATA_DIR, "all_positions.csv")
    df.to_csv(positions_file, index=False, float_format='%.2f')
    print(f"{Fore.GREEN}🌙 Moon Dev says: Saved {len(all_positions)} positions to {positions_file} 🚀")
    
    # Create and save aggregated view
    print(f"\n{Fore.YELLOW}🔄 Creating aggregated view...")
    agg_df = df.groupby(['coin', 'is_long']).agg({
        'position_value': 'sum',
        'unrealized_pnl': 'sum',
        'address': 'count',
        'leverage': 'mean',  # Average leverage
        'liquidation_price': lambda x: np.nan if all(pd.isna(x)) else np.nanmean(x)  # Average liquidation price, ignoring NaN values
    }).reset_index()
    
    # Add direction and rename columns
    agg_df['direction'] = agg_df['is_long'].apply(lambda x: 'LONG' if x else 'SHORT')
    agg_df = agg_df.rename(columns={
        'address': 'num_traders',
        'position_value': 'total_value',
        'unrealized_pnl': 'total_pnl',
        'leverage': 'avg_leverage',
        'liquidation_price': 'avg_liquidation_price'
    })
    
    # Calculate average value per trader
    agg_df['avg_value_per_trader'] = agg_df['total_value'] / agg_df['num_traders']
    
    # Sort by total value
    agg_df = agg_df.sort_values('total_value', ascending=False)
    
    # Save aggregated view
    agg_file = os.path.join(DATA_DIR, "aggregated_positions.csv")
    agg_df.to_csv(agg_file, index=False, float_format='%.2f')
    print(f"{Fore.GREEN}📊 Saved aggregated positions to {agg_file}")
    
    # Display summaries (for terminal display only, not affecting CSV output)
    print(f"\n{Fore.CYAN}{'='*30} POSITION SUMMARY {'='*30}")
    display_cols = ['coin', 'direction', 'total_value', 'num_traders', 'avg_value_per_trader', 'avg_leverage']
    
    # Temporarily format numbers with commas for display only
    with pd.option_context('display.float_format', '{:,.2f}'.format):
        print(f"{Fore.WHITE}{agg_df[display_cols]}")
        
        print(f"\n{Fore.GREEN}🔝 TOP LONG POSITIONS (AGGREGATED):")
        print(f"{Fore.GREEN}{agg_df[agg_df['is_long']][display_cols].head()}")
        
        print(f"\n{Fore.RED}🔝 TOP SHORT POSITIONS (AGGREGATED):")
        print(f"{Fore.RED}{agg_df[~agg_df['is_long']][display_cols].head()}")
    
    # Display top individual positions and get the dataframes
    longs_df, shorts_df = display_top_individual_positions(df)
    
    # Save top whale positions to CSV
    save_top_whale_positions_to_csv(longs_df, shorts_df)
    
    # Display risk metrics and get risky positions
    risky_longs_df, risky_shorts_df = display_risk_metrics(df)
    
    # Save liquidation risk positions to CSV
    save_liquidation_risk_to_csv(risky_longs_df, risky_shorts_df)
    
    return df, agg_df

def save_top_whale_positions_to_csv(longs_df, shorts_df):
    """
    Save top whale positions to a CSV file
    """
    if longs_df is None and shorts_df is None:
        print(f"{Fore.RED}🌙 Moon Dev says: No top whale positions to save! 😢")
        return
    
    # Create a timestamp for the filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save top long positions
    if longs_df is not None and not longs_df.empty:
        # Add a direction column
        longs_df = longs_df.copy()
        longs_df['direction'] = 'LONG'
        
        # Save to CSV
        longs_file = os.path.join(DATA_DIR, "top_whale_long_positions.csv")
        longs_df.to_csv(longs_file, index=False, float_format='%.2f')
        print(f"{Fore.GREEN}🌙 Moon Dev says: Saved {len(longs_df)} top long whale positions to {longs_file} 🚀")
    
    # Save top short positions
    if shorts_df is not None and not shorts_df.empty:
        # Add a direction column
        shorts_df = shorts_df.copy()
        shorts_df['direction'] = 'SHORT'
        
        # Save to CSV
        shorts_file = os.path.join(DATA_DIR, "top_whale_short_positions.csv")
        shorts_df.to_csv(shorts_file, index=False, float_format='%.2f')
        print(f"{Fore.GREEN}🌙 Moon Dev says: Saved {len(shorts_df)} top short whale positions to {shorts_file} 🚀")
    
    # Combine long and short positions into a single file
    if (longs_df is not None and not longs_df.empty) or (shorts_df is not None and not shorts_df.empty):
        # Create combined DataFrame
        combined_df = pd.concat([longs_df, shorts_df]) if longs_df is not None and shorts_df is not None else (longs_df if longs_df is not None else shorts_df)
        
        # Sort by position value
        combined_df = combined_df.sort_values('position_value', ascending=False)
        
        # Save to CSV
        combined_file = os.path.join(DATA_DIR, "top_whale_positions.csv")
        combined_df.to_csv(combined_file, index=False, float_format='%.2f')
        print(f"{Fore.GREEN}🌙 Moon Dev says: Saved {len(combined_df)} combined top whale positions to {combined_file} 🚀")

def process_address_data(address):
    """Process a single address - for parallel execution"""
    # Add a delay to avoid rate limiting
    time.sleep(API_REQUEST_DELAY)
    data, address = get_positions_for_address(address)
    if data:
        return process_positions(data, address)
    return []

def save_progress(processed_addresses, all_positions):
    """Save progress to allow resuming if the script is interrupted"""
    try:
        # Create a progress file with processed addresses
        progress_file = os.path.join(DATA_DIR, "progress.json")
        progress_data = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "processed_addresses": processed_addresses,
            "positions_count": len(all_positions)
        }
        
        with open(progress_file, 'w') as f:
            json.dump(progress_data, f, indent=4)
        
        # Also save the current positions
        if all_positions:
            temp_positions_file = os.path.join(DATA_DIR, "partial_positions.json")
            with open(temp_positions_file, 'w') as f:
                json.dump(all_positions, f, indent=4)
        
        print(f"{Fore.GREEN}🌙 Moon Dev says: {Fore.CYAN}Progress saved! Processed {len(processed_addresses)} addresses with {len(all_positions)} positions 💾")
    except Exception as e:
        print(f"{Fore.RED}⚠️ Error saving progress: {str(e)}")

def load_progress():
    """Load progress to resume from where we left off"""
    progress_file = os.path.join(DATA_DIR, "progress.json")
    positions_file = os.path.join(DATA_DIR, "partial_positions.json")
    
    processed_addresses = []
    positions = []
    
    try:
        # Check if progress file exists
        if os.path.exists(progress_file):
            with open(progress_file, 'r') as f:
                progress_data = json.load(f)
                processed_addresses = progress_data.get("processed_addresses", [])
                timestamp = progress_data.get("timestamp", "unknown")
                positions_count = progress_data.get("positions_count", 0)
                
                print(f"{Fore.CYAN}🌙 Moon Dev says: {Fore.GREEN}Found saved progress from {timestamp} with {len(processed_addresses)} addresses processed and {positions_count} positions 🚀")
        
        # Check if positions file exists
        if os.path.exists(positions_file):
            with open(positions_file, 'r') as f:
                positions = json.load(f)
                print(f"{Fore.CYAN}🌙 Moon Dev says: {Fore.GREEN}Loaded {len(positions)} positions from previous run 🚀")
    except Exception as e:
        print(f"{Fore.RED}⚠️ Error loading progress: {str(e)}")
        
    return processed_addresses, positions

def fetch_all_positions_parallel(addresses):
    """
    Fetch positions for all addresses in parallel using ThreadPoolExecutor
    with progress tracking and resuming capability
    """
    # Load progress if available
    processed_addresses, all_positions = load_progress()
    
    # Filter out already processed addresses
    remaining_addresses = [addr for addr in addresses if addr not in processed_addresses]
    
    if not remaining_addresses and all_positions:
        print(f"{Fore.GREEN}✅ All addresses have been processed already! Using cached results from previous run.")
        print(f"{Fore.YELLOW}ℹ️ To fetch fresh data, run without the --use-cache flag or use --reset.")
        return all_positions
    
    # If we have partial progress but still need to process more addresses
    if all_positions and len(processed_addresses) > 0:
        print(f"{Fore.GREEN}✅ Resuming from previous run with {len(all_positions)} positions already fetched.")
        print(f"{Fore.GREEN}✅ {len(processed_addresses)} addresses already processed, {len(remaining_addresses)} remaining.")
    
    total_addresses = len(remaining_addresses)
    print(f"\n{Fore.CYAN}🚀 Starting parallel processing with {Fore.YELLOW}{MAX_WORKERS} workers{Fore.CYAN} for {Fore.YELLOW}{total_addresses} remaining addresses")
    
    # Save progress periodically (every 50 addresses)
    progress_interval = 50
    
    # Use ThreadPoolExecutor for parallel processing
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all tasks and create a future-to-address mapping
        future_to_address = {executor.submit(process_address_data, address): address for address in remaining_addresses}
        
        # Process results as they complete with a progress bar
        completed = 0
        with tqdm(total=total_addresses, desc=f"{Fore.CYAN}Fetching positions", bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]") as progress_bar:
            for future in concurrent.futures.as_completed(future_to_address):
                address = future_to_address[future]
                try:
                    positions = future.result()
                    if positions:
                        all_positions.extend(positions)
                        print(f"{Fore.GREEN}✅ Found {len(positions)} positions for {address[:6]}...{address[-4:]}")
                    else:
                        print(f"{Fore.YELLOW}ℹ️ No positions found for {address[:6]}...{address[-4:]}")
                except Exception as e:
                    print(f"{Fore.RED}❌ Error processing {address[:6]}...{address[-4:]}: {str(e)}")
                
                # Mark this address as processed
                processed_addresses.append(address)
                
                # Update progress
                completed += 1
                progress_bar.update(1)
                
                # Save progress periodically
                if completed % progress_interval == 0:
                    save_progress(processed_addresses, all_positions)
                    
        # Save final progress
        save_progress(processed_addresses, all_positions)
                
    print(f"\n{Fore.GREEN}✅ Parallel processing complete! Found {len(all_positions)} total positions")
    return all_positions

def main():
    """Main function to run the position tracker"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="🌙 Moon Dev's Hyperliquid Whale Position Tracker")
    parser.add_argument('--reset', action='store_true', help='Reset progress and start from scratch')
    parser.add_argument('--use-cache', action='store_true', help='Use cached data if available instead of fetching fresh data')
    parser.add_argument('--delay', type=float, default=0.1, help='Delay between API requests in seconds (default: 0.1)')
    args = parser.parse_args()
    
    # Set the global delay value
    global API_REQUEST_DELAY
    API_REQUEST_DELAY = args.delay
    
    # Reset progress if requested
    if args.reset:
        progress_file = os.path.join(DATA_DIR, "progress.json")
        positions_file = os.path.join(DATA_DIR, "partial_positions.json")
        
        if os.path.exists(progress_file):
            os.remove(progress_file)
            print(f"{Fore.YELLOW}🔄 Progress file reset!")
            
        if os.path.exists(positions_file):
            os.remove(positions_file)
            print(f"{Fore.YELLOW}🔄 Partial positions file reset!")
    
    # Always clear progress files by default unless --use-cache is specified
    if not args.use_cache:
        progress_file = os.path.join(DATA_DIR, "progress.json")
        positions_file = os.path.join(DATA_DIR, "partial_positions.json")
        
        if os.path.exists(progress_file):
            os.remove(progress_file)
            print(f"{Fore.YELLOW}🔄 Clearing cached progress to fetch fresh data!")
            
        if os.path.exists(positions_file):
            os.remove(positions_file)
            print(f"{Fore.YELLOW}🔄 Clearing cached positions to fetch fresh data!")
    
    start_time = time.time()
    print(f"\n{Fore.CYAN}{'='*80}")
    print(f"{Fore.MAGENTA}{'*'*20} 🌙 Moon Dev's Whale Position Tracker Starting... 🐋 {'*'*20}")
    print(f"{Fore.CYAN}{'='*80}")
    
    # Ensure data directory exists
    ensure_data_dir()
    
    # Load wallet addresses
    addresses = load_wallet_addresses()
    if not addresses:
        print(f"{Fore.RED}⚠️ No addresses loaded! Exiting...")
        return
    
    print(f"{Fore.YELLOW}📝 Tracking {len(addresses)} wallet addresses")
    print(f"{Fore.YELLOW}💰 Minimum position value: ${MIN_POSITION_VALUE:,}")
    print(f"{Fore.YELLOW}🧵 Using {MAX_WORKERS} parallel threads")
    print(f"{Fore.YELLOW}⏱️ API request delay: {API_REQUEST_DELAY} seconds")
    print(f"{Fore.YELLOW}🔄 Using cached data: {args.use_cache}")
    
    # Fetch and save positions using parallel processing
    all_positions = fetch_all_positions_parallel(addresses)
    positions_df, agg_df = save_positions_to_csv(all_positions)
    
    # Calculate and display execution time
    execution_time = time.time() - start_time
    print(f"\n{Fore.CYAN}⏱️ Execution time: {execution_time:.2f} seconds ({execution_time/60:.2f} minutes)")
    
    print(f"\n{Fore.MAGENTA}{'*'*20} 🌙 Moon Dev says: Position tracking complete! 🚀 {'*'*20}")
    print(f"{Fore.CYAN}📁 CSV files saved in: {DATA_DIR}")
    return positions_df, agg_df

if __name__ == "__main__":
    main()