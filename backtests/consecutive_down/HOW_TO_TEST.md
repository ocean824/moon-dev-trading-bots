# How to Test Each Strategy on All Data Sources

## Simple Process - Test Each Strategy Individually

### Step 1: Navigate to this folder
```bash
cd /Users/md/Dropbox/dev/github/moon-dev-trading-bots/backtests/consecutive_down
```

### Step 2: Run any strategy file directly

**Test the Base Strategy:**
```bash
python consecutive_down_base.py
```

**Test the ADX Strategy:**
```bash
python consecutive_down_adx.py
```

**Test the MFI Strategy:**
```bash
python consecutive_down_mfi.py
```

**Test the VWAP Strategy:**
```bash
python consecutive_down_vwap.py
```

**Test the Kaufman Strategy:**
```bash
python consecutive_down_kaufman.py
```

### What Happens:

1. The strategy runs its normal single backtest first (on default data)
2. Then automatically tests on ALL 10 data sources:
   - BTC 1-hour (regular, gapped, inverse)
   - BTC 5-minute (regular, gapped, inverse)
   - BTC 1-day (1000 weeks, 100 weeks)
   - BTC 6-hour
   - BTC 1-minute

3. Creates a `results/` folder RIGHT HERE in the consecutive_down folder

4. Saves a CSV file with all results:
   - File name: `ConsecutiveDown_[Type]_[timestamp].csv`
   - One row for each data source (10 rows total)
   - All key metrics in columns

### Finding Your Results:

After running any strategy:
```bash
ls results/
```

You'll see files like:
- `ConsecutiveDown_Base_20250823_103000.csv`
- `ConsecutiveDown_ADX_20250823_103500.csv`
- etc.

### Open in Excel:
```bash
open results/*.csv
```

### What's in the CSV:

Each CSV has these columns:
- **Data_Source**: Which timeframe/data type
- **Rows**: How much data
- **Return_%**: Total return
- **Sortino**: Risk-adjusted return (higher = better)
- **Sharpe**: Another risk metric
- **Max_DD_%**: Maximum drawdown
- **Trades**: Number of trades
- **Win_Rate_%**: Percentage of winning trades
- Plus 10 more metrics!

### Pro Tips:

1. **Run one at a time** - Each test takes 1-2 minutes
2. **Check the results folder** after each run
3. **Compare CSVs** in Excel to see which strategy works best on which timeframe
4. **Look for patterns** - Maybe ADX works great on 1-hour but terrible on 1-minute

That's it! Just run `python [strategy_file].py` and check the results folder!