'''
🌙 Moon Dev's Hyperliquid Liquidation Hunter Bot 🚀
🎯 Trading strategy: Target coins with largest liquidation imbalance for potential cascade liquidations
🔍 This bot analyzes whale positions to determine market bias (long/short)
💥 Then hunts for liquidation events to enter trades in the direction of the bias

Built with love by Moon Dev 🌙 ✨
disclaimer: this is not financial advice and there is no guarantee of any kind. use at your own risk.
'''

import sys
import os
import time
import schedule
import json
import requests
import pandas as pd
import numpy as np
import traceback
from termcolor import colored
import colorama
from colorama import Fore, Back, Style
from datetime import datetime, timedelta
import pytz
from eth_account.signers.local import LocalAccount
import eth_account
from dotenv import load_dotenv

# Add the parent directory to the Python path so we can import modules from there
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, parent_dir)

# Import local modules
import nice_funcs as n
from api import MoonDevAPI

# Initialize colorama for terminal colors
colorama.init(autoreset=True)

# Load environment variables from .env file
load_dotenv()

# Get the Hyperliquid key from environment variables
HYPER_LIQUID_KEY = os.getenv('HYPER_LIQUID_KEY')

# Moon Dev ASCII Art Banner
MOON_DEV_BANNER = f"""{Fore.CYAN}
   __  ___                    ____           
  /  |/  /___  ____  ____    / __ \___  _  __
 / /|_/ / __ \/ __ \/ __ \  / / / / _ \| |/_/
/ /  / / /_/ / /_/ / / / / / /_/ /  __/>  <  
/_/  /_/\____/\____/_/ /_(_)____/\___/_/|_|  
                                             
{Fore.MAGENTA}🚀 Hyperliquid Liquidation Hunter Bot 🌙{Fore.RESET}
"""

# ===== CONFIGURATION =====
# Symbol to trade
symbol = 'BTC'  # Default symbol, can be changed as needed
LEVERAGE = 5     # Leverage to use for trading
POSITION_SIZE_USD = 10  # Position size in USD

# Constants
LIQUIDATION_LOOKBACK_MINUTES = 5  # Time period to look back for liquidations
LIQUIDATION_TRIGGER_AMOUNT = 100000  # $500k trigger amount for liquidations

# Take profit and stop loss settings
TAKE_PROFIT_PERCENT = 1  # Take profit percentage
STOP_LOSS_PERCENT = -6.0  # Stop loss percentage

# Add these constants near the top with other constants
# ===== CONFIGURATION =====
MIN_POSITION_VALUE = 25000  # Only track positions with value >= $25,000
TOP_N_POSITIONS = 25  # Number of top positions to display
HIGHLIGHT_THRESHOLD = 2000000  # $2 million
TOKENS_TO_ANALYZE = ['BTC', 'ETH', 'WIF', 'SOL', 'FARTCOIN', 'BNB']

# Initialize account
account = LocalAccount = eth_account.Account.from_key(HYPER_LIQUID_KEY)

# Initialize API
api = MoonDevAPI()

# Trading recommendation state
trading_bias = None  # 'long' or 'short'
recommendation_text = "Waiting for initial analysis..."
last_analysis_time = None
ANALYSIS_INTERVAL_MINUTES = 15  # How often to refresh the bias analysis

def print_banner():
    """Print Moon Dev banner with a random quote"""
    print(MOON_DEV_BANNER)
    print(f"{Fore.CYAN}{'='*80}")
    print(f"{Fore.YELLOW}🚀 Moon Dev Liquidation Hunter Bot is starting up! 🎯")
    print(f"{Fore.YELLOW}💰 Trading {symbol} with {LEVERAGE}x leverage")
    print(f"{Fore.YELLOW}💵 Position size: ${POSITION_SIZE_USD} USD")
    print(f"{Fore.CYAN}{'='*80}\n")

def analyze_market():
    """
    Analyze market conditions and set trading bias based on liquidation risk analysis
    """
    global trading_bias, recommendation_text, last_analysis_time
    
    print(f"\n{Fore.CYAN}{'='*80}")
    print(f"{Fore.CYAN}{'='*25} 🔍 MARKET ANALYSIS 🔍 {'='*25}")
    print(f"{Fore.CYAN}{'='*80}")
    
    try:
        # Fetch positions data from Moon Dev API
        print(f"{Fore.YELLOW}🌙 Moon Dev API: Fetching positions data...")
        positions_df = api.get_positions_hlp()
        
        if positions_df is None or positions_df.empty:
            print(f"{Fore.RED}❌ Failed to get positions data from API")
            return False
        
        print(f"{Fore.GREEN}✅ Successfully fetched {len(positions_df)} positions")
        
        # Filter out small positions
        positions_df = positions_df[positions_df['position_value'] >= MIN_POSITION_VALUE].copy()
        print(f"{Fore.GREEN}📊 Found {len(positions_df)} positions after filtering (min value: ${MIN_POSITION_VALUE:,})")
        
        # Convert numeric columns
        numeric_cols = ['entry_price', 'position_value', 'unrealized_pnl', 'liquidation_price', 'leverage']
        for col in numeric_cols:
            if col in positions_df.columns:
                positions_df[col] = pd.to_numeric(positions_df[col], errors='coerce')
        
        # Validate and correct position types
        valid_liq_df = positions_df[positions_df['liquidation_price'] > 0].copy()
        if not valid_liq_df.empty:
            valid_liq_df['is_long_corrected'] = valid_liq_df['liquidation_price'] < valid_liq_df['entry_price']
            valid_liq_df['is_long'] = valid_liq_df['is_long_corrected']
            positions_df.loc[valid_liq_df.index, 'is_long'] = valid_liq_df['is_long']
        
        # Display top individual positions
        print(f"\n{Fore.CYAN}{'='*120}")
        print(f"{Fore.CYAN}{'='*35} 🐳 TOP INDIVIDUAL WHALE POSITIONS 🐳 {'='*35}")
        print(f"{Fore.CYAN}{'='*120}")
        
        # Sort by position value for longs and shorts
        longs = positions_df[positions_df['is_long']].sort_values('position_value', ascending=False)
        shorts = positions_df[~positions_df['is_long']].sort_values('position_value', ascending=False)
        
        # Display top long positions
        print(f"\n{Fore.GREEN}{Style.BRIGHT}🚀 TOP {TOP_N_POSITIONS} INDIVIDUAL LONG POSITIONS 📈")
        print(f"{Fore.GREEN}{'-'*120}")
        
        if len(longs) > 0:
            for i, (_, row) in enumerate(longs.head(TOP_N_POSITIONS).iterrows(), 1):
                liq_price = row['liquidation_price'] if row['liquidation_price'] > 0 else "N/A"
                liq_display = f"${liq_price:,.2f}" if liq_price != "N/A" else "N/A"
                
                print(f"{Fore.GREEN}#{i} {Fore.YELLOW}{row['coin']} {Fore.GREEN}${row['position_value']:,.2f} " + 
                      f"{Fore.BLUE}| Entry: ${row['entry_price']:,.2f} " +
                      f"{Fore.MAGENTA}| PnL: ${row['unrealized_pnl']:,.2f} " +
                      f"{Fore.CYAN}| Leverage: {row['leverage']}x " +
                      f"{Fore.RED}| Liq: {liq_display}")
                print(f"{Fore.CYAN}   Address: {row['address']}")
        
        # Display top short positions
        print(f"\n{Fore.RED}{Style.BRIGHT}💥 TOP {TOP_N_POSITIONS} INDIVIDUAL SHORT POSITIONS 📉")
        print(f"{Fore.RED}{'-'*120}")
        
        if len(shorts) > 0:
            for i, (_, row) in enumerate(shorts.head(TOP_N_POSITIONS).iterrows(), 1):
                liq_price = row['liquidation_price'] if row['liquidation_price'] > 0 else "N/A"
                liq_display = f"${liq_price:,.2f}" if liq_price != "N/A" else "N/A"
                
                print(f"{Fore.RED}#{i} {Fore.YELLOW}{row['coin']} {Fore.RED}${row['position_value']:,.2f} " + 
                      f"{Fore.BLUE}| Entry: ${row['entry_price']:,.2f} " +
                      f"{Fore.MAGENTA}| PnL: ${row['unrealized_pnl']:,.2f} " +
                      f"{Fore.CYAN}| Leverage: {row['leverage']}x " +
                      f"{Fore.RED}| Liq: {liq_display}")
                print(f"{Fore.CYAN}   Address: {row['address']}")
        
        # Positions closest to liquidation
        print(f"\n{Fore.CYAN}{'='*120}")
        print(f"{Fore.CYAN}{'='*35} 🔥 POSITIONS CLOSEST TO LIQUIDATION 🔥 {'='*35}")
        print(f"{Fore.CYAN}{'='*120}")
        
        # Get current prices for all tokens
        current_prices = {}
        for token in TOKENS_TO_ANALYZE:
            current_prices[token] = n.get_current_price(token)
            print(f"{Fore.YELLOW}💰 Current price for {token}: ${current_prices[token]:,.2f}")
        
        # Calculate distance to liquidation for each position
        positions_df['current_price'] = positions_df['coin'].map(current_prices)
        positions_df['distance_to_liq_pct'] = np.where(
            positions_df['is_long'],
            abs((positions_df['current_price'] - positions_df['liquidation_price']) / positions_df['current_price'] * 100),
            abs((positions_df['liquidation_price'] - positions_df['current_price']) / positions_df['current_price'] * 100)
        )
        
        # Sort by distance to liquidation
        risky_positions = positions_df[positions_df['coin'].isin(TOKENS_TO_ANALYZE)].copy()
        risky_longs = risky_positions[risky_positions['is_long']].sort_values('distance_to_liq_pct')
        risky_shorts = risky_positions[~risky_positions['is_long']].sort_values('distance_to_liq_pct')
        
        # Display risky long positions
        print(f"\n{Fore.GREEN}{Style.BRIGHT}🚀 TOP {TOP_N_POSITIONS} LONG POSITIONS CLOSEST TO LIQUIDATION 📈")
        print(f"{Fore.GREEN}{'-'*120}")
        
        for i, (_, row) in enumerate(risky_longs.head(TOP_N_POSITIONS).iterrows(), 1):
            highlight = row['position_value'] > HIGHLIGHT_THRESHOLD
            display_text = f"{Fore.GREEN}#{i} {Fore.YELLOW}{row['coin']} {Fore.GREEN}${row['position_value']:,.2f} " + \
                          f"{Fore.BLUE}| Entry: ${row['entry_price']:,.2f} " + \
                          f"{Fore.RED}| Liq: ${row['liquidation_price']:,.2f} " + \
                          f"{Fore.MAGENTA}| Current: ${row['current_price']:,.2f} " + \
                          f"{Fore.MAGENTA}| Distance: {row['distance_to_liq_pct']:.2f}% " + \
                          f"{Fore.CYAN}| Leverage: {row['leverage']}x"
            if highlight:
                display_text = colored(display_text, 'black', 'on_yellow')
            print(display_text)
            print(f"{Fore.CYAN}   Address: {row['address']}")
        
        # Display risky short positions
        print(f"\n{Fore.RED}{Style.BRIGHT}💥 TOP {TOP_N_POSITIONS} SHORT POSITIONS CLOSEST TO LIQUIDATION 📉")
        print(f"{Fore.RED}{'-'*120}")
        
        for i, (_, row) in enumerate(risky_shorts.head(TOP_N_POSITIONS).iterrows(), 1):
            highlight = row['position_value'] > HIGHLIGHT_THRESHOLD
            display_text = f"{Fore.RED}#{i} {Fore.YELLOW}{row['coin']} {Fore.RED}${row['position_value']:,.2f} " + \
                          f"{Fore.BLUE}| Entry: ${row['entry_price']:,.2f} " + \
                          f"{Fore.RED}| Liq: ${row['liquidation_price']:,.2f} " + \
                          f"{Fore.MAGENTA}| Current: ${row['current_price']:,.2f} " + \
                          f"{Fore.MAGENTA}| Distance: {row['distance_to_liq_pct']:.2f}% " + \
                          f"{Fore.CYAN}| Leverage: {row['leverage']}x"
            if highlight:
                display_text = colored(display_text, 'black', 'on_yellow')
            print(display_text)
            print(f"{Fore.CYAN}   Address: {row['address']}")
        
        # Liquidation impact analysis
        print(f"\n{Fore.CYAN}{'='*120}")
        print(f"{Fore.CYAN}{'='*35} 💥 LIQUIDATION IMPACT FOR 3% PRICE MOVE 💥 {'='*35}")
        print(f"{Fore.CYAN}{'='*120}")
        
        # Initialize liquidation tracking
        total_long_liquidations = {}
        total_short_liquidations = {}
        all_long_liquidations = 0
        all_short_liquidations = 0
        
        for coin in TOKENS_TO_ANALYZE:
            if coin not in current_prices:
                continue
                
            # Filter positions for current coin
            coin_positions = positions_df[positions_df['coin'] == coin].copy()
            if coin_positions.empty:
                continue
            
            # Calculate 3% price move
            current_price = current_prices[coin]
            coin_positions['price_move'] = current_price * 0.03
            
            # Calculate potential liquidations
            long_liquidations = coin_positions[(coin_positions['is_long']) &
                                           (coin_positions['liquidation_price'] >= current_price - coin_positions['price_move'])]
            total_long_liquidation_value = long_liquidations['position_value'].sum()
            long_price_after_move = current_price - (current_price * 0.03)
            
            short_liquidations = coin_positions[(~coin_positions['is_long']) &
                                            (coin_positions['liquidation_price'] <= current_price + coin_positions['price_move'])]
            total_short_liquidation_value = short_liquidations['position_value'].sum()
            short_price_after_move = current_price + (current_price * 0.03)
            
            # Store liquidation values
            total_long_liquidations[coin] = total_long_liquidation_value
            total_short_liquidations[coin] = total_short_liquidation_value
            all_long_liquidations += total_long_liquidation_value
            all_short_liquidations += total_short_liquidation_value
            
            # Display results for each coin
            print(f"{Fore.GREEN}{coin} Long Liquidations (3% move DOWN to ${long_price_after_move:,.2f}): ${total_long_liquidation_value:,.2f}")
            print(f"{Fore.RED}{coin} Short Liquidations (3% move UP to ${short_price_after_move:,.2f}): ${total_short_liquidation_value:,.2f}")
        
        # Display total liquidation summary
        print(f"\n{Fore.CYAN}{'='*120}")
        print(f"{Fore.CYAN}{'='*35} 💰 TOTAL LIQUIDATION SUMMARY 💰 {'='*35}")
        print(f"{Fore.CYAN}{'='*120}")
        print(f"{Fore.GREEN}Total Long Liquidations (3% move DOWN): ${all_long_liquidations:,.2f}")
        print(f"{Fore.RED}Total Short Liquidations (3% move UP): ${all_short_liquidations:,.2f}")
        
        # Generate trading recommendations
        print(f"\n{Fore.CYAN}{'='*120}")
        print(f"{Fore.CYAN}{'='*35} 🚀 TRADING RECOMMENDATIONS 🚀 {'='*35}")
        print(f"{Fore.CYAN}{'='*120}")
        
        # Overall market recommendation
        if all_long_liquidations > all_short_liquidations:
            trading_bias = 'short'
            recommendation_text = f"SHORT THE MARKET (${all_long_liquidations:,.2f} long liquidations at risk within a 3% move)"
            print(f"{Back.GREEN}{Fore.BLACK}{Style.BRIGHT}MARKET RECOMMENDATION: {recommendation_text}{Style.RESET_ALL}")
        else:
            trading_bias = 'long'
            recommendation_text = f"LONG THE MARKET (${all_short_liquidations:,.2f} short liquidations at risk within a 3% move)"
            print(f"{Back.GREEN}{Fore.BLACK}{Style.BRIGHT}MARKET RECOMMENDATION: {recommendation_text}{Style.RESET_ALL}")
        
        # Individual coin recommendations
        print(f"\n{Fore.CYAN}{'='*30} INDIVIDUAL COIN RECOMMENDATIONS {'='*30}")
        
        # Sort coins by liquidation imbalance
        liquidation_imbalance = {}
        for coin in total_long_liquidations.keys():
            if coin in total_short_liquidations:
                liquidation_imbalance[coin] = abs(total_long_liquidations[coin] - total_short_liquidations[coin])
        
        sorted_coins = sorted(liquidation_imbalance.keys(), key=lambda x: liquidation_imbalance[x], reverse=True)
        
        for coin in sorted_coins:
            long_liq = total_long_liquidations[coin]
            short_liq = total_short_liquidations[coin]
            
            if long_liq < 10000 and short_liq < 10000:
                continue
                
            if long_liq > short_liq:
                rec = f"{coin}: SHORT (${long_liq:,.2f} long liquidations vs ${short_liq:,.2f} short within a 3% move)"
                print(f"{Back.GREEN}{Fore.BLACK}{Style.BRIGHT}{rec}{Style.RESET_ALL}")
            else:
                rec = f"{coin}: LONG (${short_liq:,.2f} short liquidations vs ${long_liq:,.2f} long within a 3% move)"
                print(f"{Back.GREEN}{Fore.BLACK}{Style.BRIGHT}{rec}{Style.RESET_ALL}")
        
        # Update last analysis time
        last_analysis_time = datetime.now()
        
        return True
        
    except Exception as e:
        print(f"{Fore.RED}❌ Error during market analysis: {str(e)}")
        print(f"{Fore.RED}📋 Stack trace:\n{traceback.format_exc()}")
        return False

def get_recent_liquidations():
    """
    Get recent liquidations from Moon Dev API
    """
    try:
        # Fetch liquidation data
        liquidations = api.get_liquidation_data(limit=1000)
        if liquidations is None:
            print(f"{Fore.RED}❌ Failed to fetch liquidation data")
            return None, 0, 0
        
        # Print column names for debugging
        print(f"\n{Fore.CYAN}📊 Liquidation data columns: {liquidations.columns.tolist()}")
        
        # Based on the API output:
        # - Column 0: Symbol (e.g., 'BTC')
        # - Column 1: Side (e.g., 'SELL' for long liquidations, 'BUY' for short liquidations)
        # - Column 10: Timestamp (e.g., '1717505218553')
        # - Column 11: USD Size (e.g., '207.21417599999998')
        
        # Filter to our symbol
        symbol_liquidations = liquidations[liquidations.iloc[:, 0] == symbol]
        
        if symbol_liquidations.empty:
            print(f"{Fore.YELLOW}⚠️ No liquidations found for {symbol}")
            return None, 0, 0
        
        # Convert to milliseconds timestamp
        current_time_ms = int(datetime.now().timestamp() * 1000)
        cutoff_time_ms = current_time_ms - (LIQUIDATION_LOOKBACK_MINUTES * 60 * 1000)
        
        # Filter liquidations within the lookback period using the timestamp column (index 10)
        recent_liquidations = symbol_liquidations[symbol_liquidations.iloc[:, 10].astype(float) >= cutoff_time_ms]
        
        if recent_liquidations.empty:
            return None, 0, 0
        
        # Separate long and short liquidations
        # Long liquidations have side == "SELL", Short liquidations have side == "BUY"
        long_liqs = recent_liquidations[recent_liquidations.iloc[:, 1] == "SELL"]
        short_liqs = recent_liquidations[recent_liquidations.iloc[:, 1] == "BUY"]
        
        # Calculate totals
        long_liq_amount = long_liqs.iloc[:, 11].astype(float).sum() if not long_liqs.empty else 0
        short_liq_amount = short_liqs.iloc[:, 11].astype(float).sum() if not short_liqs.empty else 0
        
        return recent_liquidations, long_liq_amount, short_liq_amount
        
    except Exception as e:
        print(f"{Fore.RED}❌ Error getting liquidations: {str(e)}")
        print(f"{Fore.RED}📋 Stack trace:\n{traceback.format_exc()}")
        return None, 0, 0

def should_enter_trade(long_liq_amount, short_liq_amount):
    """
    Determine if we should enter a trade based on liquidation amounts and trading bias
    """
    if trading_bias is None:
        print(f"{Fore.YELLOW}⚠️ No trading bias set yet - run market analysis first")
        return False, "No trading bias set"
    
    # If our bias is short, we want to enter when SHORT liquidations exceed our threshold
    # This gives us a better entry as shorts are forced to cover, causing temporary spikes
    if trading_bias == 'short' and short_liq_amount >= LIQUIDATION_TRIGGER_AMOUNT:
        return True, f"ENTER SHORT - Short liquidations (${short_liq_amount:,.2f}) exceeding threshold (${LIQUIDATION_TRIGGER_AMOUNT:,.2f})"
    
    # If our bias is long, we want to enter when LONG liquidations exceed our threshold
    # This gives us a better entry as longs are forced to sell, causing temporary dips
    if trading_bias == 'long' and long_liq_amount >= LIQUIDATION_TRIGGER_AMOUNT:
        return True, f"ENTER LONG - Long liquidations (${long_liq_amount:,.2f}) exceeding threshold (${LIQUIDATION_TRIGGER_AMOUNT:,.2f})"
    
    # Be specific about which type of liquidations we're waiting for
    if trading_bias == 'short':
        return False, f"Waiting for SHORT liquidations of ${LIQUIDATION_TRIGGER_AMOUNT:,.2f} or more to enter SHORT position"
    else:
        return False, f"Waiting for LONG liquidations of ${LIQUIDATION_TRIGGER_AMOUNT:,.2f} or more to enter LONG position"

def bot():
    """
    Main bot function that runs on each cycle
    """
    try:
        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"{Fore.YELLOW}🌙 Moon Dev's Liquidation Hunter - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 🚀")
        print(f"{Fore.CYAN}{'='*80}")
        
        # Check if we need to refresh our market analysis
        global last_analysis_time
        if last_analysis_time is None or (datetime.now() - last_analysis_time).total_seconds() / 60 >= ANALYSIS_INTERVAL_MINUTES:
            print(f"{Fore.YELLOW}🔄 Time to refresh market analysis...")
            analyze_market()
        else:
            minutes_since_analysis = (datetime.now() - last_analysis_time).total_seconds() / 60
            print(f"{Fore.YELLOW}ℹ️ Using existing analysis from {minutes_since_analysis:.1f} minutes ago")
            print(f"{Fore.YELLOW}🎯 Current bias: {trading_bias.upper() if trading_bias else 'None'}")
            print(f"{Fore.YELLOW}💡 {recommendation_text}")
        
        # First action: Check for existing positions and close if profit/loss targets hit
        print(f"\n{Fore.CYAN}🔍 Checking for existing positions...")
        positions, im_in_pos, mypos_size, pos_sym, entry_px, pnl_perc, is_long = n.get_position(symbol, account)
        print(f"{Fore.CYAN}📊 Current positions: {positions}")
        
        if im_in_pos:
            print(f"{Fore.GREEN}📈 In position, checking PnL for close conditions...")
            # Check if we need to close based on profit/loss targets
            n.pnl_close(symbol, TAKE_PROFIT_PERCENT, STOP_LOSS_PERCENT, account)
            
            # After pnl_close may have closed the position, check again if we're still in position
            positions, im_in_pos, mypos_size, pos_sym, entry_px, pnl_perc, is_long = n.get_position(symbol, account)
            
            if im_in_pos:
                print(f"{Fore.GREEN}✅ Current position maintained: {symbol} {'LONG' if is_long else 'SHORT'} {mypos_size} @ ${entry_px} (PnL: {pnl_perc}%)")
                return  # Exit early since we're already in a position
        else:
            print(f"{Fore.YELLOW}📉 Not in position, looking for entry opportunities...")
        
        # Get recent liquidations
        print(f"\n{Fore.CYAN}🔍 Looking for liquidations on {symbol}...")
        recent_liquidations, long_liq_amount, short_liq_amount = get_recent_liquidations()
        
        if recent_liquidations is not None:
            # Print summary of liquidations
            print(f"\n{Fore.CYAN}💧 Total Liquidations in the last {LIQUIDATION_LOOKBACK_MINUTES} minutes:")
            print(f"{Fore.GREEN}📉 LONG Liquidations: ${long_liq_amount:,.2f}")
            print(f"{Fore.RED}📈 SHORT Liquidations: ${short_liq_amount:,.2f}")
            
            # Show the largest liquidations
            if not recent_liquidations.empty:
                largest_liquidations = recent_liquidations.sort_values(by=recent_liquidations.columns[11], ascending=False).head(5)
                print(f"\n{Fore.CYAN}💥 Top 5 largest liquidations:")
                for idx, row in largest_liquidations.iterrows():
                    symbol_val = row.iloc[0]  # Symbol at index 0
                    side_val = row.iloc[1]    # Side at index 1
                    usd_size_val = float(row.iloc[11])  # USD Size at index 11
                    
                    # Classify liquidation type
                    liq_type = "LONG LIQ" if side_val == "SELL" else "SHORT LIQ"
                    
                    # Format timestamp
                    timestamp_ms = int(float(row.iloc[10]))
                    time_str = datetime.fromtimestamp(timestamp_ms / 1000).strftime('%H:%M:%S')
                    
                    print(f"   {time_str} | {symbol_val} | {liq_type} | ${usd_size_val:,.2f}")
        else:
            print(f"{Fore.YELLOW}⚠️ No liquidation data available")
            return
        
        # Determine if we should enter a trade
        should_enter, entry_message = should_enter_trade(long_liq_amount, short_liq_amount)
        print(f"\n{Fore.YELLOW}🎯 {entry_message}")
        
        if should_enter and not im_in_pos:
            # Get orderbook data
            print(f"\n{Fore.CYAN}📚 Fetching orderbook data...")
            ask, bid, l2_data = n.ask_bid(symbol)
            print(f"{Fore.GREEN}💰 Current price - Ask: ${ask:.2f}, Bid: ${bid:.2f}")
            
            # Adjust leverage and position size
            lev, pos_size = n.adjust_leverage_usd_size(symbol, POSITION_SIZE_USD, LEVERAGE, account)
            print(f"{Fore.YELLOW}📊 Leverage: {lev}x | Position size: {pos_size}")
            
            # Place appropriate order based on trading bias
            n.cancel_all_orders(account)
            print(f"{Fore.YELLOW}🚫 Canceled all existing orders")
            
            if trading_bias == 'short':
                # Place a sell order at the current ask price (market-like limit order)
                n.limit_order(symbol, False, pos_size, ask, False, account)
                print(f"{Fore.RED}💸 Placed SELL order for {pos_size} {symbol} at ${ask}")
                print(f"{Fore.RED}📉 Looking to profit from long liquidations cascade")
            else:  # trading_bias == 'long'
                # Place a buy order at the current bid price (market-like limit order)
                n.limit_order(symbol, True, pos_size, bid, False, account)
                print(f"{Fore.GREEN}🛒 Placed BUY order for {pos_size} {symbol} at ${bid}")
                print(f"{Fore.GREEN}📈 Looking to profit from short liquidations cascade")
            
            print(f"{Fore.YELLOW}⏳ Order placed, waiting for fill...")
        else:
            print(f"{Fore.YELLOW}⏳ Conditions not met for entry, continuing to monitor...")
        
        # Easter egg
        print(f"\n{Fore.MAGENTA}🌕 Thanks for using Moon Dev Trading Bots! 🤖")
        
    except Exception as e:
        print(f"{Fore.RED}❌ Error in bot execution: {str(e)}")
        print(f"{Fore.RED}📋 Stack trace:\n{traceback.format_exc()}")

if __name__ == "__main__":
    # Display banner
    print_banner()
    
    # Initial market analysis
    print(f"{Fore.YELLOW}🔍 Performing initial market analysis...")
    analyze_market()
    
    # Initial bot run
    print(f"{Fore.YELLOW}🚀 Starting first bot cycle...")
    bot()
    
    # Schedule the bot to run every minute
    schedule.every(1).minutes.do(bot)
    
    # Schedule market analysis to run periodically
    schedule.every(ANALYSIS_INTERVAL_MINUTES).minutes.do(analyze_market)
    
    print(f"{Fore.GREEN}✅ Bot scheduled to run every minute")
    print(f"{Fore.GREEN}✅ Market analysis scheduled to run every {ANALYSIS_INTERVAL_MINUTES} minutes")
    
    while True:
        try:
            # Run pending scheduled tasks
            schedule.run_pending()
            time.sleep(1)
        except Exception as e:
            print(f"{Fore.RED}❌ Encountered an error: {e}")
            print(f"{Fore.RED}📋 Stack trace:\n{traceback.format_exc()}")
            # Wait before retrying to avoid rapid error logging
            time.sleep(10)
