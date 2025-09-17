# Fair Value Gap (FVG) Volumatic Trading Strategies

## Overview

This folder contains a comprehensive implementation of Fair Value Gap (FVG) trading strategies based on the Volumatic Fair Value Gaps TradingView indicator concept. The strategies identify and trade price inefficiencies (gaps) in the market using volume analysis and various technical indicators for confirmation.

## Strategy Variations

### 1. FVG Base Strategy (`fvg_base.py`)
- **Core Logic**: Identifies bullish/bearish Fair Value Gaps using 3-bar patterns
- **Entry Signals**:
  - Bullish FVG: When Low[0] > High[-2] with volume confirmation
  - Bearish FVG: When High[0] < Low[-2] with volume confirmation
- **Exit Signals**:
  - Take profit/stop loss targets
  - Gap mitigation (when gap is 50% filled)
- **Key Parameters**:
  - Min Gap Size: 0.5%
  - Volume Threshold: 1.2x average
  - Bull/Bear Volume Ratio: 60/40%

### 2. FVG + MFI Strategy (`fvg_mfi.py`)
- **Enhancement**: Adds Money Flow Index for volume-price relationship
- **Additional Filters**:
  - MFI oversold (<30) for long entries
  - MFI overbought (>70) for short entries
  - MFI momentum for trend confirmation
- **Dynamic Targets**: Adjusts TP/SL based on MFI levels
- **Exit Enhancement**: MFI divergence detection

### 3. FVG + ADX Strategy (`fvg_adx.py`)
- **Enhancement**: Uses ADX for trend strength validation
- **Additional Filters**:
  - ADX > 25 for trend confirmation
  - +DI/-DI directional confirmation
  - ADX acceleration for trend momentum
- **Dynamic Sizing**: Position size based on ADX strength
- **Exit Enhancement**: Trend weakening detection

### 4. FVG + Kalman Filter Strategy (`fvg_kalman.py`)
- **Enhancement**: Applies Kalman filtering for noise reduction
- **Additional Features**:
  - Smoothed price action for cleaner gap detection
  - Trend estimation and prediction
  - Confidence-based entry filtering
  - Adaptive targets based on filter confidence
- **Exit Enhancement**: Kalman trend reversal detection

## Key Components

### Fair Value Gap Detection
```python
# Bullish FVG: Gap up with volume
if current_low > two_bars_ago_high:
    gap_size = current_low - two_bars_ago_high
    if gap_percent >= min_gap_threshold:
        # Enter long

# Bearish FVG: Gap down with volume
if current_high < two_bars_ago_low:
    gap_size = two_bars_ago_low - current_high
    if gap_percent >= min_gap_threshold:
        # Enter short
```

### Volume Analysis
- Calculates bull vs bear volume within each candle
- Requires volume surge (1.2x average) for valid gaps
- Uses volume ratios for directional bias

### Gap Mitigation Tracking
- Monitors when price fills/mitigates the gap
- Exits positions when gaps are 50% filled
- Tracks gap levels for dynamic support/resistance

## File Structure

```
fvg_volumatic/
├── fvg_base.py              # Base FVG strategy
├── fvg_mfi.py               # FVG + MFI enhancement
├── fvg_adx.py               # FVG + ADX enhancement
├── fvg_kalman.py            # FVG + Kalman filter enhancement
├── test_all_fvg_strategies.py  # Comprehensive testing script
├── test_single_dataset.py   # Quick single dataset test
├── run_multi_data_test.py   # Multi-data testing script
├── results/                 # Strategy backtest results
└── README.md                # This file
```

## Usage

### Run Individual Strategy
```bash
cd backtests/fvg_volumatic
python fvg_base.py        # Run base strategy
python fvg_mfi.py         # Run MFI variant
python fvg_adx.py         # Run ADX variant
python fvg_kalman.py      # Run Kalman variant
```

### Test All Strategies
```bash
python test_all_fvg_strategies.py  # Test all variants
python run_multi_data_test.py      # Multi-data test
```

### Quick Test
```bash
python test_single_dataset.py  # Quick test on single dataset
```

## Performance Expectations

Based on the Fair Value Gap concept:
- **Win Rate**: 35-45% (typical for trend-following gaps)
- **Risk/Reward**: 1.5:1 to 2:1
- **Best Market Conditions**: Trending markets with clear momentum
- **Challenging Conditions**: Ranging/choppy markets

## Multi-Data Testing

All strategies are configured to test on 25+ data sources including:
- **Crypto**: BTC, ETH, SOL (multiple timeframes)
- **Stocks**: AAPL, TSLA, NVDA, GOOG
- **Futures**: ES, NQ
- **Timeframes**: 1m, 5m, 15m, 1h, 6h, 1d

Results are automatically saved to CSV files in the `results/` folder.

## Key Indicators Used

1. **Volume Moving Average**: Filters for significant volume
2. **ATR**: Dynamic gap validation and position sizing
3. **MFI**: Money flow and volume-price relationship
4. **ADX/DI**: Trend strength and direction
5. **Kalman Filter**: Noise reduction and trend estimation

## Risk Management

- **Position Sizing**: Fixed 1,000,000 for Bitcoin compatibility
- **Stop Loss**: 2-3% default (adjustable)
- **Take Profit**: 3-4% default (adjustable)
- **Gap Mitigation Exit**: 50% gap fill triggers exit
- **Commission**: 0.045% per trade

## Notes

- FVGs represent market inefficiencies that often get filled
- Volume confirmation is crucial for valid gap identification
- Different variants suit different market conditions
- Kalman filter variant is most sophisticated but computationally intensive
- ADX variant best for strong trending markets
- MFI variant best for volume-driven markets

## Future Improvements

1. Add market structure analysis for context
2. Implement multi-timeframe gap confirmation
3. Add liquidity zone detection near gaps
4. Include order flow imbalance analysis
5. Add machine learning for gap quality scoring