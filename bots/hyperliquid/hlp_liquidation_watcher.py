"""
Moon Dev's HLP Liquidator Watcher
==================================
Monitors the 4 HLP liquidator accounts for activation.

These accounts sit idle with funds but no positions until liquidation
opportunities arise. This script detects when they become active.

Moon Dev

Usage: python bots/hyperliquid/hlp_liquidation_watcher.py
"""

import sqlite3
import requests
import time
import os
from datetime import datetime
from colorama import Fore, Back, Style, init

init(autoreset=True)

# Configuration
DB_PATH = "bots/hyperliquid/data/hlp_tracker/hlp_data.db"
API_URL = "https://api.hyperliquid.xyz/info"
CHECK_INTERVAL_SECONDS = 60  # Check every minute

# Liquidator accounts specifically (the ones that are usually idle)
LIQUIDATOR_ADDRESSES = {
    "HLP Liquidator": "0x2e3d94f0562703b25c83308a05046ddaf9a8dd14",
    "HLP Liquidator 2": "0xb0a55f13d22f66e6d495ac98113841b2326e9540",
    "HLP Liquidator 3": "0x5e177e5e39c0f4e421f5865a6d8beed8d921cb70",
    "HLP Liquidator 4": "0x2ed5c4484ea3ff8b57d5f2fb152a40d9f2b68308",
}


def get_user_positions(address):
    """Fetch positions for a Hyperliquid wallet"""
    payload = {"type": "clearinghouseState", "user": address}
    response = requests.post(API_URL, json=payload, timeout=30)
    response.raise_for_status()
    return response.json()


def check_liquidator_status(address, name):
    """
    Check if a liquidator account has any open positions.

    Returns:
        dict with status info or None on error
    """
    try:
        data = get_user_positions(address)

        if not isinstance(data, dict):
            return None

        margin = data.get('marginSummary', {})
        account_value = float(margin.get('accountValue', 0))

        asset_positions = data.get('assetPositions', [])

        # Count actual positions (with non-zero size)
        positions = []
        for pos in asset_positions:
            if 'position' not in pos:
                continue
            p = pos['position']
            size = float(p.get('szi', 0))
            if size != 0:
                positions.append({
                    'coin': p.get('coin', ''),
                    'size': size,
                    'value': float(p.get('positionValue', 0)),
                    'pnl': float(p.get('unrealizedPnl', 0)),
                    'side': 'LONG' if size > 0 else 'SHORT'
                })

        return {
            'name': name,
            'address': address,
            'account_value': account_value,
            'position_count': len(positions),
            'positions': positions,
            'is_active': len(positions) > 0
        }

    except Exception as e:
        print(f"{Fore.RED}Error checking {name}: {e}")
        return None


def log_liquidator_event(conn, name, address, event_type, coin=None, position_value=None, details=None):
    """Log a liquidator event to database"""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO liquidator_events (
            timestamp, address, liquidator_name, event_type, coin, position_value, details
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (datetime.now(), address, name, event_type, coin, position_value, details))
    conn.commit()


def print_banner():
    """Print banner"""
    banner = f"""
{Fore.CYAN}{'='*70}
{Fore.RED}
    ██╗     ██╗ ██████╗     ██╗    ██╗ █████╗ ████████╗ ██████╗██╗  ██╗
    ██║     ██║██╔═══██╗    ██║    ██║██╔══██╗╚══██╔══╝██╔════╝██║  ██║
    ██║     ██║██║   ██║    ██║ █╗ ██║███████║   ██║   ██║     ███████║
    ██║     ██║██║▄▄ ██║    ██║███╗██║██╔══██║   ██║   ██║     ██╔══██║
    ███████╗██║╚██████╔╝    ╚███╔███╔╝██║  ██║   ██║   ╚██████╗██║  ██║
    ╚══════╝╚═╝ ╚══▀▀═╝      ╚══╝╚══╝ ╚═╝  ╚═╝   ╚═╝    ╚═════╝╚═╝  ╚═╝
{Fore.CYAN}{'='*70}
{Fore.WHITE}  Moon Dev's HLP Liquidator Watcher
{Fore.YELLOW}  Monitoring {len(LIQUIDATOR_ADDRESSES)} liquidator accounts every {CHECK_INTERVAL_SECONDS}s
{Fore.CYAN}{'='*70}
"""
    print(banner)


def format_usd(value):
    """Format USD value"""
    if abs(value) >= 1_000_000:
        return f"${value/1_000_000:.2f}M"
    elif abs(value) >= 1_000:
        return f"${value/1_000:.1f}K"
    else:
        return f"${value:.2f}"


def main():
    """Main function - monitors liquidator accounts"""
    print_banner()

    # Connect to database
    conn = sqlite3.connect(DB_PATH)

    # Track previous state to detect changes
    previous_state = {}
    for name in LIQUIDATOR_ADDRESSES:
        previous_state[name] = {'is_active': False, 'positions': []}

    print(f"{Fore.WHITE}Starting liquidator monitoring...")
    print(f"{Fore.WHITE}Press Ctrl+C to stop\n")

    check_count = 0

    while True:
        try:
            check_count += 1
            timestamp = datetime.now().strftime('%H:%M:%S')
            any_active = False

            print(f"{Fore.CYAN}[{timestamp}] Check #{check_count}")

            for name, address in LIQUIDATOR_ADDRESSES.items():
                status = check_liquidator_status(address, name)

                if status is None:
                    continue

                is_active = status['is_active']
                was_active = previous_state[name]['is_active']
                short_addr = f"{address[:6]}...{address[-4:]}"

                # Detect state changes
                if is_active and not was_active:
                    # ACTIVATED - This is the key event!
                    print(f"\n{Back.RED}{Fore.WHITE}🚨 LIQUIDATOR ACTIVATED! 🚨{Style.RESET_ALL}")
                    print(f"{Fore.RED}  {name} ({short_addr}) just opened positions!")

                    for pos in status['positions']:
                        print(f"{Fore.YELLOW}    {pos['coin']} {pos['side']} {format_usd(pos['value'])}")
                        log_liquidator_event(
                            conn, name, address, 'position_opened',
                            coin=pos['coin'],
                            position_value=pos['value'],
                            details=f"{pos['side']} {pos['size']}"
                        )

                    log_liquidator_event(conn, name, address, 'activated',
                                        details=f"{status['position_count']} positions opened")
                    print()

                elif not is_active and was_active:
                    # DEACTIVATED - closed all positions
                    print(f"\n{Fore.YELLOW}📤 {name} closed all positions (back to idle)")
                    log_liquidator_event(conn, name, address, 'deactivated',
                                        details="All positions closed")
                    print()

                elif is_active:
                    # Check for new positions added
                    prev_coins = set(p.get('coin') for p in previous_state[name]['positions'])
                    curr_coins = set(p['coin'] for p in status['positions'])
                    new_coins = curr_coins - prev_coins
                    closed_coins = prev_coins - curr_coins

                    for coin in new_coins:
                        pos = next((p for p in status['positions'] if p['coin'] == coin), None)
                        if pos:
                            print(f"{Fore.YELLOW}  📈 {name} opened new {pos['coin']} {pos['side']} {format_usd(pos['value'])}")
                            log_liquidator_event(conn, name, address, 'position_opened',
                                               coin=coin, position_value=pos['value'],
                                               details=f"{pos['side']} {pos['size']}")

                    for coin in closed_coins:
                        print(f"{Fore.CYAN}  📉 {name} closed {coin} position")
                        log_liquidator_event(conn, name, address, 'position_closed', coin=coin)

                # Print current status
                if is_active:
                    any_active = True
                    total_value = sum(p['value'] for p in status['positions'])
                    total_pnl = sum(p['pnl'] for p in status['positions'])
                    pnl_color = Fore.GREEN if total_pnl >= 0 else Fore.RED
                    print(f"{Fore.RED}  🔴 {name}: ACTIVE - {status['position_count']} positions "
                          f"({format_usd(total_value)}) PnL: {pnl_color}{format_usd(total_pnl)}")
                else:
                    print(f"{Fore.GREEN}  🟢 {name}: Idle ({format_usd(status['account_value'])})")

                # Update previous state
                previous_state[name] = {
                    'is_active': is_active,
                    'positions': status['positions']
                }

                time.sleep(0.1)

            # Summary
            if any_active:
                print(f"\n{Fore.RED}⚠️  LIQUIDATORS ARE ACTIVE - MARKET OPPORTUNITY!")
            else:
                print(f"{Fore.GREEN}  All liquidators idle - normal market conditions")

            print(f"{Fore.CYAN}  Next check in {CHECK_INTERVAL_SECONDS}s...\n")

            # Wait for next check
            time.sleep(CHECK_INTERVAL_SECONDS)

        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Stopping liquidator watcher...")
            break
        except Exception as e:
            print(f"{Fore.RED}Error: {e}")
            print(f"{Fore.YELLOW}Retrying in 30 seconds...")
            time.sleep(30)

    conn.close()

    print(f"\n{Fore.CYAN}{'='*70}")
    print(f"{Fore.GREEN}Liquidator watcher stopped.")
    print(f"{Fore.CYAN}{'='*70}")


if __name__ == "__main__":
    main()
