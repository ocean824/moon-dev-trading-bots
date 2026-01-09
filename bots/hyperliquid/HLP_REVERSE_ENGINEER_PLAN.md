# HLP Strategy Reverse Engineering Plan
## Moon Dev's Guide to Understanding How HLP Made $118M

---

## What We Know

**HLP (Hyperliquidity Provider)** runs 7 component strategies:

| Name | Address | Status | Purpose |
|------|---------|--------|---------|
| HLP Strategy A | `0x010461c14e146ac35fe42271bdc1134ee31c703a` | ACTIVE | Short-biased MM |
| HLP Strategy B | `0x31ca8395cf837de08b24da3f660e77761dfb974b` | ACTIVE | Long-biased MM |
| HLP Liquidator | `0x2e3d94f0562703b25c83308a05046ddaf9a8dd14` | IDLE ($1M) | Liquidation hunting |
| HLP Liquidator 2 | `0xb0a55f13d22f66e6d495ac98113841b2326e9540` | IDLE ($30M) | Liquidation hunting |
| HLP Liquidator 3 | `0x5e177e5e39c0f4e421f5865a6d8beed8d921cb70` | IDLE ($1M) | Liquidation hunting |
| HLP Liquidator 4 | `0x2ed5c4484ea3ff8b57d5f2fb152a40d9f2b68308` | IDLE ($1M) | Liquidation hunting |
| HLP Strategy X | `0x469f690213c467c39a23efacfd2816896009d7d8` | IDLE ($1K) | Unknown |

**Key Insight:** Strategy A and B run OPPOSITE positions to stay delta-neutral overall.

---

## Data Collection Scripts to Build

### 1. `hlp_db_setup.py` - Database Initialization
```python
# Creates SQLite database with tables:
# - positions (5-min snapshots)
# - trades (historical fills)
# - liquidator_events (when idle accounts activate)
# - position_deltas (net exposure over time)
```

### 2. `hlp_trade_history.py` - Trade Reconstruction
**API Endpoint:** `userFills`
```python
payload = {"type": "userFills", "user": address}
```
**Collects:**
- Every trade execution with timestamp
- Price, size, side (buy/sell)
- Fee paid/rebate earned (maker vs taker)
- Links trades to positions

### 3. `hlp_position_tracker.py` - Time-Series Snapshots
**API Endpoint:** `clearinghouseState`
**Frequency:** Every 5 minutes
**Collects:**
- All positions for all 7 addresses
- Position changes (deltas)
- Net long/short exposure

### 4. `hlp_liquidation_watcher.py` - Liquidator Monitor
**Frequency:** Every 1 minute
**Watches:** The 4 idle liquidator accounts
**Triggers:**
- Any position opens on idle account
- Cross-reference with Moon Dev API liquidation events

---

## SQLite Database Schema

```sql
-- Position snapshots
CREATE TABLE positions (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME,
    address TEXT,
    strategy_name TEXT,
    coin TEXT,
    side TEXT,
    size REAL,
    position_value REAL,
    entry_price REAL,
    unrealized_pnl REAL,
    leverage REAL,
    liquidation_price REAL
);

-- Trade fills
CREATE TABLE trades (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME,
    address TEXT,
    strategy_name TEXT,
    coin TEXT,
    side TEXT,
    price REAL,
    size REAL,
    usd_value REAL,
    fee REAL,
    is_maker BOOLEAN,
    order_id TEXT
);

-- Liquidator events
CREATE TABLE liquidator_events (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME,
    address TEXT,
    liquidator_name TEXT,
    event_type TEXT,
    coin TEXT,
    details TEXT
);

-- Net exposure tracking
CREATE TABLE position_deltas (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME,
    coin TEXT,
    net_long_value REAL,
    net_short_value REAL,
    net_delta REAL,
    delta_change REAL
);
```

---

## Key Questions to Answer

1. **Entry Timing:** When do they open positions? (Price level? Volatility? Funding rate?)
2. **Position Sizing:** How do they size? (Fixed? Volatility-adjusted? Kelly?)
3. **Exit Strategy:** When do they close? (Target PnL? Time-based? Market condition?)
4. **Risk Management:** How do they stay delta-neutral?
5. **Liquidator Trigger:** What activates the liquidator accounts?
6. **Maker vs Taker:** Do they provide or take liquidity?
7. **Funding Strategy:** Do they intentionally farm funding rates?

---

## Server Deployment

All scripts run 24/7 on server:

| Script | Frequency | Purpose |
|--------|-----------|---------|
| `hlp_position_tracker.py` | Every 5 min | Position snapshots |
| `hlp_trade_history.py` | Every 1 hour | Backfill new trades |
| `hlp_liquidation_watcher.py` | Every 1 min | Watch idle accounts |

Data stored in: `data/hlp_tracker/hlp_data.db`

---

## Expected Insights (After 1 Week)

- **Trade patterns:** Maker vs taker ratio, avg trade size, time of day patterns
- **Position changes:** Entry/exit timing relative to price moves
- **Liquidator activity:** Conditions that trigger liquidator account activation
- **Delta drift:** How net exposure changes over time
- **Profit attribution:** Trading PnL vs funding vs liquidations

---

## Files to Create

```
bots/hyperliquid/
├── hlp_db_setup.py            # Database initialization
├── hlp_trade_history.py       # Trade fill collection
├── hlp_position_tracker.py    # Position snapshots
├── hlp_liquidation_watcher.py # Liquidator monitoring
└── data/hlp_tracker/
    └── hlp_data.db            # SQLite database
```

---

## Moon Dev's Notes

HLP's edge appears to be:
1. **Scale** - $295M TVL means they can provide deep liquidity
2. **Delta-neutral** - Strategy A shorts what Strategy B longs
3. **Liquidation profits** - $34M sitting in liquidator accounts waiting
4. **Funding arbitrage** - Positioned to earn funding on both sides
5. **Information edge** - They see order flow as the main liquidity provider

To replicate at smaller scale:
- Focus on coins with high funding rates
- Monitor liquidation cascades and front-run them
- Stay delta-neutral but earn spread + funding
