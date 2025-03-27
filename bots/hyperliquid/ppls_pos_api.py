'''
🌙 Moon Dev's Hyperliquid Position Tracker (API Version) 🚀
Built with love by Moon Dev 🌙 ✨

This script uses the Moon Dev API to get pre-collected Hyperliquid positions data
and performs analysis to identify whale positions and liquidation risks.

Unlike ppls_positions.py, this version doesn't query Hyperliquid directly,
but instead uses centralized data already collected by the Moon Dev API.

disclaimer: this is not financial advice and there is no guarantee of any kind. use at your own risk.
'''

import os
import json
import time
import pandas as pd
import numpy as np
from datetime import datetime
import colorama
from colorama import Fore, Back, Style
import nice_funcs as n  # Import directly from the same directory
import argparse
import sys
import traceback
import random
from termcolor import colored
import schedule  # Add import for scheduler

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from api import MoonDevAPI  # Import MoonDevAPI from the root directory

# Initialize colorama for terminal colors
colorama.init(autoreset=True)

# Configure pandas to display numbers with commas and no scientific notation
pd.set_option('display.float_format', '{:.2f}'.format)  # No dollar sign
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)

# Moon Dev ASCII Art Banner
MOON_DEV_BANNER = f"""{Fore.CYAN}
   __  ___                    ____           
  /  |/  /___  ____  ____    / __ \___  _  __
 / /|_/ / __ \/ __ \/ __ \  / / / / _ \| |/_/
/ /  / / /_/ / /_/ / / / / / /_/ /  __/>  <  
/_/  /_/\____/\____/_/ /_(_)____/\___/_/|_|  
                                             
{Fore.MAGENTA}🚀 Hyperliquid Position Tracker API Edition 🌙{Fore.RESET}
"""

# Fun Moon Dev quotes
MOON_DEV_QUOTES = [
    "Tracking whales like a boss! 🐋",
    "Liquidations incoming... maybe! 💥",
    "Moon Dev API - making data fun again! 🎯",
    "To the moon! 🚀 (not financial advice)",
    "Who needs sleep when you have APIs? 😴",
    "Whales move markets, so track the whales! 🐳",
    "Moon Dev sees all the positions... 👀",
    "Diamond hands or liquidation lands? 💎",
    "Watch the whales, follow the money! 💰",
    "API-powered alpha at your fingertips! ✨"
]

# ===== CONFIGURATION =====
DATA_DIR = "bots/hyperliquid/data/ppls_positions_api"  # Directory path, not file path
MIN_POSITION_VALUE = 25000  # Only track positions with value >= $25,000
TOP_N_POSITIONS = 25  # Number of top positions to display

# List of tokens to analyze for positions closest to liquidation
TOKENS_TO_ANALYZE = ['BTC', 'ETH', 'WIF', 'SOL', 'FARTCOIN', 'BNB']

# Highlight threshold for positions
HIGHLIGHT_THRESHOLD = 2000000  # $2 million

def get_random_quote():
    """Return a random Moon Dev quote"""
    return random.choice(MOON_DEV_QUOTES)

def ensure_data_dir():
    """Ensure the data directory exists"""
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        print(f"{Fore.CYAN}🌙 Moon Dev says: {Fore.GREEN}Data directory ready at {DATA_DIR} 🚀")
        print(f"{Fore.MAGENTA}💫 Thanks for using Moon Dev's API-powered tools! 💫")
    except Exception as e:
        print(f"{Fore.RED}⚠️ Error creating directory: {str(e)}")
        return False
    return True

def display_top_individual_positions(df, n=TOP_N_POSITIONS):
    """
    Display top individual long and short positions
    """
    if df is None or df.empty:
        print(f"{Fore.RED}No positions to display!")
        return None, None
    
    # Create a copy to avoid modifying the original
    display_df = df.copy()
    
    # Validate position types for positions with valid liquidation prices
    valid_liq_df = display_df[display_df['liquidation_price'] > 0].copy()
    if not valid_liq_df.empty:
        # Verify if the position type matches the relationship between entry and liquidation price
        valid_liq_df['position_type_verified'] = np.where(
            valid_liq_df['is_long'],
            valid_liq_df['liquidation_price'] < valid_liq_df['entry_price'],  # Long should have liq price < entry
            valid_liq_df['liquidation_price'] > valid_liq_df['entry_price']   # Short should have liq price > entry
        )
        
        # Count inconsistencies
        inconsistent_positions = valid_liq_df[~valid_liq_df['position_type_verified']]
        
        if len(inconsistent_positions) > 0:
            print(f"{Fore.YELLOW}⚠️ Note: Some positions being displayed have been reclassified based on their liquidation prices.")
            
            # Create a corrected position type column based on liquidation vs entry price
            valid_liq_df['is_long_corrected'] = valid_liq_df['liquidation_price'] < valid_liq_df['entry_price']
            
            # Update the is_long column with corrected values
            valid_liq_df['is_long'] = valid_liq_df['is_long_corrected']
            
            # Update the display dataframe with corrected position types
            display_df.loc[valid_liq_df.index, 'is_long'] = valid_liq_df['is_long']
    
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
        return None, None, None
    
    print(f"\n{Fore.CYAN}{'='*120}")
    print(f"{Fore.CYAN}{'='*35} 🔥 POSITIONS CLOSEST TO LIQUIDATION 🔥 {'='*35}")
    print(f"{Fore.CYAN}{'='*120}")
    
    # Create a copy to avoid modifying the original
    risk_df = df.copy()
    
    # Filter out positions with invalid liquidation prices
    risk_df = risk_df[risk_df['liquidation_price'] > 0]
    
    if risk_df.empty:
        print(f"{Fore.YELLOW}No positions with valid liquidation prices found!")
        return None, None, None
    
    # Filter risk_df to only include tokens in TOKENS_TO_ANALYZE
    risk_df = risk_df[risk_df['coin'].isin(TOKENS_TO_ANALYZE)]

    # Fetch current prices for tokens in TOKENS_TO_ANALYZE once
    unique_coins = risk_df['coin'].unique()
    current_prices = {coin: n.get_current_price(coin) for coin in unique_coins}
    print(f"{Fore.CYAN}🔍 Fetching current prices for: {', '.join(unique_coins)}")
    for coin, price in current_prices.items():
        print(f"{Fore.YELLOW}💰 Current price for {coin}: ${price:,.2f}")

    # Add current price to the DataFrame
    risk_df['current_price'] = risk_df['coin'].map(current_prices)
    
    # Calculate standardized distance to liquidation using current price
    risk_df['distance_to_liq_pct'] = np.where(
        risk_df['is_long'],
        abs((risk_df['current_price'] - risk_df['liquidation_price']) / risk_df['current_price'] * 100),
        abs((risk_df['liquidation_price'] - risk_df['current_price']) / risk_df['current_price'] * 100)
    )

    # Correct position type based on liquidation price
    risk_df['is_long_corrected'] = risk_df['liquidation_price'] < risk_df['entry_price']
    risk_df['is_long'] = risk_df['is_long_corrected']

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
            highlight = row['position_value'] > HIGHLIGHT_THRESHOLD
            display_text = f"{Fore.GREEN}#{i} {Fore.YELLOW}{row['coin']} {Fore.GREEN}${row['position_value']:,.2f} " + \
                           f"{Fore.BLUE}| Entry: ${row['entry_price']:,.2f} " + \
                           f"{Fore.RED}| Liq: ${row['liquidation_price']:,.2f} " + \
                           f"{Fore.MAGENTA}| Current: ${row['current_price']:,.2f} " + \
                           f"{Fore.MAGENTA}| Distance: {row['distance_to_liq_pct']:.2f}% " + \
                           f"{Fore.CYAN}| Leverage: {row['leverage']}x"
            if highlight:
                # Use darker colors on yellow background for better readability
                display_text = colored(f"#{i} {row['coin']} ${row['position_value']:,.2f} " + \
                               f"| Entry: ${row['entry_price']:,.2f} " + \
                               f"| Liq: ${row['liquidation_price']:,.2f} " + \
                               f"| Current: ${row['current_price']:,.2f} " + \
                               f"| Distance: {row['distance_to_liq_pct']:.2f}% " + \
                               f"| Leverage: {row['leverage']}x", 'black', 'on_yellow')
            print(display_text)
            print(f"{Fore.CYAN}   Address: {row['address']}")
    else:
        print(f"{Fore.YELLOW}No long positions with liquidation prices found!")
    
    # Display positions closest to liquidation - SHORTS
    print(f"\n{Fore.RED}{Style.BRIGHT}💥 TOP {TOP_N_POSITIONS} SHORT POSITIONS CLOSEST TO LIQUIDATION 📉")
    print(f"{Fore.RED}{'-'*120}")
    
    if len(risky_shorts) > 0:
        for i, (_, row) in enumerate(risky_shorts.head(TOP_N_POSITIONS).iterrows(), 1):
            highlight = row['position_value'] > HIGHLIGHT_THRESHOLD
            display_text = f"{Fore.RED}#{i} {Fore.YELLOW}{row['coin']} {Fore.RED}${row['position_value']:,.2f} " + \
                           f"{Fore.BLUE}| Entry: ${row['entry_price']:,.2f} " + \
                           f"{Fore.RED}| Liq: ${row['liquidation_price']:,.2f} " + \
                           f"{Fore.MAGENTA}| Current: ${row['current_price']:,.2f} " + \
                           f"{Fore.MAGENTA}| Distance: {row['distance_to_liq_pct']:.2f}% " + \
                           f"{Fore.CYAN}| Leverage: {row['leverage']}x"
            if highlight:
                # Use darker colors on yellow background for better readability
                display_text = colored(f"#{i} {row['coin']} ${row['position_value']:,.2f} " + \
                               f"| Entry: ${row['entry_price']:,.2f} " + \
                               f"| Liq: ${row['liquidation_price']:,.2f} " + \
                               f"| Current: ${row['current_price']:,.2f} " + \
                               f"| Distance: {row['distance_to_liq_pct']:.2f}% " + \
                               f"| Leverage: {row['leverage']}x", 'black', 'on_yellow')
            print(display_text)
            print(f"{Fore.CYAN}   Address: {row['address']}")
    else:
        print(f"{Fore.YELLOW}No short positions with liquidation prices found!")
    
    # Print footer
    print(f"\n{Fore.CYAN}{'='*120}")
    print(f"{Fore.CYAN}{'='*30} 🌙 Moon Dev Liquidation Tracker - Trade Safely! 🚀 {'='*30}")
    print(f"{Fore.CYAN}{'='*120}")
    
    return risky_longs.head(TOP_N_POSITIONS), risky_shorts.head(TOP_N_POSITIONS), current_prices

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

def process_positions(df, coin_filter=None):
    """
    Process the position data into a more usable format, filtering positions below min value
    and optionally by coin
    """
    if df is None or df.empty:
        print(f"{Fore.RED}No positions data to process!")
        return pd.DataFrame()
    
    print(f"{Fore.CYAN}🔍 Processing {len(df)} positions...")
    print(f"{Fore.YELLOW}🪄 {get_random_quote()}")
    
    # Filter positions below minimum value threshold
    filtered_df = df[df['position_value'] >= MIN_POSITION_VALUE].copy()
    
    # Make sure numeric columns are the right type
    numeric_cols = ['entry_price', 'position_value', 'unrealized_pnl', 'liquidation_price', 'leverage']
    for col in numeric_cols:
        if col in filtered_df.columns:
            filtered_df[col] = pd.to_numeric(filtered_df[col], errors='coerce')
    
    # Convert boolean columns if needed
    if 'is_long' in filtered_df.columns and filtered_df['is_long'].dtype != bool:
        filtered_df['is_long'] = filtered_df['is_long'].map({'True': True, 'False': False}) 
        # If it's stored as strings like 'True' and 'False'
    
    # Validate position types for positions with valid liquidation prices
    valid_liq_df = filtered_df[filtered_df['liquidation_price'] > 0].copy()
    if not valid_liq_df.empty:
        # Verify if the position type matches the relationship between entry and liquidation price
        valid_liq_df['position_type_verified'] = np.where(
            valid_liq_df['is_long'],
            valid_liq_df['liquidation_price'] < valid_liq_df['entry_price'],  # Long should have liq price < entry
            valid_liq_df['liquidation_price'] > valid_liq_df['entry_price']   # Short should have liq price > entry
        )
        
        # Count inconsistencies
        inconsistent_positions = valid_liq_df[~valid_liq_df['position_type_verified']]
        
        if len(inconsistent_positions) > 0:
            print(f"{Fore.RED}⚠️ WARNING: Found {len(inconsistent_positions)} positions with inconsistent position types!")
            print(f"{Fore.RED}⚠️ For long positions, liquidation price should be LOWER than entry price.")
            print(f"{Fore.RED}⚠️ For short positions, liquidation price should be HIGHER than entry price.")
            print(f"{Fore.YELLOW}🔧 Correcting position types based on liquidation vs. entry price relationships...")
            
            # Create a corrected position type column based on liquidation vs entry price
            valid_liq_df['is_long_corrected'] = valid_liq_df['liquidation_price'] < valid_liq_df['entry_price']
            
            # Update the is_long column with corrected values
            valid_liq_df['is_long'] = valid_liq_df['is_long_corrected']
            
            # Update the filtered dataframe with corrected position types
            filtered_df.loc[valid_liq_df.index, 'is_long'] = valid_liq_df['is_long']
            
            print(f"{Fore.GREEN}✅ Position types corrected!")
    
    # Filter by coin if specified
    if coin_filter:
        coin_filter = coin_filter.upper()  # Convert to uppercase for case-insensitive matching
        filtered_df = filtered_df[filtered_df['coin'] == coin_filter]
        print(f"{Fore.MAGENTA}🪙 Filtering for {coin_filter} positions only")
        print(f"{Fore.MAGENTA}🔍 Found {len(filtered_df)} {coin_filter} positions with value >= ${MIN_POSITION_VALUE:,}")
    
    print(f"{Fore.GREEN}✅ Processed {len(filtered_df)} positions after filtering (min value: ${MIN_POSITION_VALUE:,})")
    return filtered_df

def save_positions_to_csv(df, current_prices=None):
    """
    Save all positions to a CSV file and create aggregated views
    """
    if df is None or df.empty:
        print(f"{Fore.RED}🌙 Moon Dev says: No positions found to save! 😢")
        return None, None
    
    # Format numeric columns
    numeric_cols = ['entry_price', 'position_value', 'unrealized_pnl', 'liquidation_price', 'leverage']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Save all positions
    positions_file = os.path.join(DATA_DIR, "all_positions.csv")
    df.to_csv(positions_file, index=False, float_format='%.2f')
    print(f"{Fore.GREEN}🌙 Moon Dev says: Saved {len(df)} positions to {positions_file} 🚀")
    
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
    risky_longs_df, risky_shorts_df, fetched_prices = display_risk_metrics(df)
    
    # Save liquidation risk positions to CSV
    save_liquidation_risk_to_csv(risky_longs_df, risky_shorts_df)

    # Check if we have current prices from the risk metrics function
    if current_prices is None:
        current_prices = fetched_prices
    
    # Check if we still need to get prices (should never happen as display_risk_metrics has already fetched them)
    if current_prices is None:
        # Fetch current prices for tokens in TOKENS_TO_ANALYZE only if needed
        print(f"{Fore.YELLOW}🔍 No current prices available, fetching now...")
        unique_coins = df[df['coin'].isin(TOKENS_TO_ANALYZE)]['coin'].unique()
        current_prices = {coin: n.get_current_price(coin) for coin in unique_coins}
        for coin, price in current_prices.items():
            print(f"{Fore.YELLOW}💰 Current price for {coin}: ${price:,.2f}")

    # Use current prices for liquidation impact analysis
    print(f"\n{Fore.CYAN}{'='*120}")
    print(f"{Fore.CYAN}{'='*35} 💥 LIQUIDATION IMPACT FOR 3% PRICE MOVE 💥 {'='*35}")
    print(f"{Fore.CYAN}{'='*120}")

    # Initialize dictionaries to track liquidation values
    total_long_liquidations = {}
    total_short_liquidations = {}
    all_long_liquidations = 0
    all_short_liquidations = 0
    
    for coin in TOKENS_TO_ANALYZE:
        if coin not in current_prices:
            print(f"{Fore.YELLOW}⚠️ No price data for {coin}, skipping...")
            continue
            
        # Filter positions for the current coin
        coin_positions = df[df['coin'] == coin].copy()
        if coin_positions.empty:
            print(f"{Fore.YELLOW}⚠️ No positions found for {coin}, skipping...")
            continue

        # Add current price to the coin positions DataFrame
        current_price = current_prices[coin]
        coin_positions['current_price'] = current_price
        
        # Calculate 3% price move
        coin_positions['price_move'] = coin_positions['current_price'] * 0.03

        # Calculate potential liquidations for long positions
        long_liquidations = coin_positions[(coin_positions['is_long']) &
                                         (coin_positions['liquidation_price'] >= coin_positions['current_price'] - coin_positions['price_move'])]
        total_long_liquidation_value = long_liquidations['position_value'].sum()
        long_price_after_move = current_price - (current_price * 0.03)

        # Calculate potential liquidations for short positions
        short_liquidations = coin_positions[(~coin_positions['is_long']) &
                                          (coin_positions['liquidation_price'] <= coin_positions['current_price'] + coin_positions['price_move'])]
        total_short_liquidation_value = short_liquidations['position_value'].sum()
        short_price_after_move = current_price + (current_price * 0.03)

        # Store liquidation values in dictionary
        total_long_liquidations[coin] = total_long_liquidation_value
        total_short_liquidations[coin] = total_short_liquidation_value
        
        # Add to total liquidations
        all_long_liquidations += total_long_liquidation_value
        all_short_liquidations += total_short_liquidation_value

        # Display results
        print(f"{Fore.GREEN}{coin} Long Liquidations (3% move DOWN to ${long_price_after_move:,.2f}): ${total_long_liquidation_value:,.2f}")
        print(f"{Fore.RED}{coin} Short Liquidations (3% move UP to ${short_price_after_move:,.2f}): ${total_short_liquidation_value:,.2f}")

    # Display summary of total liquidations
    print(f"\n{Fore.CYAN}{'='*120}")
    print(f"{Fore.CYAN}{'='*35} 💰 TOTAL LIQUIDATION SUMMARY 💰 {'='*35}")
    print(f"{Fore.CYAN}{'='*120}")
    print(f"{Fore.GREEN}Total Long Liquidations (3% move DOWN): ${all_long_liquidations:,.2f}")
    print(f"{Fore.RED}Total Short Liquidations (3% move UP): ${all_short_liquidations:,.2f}")
    
    # Generate trading recommendations based on liquidation imbalance
    print(f"\n{Fore.CYAN}{'='*120}")
    print(f"{Fore.CYAN}{'='*35} 🚀 TRADING RECOMMENDATIONS 🚀 {'='*35}")
    print(f"{Fore.CYAN}{'='*120}")
    
    # Overall market recommendation
    if all_long_liquidations > all_short_liquidations:
        recommendation = f"MARKET RECOMMENDATION: SHORT THE MARKET (${all_long_liquidations:,.2f} long liquidations at risk within a 3% move of current price)"
        print(f"{Back.GREEN}{Fore.BLACK}{Style.BRIGHT}{recommendation}{Style.RESET_ALL}")
    else:
        recommendation = f"MARKET RECOMMENDATION: LONG THE MARKET (${all_short_liquidations:,.2f} short liquidations at risk within a 3% move of current price)"
        print(f"{Back.GREEN}{Fore.BLACK}{Style.BRIGHT}{recommendation}{Style.RESET_ALL}")
    
    # Individual coin recommendations
    print(f"\n{Fore.CYAN}{'='*30} INDIVIDUAL COIN RECOMMENDATIONS {'='*30}")
    
    # Sort coins by liquidation imbalance (largest difference first)
    liquidation_imbalance = {}
    for coin in total_long_liquidations.keys():
        if coin in total_short_liquidations:
            liquidation_imbalance[coin] = abs(total_long_liquidations[coin] - total_short_liquidations[coin])
    
    sorted_coins = sorted(liquidation_imbalance.keys(), key=lambda x: liquidation_imbalance[x], reverse=True)
    
    for coin in sorted_coins:
        long_liq = total_long_liquidations[coin]
        short_liq = total_short_liquidations[coin]
        
        # Only show recommendations for coins with significant liquidation risk
        if long_liq < 10000 and short_liq < 10000:
            continue
            
        if long_liq > short_liq:
            rec = f"{coin}: SHORT (${long_liq:,.2f} long liquidations vs ${short_liq:,.2f} short within a 3% move)"
            print(f"{Back.GREEN}{Fore.BLACK}{Style.BRIGHT}{rec}{Style.RESET_ALL}")
        else:
            rec = f"{coin}: LONG (${short_liq:,.2f} short liquidations vs ${long_liq:,.2f} long within a 3% move)"
            print(f"{Back.GREEN}{Fore.BLACK}{Style.BRIGHT}{rec}{Style.RESET_ALL}")
    
    print(f"\n{Fore.MAGENTA}💡 Trading strategy: Target coins with largest liquidation imbalance for potential cascade liquidations")
    print(f"{Fore.YELLOW}⚠️ Moon Dev says: Always use proper risk management! Liquidation hunting is high-risk trading!")

    print(f"{Fore.CYAN}{'='*80}")
    print(f"{Fore.CYAN}{'='*20} 🌙 Moon Dev Liquidation Impact Analysis Complete! 🚀 {'='*20}")
    
    return df, agg_df

def fetch_positions_from_api():
    """
    Fetch positions from Moon Dev API
    """
    try:
        print(f"{Fore.CYAN}🌙 Moon Dev API: {Fore.GREEN}Fetching HLP positions data... 🚀")
        print(f"{Fore.YELLOW}🧙‍♂️ Summoning the power of Moon Dev's API... please wait!")
        
        # Initialize the API
        api = MoonDevAPI()
        
        # Get positions data from the API
        positions_df = api.get_positions_hlp()
        
        if positions_df is None or positions_df.empty:
            print(f"{Fore.RED}❌ No positions data received from API!")
            return None
            
        print(f"{Fore.GREEN}✅ Successfully fetched {len(positions_df)} positions from Moon Dev API! 🎉")
        print(f"{Fore.CYAN}🌟 Moon Dev's API has delivered the whale data! Ready to analyze! 🐋")

        # Debug: Print the first few rows of the DataFrame to verify data mapping
        print(f"{Fore.CYAN}🔍 Debug: First few rows of positions data:")
        print(positions_df.head())

        # Debug: Print column names to ensure correct mapping
        print(f"{Fore.CYAN}🔍 Debug: Column names in positions data:")
        print(positions_df.columns)

        return positions_df
        
    except Exception as e:
        print(f"{Fore.RED}❌ Error fetching positions: {str(e)}")
        print(f"{Fore.RED}📋 Stack trace:\n{traceback.format_exc()}")
        return None

def fetch_aggregated_positions_from_api():
    """
    Fetch aggregated positions from Moon Dev API
    """
    try:
        print(f"{Fore.CYAN}🌙 Moon Dev API: {Fore.GREEN}Fetching aggregated HLP positions data... 🚀")
        print(f"{Fore.YELLOW}⚡ Moon Dev's API working its magic... ⚡")
        
        # Initialize the API
        api = MoonDevAPI()
        
        # Get aggregated positions data from the API
        agg_positions_df = api.get_agg_positions_hlp()
        
        if agg_positions_df is None or agg_positions_df.empty:
            print(f"{Fore.RED}❌ No aggregated positions data received from API!")
            return None
            
        print(f"{Fore.GREEN}✅ Successfully fetched {len(agg_positions_df)} aggregated positions from Moon Dev API! 🎯")
        print(f"{Fore.CYAN}🔮 Moon Dev's crystal ball has revealed the market trends! 📊")
        return agg_positions_df
        
    except Exception as e:
        print(f"{Fore.RED}❌ Error fetching aggregated positions: {str(e)}")
        print(f"{Fore.RED}📋 Stack trace:\n{traceback.format_exc()}")
        return None

def bot():
    """Main function to run the position tracker (renamed from main to bot)"""
    # Use global configuration variables
    global MIN_POSITION_VALUE, TOP_N_POSITIONS
    
    # Display Moon Dev banner
    print(MOON_DEV_BANNER)
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="🌙 Moon Dev's Hyperliquid Whale Position Tracker (API Version)")
    parser.add_argument('--min-value', type=int, default=MIN_POSITION_VALUE, 
                        help=f'Minimum position value to consider (default: ${MIN_POSITION_VALUE:,})')
    parser.add_argument('--top-n', type=int, default=TOP_N_POSITIONS,
                        help=f'Number of top positions to display (default: {TOP_N_POSITIONS})')
    parser.add_argument('--agg-only', action='store_true',
                        help='Only show aggregated data (faster, less detailed)')
    parser.add_argument('--coin', type=str, default=None,
                        help='Filter positions by coin (e.g., BTC, ETH, SOL)')
    parser.add_argument('--verify-positions', action='store_true', default=True,
                        help='Verify and correct position types based on liquidation prices')
    args = parser.parse_args()
    
    # Update configuration based on arguments
    MIN_POSITION_VALUE = args.min_value
    TOP_N_POSITIONS = args.top_n
    
    start_time = time.time()
    print(f"sup dawg")
    print(f"\n{Fore.CYAN}{'='*80}")
    print(f"{Fore.MAGENTA}{'*'*20} 🌙 Moon Dev's Whale Position Tracker (API Version) 🐋 {'*'*20}")
    print(f"{Fore.CYAN}{'='*80}")
    print(f"{Fore.YELLOW}🚀 Initializing Moon Dev's whale tracking systems... 📡")
    print(f"{Fore.YELLOW}💬 {get_random_quote()}")
    
    # Explain position verification
    if args.verify_positions:
        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"{Fore.CYAN}{'='*25} 📋 POSITION TYPE VERIFICATION INFO 📋 {'='*25}")
        print(f"{Fore.CYAN}{'='*80}")
        print(f"{Fore.YELLOW}ℹ️ This script verifies position types (LONG/SHORT) based on liquidation prices:")
        print(f"{Fore.GREEN}✅ LONG positions: Liquidation price should be LOWER than entry price")
        print(f"{Fore.GREEN}   Example: Entry $100, Liquidation $80 → Price drops, position is liquidated")
        print(f"{Fore.RED}✅ SHORT positions: Liquidation price should be HIGHER than entry price")
        print(f"{Fore.RED}   Example: Entry $100, Liquidation $120 → Price rises, position is liquidated")
        print(f"{Fore.YELLOW}🔍 If position data doesn't match these rules, the script will auto-correct it.")
        print(f"{Fore.CYAN}{'='*80}\n")
    
    # Ensure data directory exists
    ensure_data_dir()
    
    print(f"{Fore.YELLOW}💰 Minimum position value: ${MIN_POSITION_VALUE:,}")
    print(f"{Fore.YELLOW}🔝 Top positions to display: {TOP_N_POSITIONS}")
    if args.coin:
        print(f"{Fore.YELLOW}🪙 Filtering for coin: {args.coin.upper()}")
    print(f"{Fore.CYAN}⭐ Moon Dev API is ready to show you the money! 💸")
    
    # Fetch aggregated positions data first (this is faster)
    agg_df = fetch_aggregated_positions_from_api()
    
    if agg_df is not None:
        # Save aggregated positions
        agg_file = os.path.join(DATA_DIR, "aggregated_positions_from_api.csv")
        agg_df.to_csv(agg_file, index=False, float_format='%.2f')
        print(f"{Fore.GREEN}📊 Saved aggregated positions to {agg_file}")
        print(f"{Fore.CYAN}💾 Moon Dev has blessed your disk with whale data! 🐋")
        
        # Add direction column
        agg_df['direction'] = agg_df['is_long'].apply(lambda x: 'LONG' if x else 'SHORT')
        
        # Filter by coin if specified
        if args.coin:
            coin = args.coin.upper()
            agg_df = agg_df[agg_df['coin'] == coin]
            print(f"{Fore.MAGENTA}🪙 Filtered for {coin} aggregated positions")
            print(f"{Fore.MAGENTA}🔍 Found {len(agg_df)} {coin} aggregated positions")
        
        # Display aggregated summaries
        print(f"\n{Fore.CYAN}{'='*30} AGGREGATED POSITION SUMMARY {'='*30}")
        display_cols = ['coin', 'direction', 'total_value', 'num_traders', 'liquidation_price']
        
        # Temporarily format numbers with commas for display only
        with pd.option_context('display.float_format', '{:,.2f}'.format):
            print(f"{Fore.WHITE}{agg_df[display_cols]}")
            
            print(f"\n{Fore.GREEN}🔝 TOP LONG POSITIONS (AGGREGATED):")
            print(f"{Fore.GREEN}{agg_df[agg_df['is_long']][display_cols].head()}")
            
            print(f"\n{Fore.RED}🔝 TOP SHORT POSITIONS (AGGREGATED):")
            print(f"{Fore.RED}{agg_df[~agg_df['is_long']][display_cols].head()}")
    
    # If not only showing aggregated data, fetch and process detailed positions
    if not args.agg_only:
        # Fetch detailed positions data
        positions_df = fetch_positions_from_api()
        
        if positions_df is not None:
            # Process positions (filter by min value, etc.)
            processed_df = process_positions(positions_df, args.coin)
            
            if not processed_df.empty:
                # Display top individual positions and get the dataframes
                longs_df, shorts_df = display_top_individual_positions(processed_df)
                
                # Save top whale positions to CSV
                save_top_whale_positions_to_csv(longs_df, shorts_df)
                
                # Get risk metrics and current prices in one step
                risky_longs_df, risky_shorts_df, current_prices = display_risk_metrics(processed_df)
                
                # Save liquidation risk positions to CSV
                save_liquidation_risk_to_csv(risky_longs_df, risky_shorts_df)
                
                # Pass the already fetched current prices to save_positions_to_csv
                positions_df, _ = save_positions_to_csv(processed_df, current_prices)
            else:
                print(f"{Fore.RED}⚠️ No positions found after filtering! Try adjusting your filters.")
    
    # Calculate and display execution time
    execution_time = time.time() - start_time
    print(f"{Fore.CYAN}⏱️ Execution time: {execution_time:.2f} seconds ({execution_time/60:.2f} minutes)")
    print(f"{Fore.CYAN}📁 CSV files saved in: {DATA_DIR}")
    print(f"{Fore.MAGENTA}⏰ NEXT RUN SCHEDULED IN 1 MINUTE ⏰")

if __name__ == "__main__":
    # Initial run
    bot()
    
    # Schedule the main function to run every minute
    schedule.every(1).minutes.do(bot)
    
    while True:
        try:
            # Run pending scheduled tasks
            schedule.run_pending()
            time.sleep(1)
        except Exception as e:
            print(f"{Fore.RED}Encountered an error: {e}")
            print(f"{Fore.RED}📋 Stack trace:\n{traceback.format_exc()}")
            # Wait before retrying to avoid rapid error logging
            time.sleep(10)
