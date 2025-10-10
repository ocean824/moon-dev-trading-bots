# ATR Rope Trading Strategy Suite

## Overview
The ATR Rope strategy suite implements an advanced trend-following system based on the "rope smoothing" concept. Like a rope that stabilizes movement, the indicator only moves when price exceeds an ATR-based threshold, creating a smooth trend line that filters out noise while capturing significant moves.

## Core Concept
The ATR Rope indicator works by:
1. **Rope Smoothing**: Creates a smoothed price line that only updates when price moves beyond an ATR threshold
2. **Direction Detection**: Identifies three market states:
   - Bullish (rope rising) = 1
   - Bearish (rope falling) = -1
   - Consolidating (rope flat) = 0
3. **Consolidation Ranges**: Tracks periods when price is range-bound within ATR boundaries
4. **Dynamic Bands**: Upper/lower bands based on ATR multiplier for breakout detection

## Strategy Variations

### 1. ATR Rope Base (`atr_rope_base.py`)
- Core rope smoothing implementation
- Trades breakouts from consolidation ranges
- Trend reversal signals when rope direction changes
- Pullback entries when price returns to rope in trending markets

### 2. ATR Rope + RSI (`atr_rope_rsi.py`)
- Adds RSI confirmation to filter signals
- Avoids entries in overbought/oversold conditions
- Better timing on trend reversals
- RSI divergence detection

### 3. ATR Rope + Volume (`atr_rope_volume.py`)
- Volume confirmation for breakouts
- Filters weak signals with low volume
- On-Balance Volume (OBV) for trend confirmation
- Enhanced targets on high-volume breakouts

### 4. ATR Rope + MACD (`atr_rope_macd.py`)
- MACD for trend and momentum confirmation
- MACD histogram for momentum strength
- Crossover signals for trend changes
- Divergence pattern detection

### 5. ATR Rope + MFI (`atr_rope_mfi.py`)
- Money Flow Index for volume-weighted momentum
- Detects accumulation/distribution patterns
- Extreme reversal signals
- Money flow divergence patterns

## Key Features

### Entry Signals
1. **Consolidation Breakouts**: Enter when rope transitions from flat to directional
2. **Trend Reversals**: Enter when rope direction changes
3. **Pullback Entries**: Enter on price pullbacks to rope in trending markets
4. **Indicator Confirmation**: Each variation adds specific confirmation filters

### Exit Signals
1. **Direction Change**: Exit when rope turns against position
2. **ATR-Based Stops**: Dynamic stop loss based on ATR multiplier
3. **Indicator Divergence**: Exit on indicator warnings (RSI, MFI, MACD)
4. **Volume Exhaustion**: Exit on extremely low volume (volume strategy)

## Parameters

### Common Parameters
- `ATR_PERIOD`: 14 (ATR calculation period)
- `ATR_MULTIPLIER`: 1.5 (Threshold for rope movement)
- `ROPE_SMOOTH_PERIOD`: 3 (Smoothing for rope line)
- `TAKE_PROFIT_ATR_MULT`: 3.0 (Take profit at 3x ATR)
- `STOP_LOSS_ATR_MULT`: 1.5 (Stop loss at 1.5x ATR)

### Strategy-Specific Parameters
- **RSI**: Period=14, OB=70, OS=30
- **Volume**: MA Period=20, Threshold=1.2x average
- **MACD**: Fast=12, Slow=26, Signal=9
- **MFI**: Period=14, OB=80, OS=20

## Usage

### Test Individual Strategy
```python
# Run a single strategy
python atr_rope_base.py

# Or any variation
python atr_rope_rsi.py
python atr_rope_volume.py
python atr_rope_macd.py
python atr_rope_mfi.py
```

### Test All Strategies
```python
# Run complete test suite on all data sources
python test_all_atr_rope.py
```

### Results
Results are saved in the `results/` directory:
- Individual CSV files for each strategy
- Comparison report with all strategies
- Performance metrics across 25+ data sources

## Performance Metrics
Each strategy is evaluated on:
- Total Return %
- Sharpe Ratio
- Sortino Ratio
- Maximum Drawdown
- Win Rate
- Profit Factor
- Expectancy
- Number of Trades

## Data Sources Tested
- Bitcoin: 1m, 5m, 15m, 1h, 6h, 1d timeframes
- Ethereum: 15m, 1h, 6h, 1d timeframes
- Solana: 1m, 15m, 1h, 6h, 1d timeframes
- Stocks: AAPL, TSLA, GOOG, NVDA
- Futures: ES, NQ

## Best Practices
1. **Start with Base Strategy**: Understand core rope mechanics first
2. **Add Confirmations**: Layer indicators based on market conditions
3. **Adjust ATR Multiplier**: Lower values = more sensitive, higher = more filtering
4. **Monitor Consolidations**: Best signals often come from consolidation breakouts
5. **Use Appropriate Timeframes**: Works best on 1h+ timeframes

## Notes
- Position size fixed at 1,000,000 for Bitcoin compatibility
- Commission set to 0.045% (Coinbase Pro fees)
- All strategies use stop loss and take profit orders
- Designed for trend-following, not mean reversion