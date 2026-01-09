"""
Moon Dev's HLP Position Tracker
================================
Takes snapshots of all HLP positions every 5 minutes.
Stores time-series data for strategy analysis.

Moon Dev

Usage: python bots/hyperliquid/hlp_position_tracker.py
"""

import sqlite3
import requests
import time
import os
from datetime import datetime
from colorama import Fore, Style, init

init(autoreset=True)

# Configuration
DB_PATH = "bots/hyperliquid/data/hlp_tracker/hlp_data.db"
API_URL = "https://api.hyperliquid.xyz/info"
SNAPSHOT_INTERVAL_MINUTES = 5

# HLP addresses
HLP_ADDRESSES = {
    "HLP Strategy A": "0x010461c14e146ac35fe42271bdc1134ee31c703a",
    "HLP Strategy B": "0x31ca8395cf837de08b24da3f660e77761dfb974b",
    "HLP Liquidator": "0x2e3d94f0562703b25c83308a05046ddaf9a8dd14",
    "HLP Liquidator 2": "0xb0a55f13d22f66e6d495ac98113841b2326e9540",
    "HLP Liquidator 3": "0x5e177e5e39c0f4e421f5865a6d8beed8d921cb70",
    "HLP Liquidator 4": "0x2ed5c4484ea3ff8b57d5f2fb152a40d9f2b68308",
    "HLP Strategy X": "0x469f690213c467c39a23efacfd2816896009d7d8",
}


def get_user_positions(address):
    """Fetch positions for a Hyperliquid wallet"""
    payload = {"type": "clearinghouseState", "user": address}
    response = requests.post(API_URL, json=payload, timeout=30)
    response.raise_for_status()
    return response.json()


def take_snapshot(conn):
    """Take a snapshot of all HLP positions"""
    cursor = conn.cursor()
    timestamp = datetime.now()

    total_positions = 0
    total_long_value = 0
    total_short_value = 0

    # Collect all position deltas for net exposure calculation
    coin_deltas = {}

    for strategy_name, address in HLP_ADDRESSES.items():
        try:
            data = get_user_positions(address)

            if not isinstance(data, dict):
                continue

            # Extract margin summary for account snapshot
            margin = data.get('marginSummary', {})
            account_value = float(margin.get('accountValue', 0))

            asset_positions = data.get('assetPositions', [])

            # Track per-account stats
            account_long_value = 0
            account_short_value = 0
            account_long_pnl = 0
            account_short_pnl = 0
            account_long_count = 0
            account_short_count = 0
            account_total_pnl = 0

            for pos in asset_positions:
                if 'position' not in pos:
                    continue

                p = pos['position']
                size = float(p.get('szi', 0))

                if size == 0:
                    continue

                coin = p.get('coin', '')
                position_value = float(p.get('positionValue', 0))
                entry_price = float(p.get('entryPx', 0))
                unrealized_pnl = float(p.get('unrealizedPnl', 0))
                liq_price = float(p.get('liquidationPx', 0) or 0)

                leverage_data = p.get('leverage', {})
                leverage = leverage_data.get('value', 0) if isinstance(leverage_data, dict) else 0

                is_long = size > 0
                side = 'long' if is_long else 'short'

                # Track account stats
                if is_long:
                    account_long_value += position_value
                    account_long_pnl += unrealized_pnl
                    account_long_count += 1
                    total_long_value += position_value
                else:
                    account_short_value += position_value
                    account_short_pnl += unrealized_pnl
                    account_short_count += 1
                    total_short_value += position_value

                account_total_pnl += unrealized_pnl

                # Track coin deltas for net exposure
                if coin not in coin_deltas:
                    coin_deltas[coin] = {'long': 0, 'short': 0}
                if is_long:
                    coin_deltas[coin]['long'] += position_value
                else:
                    coin_deltas[coin]['short'] += position_value

                # Insert position record
                cursor.execute("""
                    INSERT INTO positions (
                        timestamp, address, strategy_name, coin, side,
                        size, position_value, entry_price, unrealized_pnl,
                        leverage, liquidation_price
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    timestamp, address, strategy_name, coin, side,
                    size, position_value, entry_price, unrealized_pnl,
                    leverage, liq_price
                ))

                total_positions += 1

            # Insert account snapshot
            cursor.execute("""
                INSERT INTO account_snapshots (
                    timestamp, address, strategy_name, account_value,
                    total_position_value, total_pnl, long_count, short_count,
                    long_value, short_value, long_pnl, short_pnl
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                timestamp, address, strategy_name, account_value,
                account_long_value + account_short_value, account_total_pnl,
                account_long_count, account_short_count,
                account_long_value, account_short_value,
                account_long_pnl, account_short_pnl
            ))

            time.sleep(0.1)  # Small delay between API calls

        except Exception as e:
            print(f"{Fore.RED}Error fetching {strategy_name}: {e}")

    # Calculate and store net position deltas
    for coin, values in coin_deltas.items():
        long_val = values['long']
        short_val = values['short']
        net_delta = long_val - short_val

        cursor.execute("""
            INSERT INTO position_deltas (
                timestamp, coin, net_long_value, net_short_value, net_delta
            ) VALUES (?, ?, ?, ?, ?)
        """, (timestamp, coin, long_val, short_val, net_delta))

    conn.commit()

    return total_positions, total_long_value, total_short_value, len(coin_deltas)


def print_banner():
    """Print banner"""
    banner = f"""
{Fore.CYAN}{'='*70}
{Fore.MAGENTA}
    ██╗  ██╗██╗     ██████╗     ████████╗██████╗  █████╗  ██████╗██╗  ██╗
    ██║  ██║██║     ██╔══██╗    ╚══██╔══╝██╔══██╗██╔══██╗██╔════╝██║ ██╔╝
    ███████║██║     ██████╔╝       ██║   ██████╔╝███████║██║     █████╔╝
    ██╔══██║██║     ██╔═══╝        ██║   ██╔══██╗██╔══██║██║     ██╔═██╗
    ██║  ██║███████╗██║            ██║   ██║  ██║██║  ██║╚██████╗██║  ██╗
    ╚═╝  ╚═╝╚══════╝╚═╝            ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝
{Fore.CYAN}{'='*70}
{Fore.WHITE}  Moon Dev's HLP Position Tracker
{Fore.YELLOW}  Snapshots every {SNAPSHOT_INTERVAL_MINUTES} minutes | Tracking {len(HLP_ADDRESSES)} strategies
{Fore.CYAN}{'='*70}
"""
    print(banner)


def get_db_stats(conn):
    """Get database statistics"""
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM positions")
    pos_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM account_snapshots")
    snap_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT timestamp) FROM positions")
    snapshot_times = cursor.fetchone()[0]

    cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM positions")
    date_range = cursor.fetchone()

    return {
        'positions': pos_count,
        'snapshots': snap_count,
        'unique_times': snapshot_times,
        'min_date': date_range[0],
        'max_date': date_range[1]
    }


def main():
    """Main function - runs position tracker on a loop"""
    print_banner()

    # Connect to database
    conn = sqlite3.connect(DB_PATH)

    print(f"{Fore.WHITE}  Database: {DB_PATH}")

    # Get initial stats
    stats = get_db_stats(conn)
    print(f"{Fore.WHITE}  Existing snapshots: {stats['unique_times']}")
    if stats['min_date']:
        print(f"{Fore.WHITE}  Date range: {stats['min_date']} to {stats['max_date']}")

    print(f"\n{Fore.CYAN}Starting position tracking loop...")
    print(f"{Fore.WHITE}Press Ctrl+C to stop\n")

    snapshot_count = 0

    while True:
        try:
            start_time = time.time()

            # Take snapshot
            positions, long_val, short_val, coins = take_snapshot(conn)
            snapshot_count += 1

            elapsed = time.time() - start_time
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # Print status
            net_delta = long_val - short_val
            delta_color = Fore.GREEN if net_delta > 0 else Fore.RED if net_delta < 0 else Fore.WHITE

            print(f"{Fore.CYAN}[{timestamp}] {Fore.WHITE}Snapshot #{snapshot_count}")
            print(f"  Positions: {positions} | Coins: {coins}")
            print(f"  {Fore.GREEN}Longs: ${long_val/1e6:.2f}M{Fore.WHITE} | "
                  f"{Fore.RED}Shorts: ${short_val/1e6:.2f}M{Fore.WHITE} | "
                  f"Net: {delta_color}${net_delta/1e6:+.2f}M")
            print(f"  {Fore.YELLOW}Next snapshot in {SNAPSHOT_INTERVAL_MINUTES} min\n")

            # Wait for next snapshot
            time.sleep(SNAPSHOT_INTERVAL_MINUTES * 60)

        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Stopping position tracker...")
            break
        except Exception as e:
            print(f"{Fore.RED}Error: {e}")
            print(f"{Fore.YELLOW}Retrying in 60 seconds...")
            time.sleep(60)

    conn.close()

    # Final stats
    conn = sqlite3.connect(DB_PATH)
    stats = get_db_stats(conn)
    conn.close()

    print(f"\n{Fore.CYAN}{'='*70}")
    print(f"{Fore.GREEN}Session complete!")
    print(f"  Total snapshots taken: {snapshot_count}")
    print(f"  Total position records: {stats['positions']}")
    print(f"{Fore.CYAN}{'='*70}")


if __name__ == "__main__":
    main()
