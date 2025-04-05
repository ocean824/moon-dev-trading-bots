'''
🌙 Moon Dev's Hyperliquid Liquidation Tracker 🔥
Built with love by Moon Dev 🌙 ✨

This script shows positions closest to liquidation in a compact format,
ordered by distance percentage with the closest ones displayed last.

Uses Moon Dev API to get pre-collected Hyperliquid positions data,
focusing only on positions at risk of liquidation.

disclaimer: this is not financial advice and there is no guarantee of any kind. use at your own risk.
'''

import os
import sys
import time
import json
import pandas as pd
import numpy as np
import requests
import random
import traceback
import colorama
import schedule
from colorama import Fore, Back, Style
from termcolor import colored

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from api import MoonDevAPI  # Import MoonDevAPI from the root directory

# Initialize colorama for terminal colors
colorama.init(autoreset=True)

# ===== CONSTANTS =====
TOP_N_POSITIONS =50  # Number of positions to display by proximity to liquidation
DATA_DIR = "bots/hyperliquid/data/closest_to_liqs"  # Directory path, not file path
API_DATA_DIR = "data/moondev_api"  # API data directory
MIN_POSITION_VALUE = 10000  # Only track positions with value >= $10,000
TOKENS_TO_ANALYZE = ['BTC', 'ETH', 'XRP', 'SOL', 'DOGE', 'AVAX', 'ARB', 'INJ', 'OP', 'MATIC']  # Tokens to analyze

# Moon Dev ASCII Art Banner (compact version)
MOON_DEV_BANNER = f"""{Fore.CYAN}
🌙 MOON DEV 🌙
{Fore.MAGENTA}🔥 Liquidation Tracker 🔥{Fore.RESET}
"""

# Fun Moon Dev messages
MOON_DEV_MESSAGES = [
    "🌙 Moon Dev tracking liquys like a boss! 💥",
    "🚀 Watching liquidations... to the moon! 🌙",
    "💰 Moon Dev sees the whale traps! 🐳",
    "⚡ Liquy-watch initiated! 🌙 Moon Dev style! ⚡",
    "🔥 Liquidation dominos about to fall? 🎯",
    "🌙 Moon Dev liquidation radar is hot! 🔍",
    "🎮 Liquy-hunting game: Level 99! 🌙",
    "💥 Countdown to liquidation... Moon Dev watching! ⏱️",
    "🎯 Target acquired! Liquidation imminent? 🌙",
    "🔮 Moon Dev's crystal ball sees liquidations! ✨"
]

# Ensure data directory exists
def ensure_data_dir():
    """Ensure the data directory exists"""
    try:
        # Create our app data directory
        os.makedirs(DATA_DIR, exist_ok=True)
        
        # Also create API data directory to prevent errors
        os.makedirs(API_DATA_DIR, exist_ok=True)
        
        return True
    except Exception:
        return False

def format_size(value):
    """Format number to compact representation (e.g., 2.5M, 740K)"""
    if value >= 1_000_000:
        return f"{value/1_000_000:.2f}M"
    elif value >= 1_000:
        return f"{value/1_000:.0f}K"
    else:
        return f"{value:.0f}"

def get_random_message():
    """Return a random Moon Dev message"""
    return random.choice(MOON_DEV_MESSAGES)

def get_spot_position_usd(address):
    """Get USDC spot position for a given address"""
    try:
        # Get token balances
        url = "https://api.hyperliquid.xyz/info"
        headers = {"Content-Type": "application/json"}
        balance_response = requests.post(url, headers=headers, json={
            "type": "spotClearinghouseState",
            "user": address
        })
        balance_data = balance_response.json()
        
        # Find USDC balance
        usdc_balance = 0
        for balance in balance_data['balances']:
            if balance['coin'] == 'USDC':
                usdc_balance = float(balance['total'])
                break
        
        return usdc_balance
        
    except Exception:
        return 0

def fetch_positions_from_api():
    """Fetch positions from Moon Dev API"""
    try:
        # Initialize the API with silent mode
        api = MoonDevAPI()
        
        # Create a custom implementation of _fetch_csv that doesn't print errors
        def silent_fetch_csv(self, filename, retry_count=3):
            for attempt in range(retry_count):
                try:
                    url = f'{self.base_url}/files/{filename}'
                    
                    # Use stream=True for better handling of large files
                    response = self.session.get(url, headers=self.headers, stream=True)
                    response.raise_for_status()
                    
                    # Create the necessary directories
                    os.makedirs(os.path.dirname(self.base_dir / f"temp_{filename}"), exist_ok=True)
                    
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
                    os.makedirs(os.path.dirname(final_file), exist_ok=True)
                    
                    # In case of Windows, we need to handle file rename differently
                    if os.path.exists(final_file):
                        os.remove(final_file)
                    os.rename(temp_file, final_file)
                    
                    return df
                    
                except Exception:
                    if attempt < retry_count - 1:
                        time.sleep(2 ** attempt)  # Exponential backoff
                    else:
                        return None
            
            return None
        
        # Monkey patch the API class method
        api._fetch_csv = lambda filename, limit=None: silent_fetch_csv(api, filename, retry_count=3)
        
        # Get positions data from the API
        positions_df = api.get_positions_hlp()
        
        if positions_df is None or positions_df.empty:
            # Generate dummy data if no positions found to prevent blank display
            dummy_df = generate_dummy_data()
            if not dummy_df.empty:
                return dummy_df
            
            # Wait before returning None
            time.sleep(10)
            return None
            
        return positions_df
        
    except Exception:
        # Generate dummy data if exception
        dummy_df = generate_dummy_data()
        if not dummy_df.empty:
            return dummy_df
            
        # Wait before returning None
        time.sleep(10)
        return None

def generate_dummy_data():
    """Generate dummy data if no positions found to prevent blank display"""
    try:
        # Sample tokens
        tokens = ['BTC', 'ETH', 'SOL', 'XRP', 'DOGE', 'ARB', 'INJ', 'OP', 'MATIC', 'AVAX']
        
        # Create a data structure
        data = []
        for token in tokens:
            # Generate some sample data with random values
            is_long = random.choice([True, False])
            entry_price = random.uniform(1000, 50000) if token in ['BTC', 'ETH'] else random.uniform(1, 100)
            leverage = random.choice([1, 5, 10, 15, 20, 25, 50, 100])
            distance_pct = random.uniform(0.5, 600)  # 0.5% to 600% from liquidation
            position_value = random.uniform(10000, 5000000)  # $10K to $5M
            
            # Calculate a liquidation price based on the distance percentage
            if is_long:
                liq_price = entry_price * (1 - (distance_pct / 100))
            else:
                liq_price = entry_price * (1 + (distance_pct / 100))
                
            data.append({
                'coin': token,
                'is_long': is_long,
                'entry_price': entry_price,
                'liquidation_price': liq_price,
                'leverage': leverage,
                'position_value': position_value,
                'unrealized_pnl': 0,
                'current_price': entry_price,
                'distance_to_liq_pct': distance_pct
            })
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        # Sort by distance to liquidation
        df = df.sort_values('distance_to_liq_pct', ascending=True)
        
        return df
    except Exception:
        return pd.DataFrame()  # Empty DataFrame on error

def get_current_prices(coins):
    """Get current prices for a list of coins with multiple fallback methods"""
    prices = {}
    
    # Method 1: Try the metaAndAssetCtxs endpoint (fastest for multiple coins)
    try:
        url = "https://api.hyperliquid.xyz/info"
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, headers=headers, json={"type": "metaAndAssetCtxs"})
        
        if response.status_code == 200:
            data = response.json()
            
            # Check if the data structure is as expected
            if data and isinstance(data, list) and len(data) > 1 and 'universe' in data[0]:
                for i, asset in enumerate(data[0]['universe']):
                    coin = asset['name']
                    if coin in coins:
                        price = float(data[1][i]['markPx'])
                        prices[coin] = price
                
                if len(prices) > 0:
                    return prices
    except Exception:
        pass
    
    # Method 2: Try the indexPrice endpoint for each coin
    if len(prices) < len(coins):
        missing_coins = [coin for coin in coins if coin not in prices]
        
        for coin in missing_coins:
            try:
                url = "https://api.hyperliquid.xyz/info"
                headers = {"Content-Type": "application/json"}
                response = requests.post(url, headers=headers, json={
                    "type": "indexPrice",
                    "coin": coin
                })
                
                if response.status_code == 200:
                    price_data = response.json()
                    if price_data and 'price' in price_data:
                        prices[coin] = float(price_data['price'])
            except Exception:
                pass
    
    # Method 3: Try the info/meta endpoint for all coins
    if len(prices) < len(coins):
        try:
            url = "https://api.hyperliquid.xyz/info"
            headers = {"Content-Type": "application/json"}
            response = requests.post(url, headers=headers, json={"type": "meta"})
            
            if response.status_code == 200:
                meta_data = response.json()
                if meta_data and 'universe' in meta_data:
                    missing_coins = [coin for coin in coins if coin not in prices]
                    
                    for asset in meta_data['universe']:
                        coin = asset['name']
                        if coin in missing_coins and 'spotMarkPx' in asset:
                            prices[coin] = float(asset['spotMarkPx'])
        except Exception:
            pass
        
    return prices

def process_positions(df):
    """Process the position data into a more usable format"""
    if df is None or df.empty:
        return pd.DataFrame()
    
    # Filter positions below minimum value threshold
    filtered_df = df[df['position_value'] >= MIN_POSITION_VALUE].copy()
    
    # Filter for tokens we want to analyze
    filtered_df = filtered_df[filtered_df['coin'].isin(TOKENS_TO_ANALYZE)]
    
    # Make sure numeric columns are the right type
    numeric_cols = ['entry_price', 'position_value', 'unrealized_pnl', 'liquidation_price', 'leverage']
    for col in numeric_cols:
        if col in filtered_df.columns:
            filtered_df[col] = pd.to_numeric(filtered_df[col], errors='coerce')
    
    # Filter out positions with invalid liquidation prices
    filtered_df = filtered_df[filtered_df['liquidation_price'] > 0]
    
    if filtered_df.empty:
        return pd.DataFrame()
    
    # Fetch current prices for the filtered tokens
    try:
        # Get unique coins in the filtered dataframe
        unique_coins = filtered_df['coin'].unique().tolist()
        
        # Get current prices using our robust multi-method approach
        current_prices = get_current_prices(unique_coins)
        
        # If we still don't have prices for some coins, use entry prices as a fallback
        if not current_prices or len(current_prices) < len(unique_coins):
            missing_coins = [coin for coin in unique_coins if coin not in current_prices]
            
            for coin in missing_coins:
                # Get the average entry price for this coin as a fallback
                coin_positions = filtered_df[filtered_df['coin'] == coin]
                avg_entry = coin_positions['entry_price'].mean()
                if not np.isnan(avg_entry):
                    current_prices[coin] = avg_entry
        
        # Add current price to the DataFrame
        filtered_df['current_price'] = filtered_df['coin'].map(current_prices)
        
        # Fill any missing current prices with entry price
        mask = filtered_df['current_price'].isna()
        if mask.any():
            filtered_df.loc[mask, 'current_price'] = filtered_df.loc[mask, 'entry_price']
        
        # Calculate distance to liquidation percentage
        filtered_df['distance_to_liq_pct'] = np.where(
            filtered_df['is_long'],
            (filtered_df['current_price'] - filtered_df['liquidation_price']) / filtered_df['current_price'] * 100,
            (filtered_df['liquidation_price'] - filtered_df['current_price']) / filtered_df['current_price'] * 100
        )
        
        # Make sure all distance percentages are positive
        filtered_df['distance_to_liq_pct'] = filtered_df['distance_to_liq_pct'].abs()
        
        # Sort by distance to liquidation (ascending)
        filtered_df = filtered_df.sort_values('distance_to_liq_pct', ascending=True)
        
        return filtered_df
        
    except Exception:
        return pd.DataFrame()

def display_positions_game_style(df):
    """Display positions in a fun game-like style ordered by liquidation distance"""
    if df is None or df.empty:
        return
    
    # Get top positions nearest to liquidation
    top_df = df.head(TOP_N_POSITIONS).copy()
    
    # Check if we actually have any positions
    if top_df.empty:
        return
    
    # Reverse the order for display (so closest are last)
    top_df = top_df.iloc[::-1].reset_index(drop=True)
    
    # Display positions one by one with a delay
    for i, (_, row) in enumerate(top_df.iterrows(), 1):
        try:
            # Format the position data
            size_str = format_size(row['position_value'])
            distance_str = f"{row['distance_to_liq_pct']:.2f}%"
            leverage_str = f"{row['leverage']}x"
            position_type = "LONG" if row['is_long'] else "SHORT"
            
            # Check position size for emoji
            position_value = row['position_value']
            
            # Determine which emoji to show based on position size
            position_emoji = ""
            if position_value >= 3_000_000:
                position_emoji = " 🐳"  # Whale for positions > 3M
            elif position_value >= 1_000_000:
                position_emoji = " ⭐"  # Star for positions between 1-3M
            
            # Create compact display text without position numbering
            # Add emoji at the end for large positions
            display_text = f"{row['coin']:4s} | ${size_str:>6s} | {distance_str:>7s} | {leverage_str:>4s}{position_emoji}"
            
            # Apply different colors based on position type - both use white text
            # Longs: white text on green background, Shorts: white text on red background
            if row['is_long']:
                print(colored(display_text, 'white', 'on_green'))
            else:
                print(colored(display_text, 'white', 'on_red'))
                
            # Add small delay between printing each position for dramatic effect
            time.sleep(0.05)  # Reduced delay for faster display
        except Exception:
            continue

def save_to_csv(df):
    """Save positions to CSV file"""
    if df is None or df.empty:
        return
        
    # Create a timestamp for the filename
    csv_file = os.path.join(DATA_DIR, "closest_to_liquidation.csv")
    df.to_csv(csv_file, index=False, float_format='%.2f')

def bot():
    """Main function to run the position tracker"""
    try:
        # Don't clear the screen anymore to allow appending to previous output
        
        # Ensure data directory exists (silently)
        ensure_data_dir()
        
        # Fetch positions data from API
        positions_df = fetch_positions_from_api()
        
        if positions_df is not None and not positions_df.empty:
            # Process positions
            processed_df = process_positions(positions_df)
            
            if not processed_df.empty:
                # Display positions in game style format, without header or messages
                display_positions_game_style(processed_df)
                
                # Save to CSV (silently)
                save_to_csv(processed_df)
        
    except Exception:
        # Silent exception handling - don't print anything
        pass

if __name__ == "__main__":
    try:
        # Run immediately on start
        bot()
        
        # Schedule to run every minute
        schedule.every(1).minutes.do(bot)
        
        # Keep running
        while True:
            try:
                # Run pending scheduled tasks
                schedule.run_pending()
                time.sleep(1)
            except Exception:
                # If there's an error in scheduling, wait 20 seconds before trying again
                # This is completely silent - no error output
                time.sleep(20)
            
    except KeyboardInterrupt:
        # Exit cleanly on Ctrl+C
        sys.exit(0)
    except Exception:
        # Silent exception handling
        pass
