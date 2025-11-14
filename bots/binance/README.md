# Binance Bots by Moon Dev

This directory contains Binance-specific trading bots and tools.

## Price Tracker

`price_tracker.py` - A super fun, compact real-time crypto price tracker using Binance WebSocket.

### Features
- 🌙 Real-time price updates via Binance WebSocket
- 🎨 Beautiful colored terminal display using Rich library
- 📊 Compact design - takes up minimal screen space
- ⏰ Tracks BTC and ETH prices
- 📈 5-minute percentage change tracking
- 📉 30-minute percentage change tracking
- 🔄 Live updating display (refreshes 4x per second)
- 🟢 Green for gains, 🔴 Red for losses

### Usage

```bash
# Run from project root
python bots/binance/price_tracker.py
```

Press `Ctrl+C` to exit.

### Configuration

To track different tokens, modify the `symbols` list in the `main()` function:

```python
symbols = ['BTC', 'ETH']  # Add or remove symbols here
```

### Requirements
- `websocket-client` - For WebSocket connection
- `rich` - For beautiful terminal display

Both are already included in the project's requirements.txt.

### Notes
- All prices are in USDT pairs (e.g., BTC = BTCUSDT)
- The tracker uses Binance's public WebSocket API (no API key required)
- Updates happen in real-time as prices change on Binance
- Green colors indicate price increases, red indicates decreases
- Display updates 4 times per second for smooth visuals
- Historical data is kept for 30 minutes to calculate time-based changes

---

Built with 🌙 by Moon Dev
