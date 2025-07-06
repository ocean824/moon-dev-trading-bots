'''
🌙 MOON DEV Close All Positions Script 🚀
Emergency position closer - closes ALL open positions on HyperLiquid

Connects to your account and closes every position using the kill switch.
Choose between normal closes (limit orders) or market closes (faster).
'''

import sys
import os
from termcolor import colored
import colorama
from colorama import Fore, Back, Style
from eth_account.signers.local import LocalAccount
import eth_account
from dotenv import load_dotenv

# Add the parent directory to the Python path so we can import modules from there
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, parent_dir)

# Import local modules
import nice_funcs as n

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
                                             
{Fore.RED}🚨 EMERGENCY POSITION CLOSER 🚨{Fore.RESET}
"""

# Initialize account
account = LocalAccount = eth_account.Account.from_key(HYPER_LIQUID_KEY)

def print_banner():
    """Print Moon Dev banner with warning"""
    print(MOON_DEV_BANNER)
    print(f"{Fore.RED}⚠️ WARNING: This will close ALL open positions! ⚠️")
    print(f"{Fore.YELLOW}🌙 Moon Dev Emergency Position Closer - Use with caution! 🚀")

def main():
    """Main function to close all positions"""
    try:
        print_banner()
        
        # Get current positions info first
        print(f"\n{Fore.CYAN}🔍 Moon Dev checking current positions...")
        
        # Check account balance and positions
        balance = n.get_balance(account)
        print(f"{Fore.GREEN}💰 Account balance: ${balance:,.2f}")
        
        # Ask user for confirmation
        print(f"\n{Fore.YELLOW}Choose closing method:")
        print(f"{Fore.CYAN}1. Normal close (limit orders - safer)")
        print(f"{Fore.RED}2. Market close (aggressive fills - faster)")
        print(f"{Fore.YELLOW}3. Cancel and exit")
        
        choice = input(f"\n{Fore.WHITE}Enter your choice (1/2/3): ").strip()
        
        if choice == "1":
            print(f"\n{Fore.GREEN}🎯 Moon Dev closing all positions with limit orders...")
            n.close_all_positions(account)
            print(f"{Fore.GREEN}✅ All positions closed successfully! 🎉")
            
        elif choice == "2":
            print(f"\n{Fore.RED}🚀 Moon Dev closing all positions with market orders...")
            n.close_all_positions_mkt(account)
            print(f"{Fore.GREEN}✅ All positions closed successfully! 🎉")
            
        elif choice == "3":
            print(f"{Fore.YELLOW}👋 Moon Dev cancelled - no positions closed")
            return
            
        else:
            print(f"{Fore.RED}❌ Invalid choice. Exiting for safety.")
            return
            
        # Final balance check
        print(f"\n{Fore.CYAN}📊 Moon Dev final check...")
        final_balance = n.get_balance(account)
        print(f"{Fore.GREEN}💰 Final account balance: ${final_balance:,.2f}")
        
        print(f"\n{Fore.MAGENTA}🌕 Moon Dev position closer complete! Stay safe! 🌙")
        
    except Exception as e:
        print(f"{Fore.RED}❌ Moon Dev encountered an error: {str(e)}")
        print(f"{Fore.RED}⚠️ Please check your positions manually!")

if __name__ == "__main__":
    main() 