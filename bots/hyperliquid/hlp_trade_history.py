"""
Moon Dev's HLP Trade History Collector
=======================================
Fetches all historical trade fills for HLP addresses.

Backfills initially, then runs hourly for new trades.

Moon Dev

Usage: python bots/hyperliquid/hlp_trade_history.py
       python bots/hyperliquid/hlp_trade_history.py --continuous  # Run in loop
"""

import sqlite3
import requests
import time
import argparse
from datetime import datetime
from colorama import Fore, Style, init

init(autoreset=True)

# Configuration
DB_PATH = "bots/hyperliquid/data/hlp_tracker/hlp_data.db"
API_URL = "https://api.hyperliquid.xyz/info"
REFRESH_HOURS = 1  # How often to check for new trades in continuous mode

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


def get_user_fills(address, start_time=None):
    """
    Fetch trade fills for a user from Hyperliquid API.

    Args:
        address: Wallet address
        start_time: Unix timestamp in milliseconds (optional, for pagination)

    Returns:
        List of fill objects
    """
    payload = {
        "type": "userFills",
        "user": address
    }

    if start_time:
        payload["startTime"] = start_time

    response = requests.post(API_URL, json=payload, timeout=30)
    response.raise_for_status()
    return response.json()


def parse_fill(fill, address, strategy_name):
    """Parse a fill object into database row format"""
    try:
        # Extract timestamp
        timestamp = datetime.fromtimestamp(fill.get('time', 0) / 1000)

        # Determine side
        side = 'buy' if fill.get('side') == 'B' else 'sell'

        # Calculate USD value
        price = float(fill.get('px', 0))
        size = float(fill.get('sz', 0))
        usd_value = price * size

        # Fee info
        fee = float(fill.get('fee', 0))
        fee_token = fill.get('feeToken', 'USDC')

        # Maker/taker - crossed means taker
        is_maker = not fill.get('crossed', True)

        # Create unique trade ID
        trade_id = f"{fill.get('tid', '')}_{fill.get('oid', '')}"

        return {
            'timestamp': timestamp,
            'address': address,
            'strategy_name': strategy_name,
            'coin': fill.get('coin', ''),
            'side': side,
            'price': price,
            'size': size,
            'usd_value': usd_value,
            'fee': fee,
            'fee_token': fee_token,
            'is_maker': is_maker,
            'order_id': fill.get('oid', ''),
            'trade_id': trade_id
        }
    except Exception as e:
        print(f"{Fore.RED}Error parsing fill: {e}")
        return None


def save_trades_to_db(trades, conn):
    """Save trades to database, skip duplicates"""
    cursor = conn.cursor()

    inserted = 0
    skipped = 0

    for trade in trades:
        if trade is None:
            continue

        try:
            cursor.execute("""
                INSERT INTO trades (
                    timestamp, address, strategy_name, coin, side,
                    price, size, usd_value, fee, fee_token,
                    is_maker, order_id, trade_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade['timestamp'],
                trade['address'],
                trade['strategy_name'],
                trade['coin'],
                trade['side'],
                trade['price'],
                trade['size'],
                trade['usd_value'],
                trade['fee'],
                trade['fee_token'],
                trade['is_maker'],
                trade['order_id'],
                trade['trade_id']
            ))
            inserted += 1
        except sqlite3.IntegrityError:
            # Duplicate trade_id, skip
            skipped += 1

    conn.commit()
    return inserted, skipped


def fetch_all_fills_for_address(address, strategy_name, conn):
    """Fetch all historical fills for an address with pagination"""

    print(f"\n{Fore.CYAN}📡 Fetching trades for {strategy_name}...")
    print(f"{Fore.WHITE}   Address: {address[:10]}...{address[-6:]}")

    all_fills = []
    start_time = None
    page = 1

    while True:
        fills = get_user_fills(address, start_time)

        if not fills:
            break

        all_fills.extend(fills)
        print(f"{Fore.YELLOW}   Page {page}: {len(fills)} fills (Total: {len(all_fills)})")

        # Pagination: use oldest fill's timestamp for next request
        if len(fills) < 2000:  # Less than max results = no more pages
            break

        oldest_time = min(f.get('time', float('inf')) for f in fills)
        start_time = oldest_time - 1  # Go back 1ms before oldest
        page += 1

        time.sleep(0.2)  # Rate limit

    # Parse and save
    parsed_trades = [parse_fill(f, address, strategy_name) for f in all_fills]
    inserted, skipped = save_trades_to_db(parsed_trades, conn)

    print(f"{Fore.GREEN}   ✅ Inserted: {inserted}, Skipped (duplicates): {skipped}")

    return len(all_fills)


def get_trade_stats(conn):
    """Get statistics about trades in database"""
    cursor = conn.cursor()

    print(f"\n{Fore.CYAN}{'='*70}")
    print(f"{Fore.MAGENTA}📊 HLP TRADE STATISTICS")
    print(f"{Fore.CYAN}{'='*70}")

    # Total trades per strategy
    cursor.execute("""
        SELECT strategy_name, COUNT(*), SUM(usd_value), SUM(fee)
        FROM trades
        GROUP BY strategy_name
        ORDER BY COUNT(*) DESC
    """)

    print(f"\n{Fore.WHITE}Trades by Strategy:")
    for row in cursor.fetchall():
        name, count, total_value, total_fees = row
        total_value = total_value or 0
        total_fees = total_fees or 0
        print(f"  {name}: {count:,} trades | ${total_value/1e6:.2f}M volume | ${total_fees:,.2f} fees")

    # Maker vs Taker ratio
    cursor.execute("""
        SELECT
            SUM(CASE WHEN is_maker = 1 THEN 1 ELSE 0 END) as maker_count,
            SUM(CASE WHEN is_maker = 0 THEN 1 ELSE 0 END) as taker_count,
            COUNT(*) as total
        FROM trades
    """)
    row = cursor.fetchone()
    if row and row[2] > 0:
        maker, taker, total = row
        maker = maker or 0
        taker = taker or 0
        maker_pct = (maker / total) * 100 if total > 0 else 0
        print(f"\n{Fore.WHITE}Maker vs Taker:")
        print(f"  {Fore.GREEN}Maker: {maker:,} ({maker_pct:.1f}%)")
        print(f"  {Fore.RED}Taker: {taker:,} ({100-maker_pct:.1f}%)")

    # Top traded coins
    cursor.execute("""
        SELECT coin, COUNT(*), SUM(usd_value)
        FROM trades
        GROUP BY coin
        ORDER BY SUM(usd_value) DESC
        LIMIT 10
    """)

    print(f"\n{Fore.WHITE}Top 10 Coins by Volume:")
    for row in cursor.fetchall():
        coin, count, volume = row
        volume = volume or 0
        print(f"  {coin}: {count:,} trades | ${volume/1e6:.2f}M")

    # Date range
    cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM trades")
    min_date, max_date = cursor.fetchone()
    if min_date:
        print(f"\n{Fore.WHITE}Date Range: {min_date} to {max_date}")

    # Total stats
    cursor.execute("SELECT COUNT(*), SUM(usd_value), SUM(fee) FROM trades")
    total_count, total_vol, total_fees = cursor.fetchone()
    total_vol = total_vol or 0
    total_fees = total_fees or 0

    print(f"\n{Fore.YELLOW}═══════════════════════════════════════")
    print(f"{Fore.WHITE}TOTALS: {total_count:,} trades | ${total_vol/1e6:.2f}M volume | ${total_fees:,.2f} fees")
    print(f"{Fore.YELLOW}═══════════════════════════════════════")


def backfill_all():
    """Backfill all trade history for all HLP addresses"""
    conn = sqlite3.connect(DB_PATH)

    print(f"{Fore.MAGENTA}🌙 Moon Dev's HLP Trade History Collector")
    print(f"{Fore.CYAN}{'='*70}")
    print(f"{Fore.WHITE}Backfilling trade history for {len(HLP_ADDRESSES)} addresses...")

    total_fills = 0

    for name, address in HLP_ADDRESSES.items():
        try:
            fills = fetch_all_fills_for_address(address, name, conn)
            total_fills += fills
            time.sleep(0.5)  # Rate limit between addresses
        except Exception as e:
            print(f"{Fore.RED}❌ Error fetching {name}: {e}")

    print(f"\n{Fore.GREEN}✅ Backfill complete! Total fills: {total_fills:,}")

    # Show stats
    get_trade_stats(conn)

    conn.close()


def fetch_new_trades():
    """Fetch only new trades (for continuous mode)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print(f"\n{Fore.YELLOW}🔄 Checking for new trades...")

    total_new = 0

    for name, address in HLP_ADDRESSES.items():
        # Get most recent trade timestamp for this address
        cursor.execute("""
            SELECT MAX(timestamp) FROM trades WHERE address = ?
        """, (address,))
        result = cursor.fetchone()
        last_timestamp = result[0] if result[0] else None

        try:
            # Fetch recent fills
            fills = get_user_fills(address)

            if not fills:
                continue

            # Parse and filter to only new trades
            parsed = [parse_fill(f, address, name) for f in fills]

            if last_timestamp:
                # Filter to only trades after last known
                last_dt = datetime.fromisoformat(last_timestamp) if isinstance(last_timestamp, str) else last_timestamp
                parsed = [t for t in parsed if t and t['timestamp'] > last_dt]

            if parsed:
                inserted, _ = save_trades_to_db(parsed, conn)
                if inserted > 0:
                    print(f"{Fore.GREEN}   {name}: +{inserted} new trades")
                    total_new += inserted

        except Exception as e:
            print(f"{Fore.RED}   Error fetching {name}: {e}")

        time.sleep(0.2)

    conn.close()

    if total_new > 0:
        print(f"{Fore.GREEN}✅ Added {total_new} new trades")
    else:
        print(f"{Fore.YELLOW}   No new trades found")

    return total_new


def main():
    parser = argparse.ArgumentParser(description="Moon Dev's HLP Trade History Collector")
    parser.add_argument('--continuous', action='store_true', help='Run continuously, checking hourly')
    parser.add_argument('--stats', action='store_true', help='Show trade statistics only')
    args = parser.parse_args()

    if args.stats:
        conn = sqlite3.connect(DB_PATH)
        get_trade_stats(conn)
        conn.close()
        return

    # Initial backfill
    backfill_all()

    if args.continuous:
        print(f"\n{Fore.CYAN}🔄 Running in continuous mode (checking every {REFRESH_HOURS} hour(s))")
        print(f"{Fore.WHITE}   Press Ctrl+C to stop\n")

        while True:
            time.sleep(REFRESH_HOURS * 3600)
            fetch_new_trades()


if __name__ == "__main__":
    main()
