"""
🌙 Moon Dev's Whale Watcher Bot 🐋
====================================
WebSocket-based bot that monitors Hyperliquid trades for large orders.
When a single trade exceeds the threshold, logs the trader's address.

Features:
- Real-time WebSocket connection to Hyperliquid
- Monitors BTC trades (configurable)
- Logs addresses of traders making large trades to txt file
- Auto-reconnect on disconnect

Moon Dev 🌙
"""

import asyncio
import websockets
import json
import os
from datetime import datetime
from termcolor import colored
import colorama
from colorama import Fore, Style

# Initialize colorama for Windows compatibility
colorama.init(autoreset=True)

# ===== CONFIGURATION - CHANGE THESE =====
MIN_TRADE_SIZE_USD = 25000  # Minimum trade size in USD to log (Moon Dev's whale threshold!)
SYMBOL = 'BTC'  # Symbol to watch (BTC, ETH, SOL, etc.)
# =========================================

# WebSocket URL for Hyperliquid mainnet
WS_URL = "wss://api.hyperliquid.xyz/ws"

# Data folder path for logging whales - Moon Dev's whale collection!
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
WHALE_LOG_FILE = os.path.join(DATA_DIR, 'whale_addresses_from_ob.txt')

# Moon Dev ASCII Art Banner
MOON_DEV_BANNER = f"""{Fore.CYAN}
   __  ___                    ____
  /  |/  /___  ____  ____    / __ \\___  _  __
 / /|_/ / __ \\/ __ \\/ __ \\  / / / / _ \\| |/_/
/ /  / / /_/ / /_/ / / / / / /_/ /  __/>  <
/_/  /_/\\____/\\____/_/ /_(_)____/\\___/_/|_|

{Fore.MAGENTA}🐋 WHALE WATCHER Bot 🌙{Fore.RESET}
{Fore.YELLOW}Fishing for big traders on Hyperliquid! 🎣{Fore.RESET}
"""

# Stats tracking
stats = {
    'total_trades': 0,
    'whale_trades': 0,
    'unique_whales': set(),
    'largest_trade': 0,
    'start_time': None
}


def log_whale(address: str, trade_size_usd: float, side: str, price: float, size: float):
    """
    Log a whale address to the txt file.
    Moon Dev's whale fishing method! 🐋
    Only writes address if it's not already in the file (no duplicates!)
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Make sure data directory exists
    os.makedirs(DATA_DIR, exist_ok=True)

    # Check if address already exists in file to avoid duplicates
    existing_addresses = set()
    if os.path.exists(WHALE_LOG_FILE):
        with open(WHALE_LOG_FILE, 'r') as f:
            for line in f:
                addr = line.strip()
                if addr.startswith('0x'):
                    existing_addresses.add(addr)

    is_new_whale = address not in existing_addresses and address not in stats['unique_whales']

    # Only write to file if it's a NEW address (no duplicates!)
    if is_new_whale:
        with open(WHALE_LOG_FILE, 'a') as f:
            f.write(f"{address}\n")  # Only the address, nothing else!

    # Update stats
    stats['whale_trades'] += 1
    if address not in stats['unique_whales']:
        stats['unique_whales'].add(address)
    if trade_size_usd > stats['largest_trade']:
        stats['largest_trade'] = trade_size_usd

    # Print whale alert!
    whale_emoji = "🆕🐋" if is_new_whale else "🐋"
    print(f"\n{Fore.GREEN}{'='*60}")
    print(f"{Fore.CYAN}{whale_emoji} WHALE DETECTED! {whale_emoji}")
    print(f"{Fore.WHITE}Address: {Fore.YELLOW}{address}")
    print(f"{Fore.WHITE}Trade: {Fore.GREEN if side == 'B' else Fore.RED}{'BUY' if side == 'B' else 'SELL'} {size} {SYMBOL} @ ${price:,.2f}")
    print(f"{Fore.WHITE}Value: {Fore.MAGENTA}${trade_size_usd:,.2f}")
    print(f"{Fore.WHITE}Time: {Fore.CYAN}{timestamp}")
    if is_new_whale:
        print(f"{Fore.GREEN}>>> NEW WHALE! Added to file! <<<")
    else:
        print(f"{Fore.YELLOW}>>> Already in our whale list, skipping... <<<")
    print(f"{Fore.GREEN}{'='*60}\n")

    return is_new_whale


def print_stats():
    """Print current session stats. Moon Dev style! 🌙"""
    runtime = datetime.now() - stats['start_time'] if stats['start_time'] else "N/A"
    print(f"\n{Fore.CYAN}{'='*50}")
    print(f"{Fore.YELLOW}📊 MOON DEV WHALE WATCHER STATS 📊")
    print(f"{Fore.CYAN}{'='*50}")
    print(f"{Fore.WHITE}Runtime: {Fore.GREEN}{runtime}")
    print(f"{Fore.WHITE}Total trades seen: {Fore.CYAN}{stats['total_trades']:,}")
    print(f"{Fore.WHITE}Whale trades (>${MIN_TRADE_SIZE_USD:,}): {Fore.MAGENTA}{stats['whale_trades']:,}")
    print(f"{Fore.WHITE}Unique whales: {Fore.YELLOW}{len(stats['unique_whales'])}")
    print(f"{Fore.WHITE}Largest trade: {Fore.GREEN}${stats['largest_trade']:,.2f}")
    print(f"{Fore.WHITE}Log file: {Fore.CYAN}{WHALE_LOG_FILE}")
    print(f"{Fore.CYAN}{'='*50}\n")


async def subscribe_to_trades(websocket):
    """
    Subscribe to trade stream for the configured symbol.
    Moon Dev's WebSocket magic! ✨
    """
    subscribe_msg = {
        "method": "subscribe",
        "subscription": {
            "type": "trades",
            "coin": SYMBOL
        }
    }
    await websocket.send(json.dumps(subscribe_msg))
    print(f"{Fore.GREEN}🔌 Subscribed to {SYMBOL} trades stream!")


async def process_trade(trade_data):
    """
    Process a single trade and check if it's a whale.
    Moon Dev's whale detection algorithm! 🐋
    """
    stats['total_trades'] += 1

    # Extract trade info
    coin = trade_data.get('coin', '')
    side = trade_data.get('side', '')  # 'B' for buy, 'S' for sell
    price = float(trade_data.get('px', 0))
    size = float(trade_data.get('sz', 0))
    users = trade_data.get('users', [])  # [buyer_address, seller_address]

    # Calculate USD value
    trade_value_usd = price * size

    # Check if it's a whale trade
    if trade_value_usd >= MIN_TRADE_SIZE_USD:
        # Log both buyer and seller if they made large trades
        if len(users) >= 2:
            buyer_addr = users[0]
            seller_addr = users[1]

            # Log based on who made the aggressive order (the one who crossed the spread)
            if side == 'B':
                # Buyer was aggressive (taker), log them
                log_whale(buyer_addr, trade_value_usd, 'BUY', price, size)
            else:
                # Seller was aggressive (taker), log them
                log_whale(seller_addr, trade_value_usd, 'SELL', price, size)

    # Print periodic status every 100 trades
    if stats['total_trades'] % 100 == 0:
        print(f"{Fore.CYAN}📊 Trades processed: {stats['total_trades']:,} | Whales found: {stats['whale_trades']}")


async def whale_watcher():
    """
    Main WebSocket loop for watching whales.
    Moon Dev's fishing expedition! 🎣
    """
    stats['start_time'] = datetime.now()

    print(MOON_DEV_BANNER)
    print(f"\n{Fore.YELLOW}🎯 Configuration:")
    print(f"{Fore.WHITE}   Symbol: {Fore.CYAN}{SYMBOL}")
    print(f"{Fore.WHITE}   Min Trade Size: {Fore.GREEN}${MIN_TRADE_SIZE_USD:,}")
    print(f"{Fore.WHITE}   Log File: {Fore.CYAN}{WHALE_LOG_FILE}")
    print(f"\n{Fore.GREEN}🚀 Starting whale watcher... Moon Dev says let's go! 🌙\n")

    reconnect_delay = 1  # Start with 1 second delay
    max_reconnect_delay = 60  # Max 60 seconds between reconnects

    while True:
        try:
            async with websockets.connect(WS_URL, ping_interval=20, ping_timeout=10) as websocket:
                print(f"{Fore.GREEN}✅ Connected to Hyperliquid WebSocket!")
                reconnect_delay = 1  # Reset delay on successful connection

                # Subscribe to trades
                await subscribe_to_trades(websocket)

                # Listen for messages
                async for message in websocket:
                    try:
                        data = json.loads(message)

                        # Check if it's a trade message
                        if data.get('channel') == 'trades':
                            trades = data.get('data', [])
                            for trade in trades:
                                await process_trade(trade)

                        # Handle subscription confirmation
                        elif data.get('channel') == 'subscriptionResponse':
                            print(f"{Fore.GREEN}✅ Subscription confirmed: {data}")

                    except json.JSONDecodeError as e:
                        print(f"{Fore.RED}⚠️ JSON decode error: {e}")
                        continue

        except websockets.exceptions.ConnectionClosed as e:
            print(f"{Fore.YELLOW}🔌 Connection closed: {e}. Reconnecting in {reconnect_delay}s...")
            print_stats()
            await asyncio.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)

        except Exception as e:
            print(f"{Fore.RED}❌ Error: {e}. Reconnecting in {reconnect_delay}s...")
            print_stats()
            await asyncio.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)


def main():
    """
    Entry point for Moon Dev's Whale Watcher! 🐋🌙
    """
    try:
        asyncio.run(whale_watcher())
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}👋 Moon Dev's Whale Watcher shutting down...")
        print_stats()
        print(f"\n{Fore.GREEN}🐋 Whale addresses saved to: {WHALE_LOG_FILE}")
        print(f"{Fore.CYAN}Thanks for fishing with Moon Dev! 🌙\n")


if __name__ == "__main__":
    main()
