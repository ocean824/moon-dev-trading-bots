# Liquidation Cascade Detector by Moon Dev 🌙

## The Thesis

When price approaches support or resistance levels AND trade velocity spikes dramatically, liquidation cascades are occurring. This creates predictable momentum that can be traded.

**Core Concept:**
- **Near Resistance + Speed Spike** = Shorts getting liquidated → Potential breakout LONG
- **Near Support + Speed Spike** = Longs getting liquidated → Potential breakdown SHORT

## How It Works

### 1. Speed Metrics (Trade Velocity)
Monitors real-time Binance trade stream and calculates:
- Trades per 5 seconds (short-term velocity)
- Trades per 10 seconds (medium-term velocity)
- Total coin quantity traded in 10 seconds
- Total USD volume in 10 seconds
- Buy/Sell pressure ratio
- Speed multiplier vs baseline (e.g., 2.5x = 250% faster than normal)

### 2. Support/Resistance Levels
Uses Binance 1-minute historical candles to calculate:
- **20-candle window** (20 minutes) - Short-term S/R
  - Support = Lowest low in last 20 candles
  - Resistance = Highest high in last 20 candles
- **60-candle window** (1 hour) - Medium-term S/R
  - Support = Lowest low in last 60 candles
  - Resistance = Highest high in last 60 candles

Calculates percentage distance from current price to each level.

### 3. Signal Generation

**Signal Types:**
- `CALM` - Normal market conditions
- `RESISTANCE_TEST` - Near resistance with elevated speed (potential breakout setup)
- `RESISTANCE_BREAK` - Broke through resistance with velocity (shorts liquidating)
- `SUPPORT_TEST` - Near support with elevated speed (potential breakdown setup)
- `SUPPORT_BREAK` - Broke through support with velocity (longs liquidating)
- `HIGH_VELOCITY` - Extreme speed but not near S/R levels

**Signal Strength:** 0-100 confidence score based on:
- Speed multiplier magnitude
- Multiple timeframe confirmation (20 + 60 candles)
- Proximity to levels
- Whether price broke through or just testing

## Configuration Parameters

```python
detector = LiquidationDetector(
    symbol='BTCUSDT',                    # Trading pair
    proximity_threshold=0.5,              # Within 0.5% = "near" S/R
    speed_multiplier_threshold=2.0        # 2x baseline = "elevated"
)
```

**Tuning Guide:**
- `proximity_threshold`: Tighter (0.3%) = fewer signals, stronger. Wider (1.0%) = more signals, weaker.
- `speed_multiplier_threshold`: Lower (1.5x) = more sensitive. Higher (3.0x) = only extreme events.

## Usage

### Standalone Monitoring

```bash
python bots/binance/liquidation_detector.py
```

This will:
1. Connect to Binance WebSocket trade stream
2. Calculate support/resistance levels
3. Monitor trade velocity in real-time
4. Print signals to console when detected
5. Log everything to CSV

### Bot Integration

```python
from liquidation_detector import LiquidationDetector

# Initialize detector
detector = LiquidationDetector(
    symbol='BTCUSDT',
    proximity_threshold=0.5,
    speed_multiplier_threshold=2.0
)

# Start in background thread
import threading
detector_thread = threading.Thread(target=detector.run)
detector_thread.daemon = True
detector_thread.start()

# Get signals in your bot loop
while True:
    signal_data = detector.get_latest_signal()

    if signal_data['signal'] == 'RESISTANCE_BREAK':
        # Shorts liquidating - go LONG
        place_long_order()

    elif signal_data['signal'] == 'SUPPORT_BREAK':
        # Longs liquidating - go SHORT
        place_short_order()

    time.sleep(2)
```

See `example_bot_integration.py` for complete example.

## Output Data

### CSV Log Format
Every second, logs to `bots/binance/logs/liquidation_log_{symbol}_{timestamp}.csv`:

| Column | Description |
|--------|-------------|
| timestamp | ISO timestamp |
| symbol | Trading pair |
| price | Current price |
| trades_5s | Number of trades in last 5 seconds |
| trades_10s | Number of trades in last 10 seconds |
| quantity_10s | Total coins traded in 10 seconds |
| volume_usd_10s | Total USD volume in 10 seconds |
| buy_sell_ratio | Buy pressure / Sell pressure |
| support_20 | Support level (20 candles) |
| dist_support_20_pct | % distance to support (20) |
| resistance_20 | Resistance level (20 candles) |
| dist_resistance_20_pct | % distance to resistance (20) |
| support_60 | Support level (60 candles) |
| dist_support_60_pct | % distance to support (60) |
| resistance_60 | Resistance level (60 candles) |
| dist_resistance_60_pct | % distance to resistance (60) |
| speed_multiplier | Current speed / baseline speed |
| baseline_speed | Normal trades per second |
| signal | Signal type |
| signal_strength | Confidence 0-100 |

### Console Output
Signals are printed to console with color-coded alerts:
- 🚀 Green = Resistance breaks (LONG opportunities)
- 💥 Red = Support breaks (SHORT opportunities)
- ⚡ Yellow = High velocity events

### get_latest_signal() Return Value

```python
{
    'signal': 'RESISTANCE_BREAK',      # Signal type
    'strength': 85,                     # Confidence 0-100
    'price': 97234.52,                  # Current price
    'speed_multiplier': 3.2,            # Speed vs baseline
    'metrics': {                        # All speed metrics
        'trades_5s': 42,
        'trades_10s': 78,
        'quantity_10s': 12.5,
        'volume_usd_10s': 1215432.10,
        'buy_sell_ratio': 1.8,
        'current_speed': 7.8
    },
    'distances': {                      # All S/R distances
        'dist_support_20': 1.2,
        'dist_resistance_20': -0.1,     # Negative = broke through
        'dist_support_60': 2.5,
        'dist_resistance_60': 0.3
    },
    'timestamp': datetime(...)
}
```

## Trading Strategy Examples

### Conservative (High Confidence Only)
```python
signal_data = detector.get_latest_signal()

if signal_data['strength'] >= 80:  # High confidence only
    if signal_data['signal'] == 'RESISTANCE_BREAK':
        # Strong breakout, shorts liquidating
        go_long()
```

### Aggressive (Test + Break)
```python
if signal_data['signal'] == 'RESISTANCE_TEST':
    # Set limit buy slightly above resistance
    set_limit_buy(resistance * 1.001)

elif signal_data['signal'] == 'RESISTANCE_BREAK':
    # Market buy immediately
    market_buy()
```

### Mean Reversion
```python
if signal_data['signal'] == 'SUPPORT_TEST':
    # Fade the move, bet on bounce
    go_long()
    set_stop_loss(support * 0.998)
```

## Testing Recommendations

1. **Start with monitoring only** - Run the detector and watch the signals for a few days
2. **Analyze the CSV logs** - See which signals were accurate
3. **Paper trade** - Use the mock bot to test without risk
4. **Start tiny** - When going live, use $10 positions
5. **Track performance** - Keep detailed records of signal accuracy

## Additional Speed Metrics Ideas

You could extend the detector with:
- Average trade size (large trades = whales)
- Trade size distribution (many small vs few large)
- Order imbalance (bid/ask pressure)
- Time between trades (clustering detection)
- Exponential moving average of speed (smooth out noise)
- Standard deviation of speed (detect anomalies)

## Files

- `liquidation_detector.py` - Main detector module
- `example_bot_integration.py` - Example bot implementation
- `logs/` - CSV logs directory (auto-created)

## Requirements

- `websocket-client` - WebSocket connection
- `requests` - REST API calls
- `rich` - Terminal output

All included in project requirements.txt

## Notes

- No API key needed (uses public Binance data)
- Works with any Binance trading pair
- Support/Resistance updates every 60 seconds
- Baseline speed calculated after 30 seconds of data
- Logs one row per second
- Can run multiple detectors for different symbols

---

Built with 🌙 by Moon Dev

**Remember:** This is a thesis to test. Always start small, track results, and adjust parameters based on real market data!
