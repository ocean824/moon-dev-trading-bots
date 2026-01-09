"""
Moon Dev's HLP Database Setup
==============================
Creates SQLite database for HLP strategy reverse engineering.

Run once to initialize, safe to run again (won't delete data).

Moon Dev

Usage: python bots/hyperliquid/hlp_db_setup.py
"""

import sqlite3
import os
from datetime import datetime

# Database location
DB_PATH = "bots/hyperliquid/data/hlp_tracker/hlp_data.db"

# HLP addresses for reference
HLP_ADDRESSES = {
    "HLP Strategy A": "0x010461c14e146ac35fe42271bdc1134ee31c703a",
    "HLP Strategy B": "0x31ca8395cf837de08b24da3f660e77761dfb974b",
    "HLP Liquidator": "0x2e3d94f0562703b25c83308a05046ddaf9a8dd14",
    "HLP Liquidator 2": "0xb0a55f13d22f66e6d495ac98113841b2326e9540",
    "HLP Liquidator 3": "0x5e177e5e39c0f4e421f5865a6d8beed8d921cb70",
    "HLP Liquidator 4": "0x2ed5c4484ea3ff8b57d5f2fb152a40d9f2b68308",
    "HLP Strategy X": "0x469f690213c467c39a23efacfd2816896009d7d8",
}


def create_database():
    """Create the SQLite database and all tables"""

    # Ensure directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("🌙 Moon Dev's HLP Database Setup")
    print("=" * 50)

    # Position snapshots table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            address TEXT NOT NULL,
            strategy_name TEXT NOT NULL,
            coin TEXT NOT NULL,
            side TEXT NOT NULL,
            size REAL NOT NULL,
            position_value REAL NOT NULL,
            entry_price REAL,
            unrealized_pnl REAL,
            leverage REAL,
            liquidation_price REAL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("✅ Created 'positions' table")

    # Trade fills table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            address TEXT NOT NULL,
            strategy_name TEXT NOT NULL,
            coin TEXT NOT NULL,
            side TEXT NOT NULL,
            price REAL NOT NULL,
            size REAL NOT NULL,
            usd_value REAL,
            fee REAL,
            fee_token TEXT,
            is_maker BOOLEAN,
            order_id TEXT,
            trade_id TEXT UNIQUE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("✅ Created 'trades' table")

    # Liquidator events table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS liquidator_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            address TEXT NOT NULL,
            liquidator_name TEXT NOT NULL,
            event_type TEXT NOT NULL,
            coin TEXT,
            position_value REAL,
            details TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("✅ Created 'liquidator_events' table")

    # Position deltas table (aggregated net exposure)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS position_deltas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            coin TEXT NOT NULL,
            net_long_value REAL NOT NULL,
            net_short_value REAL NOT NULL,
            net_delta REAL NOT NULL,
            delta_change REAL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("✅ Created 'position_deltas' table")

    # Account snapshots table (overall account stats)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS account_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            address TEXT NOT NULL,
            strategy_name TEXT NOT NULL,
            account_value REAL NOT NULL,
            total_position_value REAL,
            total_pnl REAL,
            long_count INTEGER,
            short_count INTEGER,
            long_value REAL,
            short_value REAL,
            long_pnl REAL,
            short_pnl REAL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("✅ Created 'account_snapshots' table")

    # Funding payments table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS funding_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            address TEXT NOT NULL,
            strategy_name TEXT NOT NULL,
            coin TEXT NOT NULL,
            funding_payment REAL NOT NULL,
            position_size REAL,
            funding_rate REAL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("✅ Created 'funding_payments' table")

    # Create indexes for fast queries
    print("\n📊 Creating indexes...")

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_positions_timestamp ON positions(timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_positions_address ON positions(address)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_positions_coin ON positions(coin)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_positions_strategy ON positions(strategy_name)")

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_address ON trades(address)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_coin ON trades(coin)")

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_liquidator_timestamp ON liquidator_events(timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_liquidator_address ON liquidator_events(address)")

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_deltas_timestamp ON position_deltas(timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_deltas_coin ON position_deltas(coin)")

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_account_timestamp ON account_snapshots(timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_account_address ON account_snapshots(address)")

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_funding_timestamp ON funding_payments(timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_funding_address ON funding_payments(address)")

    print("✅ All indexes created")

    conn.commit()
    conn.close()

    print("\n" + "=" * 50)
    print(f"✅ Database created at: {DB_PATH}")
    print(f"📁 File size: {os.path.getsize(DB_PATH) / 1024:.1f} KB")
    print("=" * 50)


def print_schema():
    """Print current database schema"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()

    print("\n📋 Database Schema:")
    print("=" * 50)

    for table in tables:
        table_name = table[0]
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()

        print(f"\n📦 {table_name}:")
        for col in columns:
            print(f"   - {col[1]} ({col[2]})")

    conn.close()


def get_stats():
    """Get current database statistics"""
    if not os.path.exists(DB_PATH):
        print("❌ Database not found. Run setup first.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("\n📊 Database Statistics:")
    print("=" * 50)

    tables = ['positions', 'trades', 'liquidator_events', 'position_deltas', 'account_snapshots', 'funding_payments']

    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"   {table}: {count:,} rows")

    # Get date range if data exists
    cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM positions")
    result = cursor.fetchone()
    if result[0]:
        print(f"\n📅 Position data range: {result[0]} to {result[1]}")

    cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM trades")
    result = cursor.fetchone()
    if result[0]:
        print(f"📅 Trade data range: {result[0]} to {result[1]}")

    conn.close()

    file_size = os.path.getsize(DB_PATH)
    print(f"\n💾 Database size: {file_size / 1024 / 1024:.2f} MB")


if __name__ == "__main__":
    create_database()
    print_schema()
    get_stats()

    print("\n🌙 Moon Dev says: Database ready for HLP tracking!")
    print("   Next: Run hlp_trade_history.py to backfill trades")
