# adding my solana balance in usdc to the timer bot below

import time
import os
from datetime import datetime, timedelta
import random
from pygame import mixer
import csv
import pandas as pd
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Moon Dev's public address
MY_ADDRESS = "G1vNV2SkzGPTBTDd7c3iypL4TPNGbe37rEbJb7cxVTQS"

# USDC token address on Solana
USDC_TOKEN = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

# IGNORE_LIST was accidentally removed, adding it back
IGNORE_LIST = ['59Nv97TEcKjcz2oZvZnsSCXK6kESvCigyZUHpxnDpump','5fBmCvqNp1H82SfHrzyMaRJoFg3aa6SAaYZQb1KBmoon', '7TUw3iAMM2c5H95BzfifgQCkdwGJyrPzuJ2u7nzhPUMP', 'WHfYPSqvUnhCoJfjQJrZJVhz2GzzH5Q2BTJoabnpump', 'WHfYPSqvUnhCoJfjQJrZJVhz2GzzH5Q2BTJoabnpump']

# Get API key from environment
BIRDEYE_KEY = os.getenv('BIRDEYE_KEY')
if not BIRDEYE_KEY:
    raise ValueError("BIRDEYE_KEY environment variable not set! Please set it in your .env file")

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



def fetch_wallet_balance():
    """Gets total USD value of all tokens in wallet"""
    try:
        url = f"https://public-api.birdeye.so/v1/wallet/token_list?wallet={MY_ADDRESS}"
        headers = {"x-chain": "solana", "X-API-KEY": BIRDEYE_KEY}
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            json_response = response.json()
            if 'data' in json_response and 'items' in json_response['data']:
                df = pd.DataFrame(json_response['data']['items'])
                if not df.empty:
                    print(f"\n🌙 $1M Challenge:")
                    # Create a summary of holdings, excluding ignored tokens
                    summary = df[['symbol', 'uiAmount', 'valueUsd', 'address']].copy()
                    summary = summary[summary['valueUsd'] > 0]  # Only show tokens with value
                    # Filter out ignored tokens
                    summary = summary[~summary['address'].isin(IGNORE_LIST)]
                    for _, row in summary.iterrows():
                        print(f"🪙 {row['symbol']}: ${float(row['valueUsd']):,.2f}")
                    print()  # Add a blank line for better readability
                    
                    # Calculate total value including ALL tokens (even ignored ones)
                    total_value = df['valueUsd'].astype(float).sum()
                    return total_value
        return 0
    except Exception as e:
        print(f"❌ Error fetching wallet balance: {e}")
        return 0

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
