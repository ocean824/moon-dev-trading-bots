# Multi-Data Testing Guide

## Overview
The `multi_data_tester.py` file allows any strategy to be tested on 10+ different data sources automatically. Results are saved as CSV files in a `results/` folder created wherever you run the strategy from.

## How to Add Multi-Data Testing to ANY New Strategy

### Step 1: Create Your Strategy File
Create your strategy as normal, inheriting from `Strategy` and implementing `init()` and `next()` methods.

### Step 2: Add Multi-Data Testing Code
At the very bottom of your strategy file, add this exact code block:

```python
# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING [YOUR STRATEGY NAME] ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    # Test this strategy on all configured data sources
    results = test_on_all_data(YourStrategyClass, 'YourStrategy_Name')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/YourStrategy_Name_[timestamp].csv")
```

Replace:
- `[YOUR STRATEGY NAME]` with a description
- `YourStrategyClass` with your actual strategy class name
- `'YourStrategy_Name'` with the name for your output files

### Step 3: Run Your Strategy
```bash
cd /path/to/your/strategy/folder
python your_strategy.py
```

## Complete Example - New Strategy Template

Here's a complete template for a new strategy with multi-data testing:

```python
import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy

print("🚀 Moon Dev's [Strategy Name] Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
PARAM1 = 10
PARAM2 = 20
TAKE_PROFIT_PERCENT = 3.0
STOP_LOSS_PERCENT = 2.0

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class YourStrategy(Strategy):
    # Strategy parameters
    param1 = PARAM1
    param2 = PARAM2
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100
    
    def init(self):
        # Initialize your indicators here
        self.sma = self.I(talib.SMA, self.data.Close, self.param1)
        # Add more indicators as needed
    
    def next(self):
        # Your trading logic here
        if not self.position:
            # Entry conditions
            if self.data.Close[-1] > self.sma[-1]:
                current_price = self.data.Close[-1]
                sl_price = current_price * (1 - self.stop_loss)
                tp_price = current_price * (1 + self.take_profit)
                self.buy(sl=sl_price, tp=tp_price)

# Run single backtest (default behavior)
bt = Backtest(data, YourStrategy, cash=100000, commission=0.00045)

print("\n🌙 ===== STRATEGY - DEFAULT PARAMETERS ===== 🌙")
print(f"Param1: {PARAM1}")
print(f"Param2: {PARAM2}")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")

stats_default = bt.run()
print(stats_default)

# Optional: Add optimization
print("\n🚀 Optimizing Strategy...")
optimization_results = bt.optimize(
    param1=range(5, 21, 5),
    param2=range(10, 31, 5),
    take_profit=[i / 1000 for i in range(20, 51, 5)],
    stop_loss=[i / 1000 for i in range(10, 31, 5)],
    maximize='Sortino Ratio',
    constraint=lambda p: p.take_profit > p.stop_loss
)

print("\n🚀 ===== OPTIMIZATION RESULTS ===== 🚀")
print(optimization_results)

print("\n🏆 BEST PARAMETERS:")
print(f"Param1: {optimization_results._strategy.param1}")
print(f"Param2: {optimization_results._strategy.param2}")
print(f"Take Profit: {optimization_results._strategy.take_profit * 100:.1f}%")
print(f"Stop Loss: {optimization_results._strategy.stop_loss * 100:.1f}%")

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING YOUR STRATEGY ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    # Test this strategy on all configured data sources
    results = test_on_all_data(YourStrategy, 'YourStrategy')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/YourStrategy_[timestamp].csv")
```

## Data Sources Currently Configured

The `multi_data_tester.py` tests on these 10 data sources:

1. **BTC-1h-500wks** - 1-hour standard data
2. **BTC-1h-gapped** - 1-hour market hours only
3. **BTC-1h-inverse** - 1-hour after-hours only
4. **BTC-5m-70wks** - 5-minute standard data
5. **BTC-5m-gapped** - 5-minute market hours
6. **BTC-5m-inverse** - 5-minute after-hours
7. **BTC-1d-1000wks** - Daily long-term data
8. **BTC-1d-100wks** - Daily medium-term data
9. **BTC-6h-500wks** - 6-hour standard data
10. **BTC-1m-10wks** - 1-minute short-term data

To add more data sources, edit the `DATA_SOURCES` list at the top of `multi_data_tester.py`:

```python
DATA_SOURCES = [
    ('Name', '/path/to/csv'),
    # Add more...
]
```

## Output Format

Each CSV contains these columns:
- **Data_Source**: Name of the data source
- **Rows**: Number of data rows
- **Return_%**: Total return percentage
- **Buy_Hold_%**: Buy and hold return for comparison
- **Annual_Return_%**: Annualized return
- **Sharpe**: Sharpe ratio
- **Sortino**: Sortino ratio (higher is better)
- **Calmar**: Calmar ratio
- **Max_DD_%**: Maximum drawdown
- **Avg_DD_%**: Average drawdown
- **Trades**: Number of trades
- **Win_Rate_%**: Win rate percentage
- **Best_Trade_%**: Best single trade
- **Worst_Trade_%**: Worst single trade
- **Avg_Trade_%**: Average trade return
- **Profit_Factor**: Profit factor
- **Expectancy_%**: Expected return per trade
- **SQN**: System Quality Number

## Testing Multiple Strategies

To test multiple strategies and compare them:

```python
from multi_data_tester import test_multiple_strategies

strategies = {
    'Strategy1_Name': Strategy1Class,
    'Strategy2_Name': Strategy2Class,
    'Strategy3_Name': Strategy3Class
}

results = test_multiple_strategies(strategies, optimize=False)
```

This creates:
- Individual CSV for each strategy
- A `comparison_[timestamp].csv` with all strategies side-by-side

## Important Notes

1. **Cash Amount**: Default is $10,000,000 to handle Bitcoin prices. Adjust if needed:
   ```python
   results = test_on_all_data(YourStrategy, 'Name', cash=100000)
   ```

2. **Commission**: Default is 0.045% (0.00045). Adjust if needed:
   ```python
   results = test_on_all_data(YourStrategy, 'Name', commission=0.001)
   ```

3. **Results Location**: Results are saved in a `results/` folder created in the directory where you run the script from.

4. **Run Time**: Each strategy takes about 1-2 minutes to test on all 10 data sources.

5. **Memory**: Large datasets may require significant memory. Close other applications if needed.

## Quick Commands Reference

```bash
# Navigate to your strategy folder
cd /Users/md/Dropbox/dev/github/moon-dev-trading-bots/backtests/your_strategy_folder

# Run your strategy (tests on all data automatically)
python your_strategy.py

# Check results
ls results/

# Open latest result in Excel
open results/*.csv
```

## Troubleshooting

**Issue**: "ImportError: cannot import name 'test_on_all_data'"
**Solution**: Make sure you have the correct sys.path.append line that goes up to the backtests folder

**Issue**: Results folder not created
**Solution**: Check write permissions in your current directory

**Issue**: Out of memory errors
**Solution**: Reduce the number of data sources or test them separately

## Future Strategies Checklist

When creating a new strategy:
- [ ] Create strategy file with Strategy class
- [ ] Add single backtest code for testing
- [ ] Add optimization code (optional)
- [ ] Add multi-data testing block at the bottom
- [ ] Test on all data sources
- [ ] Compare results across timeframes
- [ ] Document best performing configurations