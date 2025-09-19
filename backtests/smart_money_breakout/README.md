# Smart Money Breakout Channels Strategy Suite

## Overview

This directory contains a comprehensive implementation of the Smart Money Breakout Channels strategy, which identifies consolidation zones through volatility normalization and trades breakouts with volume confirmation. The strategy is based on Smart Money concepts for detecting institutional accumulation and distribution patterns.

## Strategy Components

### Core Concept
The Smart Money Breakout strategy identifies periods of consolidation where institutional traders may be accumulating or distributing positions. It then trades the breakouts from these consolidation channels with various confirmation filters.

### Key Features
- **Channel Detection**: Uses normalized volatility to identify consolidation periods
- **Breakout Validation**: Requires strong closes with configurable body percentage outside channel
- **Volume Analysis**: Tracks total volume, up/down volume, and delta for confirmation
- **Multi-Mode Operation**: Supports different volume analysis modes
- **Risk Management**: ATR-based stops with dynamic take-profit ratios

## Strategy Variations

### 1. Base Strategy (`smart_money_base.py`)
- Pure channel breakout with volume confirmation
- Volatility-based consolidation detection
- Strong vs weak close filtering
- Volume delta analysis for trend alignment

### 2. MFI Enhanced (`smart_money_mfi.py`)
- Adds Money Flow Index for overbought/oversold filtering
- MFI divergence detection
- Dynamic position sizing based on MFI extremes
- Enhanced exit conditions using MFI levels

### 3. ADX Enhanced (`smart_money_adx.py`)
- Integrates ADX for trend strength confirmation
- Directional movement (+DI/-DI) validation
- Dynamic stops and targets based on trend strength
- Trend quality evaluation for entry filtering

### 4. Kalman Filter Enhanced (`smart_money_kalman.py`)
- Applies Kalman filtering for noise reduction
- Price prediction using velocity and acceleration
- Noise level estimation and filtering
- Cleaner channel detection with reduced false signals

## File Structure

```
smart_money_breakout/
├── smart_money_base.py      # Base implementation
├── smart_money_mfi.py        # MFI enhancement
├── smart_money_adx.py        # ADX enhancement
├── smart_money_kalman.py     # Kalman filter enhancement
├── quick_test.py            # Quick single-data test
├── test_all_smart_money.py  # Full multi-data test
├── results/                 # Test results directory
└── README.md               # This file
```

## Usage

### Quick Test (Single Dataset)
```bash
cd /Users/md/Dropbox/dev/github/moon-dev-trading-bots/backtests/smart_money_breakout
python quick_test.py
```

This runs all four strategies on a single BTC dataset for rapid validation.

### Individual Strategy Test
```bash
python smart_money_base.py     # Test base strategy
python smart_money_mfi.py      # Test MFI variant
python smart_money_adx.py      # Test ADX variant
python smart_money_kalman.py   # Test Kalman variant
```

Each strategy automatically tests on all 25+ configured data sources.

### Full Comparison Test
```bash
python test_all_smart_money.py
```

This tests all strategies on all data sources and creates comparison matrices.

## Parameters

### Base Parameters
- `CHANNEL_LOOKBACK`: Period for channel high/low detection (default: 20)
- `VOLATILITY_THRESHOLD`: Threshold for consolidation detection (default: 0.02)
- `BREAKOUT_STRENGTH`: Required % of candle body outside channel (default: 0.6)
- `ATR_MULTIPLIER`: Stop loss distance in ATR units (default: 2.0)
- `TAKE_PROFIT_RATIO`: Risk/reward ratio for targets (default: 2.0)

### MFI Parameters
- `MFI_PERIOD`: Money Flow Index calculation period (default: 14)
- `MFI_OVERBOUGHT`: Overbought threshold (default: 70)
- `MFI_OVERSOLD`: Oversold threshold (default: 30)

### ADX Parameters
- `ADX_PERIOD`: ADX calculation period (default: 14)
- `ADX_THRESHOLD`: Minimum ADX for trend (default: 25)
- `DI_THRESHOLD`: Minimum DI difference for direction (default: 5)

### Kalman Parameters
- `KALMAN_GAIN`: Filter gain controlling smoothness (default: 0.02)
- `KALMAN_COVARIANCE`: Initial error covariance (default: 0.0001)

## Trading Logic

### Entry Conditions

**Long Entry:**
1. Price breaks above channel high
2. Strong close requirement met (X% of body above channel)
3. Volume confirmation (>20% above average)
4. Volume delta positive (buying pressure)
5. Strategy-specific filters (MFI, ADX, Kalman)

**Short Entry:**
1. Price breaks below channel low
2. Strong close requirement met (X% of body below channel)
3. Volume confirmation (>20% above average)
4. Volume delta negative (selling pressure)
5. Strategy-specific filters

### Exit Conditions
- Stop loss: ATR-based dynamic stops
- Take profit: Risk/reward ratio targets
- Trail stops: Exit if price re-enters channel
- Strategy-specific exits (MFI extremes, ADX weakening, Kalman reversal)

## Performance Metrics

Each strategy outputs comprehensive metrics including:
- Total Return %
- Sharpe Ratio
- Sortino Ratio
- Maximum Drawdown
- Win Rate
- Profit Factor
- Average Trade Return
- Total Number of Trades

## Results

Results are saved in the `results/` directory:
- Individual strategy results: `smart_money_[variant].csv`
- Quick test comparison: `quick_test_comparison.csv`
- Full comparison: `strategy_comparison_[timestamp].csv`
- Performance matrix: `performance_matrix_[timestamp].csv`

## Optimization

Each strategy includes built-in optimization routines that test parameter combinations to maximize the Sortino Ratio. Optimization ranges are pre-configured but can be modified in each strategy file.

## Data Compatibility

The strategies are tested on 25+ data sources including:
- Multiple cryptocurrency pairs (BTC, ETH, SOL)
- Various timeframes (1m to 1d)
- Stock market data (AAPL, TSLA, NVDA, etc.)
- Futures contracts (ES, NQ)

## Risk Considerations

- **Consolidation Quality**: Not all consolidations lead to profitable breakouts
- **False Breakouts**: Strong close filtering helps but doesn't eliminate all false signals
- **Market Conditions**: Performance varies significantly across different market regimes
- **Volume Requirements**: Low-volume markets may generate fewer signals

## Best Practices

1. **Parameter Tuning**: Use optimization to find parameters suitable for your market
2. **Volume Confirmation**: Never ignore volume - it's crucial for breakout validation
3. **Risk Management**: Always use stops and appropriate position sizing
4. **Market Selection**: Test thoroughly on your target markets before live trading
5. **Timeframe Selection**: Higher timeframes generally produce more reliable signals

## Technical Notes

- Uses `backtesting.py` framework for backtesting
- Technical indicators from `talib` library
- Position size fixed at 1,000,000 for consistency
- Commission set to 0.045% (Coinbase Advanced)