'''
backetsted with this code: 64_intrashort.py

🌙 MOON DEV Parabolic Move Short Strategy Bot 🚀
Looking for parabolic upside moves to short back down

Strategy Logic:
- Calculate rolling mean and standard deviation over lookback window
- Calculate upper threshold = mean + (std_dev_multiplier * std)
- Go SHORT when price breaks above the parabolic threshold
- Use stop loss above entry and take profit below entry

Optimized Parameters from Backtests:
- BTC: Lookback=20, StdDev=3.0, TP=5.0%, SL=3.0%
- TRUMP: Lookback=10, StdDev=2.2, TP=7.0%, SL=2.0%



'''

import sys
import os
import time
import schedule
import json
import requests
import pandas as pd
import numpy as np
import pandas_ta as ta
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

# No wrappers needed - using nice_funcs directly

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
                                             
{Fore.MAGENTA}🚀 Parabolic Move Short Strategy Bot 🌙{Fore.RESET}
"""

# ===== CONFIGURATION =====
# Symbol to trade
SYMBOL = 'TRUMP'  # Can be changed to BTC, ETH, etc.
LEVERAGE = 1      # No leverage - safest trading
POSITION_SIZE_USD = 10  # Position size in USD (minimum for HyperLiquid)

# Strategy Parameters - TRUMP Optimized from 64_intrashort.py backtest (50.8% returns)
LOOKBACK_WINDOW = 10      # Optimized: 10 periods
STD_DEV_MULTIPLIER = 2.2  # Optimized: 2.2 standard deviations
TAKE_PROFIT_PERCENT = 7.0  # Optimized: 7.0% take profit
STOP_LOSS_PERCENT = -2.0   # Optimized: 2.0% stop loss (negative for short)

# Data collection settings
TIMEFRAME = '5m'          # Timeframe for data collection (5m matches backtest)

# Initialize account
account = LocalAccount = eth_account.Account.from_key(HYPER_LIQUID_KEY)

def print_banner():
    """Print Moon Dev banner"""
    print(MOON_DEV_BANNER)
    print(f"{Fore.YELLOW}🚀 Moon Dev Parabolic Short Bot - {SYMBOL} {LEVERAGE}x ${POSITION_SIZE_USD} - TP:{TAKE_PROFIT_PERCENT}% SL:{abs(STOP_LOSS_PERCENT)}% 🌙")

def get_historical_data(symbol, timeframe='5m', lookback_days=3):
    """Get historical price data for the symbol"""
    try:
        # Use the get_ohlcv2 function from nice_funcs
        snapshot_data = n.get_ohlcv2(symbol, timeframe, lookback_days)
        if snapshot_data is None or len(snapshot_data) == 0:
            return None
        
        # Process the data using nice_funcs function
        df = n.process_data_to_df(snapshot_data)
        if df is None or df.empty or 'close' not in df.columns:
            return None
        
        df['close'] = df['close'].astype(float)
        print(f"{Fore.GREEN}📊 Moon Dev got {len(df)} data points for {symbol} - Latest: ${df['close'].iloc[-1]:.4f}")
        return df
        
    except Exception as e:
        print(f"{Fore.RED}❌ Moon Dev error getting data: {str(e)}")
        return None

def calculate_parabolic_threshold(price_data, lookback_window, std_dev_multiplier):
    """
    Calculate the parabolic threshold using rolling mean and standard deviation
    
    Args:
        price_data: Series of price data
        lookback_window: Number of periods for rolling calculation
        std_dev_multiplier: Multiplier for standard deviation
    
    Returns:
        tuple: (rolling_mean, rolling_std, upper_threshold)
    """
    try:
        # Calculate rolling mean and standard deviation
        rolling_mean = price_data.rolling(window=lookback_window).mean()
        rolling_std = price_data.rolling(window=lookback_window).std()
        
        # Calculate upper threshold (mean + std_dev * std)
        upper_threshold = rolling_mean + (std_dev_multiplier * rolling_std)
        
        return rolling_mean, rolling_std, upper_threshold
        
    except Exception as e:
        print(f"{Fore.RED}❌ Error calculating parabolic threshold: {str(e)}")
        return None, None, None

def should_enter_short(current_price, upper_threshold, rolling_mean, rolling_std):
    """Determine if we should enter a short position"""
    if pd.isna(upper_threshold):
        return False, "🌙 Moon Dev waiting for enough data"
    
    # Check if price has broken above the parabolic threshold
    if current_price > upper_threshold:
        distance_from_mean = ((current_price - rolling_mean) / rolling_mean) * 100
        return True, f"🚀 PARABOLIC MOVE DETECTED! Price ${current_price:.4f} > threshold ${upper_threshold:.4f} ({distance_from_mean:.2f}% from mean)"
    
    distance_to_threshold = ((upper_threshold - current_price) / current_price) * 100
    return False, f"⏳ Waiting for parabolic move - {distance_to_threshold:.2f}% below threshold"

def bot():
    """Main bot function that runs on each cycle"""
    try:
        print(f"\n{Fore.YELLOW}🌙 Moon Dev Parabolic Short Bot - {datetime.now().strftime('%H:%M:%S')} 🚀")
        
        # First action: Check for existing positions and close if profit/loss targets hit
        positions, im_in_pos, mypos_size, pos_sym, entry_px, pnl_perc, is_long = n.get_position(SYMBOL, account)
        
        if im_in_pos:
            print(f"{Fore.GREEN}📈 Moon Dev in position: {pos_sym} {'LONG' if is_long else 'SHORT'} Size:{mypos_size} Entry:${entry_px:.4f} PnL:{pnl_perc:.2f}%")
            
            # Check if we need to close based on profit/loss targets
            n.pnl_close(SYMBOL, TAKE_PROFIT_PERCENT, STOP_LOSS_PERCENT, account)
            return  # Exit early since we're already in a position
        else:
            print(f"{Fore.YELLOW}📉 Moon Dev not in position, looking for parabolic moves...")
        
        # Get historical data
        historical_data = get_historical_data(SYMBOL, TIMEFRAME, 3)  # 3 days of data
        if historical_data is None:
            print(f"{Fore.RED}❌ Moon Dev couldn't get historical data - skipping cycle")
            return
        
        # Calculate parabolic threshold
        rolling_mean, rolling_std, upper_threshold = calculate_parabolic_threshold(
            historical_data['close'], LOOKBACK_WINDOW, STD_DEV_MULTIPLIER
        )
        
        if rolling_mean is None:
            print(f"{Fore.RED}❌ Moon Dev failed to calculate indicators - skipping cycle")
            return
        
        # Get latest values
        current_price = historical_data['close'].iloc[-1]
        latest_mean = rolling_mean.iloc[-1]
        latest_std = rolling_std.iloc[-1]
        latest_threshold = upper_threshold.iloc[-1]
        
        # Display current market analysis
        distance_from_mean = ((current_price - latest_mean) / latest_mean) * 100
        print(f"{Fore.CYAN}🧮 Moon Dev Analysis: Price:${current_price:.4f} Mean:${latest_mean:.4f} Threshold:${latest_threshold:.4f} Distance:{distance_from_mean:.2f}%")
        
        # Check if we should enter a short position
        should_enter, reason = should_enter_short(current_price, latest_threshold, latest_mean, latest_std)
        print(f"{Fore.YELLOW}🤖 Moon Dev Decision: {reason}")
        
        if should_enter:
            print(f"{Fore.GREEN}🚀 Moon Dev ENTERING SHORT POSITION! 🎯")
            
            # Adjust leverage and position size first
            lev, pos_size = n.adjust_leverage_usd_size(SYMBOL, POSITION_SIZE_USD, LEVERAGE, account)
            print(f"{Fore.GREEN}📊 Moon Dev leverage:{lev}x size:{pos_size}")
            
            # Entry loop - keep trying until we get filled
            max_attempts = 20
            attempt = 0
            
            while attempt < max_attempts:
                attempt += 1
                print(f"{Fore.YELLOW}🎯 Moon Dev entry attempt {attempt}/{max_attempts}")
                
                # Cancel all existing orders first
                n.cancel_all_orders(account)
                time.sleep(0.5)  # Brief pause after canceling
                
                # Get fresh orderbook data
                ask, bid, l2_data = n.ask_bid(SYMBOL)
                print(f"{Fore.GREEN}💰 Moon Dev fresh prices - Ask:${ask:.4f} Bid:${bid:.4f}")
                
                # Place short order at current ask price (market-like limit order)
                n.limit_order(SYMBOL, False, pos_size, ask, False, account)
                print(f"{Fore.RED}💸 Moon Dev SHORT order placed: SELL {pos_size} {SYMBOL} at ${ask:.4f}")
                
                # Wait a moment for order to potentially fill
                time.sleep(2)
                
                # Check if we're now in position
                positions, im_in_pos_check, _, _, _, _, _ = n.get_position(SYMBOL, account)
                
                if im_in_pos_check:
                    print(f"{Fore.GREEN}✅ Moon Dev FILLED! Successfully entered SHORT position! 🎉")
                    print(f"{Fore.RED}📉 SHORT {SYMBOL} | Size: {pos_size} | Entry: ${ask:.4f} - TP:{TAKE_PROFIT_PERCENT}% SL:{abs(STOP_LOSS_PERCENT)}%")
                    break
                else:
                    print(f"{Fore.YELLOW}⏳ Moon Dev order not filled yet, trying again with fresh prices...")
            
            if attempt >= max_attempts:
                print(f"{Fore.RED}❌ Moon Dev couldn't get filled after {max_attempts} attempts - market may be moving too fast")
            
        print(f"{Fore.MAGENTA}🌕 Moon Dev hunting parabolic moves! 🎯")
        
    except Exception as e:
        print(f"{Fore.RED}❌ Moon Dev error: {str(e)}")

if __name__ == "__main__":
    # Display banner
    print_banner()
    
    # Initial bot run
    bot()
    
    # Schedule the bot to run every minute
    schedule.every(1).minutes.do(bot)
    print(f"{Fore.GREEN}✅ Moon Dev bot running every minute - hunting parabolic moves! 🎯")
    
    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}👋 Moon Dev bot stopped by user")
            break
        except Exception as e:
            print(f"{Fore.RED}❌ Moon Dev error: {e}")
            time.sleep(10)
