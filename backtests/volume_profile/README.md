# Volume Profile Trading Strategies

This directory contains multiple backtesting strategies based on Volume Profile concepts from the TradingView Pine Script indicator.

## Strategy Overview

### 1. Volume Profile Base Strategy (`volume_profile_base.py`)
- **Concept**: Trades based on Value Area boundaries (VAL and VAH)
- **Entry**: When price crosses above VAL with volume confirmation
- **Exit**: When price reaches VAH or falls below VAL
- **Risk Management**: 2% stop loss, 4% take profit
- **Additional Filters**: RSI, pivot points, volume threshold

### 2. POC Mean Reversion Strategy (`volume_profile_poc.py`)
- **Concept**: Mean reversion to Point of Control (highest volume price)
- **Entry**: When price deviates from POC by 1.5%+ with volume surge
- **Exit**: When price returns to POC or hits stops
- **Risk Management**: Dynamic ATR-based stops, trailing stops
- **Additional Filters**: RSI oversold/overbought, momentum confirmation

### 3. Value Area Breakout Strategy (`volume_profile_breakout.py`)
- **Concept**: Trades breakouts above VAH and breakdowns below VAL
- **Entry**: On breakout with 1.618x volume surge (golden ratio)
- **Exit**: Trail stops using value area boundaries
- **Risk Management**: 1.5% initial stop, 2x risk/reward target
- **Additional Filters**: Pivot points, momentum, minimum value area width

### 4. Pivot Volume Strategy (`volume_profile_pivot.py`)
- **Concept**: Combines pivot points with volume profile analysis
- **Entry**: At pivot lows with accumulation, exit at pivot highs with distribution
- **Exit**: Uses POC as dynamic support/resistance
- **Risk Management**: POC-based stops, 5% take profit
- **Additional Filters**: OBV, A/D indicator, volume ratios

### 5. Volume Spike Strategy (`volume_profile_spike.py`)
- **Concept**: Trades on volume spikes using 1.618x multiplier
- **Entry**: Volume spike with direction based on POC position
- **Exit**: On volume normalization or price targets
- **Risk Management**: 1.5% stop loss, dynamic value area targets
- **Additional Filters**: Momentum, VWAP, minimum bars between trades

### 6. Simplified Base Strategy (`volume_profile_simple_base.py`)
- **Concept**: Simplified version using VWAP and basic volume levels
- **Entry**: Price crosses volume bands with confirmation
- **Exit**: At opposite band or stop loss
- **Risk Management**: 2% stop loss, 4% take profit
- **Note**: This is the most efficient version for testing

## Key Technical Indicators Used

1. **POC (Point of Control)**: Price level with highest volume
2. **VAH (Value Area High)**: Upper boundary containing 68% of volume
3. **VAL (Value Area Low)**: Lower boundary containing 68% of volume
4. **VWAP**: Volume-weighted average price
5. **Pivot Points**: Swing highs and lows for entry/exit timing
6. **Volume Ratios**: Current volume vs moving average

## Testing Framework

All strategies are integrated with the multi-data testing framework and can be tested on 25+ different data sources including:
- Bitcoin (multiple timeframes: 1m, 5m, 15m, 1h, 6h, 1d)
- Ethereum (15m, 1h, 6h, 1d)
- Solana (1m, 15m, 1h, 6h, 1d)
- Traditional stocks (AAPL, TSLA, GOOG, NVDA)
- Futures (ES, NQ)

## Running the Strategies

### Test Individual Strategy:
```bash
python volume_profile_base.py
```

### Test All Strategies:
```bash
python test_all_strategies.py
```

### Test with Multi-Data Framework:
Each strategy automatically tests on all configured data sources when run directly.

## Performance Notes

- The simplified base strategy (`volume_profile_simple_base.py`) is the most computationally efficient
- Complex volume profile calculations can be resource-intensive on large datasets
- Consider using smaller data samples for initial testing
- Results are saved to the `results/` directory as CSV files

## Risk Disclaimer

These strategies are for backtesting and research purposes only. Past performance does not guarantee future results. Always use proper risk management and test thoroughly before live trading.

## File Structure

```
volume_profile/
├── volume_profile_base.py          # Base VAL/VAH strategy
├── volume_profile_poc.py           # POC mean reversion
├── volume_profile_breakout.py      # Value area breakout
├── volume_profile_pivot.py         # Pivot point volume
├── volume_profile_spike.py         # Volume spike trading
├── volume_profile_simple_base.py   # Simplified efficient version
├── test_all_strategies.py          # Test runner
├── results/                         # Test results directory
└── README.md                        # This file
```

## Future Improvements

1. Optimize volume profile calculation for better performance
2. Add more sophisticated value area calculations
3. Implement session-based volume profiles
4. Add market profile integration
5. Include order flow analysis