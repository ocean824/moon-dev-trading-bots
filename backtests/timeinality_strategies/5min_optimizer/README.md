# 5-Minute Timeinality Strategy Optimizer

## Overview

This optimizer tests every 5-minute interval of every day to find optimal entry times for time-based trading strategies. It's the 5-minute version of the hourly optimizer.

**What it tests:**
- **288 five-minute intervals per day** (24 hours × 12 intervals per hour)
- Every day of the week (Mon-Sun)
- Both SHORT and LONG directions
- 3% Take Profit and 5% Stop Loss (same as hourly tests)
- 95% position sizing

## Setup Instructions

### 1. Create Data Folder

Create the 5-minute data folder:

```bash
mkdir -p /Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/5_min_data
```

### 2. Download 5-Minute Data

Place your 5-minute CSV files in the `/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/5_min_data/` folder.

**Required CSV format:**
- Columns: `datetime, open, high, low, close, volume`
- Datetime format: Any standard format that pandas can parse (e.g., `2024-01-01 00:00:00`)
- 5-minute intervals (no gaps)

**Example filename:**
- `SOLUSD-5min-250wks-data.csv`
- `SUIUSD-5min-52wks-data.csv`
- `BTCUSD-5min-100wks-data.csv`

### 3. Run the Optimizers

**For SHORT strategies:**
```bash
cd /Users/md/Dropbox/dev/github/moon-dev-trading-bots/backtests/timeinality_strategies/5min_optimizer/short
python 5min_short_optimizer.py
```

**For LONG strategies:**
```bash
cd /Users/md/Dropbox/dev/github/moon-dev-trading-bots/backtests/timeinality_strategies/5min_optimizer/long
python 5min_long_optimizer.py
```

## Configuration

Both scripts have the same configuration options at the top:

```python
# Test all days or specific days
TEST_DAYS = [0, 1, 2, 3, 4, 5, 6]  # All days (default)
# TEST_DAYS = [0, 1, 2, 3, 4]      # Weekdays only
# TEST_DAYS = [3]                   # Thursday only

# Take Profit and Stop Loss
TAKE_PROFIT_PERCENT = 3.0  # 3% take profit
STOP_LOSS_PERCENT = 5.0    # 5% stop loss
```

## Output

Results are saved to CSV files in the `results/` subfolder:

- **SHORT**: `/Users/md/Dropbox/dev/github/moon-dev-trading-bots/backtests/timeinality_strategies/5min_optimizer/short/results/`
- **LONG**: `/Users/md/Dropbox/dev/github/moon-dev-trading-bots/backtests/timeinality_strategies/5min_optimizer/long/results/`

**CSV columns:**
- `Data_Source` - Data file tested
- `Day` - Day of week (Monday, Tuesday, etc.)
- `Hour_UTC` - Hour (0-23)
- `Minute_UTC` - Minute (0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55)
- `Time_UTC` - Formatted time (HH:MM)
- `Return_%` - Strategy return percentage
- `BuyHold_Return_%` - Buy & hold return
- `Sharpe_Ratio` - Risk-adjusted return
- `Max_Drawdown_%` - Maximum drawdown
- `Total_Trades` - Number of trades executed
- `Win_Rate_%` - Percentage of winning trades
- `Profit_Factor` - Gross profits / gross losses

## Performance Expectations

**Number of backtests:**
- 1 data file × 7 days × 288 intervals = **2,016 backtests per file**
- 5 data files × 7 days × 288 intervals = **10,080 backtests total**

**Runtime:**
- Approximately **3-5 hours per data file** depending on dataset size
- Run overnight or use `nohup` for long-running tests

**Example using nohup:**
```bash
cd /Users/md/Dropbox/dev/github/moon-dev-trading-bots/backtests/timeinality_strategies/5min_optimizer/short
nohup python 5min_short_optimizer.py > short_optimizer.log 2>&1 &
tail -f short_optimizer.log  # Monitor progress
```

## Differences from Hourly Optimizer

| Feature | Hourly Optimizer | 5-Minute Optimizer |
|---------|-----------------|-------------------|
| Intervals per day | 24 | 288 |
| Data folder | `data/1_hr_data/` | `data/5_min_data/` |
| Backtests per file | 168 (7 days × 24 hours) | 2,016 (7 days × 288 intervals) |
| Runtime per file | ~5-10 minutes | ~3-5 hours |
| Granularity | Hour precision | 5-minute precision |

## Next Steps

After optimization completes:

1. **Analyze results** - Look for patterns in specific times
2. **Filter minimum trades** - Remove zero-trade noise (min 5 trades recommended)
3. **Sort by Sharpe Ratio** - Find best risk-adjusted performers
4. **Sort by Max Drawdown** - Find strategies with shallowest drawdowns
5. **Compare to hourly** - See if 5-minute data reveals finer-grained patterns

## Strategy Logic

**SHORT Strategy:**
- Enters SHORT at target 5-minute interval
- Stop Loss: 5% above entry price
- Take Profit: 3% below entry price
- Exits at TP/SL or next interval entry

**LONG Strategy:**
- Enters LONG at target 5-minute interval
- Stop Loss: 5% below entry price
- Take Profit: 3% above entry price
- Exits at TP/SL or next interval entry

---

**Created by:** Moon Dev 🌙
**Framework:** RBI (Research, Backtest, Implement)
**Based on:** Hourly Timeinality Optimizer
