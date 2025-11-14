# Moon Dev's Liquidation Detector - Quick Start 🚀

## What You Got

A complete liquidation cascade detection system that monitors Binance WebSocket trade streams and identifies high-probability liquidation events.

## Files Created

```
bots/binance/
├── liquidation_detector.py          # Main detector module
├── example_bot_integration.py       # Example bot using signals
├── LIQUIDATION_DETECTOR_README.md   # Full documentation
├── QUICKSTART.md                    # This file
└── logs/                            # CSV logs (auto-created)
```

## Step 1: Monitor & Learn

Run the detector standalone to watch for signals:

```bash
python bots/binance/liquidation_detector.py
```

This will:
- Connect to Binance WebSocket (BTC by default)
- Calculate support/resistance from 1-min candles
- Monitor trade velocity in real-time
- Print colored signals when liquidations detected
- Log everything to CSV for analysis

**Let it run for a few hours or days** - watch the signals, see what triggers, understand the patterns.

## Step 2: Analyze the Data

Check the CSV logs in `bots/binance/logs/`:
- Every second is logged
- When did signals fire?
- What was the speed multiplier?
- Did price actually break through?
- Which signals were accurate?

Use this data to tune the parameters!

## Step 3: Integrate Into Your Bot

```python
from liquidation_detector import LiquidationDetector
import threading
import time

# Start detector in background
detector = LiquidationDetector(
    symbol='BTCUSDT',
    proximity_threshold=0.5,      # Adjust based on your analysis
    speed_multiplier_threshold=2.0  # Adjust based on your analysis
)

detector_thread = threading.Thread(target=detector.run)
detector_thread.daemon = True
detector_thread.start()

time.sleep(5)  # Let it initialize

# In your trading loop
while True:
    signal_data = detector.get_latest_signal()

    if signal_data['strength'] >= 70:  # High confidence
        if signal_data['signal'] == 'RESISTANCE_BREAK':
            # Shorts liquidating - GO LONG
            your_exchange.buy(symbol, size)

        elif signal_data['signal'] == 'SUPPORT_BREAK':
            # Longs liquidating - GO SHORT
            your_exchange.sell(symbol, size)

    time.sleep(2)
```

## Step 4: Start Small

When you're ready to test with real money:
1. Use $10 position sizes
2. Test on one symbol first
3. Track every trade
4. Adjust parameters based on results
5. Scale slowly if it works

## Key Signals Explained

| Signal | Meaning | Likely Action |
|--------|---------|---------------|
| **RESISTANCE_BREAK** | Broke resistance + high speed | Shorts liquidating → LONG |
| **SUPPORT_BREAK** | Broke support + high speed | Longs liquidating → SHORT |
| **RESISTANCE_TEST** | Near resistance + speed spike | Potential breakout setup |
| **SUPPORT_TEST** | Near support + speed spike | Potential breakdown setup |
| **HIGH_VELOCITY** | Extreme speed, not near S/R | Neutral momentum |

## Tuning Parameters

### proximity_threshold (default: 0.5%)
- **Lower (0.3%)** = Tighter, fewer signals, higher accuracy
- **Higher (1.0%)** = Looser, more signals, lower accuracy

### speed_multiplier_threshold (default: 2.0x)
- **Lower (1.5x)** = More sensitive, catches smaller events
- **Higher (3.0x)** = Less sensitive, only extreme events

Start with defaults, then adjust based on your CSV analysis!

## What the CSV Logs

Every second:
- Current price
- Trades in last 5s and 10s
- Volume (quantity and USD)
- Buy/sell pressure ratio
- Support/Resistance levels (20 and 60 candles)
- % distance to each level
- Speed multiplier vs baseline
- Signal type and strength

## Example Output

When a signal fires, you'll see:

```
╭─ 🚀 Moon Dev Liquidation Alert 🚀 ──────────╮
│                                              │
│  Signal          RESISTANCE_BREAK           │
│  Direction       LONG                        │
│  Strength        85/100                      │
│  Price           $97,234.52                  │
│  Speed           3.2x baseline               │
│  Volume (10s)    $1,215,432                  │
│  Resistance (20) $97,180.00 (-0.06%)        │
│                                              │
╰──────────────────────────────────────────────╯
```

## Next Steps

1. **Run it now** - Let it collect data while you do other things
2. **Watch the patterns** - What triggers signals? Are they accurate?
3. **Analyze logs** - Find the sweet spot for your parameters
4. **Paper trade** - Use `example_bot_integration.py` to test logic
5. **Go live tiny** - Start with $10 positions on your exchange
6. **Track results** - Be scientific about what works
7. **Scale carefully** - Only if consistently profitable

## Additional Ideas to Test

From the CSV data, you could also analyze:
- Time of day patterns (when are liquidations most common?)
- Volume thresholds (minimum volume to take seriously)
- Multi-timeframe confirmation (both 20 and 60 candles agreeing)
- Buy/sell ratio extremes (one-sided liquidations)
- Speed acceleration (is velocity increasing?)

## Support

Read the full docs: `LIQUIDATION_DETECTOR_README.md`

---

🌙 Built by Moon Dev - Test the thesis, track results, stay small!
