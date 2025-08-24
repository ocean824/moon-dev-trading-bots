# Ultra-Fast Tick Data Collection System

## What It Does

Collects real-time order book (25 levels) and trade data from Binance at millisecond intervals for BTC, ETH, and SOL. Saves compressed tick data and converts to CSV format automatically.

- **Collection Speed**: 1-50ms updates (ultra high-frequency)
- **Data Captured**: Full order book depth + all trades
- **Storage**: Compressed JSON (.gz) converted to CSV every 5 minutes
- **Coverage**: Last 30 days of tick data maintained

## Files

1. **`ultra_fast_collector.py`** - Real-time data collector
2. **`periodic_csv_converter.py`** - Converts to CSV format

## Quick Start

### 1. Install Dependencies
```bash
pip3 install websocket-client pandas numpy
```

### 2. Run Collectors (3 separate screens)
```bash
# BTC
screen -S btc_collector
python3 ultra_fast_collector.py BTC

# ETH  
screen -S eth_collector
python3 ultra_fast_collector.py ETH

# SOL
screen -S sol_collector
python3 ultra_fast_collector.py SOL
```

### 3. Run CSV Converter (1 screen for all)
```bash
screen -S csv_converter
python3 periodic_csv_converter.py
```

## Configuration

Edit top of `periodic_csv_converter.py`:
```python
CONVERSION_INTERVAL_MINUTES = 5  # How often to convert
DAYS_TO_PROCESS = 30  # Days of history to maintain
INPUT_BASE_DIR = "/your/input/path"  # Where raw data is stored
OUTPUT_DIR = "/your/output/path"  # Where CSVs are saved
```

## Output

- **Raw Data**: `./ultra_fast_data/[SYMBOL]/` (compressed JSON)
- **CSV Files**: 
  - `btc_tickdata.csv`
  - `eth_tickdata.csv`
  - `sol_tickdata.csv`

Each CSV contains: timestamp, 15 levels of bids/asks with prices and quantities, mid price, spread.

## Notes

- Detach from screen: `Ctrl+A, D`
- View screens: `screen -ls`
- Reattach: `screen -r [name]`
- Stop collector: `Ctrl+C` in screen