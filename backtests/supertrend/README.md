# Supertrend Strategy Suite

## Overview
This directory contains a comprehensive implementation of the Supertrend indicator strategy with multiple variations for enhanced trading performance.

## What is Supertrend?
The Supertrend indicator is a trend-following indicator that uses Average True Range (ATR) to calculate dynamic support and resistance levels. It provides clear buy/sell signals based on trend changes.

### Core Logic:
- **Upper Band**: HL2 - (ATR × Multiplier)
- **Lower Band**: HL2 + (ATR × Multiplier)
- **Trend Detection**: Bullish when price closes above upper band, Bearish when below lower band
- **Band Behavior**: Bands trail price action and only move in the direction of the trend
- **Signals**: Buy when trend changes from -1 to 1, Sell when trend changes from 1 to -1

## Strategy Variations

### 1. Supertrend Base (`supertrend_base.py`)
- Pure Supertrend implementation
- ATR Period: 10
- ATR Multiplier: 3.0
- Take Profit: 5%
- Stop Loss: 3%

### 2. Supertrend + RSI (`supertrend_rsi.py`)
- Adds RSI confirmation to filter entries
- Avoids overbought entries (RSI > 70)
- Exits on RSI overbought conditions
- RSI Period: 14

### 3. Supertrend + Volume (`supertrend_volume.py`)
- Requires above-average volume for entry signals
- Volume must be 1.2x the 20-period average
- Helps filter out weak signals in low-volume periods

### 4. Supertrend + MACD (`supertrend_macd.py`)
- Uses MACD histogram for momentum confirmation
- Enters only when MACD histogram is positive
- Exits when MACD turns negative
- MACD: 12/26/9

### 5. Supertrend + ADX (`supertrend_adx.py`)
- ADX filter ensures trading only in strong trends
- Entry requires ADX > 25
- Exit when ADX < 20 (trend weakening)
- ADX Period: 14

### 6. Supertrend Multi-Timeframe (`supertrend_mtf.py`)
- Uses two Supertrend calculations with different periods
- Fast: 10-period ATR, 3.0 multiplier
- Slow: 20-period ATR, 3.5 multiplier
- Requires both timeframes to align for entry

## Usage

### Run Individual Strategy
```bash
cd /Users/md/Dropbox/dev/github/moon-dev-trading-bots/backtests/supertrend
python supertrend_base.py       # Test base strategy
python supertrend_rsi.py        # Test RSI variation
python supertrend_volume.py     # Test Volume variation
python supertrend_macd.py       # Test MACD variation
python supertrend_adx.py        # Test ADX variation
python supertrend_mtf.py        # Test Multi-timeframe variation
```

### Test All Strategies
```bash
python test_all_supertrend.py   # Run all strategies and compare
```

### View Results
```bash
ls results/                      # List all result files
open results/*.csv              # Open results in spreadsheet
```

## Data Sources Tested
Each strategy is tested on 25+ data sources including:
- Bitcoin: 1m, 5m, 15m, 1h, 6h, 1d timeframes
- Ethereum: 15m, 1h, 6h, 1d timeframes
- Solana: 1m, 15m, 1h, 6h, 1d timeframes
- Stocks: AAPL, TSLA, GOOG, NVDA
- Futures: ES, NQ

## Key Parameters

### Default Settings
- **ATR Period**: 10 (lookback for volatility calculation)
- **ATR Multiplier**: 3.0 (distance of bands from price)
- **Take Profit**: 5% (exit at 5% profit)
- **Stop Loss**: 3% (exit at 3% loss)
- **Position Size**: 1,000,000 (to handle Bitcoin prices)
- **Commission**: 0.045% (0.00045)

## Performance Metrics
Each backtest provides:
- Return %
- Sharpe Ratio
- Sortino Ratio
- Max Drawdown
- Win Rate
- Number of Trades
- Profit Factor
- Average Trade Duration

## Strategy Selection Guide

Choose your strategy based on market conditions:
- **Base**: Simple trend following, works in clear trends
- **RSI**: Good for avoiding false breakouts in ranging markets
- **Volume**: Best for liquid markets with meaningful volume patterns
- **MACD**: Excellent for momentum-driven markets
- **ADX**: Ideal for filtering out choppy/ranging periods
- **MTF**: Most conservative, best for position trading

## Notes
- All strategies use position size of 1,000,000 to handle Bitcoin prices
- Strategies are designed to work across different asset classes
- Results are saved in CSV format for further analysis
- No optimization is performed - uses default parameters only

## Further Development
To optimize parameters:
1. Edit the strategy file
2. Add optimization code after the default backtest
3. Use bt.optimize() with parameter ranges
4. Test on specific data sources before running on all