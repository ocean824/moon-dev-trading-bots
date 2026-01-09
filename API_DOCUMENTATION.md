# Moon Dev's API Documentation
## Master Reference for Hyperliquid Trading APIs

**Base URL:** `https://api.moondev.com`
**Rate Limit:** 3,600 requests/min
**Data Updates:** Every 30 seconds
**Retention:** 60 days

---

## Table of Contents

1. [Authentication](#authentication)
2. [Health Check](#health-check)
3. [Liquidation Data](#liquidation-data)
4. [Binance Liquidations](#binance-liquidations)
5. [Position Tracking](#position-tracking)
6. [Whale Activity](#whale-activity)
7. [Blockchain Events](#blockchain-events)
8. [Contract Registry](#contract-registry)
9. [Tick Data & Prices](#tick-data--prices)
10. [Order Flow & Trades](#order-flow--trades)
11. [Smart Money Intelligence](#smart-money-intelligence)
12. [User Data (Individual Wallets)](#user-data-individual-wallets)
13. [HLP (HyperLiquidity Provider)](#hlp-hyperliquidity-provider)
14. [Direct Hyperliquid API](#direct-hyperliquid-api)
15. [Python SDK Usage](#python-sdk-usage)
16. [Example Scripts](#example-scripts)

---

## Authentication

All endpoints (except `/health`) require authentication.

### Methods

**Header (Recommended):**
```
X-API-Key: YOUR_API_KEY
```

**Query Parameter:**
```
?api_key=YOUR_API_KEY
```

### Python Example
```python
from api import MoonDevAPI

api = MoonDevAPI(api_key="your_key")
# Or set MOONDEV_API_KEY in .env file
api = MoonDevAPI()
```

---

## Health Check

Check API service status (no auth required).

| Endpoint | Method | Auth |
|----------|--------|------|
| `/health` | GET | No |

```python
api.health()
# Returns: {"status": "healthy", "timestamp": "..."}
```

---

## Liquidation Data

Track liquidation events across all timeframes.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/liquidations/{timeframe}.json` | GET | Liquidation data for timeframe |
| `/api/liquidations/stats.json` | GET | Aggregated stats across all timeframes |

**Timeframes:** `10m`, `1h`, `4h`, `12h`, `24h`, `2d`, `7d`, `14d`, `30d`

### Response Structure
```python
api.get_liquidations("1h")
# Returns:
{
    "stats": {
        "total_count": 1234,
        "total_value_usd": 5432100,
        "long_count": 456,
        "short_count": 778,
        "by_coin": {
            "BTC": {"count": 234, "total_value": 2500000, "long_value": 1200000, "short_value": 1300000},
            "ETH": {"count": 345, "total_value": 1800000}
        },
        "largest": [
            {
                "usd_value": 500000,
                "coin": "BTC",
                "side": "long",
                "liq_price": 45000.0,
                "address": "0x...",
                "timestamp": "2024-01-15T10:30:00Z"
            }
        ]
    },
    "timeframe": "1h",
    "updated_at": "2024-01-15T10:35:00Z"
}
```

### Python
```python
# Specific timeframe
data = api.get_liquidations("4h")

# Aggregated stats
stats = api.get_liquidation_stats()
```

---

## Binance Liquidations

Track liquidation events from Binance Futures (separate from Hyperliquid).

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/binance_liquidations/stats.json` | GET | Summary stats (24h volume, counts) |
| `/api/binance_liquidations/10m.json` | GET | Last 10 minutes |
| `/api/binance_liquidations/1h.json` | GET | Last hour |
| `/api/binance_liquidations/24h.json` | GET | Last 24 hours |
| `/api/binance_liquidations/7d.json` | GET | Last 7 days |
| `/api/binance_liquidations/30d.json` | GET | Last 30 days |

### Response Structure
```python
api.get_binance_liquidation_stats()
# Returns:
{
    "total_count": 5432,
    "total_volume": 12500000,
    "long_count": 2345,
    "short_count": 3087,
    "long_volume": 5800000,
    "short_volume": 6700000,
    "top_coins": [
        {"coin": "BTCUSDT", "count": 456, "volume": 3500000},
        {"coin": "ETHUSDT", "count": 389, "volume": 2800000}
    ]
}

api.get_binance_liquidations("1h")
# Returns list of liquidation events:
[
    {
        "symbol": "BTCUSDT",
        "side": "long",
        "price": 45000.0,
        "quantity": 0.5,
        "value": 22500.0,
        "timestamp": 1704067200000
    }
]
```

### Python
```python
# Get aggregated stats
stats = api.get_binance_liquidation_stats()
print(f"Total liquidations: {stats['total_count']}")
print(f"Total volume: ${stats['total_volume']:,.0f}")

# Get liquidations for specific timeframe
# Available: 10m, 1h, 24h, 7d, 30d
data = api.get_binance_liquidations("1h")

# Change timeframe as needed
data_24h = api.get_binance_liquidations("24h")
data_7d = api.get_binance_liquidations("7d")
```

---

## Position Tracking

Monitor large positions near liquidation ($200k+).

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/positions.json` | GET | Large positions near liquidation |

### Response Structure
```python
api.get_positions()
# Returns:
{
    "total_positions": 150,
    "total_longs": 75,
    "total_shorts": 75,
    "min_position_value": 200000,
    "longs": [
        {
            "address": "0x...",
            "coin": "BTC",
            "value": 500000,
            "leverage": 10.0,
            "entry_price": 45000.0,
            "liq_price": 40000.0,
            "distance_pct": 11.1,
            "pnl": 25000.0
        }
    ],
    "shorts": [...],
    "updated_at": "2024-01-15T10:35:00Z"
}
```

---

## Whale Activity

Track whale traders and large trades.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/whales.json` | GET | Recent whale trades ($25k+) |
| `/api/whale_addresses.txt` | GET | Plain text whale address list |

### Response Structure
```python
api.get_whales()
# Returns:
{
    "trades": [
        {
            "timestamp": "2024-01-15T10:30:00Z",
            "coin": "BTC",
            "side": "buy",
            "size": 2.5,
            "usd_value": 112500.0,
            "address": "0x..."
        }
    ],
    "total_trades": 500,
    "min_value": 25000
}

api.get_whale_addresses()
# Returns: ["0x123...", "0x456...", ...]  (1000+ addresses)
```

---

## Blockchain Events

Real-time blockchain activity.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/events.json` | GET | Real-time blockchain events |

### Event Types
- `Transfer` - Token transfers
- `Swap` - DEX swaps
- `Deposit` - Exchange deposits
- `Withdrawal` - Exchange withdrawals

```python
api.get_events()
# Returns:
{
    "events": [...],
    "stats": {
        "total_events": 50000,
        "events_by_type": {
            "Transfer": 25000,
            "Swap": 15000,
            "Deposit": 5000,
            "Withdrawal": 5000
        }
    }
}
```

---

## Contract Registry

Track smart contracts and their activity.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/contracts.json` | GET | Contract registry with metadata |

```python
api.get_contracts()
# Returns:
{
    "contracts": [
        {
            "address": "0x...",
            "name": "Uniswap V3",
            "type": "DEX",
            "activity_count": 50000,
            "total_value": 10000000
        }
    ],
    "high_value_count": 50
}
```

---

## Tick Data & Prices

Historical price data and current prices.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/ticks/stats.json` | GET | Collection stats |
| `/api/ticks/latest.json` | GET | Current prices for all symbols |
| `/api/ticks/{symbol}_{timeframe}.json` | GET | Historical ticks |

**Symbols:** `btc`, `eth`, `hype`, `sol`, `xrp`
**Timeframes:** `10m`, `1h`, `4h`, `24h`, `7d`

```python
# Latest prices
api.get_tick_latest()
# Returns: {"btc": 45000.0, "eth": 2500.0, "sol": 100.0, ...}

# Historical data
api.get_ticks("btc", "1h")
# Returns: [{"timestamp": ..., "open": 45000, "high": 45500, "low": 44800, "close": 45200, "volume": 1000}, ...]
```

---

## Order Flow & Trades

Track trading activity and market pressure.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/trades.json` | GET | Recent 500 trades (real-time) |
| `/api/large_trades.json` | GET | Large trades >$100k (24h) |
| `/api/orderflow.json` | GET | Order flow imbalance |
| `/api/orderflow/stats.json` | GET | Service stats |
| `/api/imbalance/{timeframe}.json` | GET | Buy/sell imbalance |

**Imbalance Timeframes:** `5m`, `15m`, `1h`, `4h`, `24h`

**Tracked Coins:** BTC, ETH, HYPE, SOL, XRP

### Response Structures
```python
# Recent trades
api.get_trades()
# Returns:
{
    "trades": [
        {"coin": "BTC", "side": "buy", "size": 0.5, "price": 45000.0, "usd_value": 22500.0, "timestamp": "..."}
    ]
}

# Order flow
api.get_orderflow()
# Returns:
{
    "by_timeframe": {
        "5m": {"buy_pressure": 0.55, "cumulative_delta": 15000, "dominant": "BUY"},
        "15m": {...},
        "1h": {...},
        "4h": {...}
    },
    "by_coin": {
        "BTC": {"buy_volume": 5000000, "sell_volume": 4500000, "buy_pressure": 0.52},
        "ETH": {...}
    }
}

# Imbalance
api.get_imbalance("1h")
# Returns:
{
    "buy_volume": 5000000,
    "sell_volume": 4500000,
    "imbalance": 0.1,
    "direction": "BUY"
}
```

---

## Smart Money Intelligence

Track top performers and trading signals.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/smart_money/rankings.json` | GET | Top 100 smart + Bottom 100 dumb |
| `/api/smart_money/leaderboard.json` | GET | Top 50 performers with details |
| `/api/smart_money/signals_{timeframe}.json` | GET | Trading signals |

**Signal Timeframes:** `10m`, `1h`, `24h`

```python
# Rankings
api.get_smart_money_rankings()
# Returns:
{
    "smart_money": [
        {"address": "0x...", "pnl": 500000, "win_rate": 0.75, "trades": 150}
    ],
    "dumb_money": [...]
}

# Leaderboard
api.get_smart_money_leaderboard()
# Returns:
{
    "leaderboard": [
        {"address": "0x...", "total_pnl": 1000000, "win_rate": 0.8, "avg_trade": 25000}
    ]
}

# Signals
api.get_smart_money_signals("1h")
# Returns:
{
    "signals": [
        {"coin": "BTC", "direction": "LONG", "confidence": 0.85, "smart_money_buying": true}
    ]
}
```

---

## User Data (Individual Wallets)

Get data for any Hyperliquid wallet address.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/user/{address}/positions` | GET | User positions via Moon Dev API |
| `/api/user/{address}/fills` | GET | User trade history |

### User Positions
```python
api.get_user_positions_api("0x010461c14e146ac35fe42271bdc1134ee31c703a")
# Returns: Same as direct Hyperliquid clearinghouseState
```

### User Fills (Trade History)
```python
# Get last 100 fills
api.get_user_fills("0x...", limit=100)

# Get ALL fills (can be 32,000+)
api.get_user_fills("0x...", limit=-1)

# Returns:
{
    "fills": [
        {
            "coin": "BTC",
            "px": "45000.0",
            "sz": "0.1",
            "side": "B",  # B=Buy, S=Sell
            "time": 1704067200000,
            "startPosition": "0.5",
            "dir": "Open Long",
            "closedPnl": "0",
            "hash": "abc123...",
            "tid": 12345,
            "fee": "1.5"
        }
    ],
    "total": 32000,
    "limit": 100,
    "address": "0x..."
}
```

---

## HLP (HyperLiquidity Provider)

Comprehensive HLP strategy tracking and analysis.

### HLP Addresses
| Name | Address | Role |
|------|---------|------|
| HLP Strategy A | `0x010461c14e146ac35fe42271bdc1134ee31c703a` | Main market maker (short-biased) |
| HLP Strategy B | `0x31ca8395cf837de08b24da3f660e77761dfb974b` | Secondary market maker (long-biased) |
| HLP Liquidator | `0x2e3d94f0562703b25c83308a05046ddaf9a8dd14` | Liquidation bot |
| HLP Liquidator 2 | `0xb0a55f13d22f66e6d495ac98113841b2326e9540` | Liquidation bot ($30M) |
| HLP Liquidator 3 | `0x5e177e5e39c0f4e421f5865a6d8beed8d921cb70` | Liquidation bot |
| HLP Liquidator 4 | `0x2ed5c4484ea3ff8b57d5f2fb152a40d9f2b68308` | Liquidation bot |
| HLP Strategy X | `0x469f690213c467c39a23efacfd2816896009d7d8` | Experimental |

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/hlp/positions` | GET | All 7 HLP strategy positions + combined net |
| `/api/hlp/trades` | GET | Historical HLP trade fills |
| `/api/hlp/trades/stats` | GET | Trade volume/fee statistics |
| `/api/hlp/positions/history` | GET | Position snapshots over time |
| `/api/hlp/liquidators` | GET | Liquidator activation events |
| `/api/hlp/deltas` | GET | Net exposure changes over time |

### HLP Positions
```python
# Full data with strategy breakdown
api.get_hlp_positions(include_strategies=True)

# Summary only (faster)
api.get_hlp_positions(include_strategies=False)

# Returns:
{
    "summary": {
        "total_account_value": 211000000,
        "total_positions": 366,
        "total_long_value": 18000000,
        "total_short_value": 17500000,
        "net_exposure_delta": 500000
    },
    "combined_positions": [
        {
            "coin": "BTC",
            "net_size": 0.5,
            "net_value": 22500,
            "long_strategies": ["HLP Strategy A"],
            "short_strategies": ["HLP Strategy B"],
            "total_long": 1.0,
            "total_short": 0.5
        }
    ],
    "strategies": {
        "HLP Strategy A": {
            "account_value": 89000000,
            "positions": [...],
            "long_count": 81,
            "short_count": 102,
            "long_value": 8760000,
            "short_value": 9150000
        }
    }
}
```

### HLP Trades
```python
api.get_hlp_trades(limit=100)
# Returns:
{
    "trades": [
        {
            "timestamp": "2024-01-15T10:30:00Z",
            "strategy": "HLP Strategy A",
            "coin": "BTC",
            "side": "B",
            "price": 45000.0,
            "size": 0.1,
            "fee": 1.5,
            "is_maker": true
        }
    ],
    "total": 5000,
    "strategies": ["HLP Strategy A", "HLP Strategy B"]
}
```

### HLP Trade Statistics
```python
api.get_hlp_trade_stats()
# Returns:
{
    "total_trades": 50000,
    "total_volume": 500000000,
    "total_fees": 250000,
    "date_range": {
        "first": "2024-01-01T00:00:00Z",
        "last": "2024-01-15T10:30:00Z"
    },
    "by_strategy": {
        "HLP Strategy A": {"trades": 25000, "volume": 250000000, "fees": 125000},
        "HLP Strategy B": {"trades": 25000, "volume": 250000000, "fees": 125000}
    },
    "by_coin": {
        "BTC": {"trades": 10000, "volume": 200000000},
        "ETH": {"trades": 8000, "volume": 150000000}
    }
}
```

### HLP Position History
```python
api.get_hlp_position_history(hours=24)
# Returns:
{
    "snapshots": [
        {
            "timestamp": "2024-01-15T10:00:00Z",
            "total_long_value": 18000000,
            "total_short_value": 17500000,
            "net_delta": 500000,
            "positions_by_coin": {...}
        }
    ],
    "interval": "5m"
}
```

### HLP Liquidator Events
```python
api.get_hlp_liquidators()
# Returns:
{
    "liquidators": [
        {
            "name": "HLP Liquidator",
            "address": "0x2e3d...",
            "status": "idle",
            "account_value": 1000000,
            "position_count": 0
        },
        {
            "name": "HLP Liquidator 2",
            "address": "0xb0a5...",
            "status": "active",
            "account_value": 30000000,
            "position_count": 5
        }
    ],
    "events": [
        {
            "timestamp": "2024-01-15T08:30:00Z",
            "liquidator": "HLP Liquidator 2",
            "event_type": "activated",
            "details": "Opened 5 positions"
        }
    ]
}
```

### HLP Net Exposure Deltas
```python
api.get_hlp_deltas(hours=24)
# Returns:
{
    "deltas": [
        {"timestamp": "2024-01-15T10:00:00Z", "net_delta": 500000},
        {"timestamp": "2024-01-15T09:55:00Z", "net_delta": 480000}
    ],
    "current": 500000,
    "change_24h": 20000
}
```

---

## Direct Hyperliquid API

For direct queries to Hyperliquid (bypasses Moon Dev API).

### Base URL
```
https://api.hyperliquid.xyz/info
```

### User Positions (clearinghouseState)
```python
# Via MoonDevAPI wrapper
api.get_user_positions("0x...")

# Direct API call
import requests
payload = {"type": "clearinghouseState", "user": "0x..."}
response = requests.post("https://api.hyperliquid.xyz/info", json=payload)
```

### Response Structure
```python
{
    "assetPositions": [
        {
            "position": {
                "coin": "BTC",
                "szi": "0.5",              # Size (positive=long, negative=short)
                "entryPx": "45000.0",
                "positionValue": "22500.0",
                "unrealizedPnl": "500.0",
                "liquidationPx": "40000.0",
                "leverage": {"value": 10}
            }
        }
    ],
    "marginSummary": {
        "accountValue": "50000.0",
        "totalNtlPos": "22500.0",
        "totalRawUsd": "50000.0"
    }
}
```

### Other Direct Endpoints

| Payload Type | Description |
|-------------|-------------|
| `clearinghouseState` | User positions and margin |
| `userFills` | Trade history for a user |
| `userFunding` | Funding payments |
| `openOrders` | Open limit orders |
| `meta` | Exchange metadata |
| `metaAndAssetCtxs` | Metadata + asset contexts |
| `l2Book` | Order book depth |
| `trades` | Recent trades for a coin |
| `candleSnapshot` | OHLCV candle data |
| `vaultDetails` | Vault information |

---

## Python SDK Usage

### Installation
```bash
pip install -r requirements.txt
```

### Quick Start
```python
from api import MoonDevAPI

# Initialize
api = MoonDevAPI()  # Uses MOONDEV_API_KEY from .env

# Get liquidation data
liqs = api.get_liquidations("1h")
print(f"1h Liquidations: {liqs['stats']['total_count']}")

# Get positions near liquidation
positions = api.get_positions()
print(f"Large positions: {positions['total_positions']}")

# Get HLP data
hlp = api.get_hlp_positions()
print(f"HLP Account Value: ${hlp['summary']['total_account_value']:,}")

# Get user positions
user_pos = api.get_user_positions("0x010461c14e146ac35fe42271bdc1134ee31c703a")
print(f"User has {len(user_pos['assetPositions'])} positions")

# Get user trade history
fills = api.get_user_fills("0x...", limit=100)
print(f"Found {fills['total']} total trades")
```

### Run Test Suite
```bash
python api.py
```

---

## Example Scripts

Located in `/api_examples/`:

| Script | Description |
|--------|-------------|
| `01_liquidations.py` | Hyperliquid liquidation dashboard |
| `02_positions.py` | Position tracking near liquidation |
| `03_whales.py` | Whale activity monitor |
| `04_events.py` | Blockchain event viewer |
| `05_contracts.py` | Contract registry explorer |
| `06_ticks.py` | Price charts and tick data |
| `07_orderflow.py` | Order flow analysis |
| `08_trades.py` | Trade stream viewer |
| `09_smart_money.py` | Smart money intelligence |
| `10_user_positions.py` | User position viewer |
| `11_user_fills.py` | User trade history |
| `12_hlp_positions.py` | HLP strategy dashboard |
| `13_binance_liquidations.py` | Binance Futures liquidation dashboard |

### HLP-Specific Scripts

Located in `/bots/hyperliquid/`:

| Script | Description |
|--------|-------------|
| `hlp_db_setup.py` | Initialize SQLite database |
| `hlp_trade_history.py` | Collect all HLP trade fills |
| `hlp_position_tracker.py` | 5-min position snapshots |
| `hlp_liquidation_watcher.py` | Monitor liquidator activation |

### Run HLP Scripts
```bash
# Initialize database
python bots/hyperliquid/hlp_db_setup.py

# Backfill trade history
python bots/hyperliquid/hlp_trade_history.py

# Start position tracking (runs continuously)
python bots/hyperliquid/hlp_position_tracker.py

# Monitor liquidators (runs continuously)
python bots/hyperliquid/hlp_liquidation_watcher.py
```

---

## Error Handling

### HTTP Status Codes
| Code | Meaning |
|------|---------|
| 200 | Success |
| 401 | Invalid/missing API key |
| 429 | Rate limit exceeded |
| 500 | Server error |

### Python Error Handling
```python
try:
    data = api.get_liquidations("1h")
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 401:
        print("Invalid API key")
    elif e.response.status_code == 429:
        print("Rate limited - slow down")
except requests.exceptions.Timeout:
    print("Request timed out")
```

---

## Need Help?

- **API Key:** https://moondev.com
- **Documentation:** https://moondev.com/docs
- **Issues:** https://github.com/moondevonyt/trading-bots/issues

---

*Built with love by Moon Dev* 🌙
