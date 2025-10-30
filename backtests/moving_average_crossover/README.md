# Moon Dev's Moving Average Crossover Strategy Suite

## Overview
This folder contains a complete Moving Average Crossover strategy framework with 4 different variations, each designed to test on 25+ data sources across crypto and traditional markets.

## Strategy Variations

### 1. **Base Strategy** (`ma_crossover_base.py`)
- Classic EMA crossover system
- Entry: Fast MA crosses above/below Slow MA
- Exit: Opposite crossover or stop-loss/take-profit
- ATR-based dynamic stop adjustments

### 2. **MFI Enhanced** (`ma_crossover_mfi.py`)
- Adds Money Flow Index for volume-weighted momentum
- Filters entries based on overbought/oversold conditions
- Dynamic position sizing based on MFI strength
- Additional RSI confirmation for stronger signals

### 3. **ADX Enhanced** (`ma_crossover_adx.py`)
- Uses ADX to filter out choppy/ranging markets
- Only trades when ADX > 25 (trending market)
- Directional Index (+DI/-DI) for trend direction confirmation
- MACD histogram for additional trend strength

### 4. **Kalman Filter Enhanced** (`ma_crossover_kalman.py`)
- Applies Kalman filtering to reduce noise
- Adaptive filtering based on market volatility
- Smoother signals with fewer whipsaws
- Kalman-filtered RSI and MACD for cleaner confirmations

## Quick Start

### Run Individual Strategy
```bash
# Navigate to strategy folder
cd /Users/md/Dropbox/dev/github/moon-dev-trading-bots/backtests/moving_average_crossover

# Run any strategy (automatically tests on all 25+ data sources)
python ma_crossover_base.py
python ma_crossover_mfi.py
python ma_crossover_adx.py
python ma_crossover_kalman.py
```

### Run All Strategies Comparison
```bash
# Compare all 4 variations
python test_all_ma_crossover.py
```

## Results Location
- Individual strategy results: `./results/[StrategyName].csv`
- Comparison results: `./results/MA_Crossover_Comparison_[timestamp].csv`

## Default Parameters

| Parameter | Base | MFI | ADX | Kalman |
|-----------|------|-----|-----|--------|
| Fast MA | 20 | 20 | 20 | 20 |
| Slow MA | 50 | 50 | 50 | 50 |
| Take Profit | 4% | 5% | 5% | 4.5% |
| Stop Loss | 2% | 2.5% | 2% | 2% |
| Position Size | $1,000,000 | $1,000,000 | $1,000,000 | $1,000,000 |
| Commission | 0.045% | 0.045% | 0.045% | 0.045% |

## Data Sources Tested
The strategies automatically test on 25+ data sources including:

### Crypto (Coinbase)
- **Bitcoin**: 1m, 5m, 15m, 1h, 6h, 1d timeframes
- **Ethereum**: 15m, 1h, 6h, 1d timeframes
- **Solana**: 1m, 15m, 1h, 6h, 1d timeframes

### Stocks (Interactive Brokers)
- **AAPL**: 15m intervals (3Y and 12Y data)
- **TSLA**: 5m intervals (30D data)
- **ES/NQ Futures**: 4h intervals (10Y data)

### Stocks (Yahoo Finance)
- **GOOG, NVDA, TSLA**: Hourly data

## Performance Metrics
Each backtest provides comprehensive metrics including:
- Total Return %
- Buy & Hold Return % (for comparison)
- Sharpe Ratio
- Sortino Ratio
- Maximum Drawdown %
- Number of Trades
- Win Rate %
- Profit Factor
- System Quality Number (SQN)
- And 15+ other metrics

## Strategy Selection Guide

Choose based on your trading style:

- **Base**: Simple and reliable, good for understanding the core concept
- **MFI**: Best for volume-based traders, reduces false signals in low-volume periods
- **ADX**: Ideal for trend followers, avoids choppy markets
- **Kalman**: Best for noise reduction, suitable for high-frequency data

## Customization

To modify parameters, edit the constants at the top of each file:

```python
# Example: Change MA periods in any strategy file
FAST_MA_PERIOD = 10  # Changed from 20
SLOW_MA_PERIOD = 30  # Changed from 50
```

## Requirements
- Python 3.8+
- backtesting.py framework
- pandas, numpy, talib
- All dependencies in requirements.txt

## Author
Moon Dev - October 2025

## Notes
- Strategies are designed for educational/research purposes
- Always validate with forward testing before live trading
- Risk management is crucial - start with small position sizes
- Each strategy adapts to different market conditions