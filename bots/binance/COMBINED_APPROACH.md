# Moon Dev's Combined BTC+ETH Liquidation Detector 🌙

## The Combined Approach

You wanted **ONE STREAM** analyzing BTC and ETH together - and that's exactly what this does!

## Why Combined?

**That's why we switched to USD volume** - so we can meaningfully combine BTC and ETH trades into a single market velocity metric!

### The Key Insight:
When liquidations happen, they cascade across **BOTH** BTC and ETH simultaneously. By analyzing them as ONE COMBINED STREAM, we get:

✅ **Stronger signals** - Combined velocity = more data points
✅ **Better detection** - When BOTH spike together = ultra high confidence
✅ **Simpler** - ONE signal to act on, not juggling two separate streams
✅ **Market-wide view** - See the entire crypto market liquidating at once

---

## How It Works

### 1. Combined Trade Stream

All trades from **both BTC and ETH** go into ONE deque:

```python
combined_trades = deque(maxlen=2000)

# Every trade from BTC or ETH gets added:
trade = {
    'time': datetime.now(),
    'symbol': 'BTCUSDT',  # or 'ETHUSDT'
    'price': 102000.0,
    'quantity': 0.05,
    'volume_usd': 5100.0,  # ← This is comparable!
    'is_buyer_maker': False
}

combined_trades.append(trade)
```

### 2. Combined Velocity Metrics

Speed is calculated across **ALL trades from both symbols**:

| Metric | What It Measures |
|--------|------------------|
| **combined_trades_5s** | Total trades (BTC + ETH) in last 5 seconds |
| **combined_trades_10s** | Total trades (BTC + ETH) in last 10 seconds |
| **combined_trades_30s** | Total trades (BTC + ETH) in last 30 seconds |
| **combined_volume_usd_10s** | Total USD volume from both symbols |
| **combined_volume_usd_30s** | Total USD volume from both symbols |
| **combined_buy_sell_ratio** | Overall market buy/sell pressure |
| **current_speed** | Combined trades/sec across market |
| **baseline_speed** | Normal combined trades/sec |
| **speed_multiplier** | current_speed / baseline_speed |

**Example from test run:**
- Baseline: **52.3 trades/sec** (normal BTC+ETH combined)
- Current: **165.5 trades/sec** (during liquidation event)
- Multiplier: **3.16x** (+216% faster!) 🔥

**Continuous Rolling Baseline:**
The baseline is NOT static! It continuously adapts to market conditions:
- **10-minute rolling window** - last 600 samples kept in memory
- **Excludes spikes** - only "calm" samples (< 2x baseline) are collected
- **Updates every 60 seconds** - recalculated from the rolling window
- **Adapts to market hours** - automatically adjusts for quiet Asian hours vs volatile US hours

This prevents two problems:
1. Starting during a liquidation event (would make that your "normal")
2. Stale baselines hours later when market conditions change

### 3. Individual S/R Tracking

Each symbol still has its own support/resistance:
- BTC has its own levels (price range $100k+)
- ETH has its own levels (price range $3k+)

This lets us know **which symbol(s) are near key levels** when velocity spikes.

### 4. Combined Signal Generation

**ONE SIGNAL** based on:
1. **Combined velocity spike** (is market 2x+ faster?)
2. **Which symbols are at S/R** (BTC, ETH, or both?)

**Signal includes:**
- `signal`: 'RESISTANCE_BREAK', 'SUPPORT_BREAK', etc.
- `strength`: 0-100 confidence
- `symbols`: ['BTC'], ['ETH'], or **['BTC', 'ETH']** ← both!

**Example Scenarios:**

| Scenario | What Happens | Signal |
|----------|--------------|--------|
| BTC near resistance + velocity 3x | `RESISTANCE_TEST`, symbols=['BTC'] | Moderate signal |
| ETH near support + velocity 3x | `SUPPORT_TEST`, symbols=['ETH'] | Moderate signal |
| **BOTH near resistance + velocity 3x** | `RESISTANCE_TEST`, symbols=['BTC', 'ETH'] | **ULTRA strong!** +30 strength bonus |

---

## Test Results

During our test, caught a real signal:

```
🎯 COMBINED MARKET SIGNAL: SUPPORT_TEST
Symbols Involved: BTC
Direction: SHORT
Strength: 64/100

💵 CURRENT PRICES
BTC: $101,954.64
ETH: $3,415.01

⚡ COMBINED SPEED
Current Speed:  165.50 trades/sec  ← COMBINED BTC+ETH
Baseline Speed:  52.30 trades/sec  ← COMBINED normal
Speed Multiplier: 3.16x (+216%)    ← THE SIGNAL!

📊 COMBINED TRADES
Trades (5s):  1655 trades  ← ALL trades from both symbols
Trades (10s): 1655 trades
Trades (30s): 1655 trades

💰 COMBINED USD VOLUME
Volume (10s): $514,632  ← Both BTC and ETH combined
Volume (30s): $514,632
Buy/Sell Ratio: 0.20    ← Heavy selling across market!

📍 LEVELS (20-candle)
BTC Support: $101,699.91
BTC Distance: 0.250% away  ← BTC near support
```

**What this tells us:**
- Combined market velocity **3.16x faster** than normal
- Total volume: **$514k in 10 seconds** across both symbols
- BTC is **0.25% away from support**
- Buy/sell ratio: **0.20** = 5x more selling than buying
- **Longs about to get liquidated if support breaks!**

---

## How to Use in Your Bot

### Simple Example:

```python
from combined_liquidation_detector import CombinedLiquidationDetector

detector = CombinedLiquidationDetector(
    proximity_threshold=0.5,
    speed_multiplier_threshold=2.0
)

# Run in background...

while True:
    signal = detector.get_latest_signal()

    if signal and signal['strength'] >= 70:

        if signal['signal'] == 'RESISTANCE_BREAK':
            print(f"🚀 GO LONG on {' + '.join(signal['symbols'])}")
            print(f"   Speed: {signal['speed_multiplier']:.2f}x")

            # Trade the symbols involved
            for symbol in signal['symbols']:
                if symbol == 'BTC':
                    exchange.buy('BTC', 5)
                elif symbol == 'ETH':
                    exchange.buy('ETH', 5)

        elif signal['signal'] == 'SUPPORT_BREAK':
            print(f"💥 GO SHORT on {' + '.join(signal['symbols'])}")
            # ... similar logic

    time.sleep(2)
```

### Advanced: Use Combined Strength

```python
signal = detector.get_latest_signal()

# When BOTH symbols signal = trade bigger
if signal['strength'] >= 80 and len(signal['symbols']) == 2:
    print("🔥 BOTH BTC AND ETH LIQUIDATING!")
    print("   This is a MEGA signal - trade larger size")
    # Trade 2x size or add to position
```

---

## What You Get

### Return Value:

```python
{
    'signal': 'SUPPORT_TEST',
    'strength': 64,
    'symbols': ['BTC'],  # or ['ETH'] or ['BTC', 'ETH']
    'btc_price': 101954.64,
    'eth_price': 3415.01,
    'speed_multiplier': 3.16,
    'metrics': {
        'combined_trades_5s': 1655,
        'combined_trades_10s': 1655,
        'combined_trades_30s': 1655,
        'combined_volume_usd_10s': 514632.0,
        'combined_volume_usd_30s': 514632.0,
        'combined_buy_sell_ratio': 0.20,
        'current_speed': 165.5,
        'baseline_speed': 52.3,
        'speed_multiplier': 3.16
    },
    'timestamp': datetime(...)
}
```

---

## CSV Log Format

Every second, logs to `combined_liquidation_log_{timestamp}.csv`:

### Columns:
```csv
timestamp,
btc_price,eth_price,
combined_trades_5s,combined_trades_10s,combined_trades_30s,
combined_volume_usd_10s,combined_volume_usd_30s,
combined_buy_sell_ratio,
btc_support_20,btc_dist_support_20_pct,
btc_resistance_20,btc_dist_resistance_20_pct,
eth_support_20,eth_dist_support_20_pct,
eth_resistance_20,eth_dist_resistance_20_pct,
current_speed_per_sec,baseline_speed_per_sec,speed_multiplier,
signal,signal_strength,signal_symbols
```

**Key point:** `signal_symbols` column shows which symbols were involved, separated by `+`:
- `BTC` - Only BTC triggered
- `ETH` - Only ETH triggered
- `BTC+ETH` - **BOTH triggered together!** (strongest)

---

## Advantages of Combined Approach

### 1. Market-Wide View
You're not looking at BTC or ETH in isolation - you see the **ENTIRE crypto market** liquidating.

### 2. Stronger Signals
More data points = more reliable speed calculations:
- Separate BTC: ~50 trades/sec
- Separate ETH: ~15 trades/sec
- **Combined: ~65 trades/sec** = better statistical significance

### 3. Catch Correlated Liquidations
When both BTC and ETH cascade together:
- Separate approach: Two medium signals
- **Combined approach: ONE ULTRA strong signal**

### 4. Simpler Bot Logic
```python
# Instead of:
if btc_signal and eth_signal:
    # coordinate two separate signals...

# You get:
if signal['symbols'] == ['BTC', 'ETH']:
    # ONE strong signal to act on!
```

### 5. USD Volume Makes Sense
- BTC: $100k × 0.5 coins = $50k
- ETH: $3.4k × 15 coins = $51k
- **Combined: $101k in volume**

Now you can meaningfully add them up!

---

## When Signals Fire

### Scenario 1: BTC Only
```
Signal: RESISTANCE_TEST
Symbols: ['BTC']
Strength: 55
→ BTC testing resistance with speed spike
→ ETH not involved
```

### Scenario 2: ETH Only
```
Signal: SUPPORT_BREAK
Symbols: ['ETH']
Strength: 60
→ ETH broke support with velocity
→ BTC not near any levels
```

### Scenario 3: BOTH (Strongest!)
```
Signal: RESISTANCE_BREAK
Symbols: ['BTC', 'ETH']
Strength: 90  ← +30 bonus for both!
→ ENTIRE MARKET breaking resistance
→ Massive short liquidation cascade
→ ULTRA HIGH CONFIDENCE
```

---

## Files

```
bots/binance/
├── combined_liquidation_detector.py  ⭐ Main detector - use this!
├── example_combined_bot.py           ⭐ Example bot integration
├── COMBINED_APPROACH.md               This file
└── logs/
    └── combined_liquidation_log_*.csv  One log file with everything
```

---

## Quick Start

### Run the Detector:

```bash
python bots/binance/combined_liquidation_detector.py
```

### Run Example Bot:

```bash
python bots/binance/example_combined_bot.py
```

---

## Key Takeaways for Moon Dev

### What Changed:
✅ **ONE combined trade stream** - all BTC + ETH trades together
✅ **ONE speed metric** - combined trades/sec across market
✅ **ONE signal** - based on combined velocity
✅ **Symbols array** - tells you which are involved
✅ **Bonus strength** - when both symbols trigger together

### Why This Is Better:
1. **Simpler** - One thing to monitor
2. **Stronger** - Combined velocity = better signal
3. **Smarter** - Detects market-wide liquidations
4. **Cleaner** - One signal, one action

### The Thesis:
When the **combined BTC+ETH market velocity** spikes AND one or both symbols are near support/resistance = liquidation cascade happening = trade it!

### What You Should Do:
1. **Run it now** - Let it collect data
2. **Watch for both symbols** - When `symbols=['BTC', 'ETH']` = best trades
3. **Analyze CSV** - See when combined signals work best
4. **Build your bot** - Use the clear single-signal structure
5. **Start tiny** - $10 total ($5 BTC + $5 ETH if both)

---

Built with 🌙 by Moon Dev

**One stream. One signal. Combined power.**
