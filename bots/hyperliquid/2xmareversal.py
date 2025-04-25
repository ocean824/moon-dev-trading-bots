'''
🌙 Moon Dev's 2x MA Reversal Strategy Bot 🚀
This bot implements a strategy that:
- Takes a SHORT when price is above 20 SMA but below 40 SMA
- Takes a LONG when price is above both SMAs
- Uses the following default parameters (from backtest):
  - Fast MA: 20
  - Slow MA: 40
  - Take Profit: 10%
  - Stop Loss: 10%
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
import uuid
import pathlib
import io
import contextlib
import talib

# Add the parent directory to the Python path
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, parent_dir)

# Import local modules
import nice_funcs as n

# Initialize colorama
colorama.init(autoreset=True)

# Load environment variables
load_dotenv()
HYPER_LIQUID_KEY = os.getenv('HYPER_LIQUID_KEY')

# Strategy Constants (from backtest)
SYMBOL = 'BTC'
LEVERAGE = 1
POSITION_SIZE_USD = 10  # Start with minimum size ($10)

# Moving Average Parameters
FAST_MA = 20
SLOW_MA = 40

# Data Parameters
TIMEFRAME = '1d'  # Daily timeframe
LOOKBACK_DAYS = 60  # Get 60 days of data to ensure enough for MA calculation

# Risk Management
TAKE_PROFIT_PERCENT = 10.0
STOP_LOSS_PERCENT = -10.0

# Moon Dev ASCII Art Banner
MOON_DEV_BANNER = f"""{Fore.CYAN}
   __  ___                    ____           
  /  |/  /___  ____  ____    / __ \___  _  __
 / /|_/ / __ \/ __ \/ __ \  / / / / _ \| |/_/
/ /  / / /_/ / /_/ / / / / / /_/ /  __/>  <  
/_/  /_/\____/\____/_/ /_(_)____/\___/_/|_|  
                                             
{Fore.MAGENTA}🚀 2x MA Reversal Trading Bot 🌙{Fore.RESET}
"""

def print_banner():
    """Print Moon Dev banner with strategy info"""
    print(MOON_DEV_BANNER)
    print(f"{Fore.CYAN}{'='*80}")
    print(f"{Fore.YELLOW}🚀 Moon Dev 2x MA Reversal Bot is starting up! 🎯")
    print(f"{Fore.YELLOW}💰 Trading {SYMBOL} with {LEVERAGE}x leverage")
    print(f"{Fore.YELLOW}💵 Position size: ${POSITION_SIZE_USD} USD")
    print(f"{Fore.YELLOW}📊 Strategy: {FAST_MA}/{SLOW_MA} MA Reversal on {TIMEFRAME} timeframe")
    print(f"{Fore.YELLOW}🎯 Take Profit: {TAKE_PROFIT_PERCENT}% | Stop Loss: {abs(STOP_LOSS_PERCENT)}%")
    print(f"{Fore.CYAN}{'='*80}\n")

def get_ma_signals():
    """Calculate moving averages and generate trading signals"""
    try:
        # Get OHLCV data
        print(f"{Fore.CYAN}📊 Fetching {LOOKBACK_DAYS} days of {TIMEFRAME} data for {SYMBOL}...")
        df = n.get_ohlcv2(SYMBOL, TIMEFRAME, LOOKBACK_DAYS)
        
        if df is None or len(df) < SLOW_MA:
            print(f"{Fore.RED}❌ Not enough data to calculate MAs (need at least {SLOW_MA} {TIMEFRAME} candles)")
            print(f"{Fore.RED}Got {len(df) if df is not None else 0} candles")
            return None, None, None, None
        
        # Calculate MAs using talib
        fast_ma = talib.SMA(df['close'], timeperiod=FAST_MA)
        slow_ma = talib.SMA(df['close'], timeperiod=SLOW_MA)
        
        current_price = df['close'].iloc[-1]
        current_fast_ma = fast_ma.iloc[-1]
        current_slow_ma = slow_ma.iloc[-1]
        
        print(f"\n{Fore.CYAN}{'='*50}")
        print(f"{Fore.YELLOW}🔍 Current Market Conditions:")
        print(f"💰 Price: ${current_price:.2f}")
        print(f"📈 {FAST_MA} {TIMEFRAME} MA: ${current_fast_ma:.2f}")
        print(f"📉 {SLOW_MA} {TIMEFRAME} MA: ${current_slow_ma:.2f}")
        print(f"{Fore.CYAN}{'='*50}\n")
        
        return current_price, current_fast_ma, current_slow_ma, df
        
    except Exception as e:
        print(f"{Fore.RED}❌ Error calculating MAs: {str(e)}")
        print(f"{Fore.RED}📋 Stack trace:\n{traceback.format_exc()}")
        return None, None, None, None

def check_entry_conditions(current_price, fast_ma, slow_ma):
    """Check if we should enter a position based on MA conditions"""
    try:
        # First check if we have valid MA values
        if None in [current_price, fast_ma, slow_ma]:
            print(f"{Fore.RED}❌ Missing MA data, cannot check entry conditions")
            return False, None
        
        # Check for short setup: price above fast MA but below slow MA
        if current_price > fast_ma and current_price < slow_ma:
            print(f"{Fore.RED}🔍 SHORT Signal: Price (${current_price:.2f}) above {FAST_MA} MA (${fast_ma:.2f}) but below {SLOW_MA} MA (${slow_ma:.2f})")
            return True, 'short'
        
        # Check for long setup: price above both MAs
        elif current_price > fast_ma and current_price > slow_ma:
            print(f"{Fore.GREEN}🔍 LONG Signal: Price (${current_price:.2f}) above both {FAST_MA} MA (${fast_ma:.2f}) and {SLOW_MA} MA (${slow_ma:.2f})")
            return True, 'long'
        
        print(f"{Fore.YELLOW}😴 No valid setup found")
        return False, None
        
    except Exception as e:
        print(f"{Fore.RED}❌ Error checking entry conditions: {str(e)}")
        print(f"{Fore.RED}📋 Stack trace:\n{traceback.format_exc()}")
        return False, None

def bot():
    """Main bot function that runs on each cycle"""
    try:
        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"{Fore.YELLOW}🌙 Moon Dev's 2x MA Reversal Bot - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 🚀")
        print(f"{Fore.CYAN}{'='*80}")
        
        # Initialize account
        account = LocalAccount = eth_account.Account.from_key(HYPER_LIQUID_KEY)
        
        # First check for existing positions and handle them
        print(f"\n{Fore.CYAN}🔍 Checking for existing positions...")
        positions, im_in_pos, pos_size, pos_sym, entry_px, pnl_perc, is_long = n.get_position(SYMBOL, account)
        
        if im_in_pos:
            print(f"{Fore.GREEN}📈 In position: {'LONG' if is_long else 'SHORT'} {pos_size} {SYMBOL} | Entry: ${entry_px:.2f} | PnL: {pnl_perc:.2f}%")
            
            # Check if we need to close based on profit/loss targets
            n.pnl_close(SYMBOL, TAKE_PROFIT_PERCENT, STOP_LOSS_PERCENT, account)
            
            # Get position again to see if it was closed
            positions, im_in_pos, pos_size, pos_sym, entry_px, pnl_perc, is_long = n.get_position(SYMBOL, account)
            
            if im_in_pos:
                print(f"{Fore.YELLOW}⏳ Position still active, skipping entry checks...")
                return
        
        # Get current MA signals
        current_price, fast_ma, slow_ma, df = get_ma_signals()
        
        # Check entry conditions
        should_enter, side = check_entry_conditions(current_price, fast_ma, slow_ma)
        
        if should_enter and not im_in_pos:
            # Get orderbook data
            print(f"\n{Fore.CYAN}📚 Fetching orderbook data...")
            ask, bid, l2_data = n.ask_bid(SYMBOL)
            print(f"{Fore.GREEN}💰 Current price - Ask: ${ask:.2f}, Bid: ${bid:.2f}")
            
            # Adjust leverage and position size
            lev, pos_size = n.adjust_leverage_usd_size(SYMBOL, POSITION_SIZE_USD, LEVERAGE, account)
            print(f"{Fore.YELLOW}📊 Leverage: {lev}x | Position size: {pos_size}")
            
            # Cancel any existing orders
            n.cancel_all_orders(account)
            print(f"{Fore.YELLOW}🚫 Canceled all existing orders")
            
            if side == 'short':
                # Place a sell order at the current ask price
                n.limit_order(SYMBOL, False, pos_size, ask, False, account)
                print(f"{Fore.RED}💸 Placed SELL order for {pos_size} {SYMBOL} at ${ask}")
                print(f"{Fore.RED}📉 MA Reversal Short Entry")
            else:  # side == 'long'
                # Place a buy order at the current bid price
                n.limit_order(SYMBOL, True, pos_size, bid, False, account)
                print(f"{Fore.GREEN}🛒 Placed BUY order for {pos_size} {SYMBOL} at ${bid}")
                print(f"{Fore.GREEN}📈 MA Reversal Long Entry")
            
            print(f"{Fore.YELLOW}⏳ Order placed, waiting for fill...")
        else:
            print(f"{Fore.YELLOW}⏳ No entry conditions met, continuing to monitor...")
        
        # Easter egg
        print(f"\n{Fore.MAGENTA}🌕 Thanks for using Moon Dev Trading Bots! 🤖")
        
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
    schedule.every(1).minutes.do(bot)
    
    print(f"{Fore.GREEN}✅ Bot scheduled to run every minute")
    
    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except Exception as e:
            print(f"{Fore.RED}❌ Encountered an error: {e}")
            print(f"{Fore.RED}📋 Stack trace:\n{traceback.format_exc()}")
            time.sleep(10)
