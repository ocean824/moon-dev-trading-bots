# Moon Dev's Liquidation Detector - Complete Data Structure 📊

## Overview

This document explains EXACTLY what data you're collecting and how to use it in your trading bot.

## Updated Metrics (Nov 13, 2025)

### Changes Made:
✅ **Removed coin volume** - Since BTC and ETH have different prices, coin quantities aren't comparable
✅ **Kept USD volume only** - This is what matters for comparing market activity
✅ **Added 30-second window** - Now tracking: 5s, 10s, and 30s trade counts
✅ **Super clear prints** - Shows current speed, baseline speed, and the multiplier/change
✅ **Clear return structure** - Documentation shows exactly what you get when calling from another file

---

## What You're Collecting

### Speed Metrics (The Core)

| Metric | Description | What It Means |
|--------|-------------|---------------|
| **trades_5s** | Number of trades in last 5 seconds | Short-term velocity burst |
| **trades_10s** | Number of trades in last 10 seconds | Medium-term velocity |
| **trades_30s** | Number of trades in last 30 seconds | Longer-term velocity trend |
| **current_speed** | Trades per second (10s window / 10) | Real-time speed |
| **baseline_speed** | Average trades/sec (set at startup) | "Normal" speed for comparison |
| **speed_multiplier** | current_speed / baseline_speed | How many times faster than normal |

**Example:**
- Baseline: 49 trades/sec (normal BTC speed)
- Current: 100 trades/sec
- Multiplier: **2.04x** (+104% faster)

This is what triggers liquidation signals!

### Volume Metrics (USD Only)

| Metric | Description | Why USD Only |
|--------|-------------|--------------|
| **volume_usd_10s** | Total USD traded in last 10 seconds | ETH at $3,400 vs BTC at $100k = different coin volumes but USD is comparable |
| **volume_usd_30s** | Total USD traded in last 30 seconds | Longer window for trend confirmation |
| **buy_sell_ratio** | Buy volume / Sell volume (10s) | >1 = more buying, <1 = more selling |

**Example:**
- BTC volume_usd_10s: $93,087
- ETH volume_usd_10s: $76,152
- Now you can compare! BTC has 22% more volume right now.

### Support/Resistance Levels

| Level | Description | Use Case |
|-------|-------------|----------|
| **support_20** | Lowest low in last 20 min candles | Short-term support |
| **resistance_20** | Highest high in last 20 min candles | Short-term resistance |
| **support_60** | Lowest low in last 60 min candles | Medium-term support |
| **resistance_60** | Highest high in last 60 min candles | Medium-term resistance |
| **dist_support_20** | % above support_20 | If 0.3% = very close |
| **dist_resistance_20** | % below resistance_20 | If 0.1% = very close |

**Distance Examples:**
- `dist_resistance_20: 0.308%` = 0.308% away from resistance (close!)
- `dist_resistance_20: -0.1%` = Negative = broke through resistance!

---

## What You Get When Calling From Your Bot

### Code Example:

```python
from multi_symbol_liquidation_detector import MultiSymbolLiquidationDetector

detector = MultiSymbolLiquidationDetector(
    symbols=['BTCUSDT', 'ETHUSDT']
)

# Run in background thread...

# Get signals
signals = detector.get_latest_signals()
```

### Return Structure:

```python
{
    'BTCUSDT': {
        'signal': 'RESISTANCE_TEST',    # Signal type
        'strength': 51,                  # Confidence 0-100
        'price': 102285.34,              # Current price
        'speed_multiplier': 2.04,        # Quick access to speed

        'metrics': {                     # ALL SPEED/VOLUME DATA
            'trades_5s': 1000,
            'trades_10s': 1000,
            'trades_30s': 1000,
            'volume_usd_10s': 93087.43,
            'volume_usd_30s': 93087.43,
            'buy_sell_ratio': 7.82,      # Heavy buying!
            'current_speed': 100.00,     # trades/sec
            'baseline_speed': 49.00,     # trades/sec
            'speed_multiplier': 2.04     # 2.04x faster
        },

        'distances': {                   # S/R DISTANCES
            'dist_support_20': 0.572,    # % above
            'dist_resistance_20': 0.308, # % below
            'dist_support_60': 0.572,
            'dist_resistance_60': 0.374
        },

        'timestamp': datetime.datetime(2025, 11, 13, 10, 40, 30)
    },

    'ETHUSDT': {
        'signal': 'RESISTANCE_TEST',
        'strength': 61,
        'price': 3421.88,
        'speed_multiplier': 3.04,        # ETH 3x faster!
        'metrics': { ... },
        'distances': { ... },
        'timestamp': datetime(...)
    }
}
```

---

## Signal Types Reference

| Signal | Meaning | Trading Action |
|--------|---------|----------------|
| **CALM** | Normal conditions | No trade |
| **RESISTANCE_TEST** | Near resistance + speed spike | Watch for breakout (potential LONG) |
| **RESISTANCE_BREAK** | Broke resistance + speed spike | Shorts liquidating → **GO LONG** |
| **SUPPORT_TEST** | Near support + speed spike | Watch for breakdown (potential SHORT) |
| **SUPPORT_BREAK** | Broke support + speed spike | Longs liquidating → **GO SHORT** |
| **HIGH_VELOCITY** | Extreme speed, not near S/R | Momentum play (neutral) |

---

## Console Output Example

When a signal fires, you see:

```
╭── 🚀 Moon Dev Liquidation Alert 🚀 ──╮
│ 🎯 SIGNAL         RESISTANCE_TEST    │
│ Symbol            BTC                │
│ Direction         LONG               │
│ Strength          51/100             │
│ Price             $102,285.34        │
│                                      │
│ ⚡ SPEED ANALYSIS                    │
│ Current Speed     100.00 trades/sec  │ ← Real-time
│ Baseline Speed    49.00 trades/sec   │ ← Normal
│ Speed Multiplier  2.04x (+104%)      │ ← The signal!
│                                      │
│ 📊 TRADE COUNTS                      │
│ Trades (5s)       1000 trades        │
│ Trades (10s)      1000 trades        │
│ Trades (30s)      1000 trades        │
│                                      │
│ 💰 USD VOLUME                        │
│ Volume (10s)      $93,087            │
│ Volume (30s)      $93,087            │
│ Buy/Sell Ratio    7.82               │ ← Heavy buying!
│                                      │
│ 📍 LEVELS (20-candle)                │
│ Resistance        $102,600.54        │
│ Distance          0.308% away        │ ← Very close!
╰──────────────────────────────────────╯

📤 Data returned by get_latest_signals()['BTCUSDT']:
  signal='RESISTANCE_TEST', strength=51, price=102285.34
  current_speed=100.00, baseline=49.00, multiplier=2.04
  trades: 5s=1000, 10s=1000, 30s=1000
  volume_10s=$93,087, volume_30s=$93,087
```

The gray text at the bottom shows EXACTLY what you'd get when calling from your bot!

---

## CSV Log Format

Every second, logs to `bots/binance/logs/liquidation_log_{SYMBOL}_{timestamp}.csv`:

### Columns:
```csv
timestamp,symbol,price,
trades_5s,trades_10s,trades_30s,
volume_usd_10s,volume_usd_30s,
buy_sell_ratio,
support_20,dist_support_20_pct,
resistance_20,dist_resistance_20_pct,
support_60,dist_support_60_pct,
resistance_60,dist_resistance_60_pct,
current_speed_per_sec,baseline_speed_per_sec,speed_multiplier,
signal,signal_strength
```

### Example Row:
```csv
2025-11-13T10:40:30.865151,BTCUSDT,102285.34,
1000,1000,1000,
93087.43,93087.43,
7.82,
101699.91,0.572,
102600.54,0.308,
101699.91,0.572,
102667.42,0.374,
100.00,49.00,2.04,
RESISTANCE_TEST,51
```

You can import these CSVs to analyze:
- Which signals worked?
- What speed multipliers are best?
- Time of day patterns?
- Volume thresholds?

---

## How to Use This in Your Trading Bot

### Simple Example:

```python
from multi_symbol_liquidation_detector import MultiSymbolLiquidationDetector
import threading
import time

# Start detector
detector = MultiSymbolLiquidationDetector(
    symbols=['BTCUSDT', 'ETHUSDT'],
    proximity_threshold=0.5,        # Within 0.5% of S/R
    speed_multiplier_threshold=2.0  # 2x speed minimum
)

# Run in background
thread = threading.Thread(target=detector.run)
thread.daemon = True
thread.start()

time.sleep(5)  # Let it initialize

# Your trading loop
while True:
    signals = detector.get_latest_signals()

    # Check BTC
    btc = signals.get('BTCUSDT')
    if btc and btc['strength'] >= 70:  # High confidence only

        if btc['signal'] == 'RESISTANCE_BREAK':
            print(f"🚀 BTC LONG: ${btc['price']:.2f}, Speed: {btc['speed_multiplier']:.2f}x")
            # YOUR EXCHANGE CODE HERE
            # exchange.buy('BTC', 10)

        elif btc['signal'] == 'SUPPORT_BREAK':
            print(f"💥 BTC SHORT: ${btc['price']:.2f}, Speed: {btc['speed_multiplier']:.2f}x")
            # YOUR EXCHANGE CODE HERE
            # exchange.sell('BTC', 10)

    # Check ETH (same logic)
    eth = signals.get('ETHUSDT')
    if eth and eth['strength'] >= 70:
        # ... same logic for ETH ...
        pass

    time.sleep(2)  # Check every 2 seconds
```

### Advanced: Using Multiple Metrics

```python
btc = signals.get('BTCUSDT')

# Only trade if:
# 1. High signal strength
# 2. Extreme speed (3x+)
# 3. High volume
# 4. Strong buy/sell ratio

if (btc['strength'] >= 80 and
    btc['speed_multiplier'] >= 3.0 and
    btc['metrics']['volume_usd_10s'] > 100000 and
    btc['metrics']['buy_sell_ratio'] > 1.5):

    print("🔥 ULTRA HIGH CONFIDENCE SIGNAL!")
    # Trade bigger size
```

---

## Key Takeaways for Moon Dev

### What Changed:
1. ✅ **Removed coin volume** - USD volume only (BTC vs ETH comparable now)
2. ✅ **Added 30-second window** - More data points for trend confirmation
3. ✅ **Crystal clear prints** - Shows baseline, current, and multiplier explicitly
4. ✅ **Clear return structure** - Documentation + console output shows exactly what you get

### What You Should Do:
1. **Run the detector** for 24-48 hours
2. **Watch the signals** - See what speed multipliers trigger
3. **Analyze CSV logs** - Find patterns in what works
4. **Build your bot** - Use the clear data structure above
5. **Start tiny** - $10 positions to test the thesis
6. **Track results** - Keep detailed logs of trades
7. **Iterate** - Adjust parameters based on real results

### The Data You Have:
- ✅ Real-time trade velocity (5s, 10s, 30s windows)
- ✅ Speed vs baseline comparison
- ✅ USD volume (comparable across BTC/ETH)
- ✅ Buy/sell pressure ratio
- ✅ Support/resistance levels (20 and 60 candles)
- ✅ Distance to levels
- ✅ Signal type and confidence

**Everything you need to test your liquidation cascade thesis!**

---

Built with 🌙 by Moon Dev

Run it: `python bots/binance/multi_symbol_liquidation_detector.py`
