# Moon Dev's BTC & ETH Liquidation Detector 🌙

## Overview

A sophisticated liquidation cascade detection system that monitors **BTC and ETH** - the two main market movers - using Binance WebSocket trade streams.

**The Thesis:** When price approaches support/resistance AND trade velocity spikes = liquidation cascades happening = tradeable momentum

## Quick Start

### Run the Multi-Symbol Detector

```bash
python bots/binance/multi_symbol_liquidation_detector.py
```

This monitors both BTC and ETH simultaneously for liquidation signals.

### Run Example Bot (Mock Trading)

```bash
python bots/binance/example_bot_integration.py
```

This shows how to integrate signals into your trading bot logic.

## Why BTC & ETH?

- **BTC** - The market leader, drives overall sentiment
- **ETH** - Second largest, often leads altcoin moves
- Together they represent the majority of crypto market cap
- Their liquidations cascade into the entire market
- Most liquid pairs on Binance = best data quality

## Files in This Directory

```
📄 multi_symbol_liquidation_detector.py  ⭐ Main detector for BTC & ETH
📄 example_bot_integration.py            ⭐ Example bot using both symbols
📄 liquidation_detector.py                Single-symbol version (if needed)
📄 price_tracker.py                       Compact price display tool
📄 README_LIQUIDATION_DETECTOR.md         This file
📄 LIQUIDATION_DETECTOR_README.md         Detailed technical docs
📄 QUICKSTART.md                          Quick start guide
📁 logs/                                  CSV logs for each symbol
```

## How It Works

### 1. Speed Detection
Monitors real-time trade velocity for both BTC and ETH:
- Trades per 5 seconds
- Trades per 10 seconds
- Volume (coins and USD)
- Buy/sell pressure ratio
- Speed multiplier vs baseline (e.g., 3.5x = 350% faster)

### 2. Support/Resistance Calculation
For each symbol independently:
- **20 candles (20 min)** - Short-term S/R
- **60 candles (1 hour)** - Medium-term S/R
- Calculates % distance from current price
- Updates every minute

### 3. Signal Generation
Detects liquidation events per symbol:
- **RESISTANCE_BREAK** → Shorts liquidating → LONG signal
- **SUPPORT_BREAK** → Longs liquidating → SHORT signal
- **RESISTANCE_TEST** → Near resistance + speed spike
- **SUPPORT_TEST** → Near support + speed spike

### 4. Logging & Alerts
- Separate CSV log for each symbol
- Real-time colored console alerts
- Exportable signals for bot integration

## Signal Examples (Real Test Run)

During our test, we caught:

**ETH Signal:**
- Price: $3,429.24
- Resistance (20): $3,436.91 (0.22% away)
- Speed: **2.03x baseline**
- Signal: RESISTANCE_TEST
- Strength: 50/100

**BTC Signal:**
- Price: $102,460.76
- Resistance (20): $102,522.90 (0.06% away)
- Speed: **4.79x baseline** 🔥
- Signal: RESISTANCE_TEST
- Strength: 140/100 (capped at 100)

Notice BTC had 4.79x normal speed while testing resistance - this is exactly what we're looking for!

## Output Format

### Console Signals
When liquidations detected, you'll see colored alerts like:

```
╭─ 🚀 Moon Dev Liquidation Alert 🚀 ─╮
│  Symbol          BTC               │
│  Signal          RESISTANCE_BREAK  │
│  Direction       LONG               │
│  Strength        85/100             │
│  Price           $97,234.52         │
│  Speed           3.2x baseline      │
│  Volume (10s)    $1,215,432         │
│  Resistance (20) $97,180.00 (-0.06%)│
╰────────────────────────────────────╯
```

### CSV Logs
Every second, logs to separate files:
- `liquidation_log_BTCUSDT_{timestamp}.csv`
- `liquidation_log_ETHUSDT_{timestamp}.csv`

Contains all metrics: price, speed, volumes, S/R levels, distances, signals

## Bot Integration

```python
from multi_symbol_liquidation_detector import MultiSymbolLiquidationDetector
import threading

# Start detector
detector = MultiSymbolLiquidationDetector(
    symbols=['BTCUSDT', 'ETHUSDT'],
    proximity_threshold=0.5,
    speed_multiplier_threshold=2.0
)

# Run in background
thread = threading.Thread(target=detector.run)
thread.daemon = True
thread.start()

# Get signals in your bot loop
while True:
    signals = detector.get_latest_signals()

    # BTC signal
    if signals['BTCUSDT']['signal'] == 'RESISTANCE_BREAK':
        exchange.buy('BTC', size)

    # ETH signal
    if signals['ETHUSDT']['signal'] == 'SUPPORT_BREAK':
        exchange.sell('ETH', size)

    time.sleep(2)
```

## Configuration

```python
MultiSymbolLiquidationDetector(
    symbols=['BTCUSDT', 'ETHUSDT'],  # Which pairs to monitor
    proximity_threshold=0.5,          # Within 0.5% = "near" S/R
    speed_multiplier_threshold=2.0    # 2x baseline = "elevated"
)
```

**Tuning:**
- **proximity_threshold**: Lower (0.3%) = stricter, higher (1.0%) = looser
- **speed_multiplier_threshold**: Lower (1.5x) = more signals, higher (3.0x) = only extreme events

## Testing Your Thesis

### Phase 1: Observe (No Trading)
Run the detector for 24-48 hours:
```bash
python bots/binance/multi_symbol_liquidation_detector.py
```

Watch the signals, study the CSV logs, understand the patterns.

### Phase 2: Analyze
Open the CSV files and check:
- Which signals were accurate?
- What speed multipliers worked best?
- Did multi-timeframe confirmation help?
- Any false signals to filter out?

### Phase 3: Paper Trade
Use the example bot:
```bash
python bots/binance/example_bot_integration.py
```

Track mock trades, see if the logic makes sense.

### Phase 4: Live Micro Testing
Start with $10 positions on each symbol:
- Track every trade
- Calculate win rate and P&L
- Adjust parameters based on results
- Only scale if consistently profitable

## What Gets Logged

CSV columns for each symbol:
- timestamp, symbol, price
- trades_5s, trades_10s
- quantity_10s, volume_usd_10s
- buy_sell_ratio
- support_20, resistance_20, support_60, resistance_60
- dist_support_20_pct, dist_resistance_20_pct, etc.
- speed_multiplier, baseline_speed
- signal, signal_strength

## Expected Behaviors

### Normal Market
- Speed multiplier: 0.8x - 1.3x
- Signal: CALM
- Both symbols trading independently

### Resistance Test (BTC Example)
- Price within 0.5% of resistance
- Speed: 2.0x - 3.0x
- Signal: RESISTANCE_TEST
- Could break up (LONG) or reject (SHORT)

### Liquidation Cascade (ETH Example)
- Price breaks through resistance
- Speed: 3.5x+++ (extreme)
- Signal: RESISTANCE_BREAK
- Shorts getting liquidated → LONG opportunity

### Support Break
- Price breaks through support with velocity
- Signal: SUPPORT_BREAK
- Longs getting liquidated → SHORT opportunity

## Common Patterns to Watch

1. **Correlated Liquidations** - Both BTC and ETH liquidate together (strongest signal)
2. **BTC Leads ETH** - BTC breaks first, ETH follows (wait for confirmation)
3. **ETH Leads BTC** - Rare but possible (higher risk)
4. **Time of Day** - Liquidations more common during high volume hours (8am-4pm EST)
5. **False Breakouts** - Speed spike but price doesn't hold (use stop losses!)

## Additional Ideas to Test

From the data you'll collect, consider:
- **Minimum volume thresholds** - Ignore low-volume signals
- **Multi-timeframe confirmation** - Require both 20 and 60 candle agreement
- **Buy/sell ratio extremes** - Very one-sided = stronger liquidation
- **Acceleration detection** - Is speed INCREASING? (better signal)
- **Cross-symbol confirmation** - Only trade when BOTH symbols signal same direction

## Baseline Speed Notes

Each symbol has different "normal" speeds:
- BTC: ~10-20 trades/sec typically
- ETH: ~30-50 trades/sec typically

The detector auto-calculates baseline after 30 seconds of data. This adapts to current market conditions and time of day.

## FAQ

**Q: Why not add more altcoins?**
A: BTC and ETH are the market leaders. Their liquidations cascade into everything else. Keep it focused on what matters.

**Q: Can I trade other exchanges based on these signals?**
A: Yes! If Binance shows liquidations, often they're happening on other exchanges too. You could trade Hyperliquid, etc.

**Q: What if baseline speed is too low/high?**
A: Run it during active market hours to get a better baseline. Or manually set it based on historical data.

**Q: How do I know if my parameters are good?**
A: The CSV logs tell you everything. Backtest your signals against actual price movements.

## Next Steps

1. **Start monitoring now** - Let it run and collect data
2. **Watch real signals** - See what triggers and when
3. **Analyze the CSVs** - Find patterns in successful signals
4. **Paper trade** - Test logic without risk
5. **Go live tiny** - $10 positions to prove the thesis
6. **Scale carefully** - Only if consistently profitable

## Support Files

- **Technical docs:** `LIQUIDATION_DETECTOR_README.md`
- **Quick start:** `QUICKSTART.md`
- **Single symbol:** `liquidation_detector.py` (if you only want one)

---

🌙 Built by Moon Dev

**Remember:** This is a thesis to test. Start small, track everything, let the data guide you!
