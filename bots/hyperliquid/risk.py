import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz
from termcolor import colored
from colorama import Fore, Back, Style
import traceback
import nice_funcs as n
from hyperliquid.utils import constants
from hyperliquid.exchange import Exchange
import time
from dotenv import load_dotenv
from eth_account.signers.local import LocalAccount
import eth_account

# Initialize colorama for terminal colors
from colorama import init
init(autoreset=True)

# Default constants
DEFAULT_LOOKBACK_HOURS = 12
DEFAULT_MAX_DRAWDOWN_PERCENT = 25
BALANCE_HISTORY_FILE = "balance_history.csv"

# Constants for kill switch
SYMBOL = 'ZEC'
KILL_UNDER_CONSTANT = True  # Toggle this to enable/disable the kill under price check
KILL_PRICE = 665 # Example kill price, adjust as needed
KILL_OVER_CONSTANT = True  # Toggle this to enable/disable the kill over price check
KILL_OVER_PRICE = 790 # Example kill over price, adjust as needed

def get_balance_history_path():
    """Get the path to the balance history CSV file"""
    # Get the directory of the current file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Create data directory if it doesn't exist
    data_dir = os.path.join(current_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    # Return the full path to the balance history file
    return os.path.join(data_dir, BALANCE_HISTORY_FILE)

def initialize_balance_history(account):
    """Initialize balance history if it doesn't exist"""
    try:
        history_path = get_balance_history_path()
        
        # If file doesn't exist, create it with current balance
        if not os.path.exists(history_path):
            try:
                # First try direct API call for most accurate balance - Moon Dev fix
                exchange = Exchange(account, constants.MAINNET_API_URL)
                account_value = exchange.get_account_value(account.address, account)
                if 'data' in account_value and 'accountValue' in account_value['data']:
                    current_balance = float(account_value['data']['accountValue'])
                    print(f"{Back.GREEN}{Fore.BLACK}✅ Got balance from direct API call: ${current_balance:,.2f}{Style.RESET_ALL}")
                else:
                    # If direct API fails, try get_balance function
                    current_balance = n.get_balance(account)
                    if current_balance <= 0:
                        print(f"{Back.RED}{Fore.WHITE}❌ Could not get actual balance. Please check your connection and try again.{Style.RESET_ALL}")
                        return False
                    print(f"{Back.GREEN}{Fore.BLACK}✅ Got balance from get_balance: ${current_balance:,.2f}{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Back.RED}{Fore.WHITE}❌ Error getting balance: {str(e)}{Style.RESET_ALL}")
                print(f"{Back.RED}{Fore.WHITE}❌ Please check your connection and try again.{Style.RESET_ALL}")
                return False
                
            # Only create history file if we got a valid balance
            if current_balance > 0:
                df = pd.DataFrame({
                    'timestamp': [datetime.now()],
                    'balance': [current_balance]
                })
                df.to_csv(history_path, index=False)
                print(f"{Back.GREEN}{Fore.BLACK}📊 Created new balance history file at {history_path}{Style.RESET_ALL}")
                print(f"{Back.GREEN}{Fore.BLACK}💰 Initial balance: ${current_balance:,.2f}{Style.RESET_ALL}")
                return True
            else:
                print(f"{Back.RED}{Fore.WHITE}❌ Invalid balance value: ${current_balance:,.2f}{Style.RESET_ALL}")
                return False
            
        return True
        
    except Exception as e:
        print(f"{Fore.RED}❌ Error initializing balance history: {str(e)}")
        print(f"{Fore.RED}📋 Stack trace:\n{traceback.format_exc()}")
        return False

def update_balance_history(account):
    """Update the balance history with current balance"""
    try:
        history_path = get_balance_history_path()
        try:
            # Use the existing get_balance function from nice_funcs
            current_balance = n.get_balance(account)
            if current_balance <= 0:
                # If unable to get balance, read the last known balance
                if os.path.exists(history_path):
                    df = pd.read_csv(history_path)
                    current_balance = df['balance'].iloc[-1]
                    print(f"{Back.GREEN}{Fore.BLACK}⚠️ Using last known balance: ${current_balance:,.2f}{Style.RESET_ALL}")
                else:
                    current_balance = 1000  # Default balance
                    print(f"{Back.GREEN}{Fore.BLACK}⚠️ Using default balance: ${current_balance:,.2f}{Style.RESET_ALL}")
        except Exception as e:
            # In case of error, use the last known balance or default
            if os.path.exists(history_path):
                df = pd.read_csv(history_path)
                current_balance = df['balance'].iloc[-1]
                print(f"{Back.GREEN}{Fore.BLACK}⚠️ Error getting balance: {str(e)}{Style.RESET_ALL}")
                print(f"{Back.GREEN}{Fore.BLACK}⚠️ Using last known balance: ${current_balance:,.2f}{Style.RESET_ALL}")
            else:
                current_balance = 1000  # Default balance
                print(f"{Back.GREEN}{Fore.BLACK}⚠️ Using default balance: ${current_balance:,.2f}{Style.RESET_ALL}")
                
        current_time = datetime.now()
        
        # Read existing history or create new DataFrame
        if os.path.exists(history_path):
            df = pd.read_csv(history_path)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        else:
            df = pd.DataFrame(columns=['timestamp', 'balance'])
        
        # Add new balance record
        new_record = pd.DataFrame({
            'timestamp': [current_time],
            'balance': [current_balance]
        })
        df = pd.concat([df, new_record], ignore_index=True)
        
        # Save updated history
        df.to_csv(history_path, index=False)
        print(f"{Back.GREEN}{Fore.BLACK}📊 Updated balance history: ${current_balance:,.2f}{Style.RESET_ALL}")
        return True
        
    except Exception as e:
        print(f"{Fore.RED}❌ Error updating balance history: {str(e)}")
        print(f"{Fore.RED}📋 Stack trace:\n{traceback.format_exc()}")
        return False

def check_drawdown(account, lookback_hours=DEFAULT_LOOKBACK_HOURS, max_drawdown_percent=DEFAULT_MAX_DRAWDOWN_PERCENT):
    """
    Check if current drawdown exceeds the maximum allowed
    
    Args:
        account: Trading account
        lookback_hours: Hours to look back for balance comparison (default: 12)
        max_drawdown_percent: Maximum allowed drawdown percentage (default: 20)
    
    Returns:
        tuple: (should_kill, message, drawdown_percent)
    """
    try:
        history_path = get_balance_history_path()
        
        # If history file doesn't exist, create it
        if not os.path.exists(history_path):
            print(f"{Back.GREEN}{Fore.BLACK}⚠️ No balance history found, initializing...{Style.RESET_ALL}")
            if not initialize_balance_history(account):
                return False, "Failed to initialize balance history", 0
            return False, "Initialized balance history", 0
        
        # Read balance history
        df = pd.read_csv(history_path)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Get current balance using the existing function
        current_balance = n.get_balance(account)
        if current_balance <= 0:
            print(f"{Back.RED}{Fore.WHITE}❌ Could not get current balance. Please check your connection.{Style.RESET_ALL}")
            return False, "Failed to get current balance", 0
            
        current_time = datetime.now()
        
        # Calculate lookback time
        lookback_time = current_time - timedelta(hours=lookback_hours)
        
        # Get historical balance within lookback period
        historical_balances = df[df['timestamp'] >= lookback_time]['balance']
        
        if historical_balances.empty:
            print(f"{Back.GREEN}{Fore.BLACK}⚠️ No balance history within {lookback_hours} hours, using latest available balance{Style.RESET_ALL}")
            # Use the most recent balance if no history in lookback period
            peak_balance = df['balance'].iloc[-1]
        else:
            # Get the highest balance in the lookback period
            peak_balance = historical_balances.max()
        
        # Calculate drawdown
        drawdown_percent = ((peak_balance - current_balance) / peak_balance) * 100
        
        # Print status with green background
        print(f"\n{Back.GREEN}{Fore.BLACK}{'='*80}{Style.RESET_ALL}")
        print(f"{Back.GREEN}{Fore.BLACK}{'='*30} 📊 MOON DEV RISK MANAGEMENT 📊 {'='*30}{Style.RESET_ALL}")
        print(f"{Back.GREEN}{Fore.BLACK}{'='*80}{Style.RESET_ALL}")
        print(f"{Back.GREEN}{Fore.BLACK}💰 Current Balance: ${current_balance:,.2f}{Style.RESET_ALL}")
        print(f"{Back.GREEN}{Fore.BLACK}📈 Peak Balance: ${peak_balance:,.2f}{Style.RESET_ALL}")
        print(f"{Back.GREEN}{Fore.BLACK}📉 Drawdown: {drawdown_percent:.2f}%{Style.RESET_ALL}")
        print(f"{Back.GREEN}{Fore.BLACK}⏱️ Lookback Period: {lookback_hours} hours{Style.RESET_ALL}")
        print(f"{Back.GREEN}{Fore.BLACK}🎯 Max Allowed Drawdown: {max_drawdown_percent}%{Style.RESET_ALL}")
        print(f"{Back.GREEN}{Fore.BLACK}{'='*80}{Style.RESET_ALL}\n")
        
        # Check if drawdown exceeds maximum
        if drawdown_percent >= max_drawdown_percent:
            message = f"🚨 MOON DEV ALERT! MAX DRAWDOWN EXCEEDED! ({drawdown_percent:.2f}% > {max_drawdown_percent}%)"
            print(f"{Back.RED}{Fore.WHITE}{Style.BRIGHT}{message}{Style.RESET_ALL}")
            return True, message, drawdown_percent
        
        # Update balance history
        update_balance_history(account)
        
        return False, f"🌙 Drawdown within limits ({drawdown_percent:.2f}%)", drawdown_percent
        
    except Exception as e:
        print(f"{Fore.RED}❌ Error checking drawdown: {str(e)}")
        print(f"{Fore.RED}📋 Stack trace:\n{traceback.format_exc()}")
        return False, "Error checking drawdown", 0

def check_and_kill_if_below_price(symbol, account, stop_loss_price):
    """
    Check if the current price of the symbol is below the stop loss price or above kill over price and call kill switch if true.

    Args:
        symbol: The trading symbol to check.
        account: The trading account.
        stop_loss_price: The stop loss price to compare against.
    """
    # Get the current price of the symbol and timestamp
    current_price = n.get_current_price(symbol)
    current_time = datetime.now(pytz.timezone('US/Eastern'))
    time_str = current_time.strftime('%Y-%m-%d %I:%M:%S %p EST')
    
    # Print price check header
    print(f"\n{Back.GREEN}{Fore.BLACK}{'='*100}{Style.RESET_ALL}")
    print(f"{Back.GREEN}{Fore.BLACK}🌙 MOON DEV PRICE CHECK STATUS 🌙{Style.RESET_ALL}")
    print(f"{Back.GREEN}{Fore.BLACK}{'='*100}{Style.RESET_ALL}")
    print(f"{Back.GREEN}{Fore.BLACK}⏰ Time: {time_str}{Style.RESET_ALL}")
    print(f"{Back.GREEN}{Fore.BLACK}📊 Current {symbol} Price: ${current_price:,.2f}{Style.RESET_ALL}")
    print(f"{Back.GREEN}{Fore.BLACK}⚠️ Kill Under Price: ${stop_loss_price:,.2f} | Kill Over Price: ${KILL_OVER_PRICE:,.2f}{Style.RESET_ALL}")
    print(f"{Back.GREEN}{Fore.BLACK}{'='*100}{Style.RESET_ALL}\n")

    # Check if the current price is below the stop loss price or above kill over price
    if current_price < stop_loss_price:
        print(f"\n{Back.RED}{Fore.WHITE}{'='*100}{Style.RESET_ALL}")
        print(f"{Back.RED}{Fore.WHITE}⏰ {time_str}{Style.RESET_ALL}")
        print(f"{Back.RED}{Fore.WHITE}🚨 MOON DEV KILL SWITCH - PRICE TOO LOW 🚨{Style.RESET_ALL}")
        print(f"{Back.RED}{Fore.WHITE}💥 {symbol} Price (${current_price:,.2f}) < Kill Under Price (${stop_loss_price:,.2f}){Style.RESET_ALL}")
        print(f"{Back.RED}{Fore.WHITE}🔄 CLOSING ALL POSITIONS NOW!{Style.RESET_ALL}")
        print(f"{Back.RED}{Fore.WHITE}{'='*100}{Style.RESET_ALL}\n")
        n.kill_switch_mkt(symbol, account)
    elif KILL_OVER_CONSTANT and current_price > KILL_OVER_PRICE:
        print(f"\n{Back.RED}{Fore.WHITE}{'='*100}{Style.RESET_ALL}")
        print(f"{Back.RED}{Fore.WHITE}⏰ {time_str}{Style.RESET_ALL}")
        print(f"{Back.RED}{Fore.WHITE}🚨 MOON DEV KILL SWITCH - PRICE TOO HIGH 🚨{Style.RESET_ALL}")
        print(f"{Back.RED}{Fore.WHITE}💥 {symbol} Price (${current_price:,.2f}) > Kill Over Price (${KILL_OVER_PRICE:,.2f}){Style.RESET_ALL}")
        print(f"{Back.RED}{Fore.WHITE}🔄 CLOSING ALL POSITIONS NOW!{Style.RESET_ALL}")
        print(f"{Back.RED}{Fore.WHITE}{'='*100}{Style.RESET_ALL}\n")
        n.kill_switch_mkt(symbol, account)
    else:
        print(f"{Back.GREEN}{Fore.BLACK}✅ MOON DEV SAYS: Price is within safe trading range! 🚀{Style.RESET_ALL}\n")

def risk_check(account, lookback_hours=DEFAULT_LOOKBACK_HOURS, max_drawdown_percent=DEFAULT_MAX_DRAWDOWN_PERCENT):
    """
    Main risk check function that can be imported into any bot
    
    Args:
        account: Trading account
        lookback_hours: Hours to look back for balance comparison (default: 12)
        max_drawdown_percent: Maximum allowed drawdown percentage (default: 20)
    
    Returns:
        bool: True if positions should be closed, False otherwise
    """
    try:
        should_kill, message, drawdown_percent = check_drawdown(
            account, 
            lookback_hours, 
            max_drawdown_percent
        )
        
        if should_kill:
            print(f"{Back.RED}{Fore.WHITE}🛑 {message}{Style.RESET_ALL}")
            print(f"{Back.RED}{Fore.WHITE}💥 MOON DEV IS CLOSING ALL POSITIONS DUE TO MAX DRAWDOWN!{Style.RESET_ALL}")
            # Use the existing close_all_positions function from nice_funcs
            try:
                n.close_all_positions(account)
                print(f"{Back.RED}{Fore.WHITE}✅ All positions closed successfully!{Style.RESET_ALL}")
            except Exception as close_err:
                print(f"{Back.RED}{Fore.WHITE}❌ Error closing positions: {str(close_err)}{Style.RESET_ALL}")
                # Try alternate method
                try:
                    n.close_all_positions_mkt(account)
                    print(f"{Back.RED}{Fore.WHITE}✅ Used market close successfully!{Style.RESET_ALL}")
                except Exception as mkt_err:
                    print(f"{Back.RED}{Fore.WHITE}❌ Error using market close: {str(mkt_err)}{Style.RESET_ALL}")
            return True
        else:
            print(f"{Back.GREEN}{Fore.BLACK}✅ 🌙 MOON DEV SAYS: {message}{Style.RESET_ALL}")

        # Check if the kill under constant is enabled and perform the check
        if KILL_UNDER_CONSTANT:
            check_and_kill_if_below_price(SYMBOL, account, KILL_PRICE)  # Example symbol, adjust as needed
        
        return False
        
    except Exception as e:
        print(f"{Fore.RED}📋 Stack trace:\n{traceback.format_exc()}")
        print(f"{Fore.RED}❌ Error in risk check: {str(e)}")
        return False

if __name__ == "__main__":
    import sys
    
    # Example usage of risk_check when running this file directly
    # Initialize account using environment variable - Moon Dev
    load_dotenv()
    HYPER_LIQUID_KEY = os.getenv('HYPER_LIQUID_KEY') # Switch between HYPER_LIQUID_KEY or HYPER_LIQUID_KEY_COLLECTOR
    account = LocalAccount = eth_account.Account.from_key(HYPER_LIQUID_KEY)
    
    # Check command-line arguments to determine which check to run
    if len(sys.argv) > 1 and sys.argv[1] == 'price_check':
        print("🌙 MOON DEV: Starting price check loop... 🚀")
        while True:
            try:
                # Run price check
                print("🌙 MOON DEV: Running price check... 🚀")
                check_and_kill_if_below_price(SYMBOL, account, KILL_PRICE)
                print("🌙 MOON DEV: Price check completed! 🌟")
                
                # Wait for 15 seconds before the next check
                time.sleep(1)
            except Exception as e:
                print(f"{Fore.RED}❌ Encountered an error: {e}")
                print(f"{Fore.RED}📋 Stack trace:\n{traceback.format_exc()}")
                # Wait before retrying to avoid rapid error logging
                time.sleep(1)
    else:
        print("🌙 MOON DEV: Starting full risk check loop... 🚀")
        while True:
            try:
                # Run full risk check
                print("🌙 MOON DEV: Running risk check... 🚀")
                risk_check(account)
                print("🌙 MOON DEV: Risk check completed! 🌟")
                
                # Wait for 15 seconds before the next check
                time.sleep(1)
            except Exception as e:
                print(f"{Fore.RED}❌ Encountered an error: {e}")
                print(f"{Fore.RED}📋 Stack trace:\n{traceback.format_exc()}")
                # Wait before retrying to avoid rapid error logging
                time.sleep(1)
