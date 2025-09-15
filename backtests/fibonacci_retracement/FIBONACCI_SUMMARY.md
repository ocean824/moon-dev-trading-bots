# Fibonacci Retracement Strategy Suite

## Overview
This directory contains a comprehensive suite of Fibonacci retracement trading strategies, each with different technical indicator combinations for enhanced performance.

## Strategy Files

### Core Strategies
1. **fibonacci_retracement_base.py** - Classic Fibonacci retracement strategy using swing highs/lows
2. **fibonacci_retracement_adx.py** - Fibonacci + ADX for trend strength filtering
3. **fibonacci_retracement_bollinger.py** - Fibonacci + Bollinger Bands for volatility confirmation
4. **fibonacci_retracement_ema.py** - Fibonacci + EMA crossovers for trend confirmation
5. **fibonacci_retracement_kalman.py** - Fibonacci + Kalman filter for noise reduction
6. **fibonacci_retracement_mfi.py** - Fibonacci + Money Flow Index for volume confirmation

### Testing & Analysis
- **test_all_fibonacci_retracement.py** - Comprehensive testing across all data sources
- **view_results.py** - Results comparison and analysis tool

## Strategy Logic

### Base Concept
All strategies identify swing highs and lows using a rolling window approach, then calculate Fibonacci retracement levels (23.6%, 38.2%, 50%, 61.8%, 100%). Trades are entered when price retraces to key levels.

### Entry Rules
- **Long entries**: In uptrends, buy at 38.2%, 50%, or 61.8% retracements
- **Short entries**: In downtrends, sell at 38.2%, 50%, or 61.8% retracements
- **Stop Loss**: 3% from entry
- **Take Profit**: 5% from entry

### Fixed Parameters (No Optimization)
- Swing Lookback: 30 periods
- Min Swing Difference: 2%
- Entry tolerance: 1% around Fibonacci levels
- Trend MA: 50 periods

## Performance Summary

### Top Performers (By Average Return)
1. **Fib+Bollinger**: 32.49% avg return (24% success rate)
2. **Fib+EMA**: 29.84% avg return (36% success rate)
3. **Fib+Kalman**: 24.62% avg return (28% success rate)

### Risk-Adjusted Performance
- **Best Sharpe Ratio**: Fib+EMA (-0.266)
- **Lowest Drawdown**: Fib+ADX (-47.61%)
- **Highest Win Rate**: Fib+EMA (41.06%)

### Most Consistent
- **Fib+EMA**: 9/25 profitable tests (36% success rate)
- **Fib+ADX**: 9/25 profitable tests (36% success rate)

## Recommendations

### Conservative Trading
Use **Fib+ADX** - Lowest drawdown with positive returns

### Aggressive Trading
Use **Fib+Bollinger** - Highest returns but higher risk

### Balanced Approach
Use **Fib+EMA** - Best overall balance of return, risk, and consistency

## Testing Notes
- All strategies tested on 25+ data sources
- Includes crypto (BTC, ETH, SOL) and stocks (AAPL, TSLA, NVDA, GOOG)
- Multiple timeframes from 1-minute to daily
- Results saved in ./results/ directory

## Usage
```bash
# Test individual strategy
python fibonacci_retracement_base.py

# Test all strategies
python test_all_fibonacci_retracement.py

# View comparison results
python view_results.py
```