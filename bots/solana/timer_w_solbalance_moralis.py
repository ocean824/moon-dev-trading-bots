# adding my solana balance in usdc to the timer bot below

import time
import os
from datetime import datetime, timedelta
import random
from pygame import mixer
import csv
# import pandas as pd # Pandas might not be needed as much with direct Moralis processing
import requests # Still needed for Moralis calls if not using their SDK directly for HTTP
from dotenv import load_dotenv
from moralis import sol_api # Import Moralis Solana API

# Load environment variables
load_dotenv()

# Moon Dev's public address
MY_ADDRESS = "G1vNV2SkzGPTBTDd7c3iypL4TPNGbe37rEbJb7cxVTQS"

# USDC token address on Solana (can be used for reference if needed)
# USDC_TOKEN = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v" # Not directly used in Moralis balance fetch

# IGNORE_LIST: Tokens to exclude from the printed summary (but still included in total balance)
IGNORE_LIST = ['59Nv97TEcKjcz2oZvZnsSCXK6kESvCigyZUHpxnDpump','5fBmCvqNp1H82SfHrzyMaRJoFg3aa6SAaYZQb1KBmoon', '7TUw3iAMM2c5H95BzfifgQCkdwGJyrPzuJ2u7nzhPUMP', 'WHfYPSqvUnhCoJfjQJrZJVhz2GzzH5Q2BTJoabnpump', 'WHfYPSqvUnhCoJfjQJrZJVhz2GzzH5Q2BTJoabnpump']

# Get API keys from environment
# BIRDEYE_KEY = os.getenv('BIRDEYE_KEY') # No longer primary for balance
# if not BIRDEYE_KEY:
#     raise ValueError("BIRDEYE_KEY environment variable not set! Please set it in your .env file")

MORALIS_KEY = os.getenv('MORALIS_KEY')
if not MORALIS_KEY:
    raise ValueError("MORALIS_KEY environment variable not set! Please set it in your .env file.")

# Make this a variable instead of a constant
timer_minutes = .1  # Default time in minutes

# ANSI escape codes for colors and styling
CLEAR = "\033[2J"  # Clear screen
WHITE = "\033[97m"
RED_BG = "\033[41m"
RESET = "\033[0m"
BOLD = "\033[1m"
HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"


def token_price_moralis(token_mint_address):
    """
    Get token price using Moralis API. Returns the USD price of the token.
    Similar to token_price() but uses Moralis instead of BirdEye.
    """
    try:
        # Moralis API endpoint for token price
        url = f"https://solana-gateway.moralis.io/token/mainnet/{token_mint_address}/price"
        
        headers = {
            "accept": "application/json",
            "X-API-Key": os.getenv('MORALIS_KEY')
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            price_data = response.json()
            if "usdPrice" in price_data:
                usd_price = price_data.get("usdPrice", 0.0)
                if usd_price is not None:
                    print(f"🌙 Moon Dev's Price Scanner: ${usd_price} for {token_mint_address[:4]} 💰")
                    return float(usd_price)
                else:
                    print(f"🚫 Moon Dev's Price Alert: No price data for {token_mint_address[:4]} 🌑")
                    return None
            else:
                print(f"⚠️ Moon Dev's Warning: Invalid response for {token_mint_address[:4]} 🌑")
                return None
        else:
            print(f"❌ Moon Dev's API Error {response.status_code} for {token_mint_address[:4]} 🌑")
            return None
            
    except Exception as e:
        print(f"💥 Moon Dev's Error Report for {token_mint_address[:4]}: {str(e)} 🌑")
        return None

def fetch_wallet_balance():
    """Gets total USD value of all tokens in wallet using Moralis API"""
    total_wallet_usd_value = 0.0
    token_summaries = []

    try:
        # 1. Get native SOL balance and its USD value
        portfolio_params = {
            "network": "mainnet",
            "address": MY_ADDRESS,
        }
        portfolio_result = sol_api.account.get_portfolio(
            api_key=MORALIS_KEY,
            params=portfolio_params,
        )

        native_sol_balance_lamports = portfolio_result.get("nativeBalance", {}).get("lamports", "0")
        native_sol_amount = int(native_sol_balance_lamports) / (10**9) # SOL has 9 decimals

        if native_sol_amount > 0:
            try:
                sol_price_params = {"network": "mainnet", "address": "So11111111111111111111111111111111111111112"} # Wrapped SOL mint address
                sol_price_data = sol_api.token.get_token_price(api_key=MORALIS_KEY, params=sol_price_params)
                sol_usd_price = sol_price_data.get("usdPrice", 0.0)
                native_sol_usd_value = native_sol_amount * sol_usd_price
                total_wallet_usd_value += native_sol_usd_value
                
                # Add SOL to summary if its value is > 0 (it's not typically in IGNORE_LIST by mint address)
                # Using "SOL" as symbol and its native mint address placeholder or a known one if desired
                token_summaries.append({
                    "symbol": "SOL", 
                    "uiAmount": native_sol_amount, 
                    "valueUsd": native_sol_usd_value, 
                    "address": "native" # Placeholder for native SOL
                })
            except Exception as e:
                print(f"❌ Error fetching SOL price: {e}")


        # 2. Get SPL token balances and their USD values
        spl_tokens = portfolio_result.get("tokens", [])

        for token in spl_tokens:
            mint_address = token.get("mint")
            if not mint_address:
                continue

            amount_raw = token.get("amountRaw", "0")
            decimals = token.get("decimals", 0)
            symbol = token.get("symbol", "N/A")
            name = token.get("name", "Unknown Token") # Added name for context

            ui_amount = int(amount_raw) / (10**decimals if decimals > 0 else 1)
            token_usd_value = 0.0

            if ui_amount > 0:
                try:
                    price_params = {"network": "mainnet", "address": mint_address}
                    price_data = sol_api.token.get_token_price(api_key=MORALIS_KEY, params=price_params)
                    usd_price = price_data.get("usdPrice", 0.0)
                    if usd_price is None: # handle if Moralis returns null for price
                        usd_price = 0.0
                    token_usd_value = ui_amount * usd_price
                except Exception as e:
                    # print(f"⚠️ Could not fetch price for {symbol} ({mint_address[:6]}...): {e}")
                    # This can be noisy, so commented out by default
                    pass # Keep token_usd_value as 0.0 if price fetch fails

            total_wallet_usd_value += token_usd_value
            
            # Store for summary, even if value is 0, filtering happens before print
            token_summaries.append({
                "symbol": symbol, 
                "uiAmount": ui_amount, 
                "valueUsd": token_usd_value, 
                "address": mint_address
            })

        # Calculate the sum of tokens that will be displayed in the summary
        summary_display_total = 0.0
        for item in token_summaries:
            if item["valueUsd"] > 0.01 and item["address"] not in IGNORE_LIST:
                summary_display_total += item["valueUsd"]

        # Print summary
        summary_title = "\n🌙 $1M Challenge:"
        print(summary_title)
        for summary_item in token_summaries:
            # Only show tokens with value > 0.01 and not in IGNORE_LIST for the summary print
            if summary_item["valueUsd"] > 0.01 and summary_item["address"] not in IGNORE_LIST:
                 # For native SOL, address is "native", so it won't be caught by IGNORE_LIST unless "native" is added
                print(f"🪙 {summary_item['symbol']}: ${float(summary_item['valueUsd']):,.2f}")
        print() # Add a blank line for better readability
        
        # Return the total of ONLY the summarized (displayed) items
        return summary_display_total

    except Exception as e:
        print(f"❌ Error fetching wallet balance with Moralis: {e}")
        import traceback
        traceback.print_exc() # Print full traceback for debugging
        return 0 # Return 0 or previous balance if error handling is more sophisticated

def get_usdc_balance():
    """Get current USDC balance from Solana"""
    try:
        return fetch_wallet_balance()
    except Exception:
        return 0

def format_time(seconds):
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes:02d}:{secs:02d}"

def get_terminal_size():
    return os.get_terminal_size()

def format_guest_name(filename):
    # Extract name between start and '__'
    name_part = filename.split('__')[0]
    # Split by '_' and join with space
    name = ' '.join(name_part.split('_'))
    return name

def play_random_sound():
    sounds_dir = "/Users/md/Dropbox/dev/github/stop-watch-timer/sounds"
    try:
        mixer.quit()
        mixer.init()
        sound_files = [f for f in os.listdir(sounds_dir) if f.endswith(('.MP3', '.mp3', '.wav', '.WAV'))]
        if sound_files:
            random_sound = random.choice(sound_files)
            sound_path = os.path.join(sounds_dir, random_sound)
            
            # Display welcome message with guest name
            guest_name = format_guest_name(random_sound)
            
            # Get terminal dimensions
            term_width, term_height = get_terminal_size()
            
            # Clear the previous timer display
            print(f"\033[{term_height-1};0H\033[2K", end='', flush=True)
            print(f"\033[{term_height};0H\033[2K", end='', flush=True)
            
            # Show the speaking message
            welcome_msg = f"{WHITE}{RED_BG}{BOLD}🎤 speaking: {guest_name}{RESET}"
            print(f"\033[{term_height-1};0H{center_text(welcome_msg)}", end='', flush=True)
            
            mixer.music.load(sound_path)
            mixer.music.play()
            while mixer.music.get_busy():
                time.sleep(0.1)
            mixer.quit()
            
            # Clear the speaking message after sound finishes
            print(f"\033[{term_height-1};0H\033[2K", end='', flush=True)
            print(f"\033[{term_height};0H\033[2K", end='', flush=True)
    except Exception as e:
        pass

def get_timer_duration():
    while True:
        try:
            minutes = float(input(f"{WHITE}Enter timer duration in minutes: {RESET}").strip())
            if minutes > 0:
                return minutes
            else:
                print(f"{RED_BG}Please enter a positive number{RESET}")
        except ValueError:
            print(f"{RED_BG}Please enter a valid number{RESET}")

def center_text(text):
    term_width, _ = get_terminal_size()
    # Center the text using string padding
    return text.center(term_width)

def log_timer_entry(minutes):
    """Log timer entries to a CSV file with timestamp 🌙"""
    csv_file = "timer_history.csv"
    timestamp = datetime.now().strftime("%m-%d %H:%M")
    balance = get_usdc_balance()
    
    try:
        # Check if file exists, if not create with headers
        try:
            with open(csv_file, 'r') as f:
                pass
        except FileNotFoundError:
            with open(csv_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Timestamp', 'Duration (mins)', 'USDC Balance'])

        # Append the new entry
        with open(csv_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([timestamp, minutes, balance])
    except Exception:
        pass

def display_status(balance, time_str, term_height):
    """Display the status line without clearing screen"""
    display_text = f"{WHITE}{RED_BG}{BOLD}Balance: ${int(balance):,} | {time_str}{RESET}"
    # Move cursor to one line above bottom of terminal and clear line
    print(f"\033[{term_height-1};0H\033[2K{center_text(display_text)}", end='', flush=True)
    # Clear the last line to ensure clean display
    print(f"\033[{term_height};0H\033[2K", end='', flush=True)

def main():
    global timer_minutes
    print(HIDE_CURSOR)
    
    # Get timer duration at startup
    timer_minutes = get_timer_duration()
    # Clear the screen completely after getting input
    print(CLEAR, end='', flush=True)
    # Log the timer entry
    log_timer_entry(timer_minutes)
    
    try:
        while True:
            end_time = datetime.now() + timedelta(minutes=timer_minutes)
            last_balance = None
            last_time_str = None
            
            while True:
                remaining = (end_time - datetime.now()).total_seconds()
                if remaining <= 0:
                    break
                
                # Get current terminal size
                term_width, term_height = get_terminal_size()
                
                # Update balance only at the start of a new timer cycle
                if last_balance is None:
                    balance = get_usdc_balance()
                    last_balance = balance
                else:
                    balance = last_balance
                
                time_str = format_time(int(remaining))
                
                # Always update display to ensure timer keeps counting
                display_status(balance, time_str, term_height)
                last_time_str = time_str
                
                time.sleep(0.1)  # Reduce CPU usage
            
            # Timer finished - always update balance at end
            term_width, term_height = get_terminal_size()
            display_status(get_usdc_balance(), "00:00", term_height)
            play_random_sound()
    except KeyboardInterrupt:
        print(SHOW_CURSOR)
        print(RESET)
        print("\nTimer stopped.")
        
    finally:
        print(SHOW_CURSOR)
        print(RESET)

if __name__ == "__main__":
    main()
