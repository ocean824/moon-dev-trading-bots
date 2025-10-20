# 🌙 SMA Strategy Variations Backtests

## Overview

This folder contains 5 different SMA (Simple Moving Average) based trading strategies with various filters to improve signal quality. Each strategy builds on a basic SMA crossover and adds a specific filter to reduce false signals.

## The 5 Strategies

### 1. **Basic SMA Crossover** (`1_sma_basic.py`)
- **Logic:** Fast SMA crosses above slow SMA = LONG, crosses below = SHORT
- **Purpose:** Baseline strategy to compare all filters against
- **Best For:** Trending markets with clear direction

### 2. **SMA + MFI Filter** (`2_sma_mfi_filter.py`)
- **Filter:** Money Flow Index (MFI) - combines price and volume
- **Logic:** Only takes longs when not overbought (MFI < 70), shorts when not oversold (MFI > 30)
- **Purpose:** Avoid buying tops and selling bottoms
- **Best For:** Avoiding entries at extremes

### 3. **SMA + Kalman Filter** (`3_sma_kalman_filter.py`)
- **Filter:** Kalman filter for adaptive smoothing
- **Logic:** Confirms SMA signals with Kalman-filtered trend direction
- **Purpose:** Reduces noise and provides cleaner signals
- **Best For:** Noisy, volatile markets

### 4. **SMA + ADX Filter** (`4_sma_adx_filter.py`)
- **Filter:** Average Directional Index (ADX) for trend strength
- **Logic:** Only trades when ADX > threshold (strong trend present)
- **Purpose:** Avoid choppy, ranging markets
- **Best For:** Filtering out sideways markets

### 5. **SMA + VWAP Filter** (`5_sma_vwap_filter.py`)
- **Filter:** Volume Weighted Average Price (VWAP)
- **Logic:** Longs only above VWAP, shorts only below VWAP
- **Purpose:** Align with institutional price levels
- **Best For:** Intraday trading with volume considerations

## Data Sources

Two datasets are ready to use (just comment/uncomment in each file):

1. **HYPE 4H Data:**
   ```python
   data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/HYPE_4h_20251020_130820_historical.csv'
   ```

2. **Pump Token 4H Data:**
   ```python
   data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/birdeye/DitHyRMQiSDhn5cnKMJV2CDDt6sVct96YrECiM49pump-4H-300days-data.csv'
   ```

## How to Run

### Individual Strategy Testing:
```bash
# Run each strategy separately for detailed analysis
python 1_sma_basic.py
python 2_sma_mfi_filter.py
python 3_sma_kalman_filter.py
python 4_sma_adx_filter.py
python 5_sma_vwap_filter.py
```

### Compare All Strategies:
```bash
# Run comparison script
python run_all_comparisons.py
```

## What Each Script Does

1. **Loads data** from specified path
2. **Runs initial backtest** with default parameters
3. **Shows performance metrics** (Return %, Sharpe, Max DD, Win Rate)
4. **Displays plot** of trades and equity curve
5. **Optimizes parameters** to find best settings
6. **Shows optimized results** with best parameters found
7. **Displays optimized plot**

## Key Metrics to Compare

- **Total Return %**: Overall profitability
- **Sharpe Ratio**: Risk-adjusted returns (higher is better)
- **Max Drawdown %**: Worst peak-to-trough decline
- **Win Rate %**: Percentage of profitable trades
- **# of Trades**: Trading frequency
- **Profit Factor**: Gross profits / gross losses

## Expected Results

Generally, you should see:
- **Basic SMA**: Most trades, but more whipsaws
- **MFI Filter**: Fewer trades, better entries
- **Kalman Filter**: Smoother equity curve
- **ADX Filter**: Fewest trades, highest win rate
- **VWAP Filter**: Best for intraday momentum

## Switching Data Sources

To test with different data:

1. Open any strategy file
2. Find these lines at the top:
   ```python
   # data_path = '/path/to/HYPE/data'
   data_path = '/path/to/pump/data'
   ```
3. Comment out current path, uncomment the other
4. Save and run

## Optimization Parameters

Each strategy optimizes different parameters:

- **All strategies**: SMA periods, TP/SL percentages
- **MFI**: Oversold/overbought thresholds
- **Kalman**: Process and measurement variance
- **ADX**: Trend strength threshold
- **VWAP**: Period and buffer zones

## Tips for Best Results

1. **Start with Basic SMA** to establish baseline
2. **Compare filters** on same dataset first
3. **Test both datasets** to see which works better
4. **Look at Sharpe Ratio** for risk-adjusted performance
5. **Consider trade frequency** vs your execution costs
6. **Check max drawdown** vs your risk tolerance

## Next Steps

After finding the best strategy/filter combination:
1. Test on longer timeframes (daily, weekly)
2. Test on shorter timeframes (1H, 15min)
3. Combine multiple filters
4. Add position sizing rules
5. Forward test on live data

---

**Created by:** Moon Dev 🌙
**Framework:** backtesting.py
**Indicators:** TA-Lib

Dr. Data Dawg - let the filters guide you to better trades!