#!/usr/bin/env python3
'''
Open and Close Bot - by Moon Dev 🌙

This bot analyzes price movement during two daily trading sessions:

MORNING SESSION:
- Analysis Period: 5:30 AM - 9:30 AM Eastern
- Trading Period: 9:30 AM - 11:00 AM Eastern

AFTERNOON SESSION:
- Analysis Period: 10:30 AM - 2:30 PM Eastern
- Trading Period: 2:30 PM - 4:00 PM Eastern

TRADING STRATEGY:
1. During each analysis period, the bot calculates the average price
2. During the trading period, it watches for extreme price moves (3%+) from that average
3. When an extreme move is detected, the bot will:
   - GO LONG when price has dropped significantly (mean reversion)
   - GO SHORT when price has risen significantly (mean reversion)
4. The bot only enters after $1M+ in matching liquidations occur, allowing us to:
   - Take over positions from liquidated traders
   - Enter at optimal prices after liquidation cascades

RISK MANAGEMENT:
- Positions automatically close at the end of each trading session
- Standard take profit (19%) and stop loss (-18%) levels
- Properly sized positions based on account balance

This strategy capitalizes on overextended price moves during active trading hours
and uses liquidation data to confirm strong directional momentum.
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
import pathlib
import io
import contextlib

# Add the parent directory to the Python path
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

# ===== CONFIGURATION =====
# Symbol to trade
SYMBOL = 'BTC'  # Default symbol, can be changed as needed
LEVERAGE = 10     # Leverage to use for trading
POSITION_SIZE_USD = 10  # Position size in USD

# Time window configuration
ANALYSIS_START_TIME_MORNING = '05:30'  # 5:30 AM Eastern
ANALYSIS_END_TIME_MORNING = '09:30'    # 9:30 AM Eastern
TRADING_START_TIME_MORNING = '09:30'   # 9:30 AM Eastern
TRADING_END_TIME_MORNING = '11:00'     # 11:00 AM Eastern

# New afternoon session times
ANALYSIS_START_TIME_AFTERNOON = '10:30'  # 10:30 AM Eastern (4 hours before trading start)
ANALYSIS_END_TIME_AFTERNOON = '14:30'    # 2:30 PM Eastern
TRADING_START_TIME_AFTERNOON = '14:30'   # 2:30 PM Eastern
TRADING_END_TIME_AFTERNOON = '16:00'     # 4:00 PM Eastern

# For backward compatibility
ANALYSIS_START_TIME = ANALYSIS_START_TIME_MORNING
ANALYSIS_END_TIME = ANALYSIS_END_TIME_MORNING
TRADING_START_TIME = TRADING_START_TIME_MORNING
TRADING_END_TIME = TRADING_END_TIME_MORNING

# Price move threshold to consider as "extreme"
EXTREME_PRICE_MOVE_PERCENT = 3  # 3% price move is considered extreme

# Analysis timeframe
ANALYSIS_TIMEFRAME = '5m'  # 5-minute candles
LOOKBACK_HOURS = 4  # Look back 4 hours for analysis

# Liquidation configuration
LIQUIDATION_LOOKBACK_MINUTES = 5  # Look back this many minutes for liquidations
ENTRY_LIQUIDATION_THRESHOLD = 1000000 #1000000  # $1M in liquidations to trigger entry

# Take profit and stop loss settings
TAKE_PROFIT_PERCENT = 19  # Take profit percentage
STOP_LOSS_PERCENT = -18 # Stop loss percentage

# Moon Dev ASCII Art Banner
# Moon Dev ASCII Art Banner
MOON_DEV_BANNER = f"""{Fore.CYAN}
  __  __  ___   ___  _  _    ___  ___ _   _ 
 |  \\/  |/ _ \\ / _ \\| \\| |  |   \\| __\\ \\ / /
 | |\\/| | (_) | (_) | .` |  | |) | _| \\ V / 
 |_|  |_|\\___/ \\___/|_|\\_|  |___/|___| \\_/  
                                             
{Fore.MAGENTA}🚀 Hyperliquid Position Tracker API Edition 🌙{Fore.RESET}
"""
# Initialize account
account = LocalAccount = eth_account.Account.from_key(HYPER_LIQUID_KEY)

# Initialize API
api = MoonDevAPI()

# ===== HELPER FUNCTIONS =====
def get_eastern_time():
    """Get current time in Eastern timezone"""
    eastern = pytz.timezone('US/Eastern')
    return datetime.now(eastern)

def is_trading_time():
    """Check if current time is within either trading window (morning or afternoon)"""
    current_time = get_eastern_time()
    
    # Create datetime objects for the morning trading window
    current_date = current_time.date()
    eastern = pytz.timezone('US/Eastern')
    morning_start = eastern.localize(datetime.combine(current_date, datetime.strptime(TRADING_START_TIME_MORNING, '%H:%M').time()))
    morning_end = eastern.localize(datetime.combine(current_date, datetime.strptime(TRADING_END_TIME_MORNING, '%H:%M').time()))
    
    # Create datetime objects for the afternoon trading window
    afternoon_start = eastern.localize(datetime.combine(current_date, datetime.strptime(TRADING_START_TIME_AFTERNOON, '%H:%M').time()))
    afternoon_end = eastern.localize(datetime.combine(current_date, datetime.strptime(TRADING_END_TIME_AFTERNOON, '%H:%M').time()))
    
    # Check if current time is in either trading window
    in_morning_window = morning_start <= current_time <= morning_end
    in_afternoon_window = afternoon_start <= current_time <= afternoon_end
    
    if in_morning_window:
        print(f"{Fore.GREEN}⏰ Currently in MORNING trading window ({TRADING_START_TIME_MORNING} - {TRADING_END_TIME_MORNING})")
        return "morning"
    elif in_afternoon_window:
        print(f"{Fore.GREEN}⏰ Currently in AFTERNOON trading window ({TRADING_START_TIME_AFTERNOON} - {TRADING_END_TIME_AFTERNOON})")
        return "afternoon"
    else:
        return False

def validate_dataframe(df):
    """Ensure all numeric columns are properly converted to numeric types"""
    if df is None or df.empty:
        return None
        
    try:
        # Convert these columns to numeric, coercing errors to NaN
        numeric_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_columns:
            if col in df.columns:
                # Convert strings to numeric, forcing errors to NaN
                df[col] = pd.to_numeric(df[col], errors='coerce')
                
        # Drop any rows with NaN values in critical columns
        df = df.dropna(subset=['close'])
        
        if df.empty:
            print(f"{Fore.RED}❌ No valid data after cleaning")
            return None
            
        # Print diagnostic info
        print(f"{Fore.GREEN}✅ Data validated: {len(df)} valid candles")
        
        # Print DataFrame sample for verification
        pd.set_option('display.max_columns', None)  # Show all columns
        pd.set_option('display.width', 1000)  # Wide display
        print(f"\n{Fore.CYAN}📊 DataFrame Sample (first 5 rows):")
        print(f"{Fore.WHITE}{df.head().to_string()}")
        
        # Print some basic statistics
        print(f"\n{Fore.CYAN}📊 DataFrame Statistics:")
        stats = df.describe()
        print(f"{Fore.WHITE}{stats.to_string()}")
        
        return df
        
    except Exception as e:
        print(f"{Fore.RED}❌ Error validating dataframe: {str(e)}")
        print(f"{Fore.RED}📋 Data sample: {df.head().to_string() if df is not None else 'None'}")
        return None

def get_analysis_data(session="morning"):
    """
    Fetch data for analysis period
    
    Args:
        session: 'morning' or 'afternoon' - which trading session to analyze
    
    Returns:
        DataFrame with analysis data or None if error
    """
    try:
        eastern = pytz.timezone('US/Eastern')
        current_date = get_eastern_time().date()
        
        # Create datetime objects for analysis window based on session
        if session == "morning":
            analysis_start = eastern.localize(datetime.combine(current_date, datetime.strptime(ANALYSIS_START_TIME_MORNING, '%H:%M').time()))
            analysis_end = eastern.localize(datetime.combine(current_date, datetime.strptime(ANALYSIS_END_TIME_MORNING, '%H:%M').time()))
            print(f"{Fore.YELLOW}🔍 Fetching MORNING analysis data from {ANALYSIS_START_TIME_MORNING} to {ANALYSIS_END_TIME_MORNING} Eastern")
        else:  # afternoon
            analysis_start = eastern.localize(datetime.combine(current_date, datetime.strptime(ANALYSIS_START_TIME_AFTERNOON, '%H:%M').time()))
            analysis_end = eastern.localize(datetime.combine(current_date, datetime.strptime(ANALYSIS_END_TIME_AFTERNOON, '%H:%M').time()))
            print(f"{Fore.YELLOW}🔍 Fetching AFTERNOON analysis data from {ANALYSIS_START_TIME_AFTERNOON} to {ANALYSIS_END_TIME_AFTERNOON} Eastern")
        
        # Convert to UTC for API calls
        analysis_start_utc = analysis_start.astimezone(pytz.UTC)
        analysis_end_utc = analysis_end.astimezone(pytz.UTC)
        
        # Get data from market API
        snapshot_data = n.fetch_candle_snapshot(
            SYMBOL, 
            ANALYSIS_TIMEFRAME, 
            analysis_start_utc, 
            analysis_end_utc
        )
        
        if snapshot_data:
            # Print raw data sample for debugging
            print(f"{Fore.CYAN}🔍 Raw API data sample (first 2 candles):")
            for i, candle in enumerate(snapshot_data[:2]):
                print(f"  Candle {i+1}: {candle}")
                
            df = n.process_data_to_df(snapshot_data)
            return validate_dataframe(df)
        else:
            print(f"{Fore.RED}❌ No data returned from API for analysis period")
            return None
            
    except Exception as e:
        print(f"{Fore.RED}❌ Error getting analysis data: {str(e)}")
        print(f"{Fore.RED}📋 Stack trace:\n{traceback.format_exc()}")
        return None

def get_current_trading_data(session="morning"):
    """
    Fetch data for the current trading session
    
    Args:
        session: 'morning' or 'afternoon' - which trading session to analyze
        
    Returns:
        DataFrame with trading session data or None if error
    """
    try:
        eastern = pytz.timezone('US/Eastern')
        current_time = get_eastern_time()
        current_date = current_time.date()
        
        # Create datetime objects for trading period based on session
        if session == "morning":
            trading_start = eastern.localize(datetime.combine(current_date, datetime.strptime(TRADING_START_TIME_MORNING, '%H:%M').time()))
            trading_end = eastern.localize(datetime.combine(current_date, datetime.strptime(TRADING_END_TIME_MORNING, '%H:%M').time()))
            print(f"{Fore.YELLOW}🔍 Fetching MORNING trading data from {TRADING_START_TIME_MORNING} to current time")
        else:  # afternoon
            trading_start = eastern.localize(datetime.combine(current_date, datetime.strptime(TRADING_START_TIME_AFTERNOON, '%H:%M').time()))
            trading_end = eastern.localize(datetime.combine(current_date, datetime.strptime(TRADING_END_TIME_AFTERNOON, '%H:%M').time()))
            print(f"{Fore.YELLOW}🔍 Fetching AFTERNOON trading data from {TRADING_START_TIME_AFTERNOON} to current time")
        
        # Make sure we don't go past the trading end time
        end_time = min(current_time, trading_end)
        
        # Convert to UTC for API calls
        trading_start_utc = trading_start.astimezone(pytz.UTC)
        end_time_utc = end_time.astimezone(pytz.UTC)
        
        # Get data from market API
        snapshot_data = n.fetch_candle_snapshot(
            SYMBOL, 
            ANALYSIS_TIMEFRAME, 
            trading_start_utc, 
            end_time_utc
        )
        
        if snapshot_data:
            # Print raw data sample for debugging
            print(f"{Fore.CYAN}🔍 Raw API data sample (first 2 candles):")
            for i, candle in enumerate(snapshot_data[:2]):
                print(f"  Candle {i+1}: {candle}")
                
            df = n.process_data_to_df(snapshot_data)
            return validate_dataframe(df)
        else:
            print(f"{Fore.RED}❌ No data returned from API for trading period")
            return None
            
    except Exception as e:
        print(f"{Fore.RED}❌ Error getting trading data: {str(e)}")
        print(f"{Fore.RED}📋 Stack trace:\n{traceback.format_exc()}")
        return None

def determine_trade_direction(session="morning"):
    """
    Determine which direction to trade based on average price analysis
    
    Args:
        session: 'morning' or 'afternoon' - which trading session to analyze
    
    Returns:
        str: 'long', 'short', or None if no trade
    """
    try:
        # Get analysis data for the specified session
        print(f"\n{Fore.CYAN}{'='*80}")
        if session == "morning":
            print(f"{Fore.CYAN}{'='*20} 🔍 MORNING ANALYSIS PERIOD DATA ({ANALYSIS_START_TIME_MORNING} - {ANALYSIS_END_TIME_MORNING}) 🔍 {'='*20}")
        else:
            print(f"{Fore.CYAN}{'='*20} 🔍 AFTERNOON ANALYSIS PERIOD DATA ({ANALYSIS_START_TIME_AFTERNOON} - {ANALYSIS_END_TIME_AFTERNOON}) 🔍 {'='*20}")
        print(f"{Fore.CYAN}{'='*80}")
        
        analysis_df = get_analysis_data(session)
        if analysis_df is None or len(analysis_df) < 3:
            print(f"{Fore.RED}❌ Insufficient data for analysis")
            return None
        
        # Calculate price metrics during analysis period
        avg_price = analysis_df['close'].mean()
        median_price = analysis_df['close'].median()
        min_analysis_price = analysis_df['low'].min()
        max_analysis_price = analysis_df['high'].max()
        std_dev = analysis_df['close'].std()
        
        # Print detailed analysis period metrics with highlighted average price
        print(f"\n{Back.GREEN}{Fore.BLACK}{'*'*80}")
        print(f"{Back.GREEN}{Fore.BLACK}{'*'*20} 📊 REFERENCE PRICE METRICS (ANALYSIS PERIOD) 📊 {'*'*20}")
        print(f"{Back.GREEN}{Fore.BLACK}{'*'*80}")
        print(f"{Back.GREEN}{Fore.BLACK}📊 AVERAGE PRICE: ${avg_price:.2f} - THIS IS OUR REFERENCE PRICE")
        print(f"{Back.GREEN}{Fore.BLACK}📊 MEDIAN PRICE: ${median_price:.2f}")
        print(f"{Back.GREEN}{Fore.BLACK}📊 PRICE RANGE: ${min_analysis_price:.2f} - ${max_analysis_price:.2f}")
        print(f"{Back.GREEN}{Fore.BLACK}📊 STANDARD DEVIATION: ${std_dev:.2f}")
        print(f"{Back.GREEN}{Fore.BLACK}{'*'*80}{Style.RESET_ALL}")
        
        # Get current trading session data
        print(f"\n{Fore.CYAN}{'='*80}")
        if session == "morning":
            print(f"{Fore.CYAN}{'='*20} 🔍 MORNING TRADING PERIOD DATA ({TRADING_START_TIME_MORNING} - now) 🔍 {'='*20}")
        else:
            print(f"{Fore.CYAN}{'='*20} 🔍 AFTERNOON TRADING PERIOD DATA ({TRADING_START_TIME_AFTERNOON} - now) 🔍 {'='*20}")
        print(f"{Fore.CYAN}{'='*80}")
        
        trading_df = get_current_trading_data(session)
        if trading_df is None or len(trading_df) < 2:
            print(f"{Fore.RED}❌ Insufficient data for current trading session")
            return None
        
        # Get min/max prices during trading session
        min_price = trading_df['low'].min()
        max_price = trading_df['high'].max()
        latest_price = trading_df['close'].iloc[-1]
        
        # Calculate percentage moves from the average
        down_move_pct = ((avg_price - min_price) / avg_price) * 100
        up_move_pct = ((max_price - avg_price) / avg_price) * 100
        current_move_pct = ((latest_price - avg_price) / avg_price) * 100
        
        # Create a simple ASCII chart showing the price movement
        max_chart_width = 50
        price_range = max(abs(up_move_pct), abs(down_move_pct))
        chart_scale = max_chart_width / price_range if price_range > 0 else 1
        
        # Calculate bar lengths based on percentage moves
        up_bar_len = int(up_move_pct * chart_scale)
        down_bar_len = int(down_move_pct * chart_scale)
        current_bar_len = int(abs(current_move_pct) * chart_scale)
        
        # Print detailed price movement analysis with visual chart
        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"{Fore.CYAN}{'='*25} 📊 PRICE MOVEMENT ANALYSIS 📊 {'='*25}")
        print(f"{Fore.CYAN}{'='*80}")
        
        # Reference price section with background for emphasis
        print(f"{Back.GREEN}{Fore.BLACK} REFERENCE PRICE FROM ANALYSIS PERIOD: ${avg_price:.2f} {Style.RESET_ALL}")
        
        # Trading period price metrics
        print(f"\n{Fore.CYAN}📊 TRADING PERIOD METRICS:")
        print(f"{Fore.YELLOW}⏰ Trading period min: ${min_price:.2f}")
        print(f"{Fore.YELLOW}⏰ Trading period max: ${max_price:.2f}")
        print(f"{Fore.YELLOW}⏰ Current price: ${latest_price:.2f}")
        
        # Price movement metrics
        print(f"\n{Fore.CYAN}📊 PRICE MOVEMENT FROM REFERENCE:")
        print(f"{Fore.GREEN}📈 Upward move: {up_move_pct:.2f}% (max: ${max_price:.2f})")
        print(f"{Fore.RED}📉 Downward move: {down_move_pct:.2f}% (min: ${min_price:.2f})")
        print(f"{Fore.YELLOW}📊 Current move: {current_move_pct:.2f}% (current: ${latest_price:.2f})")
        
        # Decision thresholds
        print(f"\n{Fore.CYAN}📊 DECISION THRESHOLDS:")
        print(f"{Fore.YELLOW}🎯 Required move for signal: {EXTREME_PRICE_MOVE_PERCENT}%")
        print(f"{Fore.YELLOW}📊 Take profit: {TAKE_PROFIT_PERCENT}%")
        print(f"{Fore.YELLOW}📊 Stop loss: {STOP_LOSS_PERCENT}%")
        
        # Visual representation of price moves
        print(f"\n{Fore.CYAN}📊 VISUAL PRICE MOVEMENT:")
        print(f"{Fore.GREEN}📈 Upward:  {'█' * up_bar_len} {up_move_pct:.2f}%")
        print(f"{Fore.RED}📉 Downward: {'█' * down_bar_len} {down_move_pct:.2f}%")
        
        if current_move_pct >= 0:
            print(f"{Fore.YELLOW}📊 Current:  {'█' * current_bar_len} {current_move_pct:.2f}%")
        else:
            print(f"{Fore.YELLOW}📊 Current:  {'█' * current_bar_len} {current_move_pct:.2f}%")
        
        # Check for extreme moves
        signal_text = None
        if down_move_pct >= EXTREME_PRICE_MOVE_PERCENT and down_move_pct > up_move_pct:
            # Price moved down significantly - go LONG
            signal_text = f"LONG (price dropped {down_move_pct:.2f}% from average)"
            print(f"\n{Back.GREEN}{Fore.BLACK}🚀 TRADE SIGNAL: {signal_text}{Style.RESET_ALL}")
            return "long"
        elif up_move_pct >= EXTREME_PRICE_MOVE_PERCENT and up_move_pct > down_move_pct:
            # Price moved up significantly - go SHORT
            signal_text = f"SHORT (price rose {up_move_pct:.2f}% from average)"
            print(f"\n{Back.GREEN}{Fore.BLACK}💥 TRADE SIGNAL: {signal_text}{Style.RESET_ALL}")
            return "short"
        else:
            print(f"\n{Fore.YELLOW}⏳ No extreme price moves detected yet. Need {EXTREME_PRICE_MOVE_PERCENT}% move, largest move is {max(up_move_pct, down_move_pct):.2f}%")
            return None
            
    except Exception as e:
        print(f"{Fore.RED}❌ Error determining trade direction: {str(e)}")
        print(f"{Fore.RED}📋 Stack trace:\n{traceback.format_exc()}")
        return None

def check_liquidations(trade_direction):
    """
    Check if liquidation threshold has been met for the given trade direction
    
    Args:
        trade_direction: 'long' or 'short' - which direction we want to trade
    
    Returns:
        bool: True if liquidation threshold is met, False otherwise
    """
    try:
        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"{Fore.CYAN}{'='*20} 🔍 LIQUIDATION ANALYSIS 🔍 {'='*20}")
        print(f"{Fore.CYAN}{'='*80}")
        
        # Explain how liquidations are calculated
        print(f"{Fore.YELLOW}📊 Liquidation Analysis Parameters:")
        print(f"{Fore.YELLOW}⏱️ Looking back {LIQUIDATION_LOOKBACK_MINUTES} minutes for liquidations")
        print(f"{Fore.YELLOW}💰 Need ${ENTRY_LIQUIDATION_THRESHOLD:,} in {trade_direction.upper()} liquidations to enter")
        
        # Get liquidation data
        liquidations = api.get_liquidation_data(limit=1000)
        if liquidations is None:
            print(f"{Fore.RED}❌ Failed to fetch liquidation data")
            return False
            
        # Print column names for debugging
        if not liquidations.empty:
            print(f"\n{Fore.CYAN}📋 Liquidation Data Structure:")
            print(f"{Fore.CYAN}Total columns: {len(liquidations.columns)}")
            print(f"{Fore.CYAN}Expected column mapping:")
            print(f"{Fore.CYAN}  Column 0: Symbol (e.g., 'BTC')")
            print(f"{Fore.CYAN}  Column 1: Side (e.g., 'SELL' for long liquidations, 'BUY' for short liquidations)")
            print(f"{Fore.CYAN}  Column 2: Price")
            print(f"{Fore.CYAN}  Column 3: Size")
            print(f"{Fore.CYAN}  Column 10: Timestamp (milliseconds)")
            print(f"{Fore.CYAN}  Column 11: USD Value")
            
            # Show actual column names and sample data for debugging
            if len(liquidations) > 0:
                print(f"\n{Fore.CYAN}Sample Row Data (first row):")
                sample_row = liquidations.iloc[0]
                for i, col in enumerate(liquidations.columns):
                    val = sample_row[i]
                    print(f"{Fore.CYAN}  Column {i} ({col}): {val} (type: {type(val).__name__})")
        
        # Get recent liquidations based on lookback minutes
        cutoff_time = int(datetime.now().timestamp() * 1000) - (LIQUIDATION_LOOKBACK_MINUTES * 60 * 1000)
        recent_liquidations = liquidations[liquidations.iloc[:, 10].astype(float) >= cutoff_time]
        
        if recent_liquidations.empty:
            print(f"{Fore.YELLOW}⚠️ No recent liquidations found in the last {LIQUIDATION_LOOKBACK_MINUTES} minutes")
            return False
            
        # Print recent liquidation stats
        total_count = len(recent_liquidations)
        long_liqs = recent_liquidations[recent_liquidations.iloc[:, 1] == "SELL"]
        short_liqs = recent_liquidations[recent_liquidations.iloc[:, 1] == "BUY"]
        long_amount = long_liqs.iloc[:, 11].astype(float).sum() if not long_liqs.empty else 0
        short_amount = short_liqs.iloc[:, 11].astype(float).sum() if not short_liqs.empty else 0
        
        print(f"\n{Fore.CYAN}📊 Liquidation Summary (Last {LIQUIDATION_LOOKBACK_MINUTES} Minutes):")
        print(f"{Fore.YELLOW}🔢 Total Liquidations: {total_count}")
        print(f"{Fore.RED}📉 LONG Liquidations: ${long_amount:,.2f}")
        print(f"{Fore.GREEN}📈 SHORT Liquidations: ${short_amount:,.2f}")
        
        # Print last 5 liquidations for debugging
        print(f"\n{Fore.CYAN}🔍 Last 5 Liquidations:")
        recent_5 = recent_liquidations.sort_values(by=recent_liquidations.columns[10], ascending=False).head(5)
        for idx, row in recent_5.iterrows():
            try:
                symbol = row.iloc[0]            # Symbol (column 0)
                side = row.iloc[1]              # Side (column 1)
                
                # Handle price field safely
                try:
                    price = float(row.iloc[2])  # Price (column 2)
                    price_str = f"${price:,.2f}"
                except (ValueError, TypeError):
                    price_str = f"{row.iloc[2]}"  # Just use the raw value if conversion fails
                
                # Handle size field safely
                try:
                    size = float(row.iloc[3])   # Size (column 3)
                    size_str = f"{size:,.6f}"
                except (ValueError, TypeError):
                    size_str = f"{row.iloc[3]}"  # Just use the raw value if conversion fails
                
                # Handle USD value field safely
                try:
                    usd_value = float(row.iloc[11])  # USD Value (column 11)
                    usd_str = f"${usd_value:,.2f}"
                except (ValueError, TypeError):
                    usd_str = f"{row.iloc[11]}"      # Just use the raw value if conversion fails
                
                # Handle timestamp conversion safely
                try:
                    timestamp_ms = int(float(row.iloc[10]))  # Timestamp (column 10)
                    time_str = datetime.fromtimestamp(timestamp_ms / 1000).strftime('%H:%M:%S')
                except (ValueError, TypeError, OverflowError):
                    # Fallback if timestamp conversion fails
                    time_str = "Unknown"
                
                # Format output based on side
                if side == "SELL":  # LONG liquidation
                    liq_str = f"{Fore.RED}LONG→SELL"
                else:  # SHORT liquidation
                    liq_str = f"{Fore.GREEN}SHORT→BUY"
                    
                print(f"{time_str} | {symbol} | {liq_str} | {price_str} | Size: {size_str} | {usd_str}")
            except Exception as e:
                print(f"{Fore.RED}❌ Error parsing liquidation row: {str(e)}")
                print(f"{Fore.YELLOW}Row data: {row.values}")
                continue
        
        # IMPORTANT: When trade signal is SHORT, we want to see SHORT liquidations
        # When trade signal is LONG, we want to see LONG liquidations
        # This allows us to take over the positions of liquidated traders
        if trade_direction == "long":
            # Filter for LONG liquidations (side == "SELL" meaning longs forced to sell)
            target_liqs = recent_liquidations[recent_liquidations.iloc[:, 1] == "SELL"]
            liq_amount = target_liqs.iloc[:, 11].astype(float).sum() if not target_liqs.empty else 0
            liq_type = "LONG"
        else:  # trade_direction == "short"
            # Filter for SHORT liquidations (side == "BUY" meaning shorts forced to buy back)
            target_liqs = recent_liquidations[recent_liquidations.iloc[:, 1] == "BUY"]
            liq_amount = target_liqs.iloc[:, 11].astype(float).sum() if not target_liqs.empty else 0
            liq_type = "SHORT"
        
        print(f"\n{Fore.CYAN}💧 Recent {liq_type} liquidations: ${liq_amount:,.2f}")
        print(f"{Fore.CYAN}📊 Looking for {liq_type} liquidations to take over their positions with our {trade_direction.upper()} signal")
        
        # Check if liquidation amount meets our threshold
        if liq_amount >= ENTRY_LIQUIDATION_THRESHOLD:
            print(f"{Back.GREEN}{Fore.BLACK}🔥 ENTRY SIGNAL: ${liq_amount:,.2f} in {liq_type} liquidations - entering {trade_direction.upper()} position{Style.RESET_ALL}")
            return True
        else:
            print(f"{Fore.YELLOW}⏳ Waiting for ${ENTRY_LIQUIDATION_THRESHOLD:,.2f} in {liq_type} liquidations (current: ${liq_amount:,.2f})")
            return False
            
    except Exception as e:
        print(f"{Fore.RED}❌ Error checking liquidations: {str(e)}")
        print(f"{Fore.RED}📋 Stack trace:\n{traceback.format_exc()}")
        return False

def enter_position(direction):
    """
    Enter a trading position based on the given direction
    
    Args:
        direction: 'long' or 'short' - which direction to trade
    
    Returns:
        bool: True if position was entered, False otherwise
    """
    try:
        # Check if we're already in a position
        positions, in_position, _, _, _, _, _ = n.get_position(SYMBOL, account)
        if in_position:
            print(f"{Fore.YELLOW}⚠️ Already in a position. Skipping entry.")
            return False
        
        # Cancel any existing orders
        n.cancel_all_orders(account)
        
        # Adjust leverage and position size
        leverage, pos_size = n.adjust_leverage_usd_size(SYMBOL, POSITION_SIZE_USD, LEVERAGE, account)
        
        # Get current price
        #current_price = n.get_current_price(SYMBOL)

        ask, bid, l2_data = n.ask_bid(SYMBOL)
        
        # Get size and price decimals for proper rounding
        sz_decimals, px_decimals = n.get_sz_px_decimals(SYMBOL)
        
        # Round the price to the correct number of decimal places
        #current_price = round(current_price, px_decimals)
        #print(f"🌙 Moon Dev rounded price to {px_decimals} decimals: ${current_price}")
        
        # Place the order
        if direction == "long":
            n.limit_order(SYMBOL, True, pos_size, bid, False, account)
            print(f"{Fore.GREEN}🚀 ENTERED LONG POSITION at ${bid:.2f}")
        else:  # direction == "short"
            n.limit_order(SYMBOL, False, pos_size, ask, False, account)
            print(f"{Fore.RED}💥 ENTERED SHORT POSITION at ${ask:.2f}")
        
        # Wait for order to be filled
        time.sleep(5)
        
        # Check if position was opened
        _, in_position, _, _, _, _, _ = n.get_position(SYMBOL, account)
        
        if in_position:
            print(f"{Fore.GREEN}✅ Position successfully opened!")
            return True
        else:
            print(f"{Fore.RED}❌ Failed to open position. Order may not have filled.")
            # Cancel all orders again
            n.cancel_all_orders(account)
            return False
            
    except Exception as e:
        print(f"{Fore.RED}❌ Error entering position: {str(e)}")
        print(f"{Fore.RED}📋 Stack trace:\n{traceback.format_exc()}")
        return False

def print_banner():
    """Print Moon Dev banner with trading session info"""
    print(MOON_DEV_BANNER)
    print(f"{Fore.CYAN}{'='*80}")
    print(f"{Fore.YELLOW}🚀 Moon Dev Open Only Bot is starting up! 🎯")
    print(f"{Fore.YELLOW}📊 Trading {SYMBOL} with {LEVERAGE}x leverage")
    print(f"{Fore.YELLOW}⏰ MORNING Analysis period: {ANALYSIS_START_TIME_MORNING} - {ANALYSIS_END_TIME_MORNING} Eastern")
    print(f"{Fore.YELLOW}⏰ MORNING Trading period: {TRADING_START_TIME_MORNING} - {TRADING_END_TIME_MORNING} Eastern")
    print(f"{Fore.YELLOW}⏰ AFTERNOON Analysis period: {ANALYSIS_START_TIME_AFTERNOON} - {ANALYSIS_END_TIME_AFTERNOON} Eastern")
    print(f"{Fore.YELLOW}⏰ AFTERNOON Trading period: {TRADING_START_TIME_AFTERNOON} - {TRADING_END_TIME_AFTERNOON} Eastern")
    print(f"{Fore.YELLOW}💰 Entry liquidation threshold: ${ENTRY_LIQUIDATION_THRESHOLD:,.2f}")
    print(f"{Fore.CYAN}{'='*80}\n")

def bot():
    """Main bot function that runs on each cycle"""
    try:
        current_time = get_eastern_time()
        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"{Fore.YELLOW}🌙 Moon Dev's Open Only Bot - {current_time.strftime('%Y-%m-%d %H:%M:%S')} ET 🚀")
        print(f"{Fore.CYAN}{'='*80}")
        
        # First check PnL to see if we need to exit with profit or loss
        print(f"{Fore.YELLOW}💰 Checking PnL conditions first...")
        n.pnl_close(SYMBOL, TAKE_PROFIT_PERCENT, STOP_LOSS_PERCENT, account)
        
        # Check if we're in a position
        positions, in_position, pos_size, pos_sym, entry_price, pnl_percent, is_long = n.get_position(SYMBOL, account)
        
        if in_position:
            print(f"{Fore.GREEN}📈 Currently in position, checking position status...")
            
            # Print position status
            direction_str = "LONG" if is_long else "SHORT"
            print(f"\n{Fore.CYAN}{'='*80}")
            print(f"{Fore.CYAN}{'='*30} 📊 POSITION STATUS 📊 {'='*30}")
            print(f"{Fore.CYAN}{'='*80}")
            print(f"{Fore.YELLOW}🪙 {SYMBOL} {direction_str} | Size: {pos_size} | Entry: ${entry_price:.2f}")
            print(f"{Fore.CYAN}💰 Current price: ${n.get_current_price(SYMBOL):.2f}")
            print(f"{Fore.MAGENTA}📊 Current PnL: {pnl_percent:.2f}%")
            print(f"{Fore.CYAN}{'='*80}\n")
            
            # Check if it's past any trading window - close position at end of window
            current_time = get_eastern_time()
            morning_end_time = datetime.strptime(TRADING_END_TIME_MORNING, '%H:%M').time()
            afternoon_end_time = datetime.strptime(TRADING_END_TIME_AFTERNOON, '%H:%M').time()
            
            if (current_time.time() > morning_end_time and 
                current_time.time() < datetime.strptime(TRADING_START_TIME_AFTERNOON, '%H:%M').time()):
                print(f"{Fore.YELLOW}⏰ Morning trading window ended at {TRADING_END_TIME_MORNING}. Closing position.")
                n.kill_switch(SYMBOL, account)
                return
            elif current_time.time() > afternoon_end_time:
                print(f"{Fore.YELLOW}⏰ Afternoon trading window ended at {TRADING_END_TIME_AFTERNOON}. Closing position.")
                n.kill_switch(SYMBOL, account)
                return
            
            # If we're still in a position, don't try to enter new ones
            return
        
        # If we're not in a position, check if it's trading time
        trading_session = is_trading_time()
        if not trading_session:
            current_hour_minute = current_time.strftime("%H:%M")
            print(f"{Fore.YELLOW}⏰ Not in any trading window. Current time: {current_hour_minute}")
            print(f"{Fore.YELLOW}⏰ Morning window: {TRADING_START_TIME_MORNING} - {TRADING_END_TIME_MORNING}")
            print(f"{Fore.YELLOW}⏰ Afternoon window: {TRADING_START_TIME_AFTERNOON} - {TRADING_END_TIME_AFTERNOON}")
            return
        
        # Now determine which direction to trade based on the current session
        trade_direction = determine_trade_direction(trading_session)
        
        if trade_direction is None:
            print(f"{Fore.YELLOW}⏳ No clear trading signal yet for {trading_session} session. Waiting...")
            return
        
        # Check if liquidation threshold has been met
        if check_liquidations(trade_direction):
            # Enter position
            enter_position(trade_direction)
        else:
            print(f"{Fore.YELLOW}⏳ Waiting for liquidation threshold to be met before entering {trade_direction.upper()} position")
        
    except Exception as e:
        print(f"{Fore.RED}❌ Error in bot execution: {str(e)}")
        print(f"{Fore.RED}📋 Stack trace:\n{traceback.format_exc()}")

if __name__ == "__main__":
    # Display banner
    print_banner()
    
    # Initial bot run
    print(f"{Fore.YELLOW}🚀 Starting first bot cycle...")
    bot()
    
    # Schedule the bot to run every minute
    schedule.every(5).seconds.do(bot)
    
    print(f"{Fore.GREEN}✅ Bot scheduled to run every minute")
    
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
