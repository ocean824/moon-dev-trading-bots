# Trend Impulse Channels Strategy Collection

## Overview
This folder contains multiple implementations of the Trend Impulse Channels indicator, originally from Pine Script. Each variation explores different approaches to improve performance and adapt to various market conditions.

## Strategy Variations

### 1. trend_impulse_base.py
**Core Implementation**
- Original Pine Script logic translated to Python
- ATR-based trend stepping mechanism
- Dynamic channel boundaries
- Trigger thresholds for trend flips
- Retest signals for continuation plays

**Parameters:**
- ATR Period: 200
- Trigger Threshold: 2.86
- Max Step Size: 0.034
- Band Multiplier: 2.02

### 2. trend_impulse_tight.py
**Scalping Variation**
- Tighter channels for more frequent trading
- Shorter ATR period (50 vs 200)
- Lower trigger threshold (1.5 vs 2.86)
- Momentum acceleration in stepping
- Quick exit mechanisms

**Best for:** High-frequency trading, volatile markets

### 3. trend_impulse_momentum.py
**Momentum-Filtered Version**
- Adds RSI and MACD confirmation
- Divergence detection
- Volume confirmation on signals
- Dynamic risk adjustment based on momentum

**Filters:**
- RSI (14): Overbought/oversold filtering
- MACD (12/26/9): Trend confirmation
- Volume: 1.5x average for breakouts

### 4. trend_impulse_volume.py
**Volume-Weighted Implementation**
- Volume-weighted step sizes
- VWAP integration for support/resistance
- OBV trend confirmation
- Adaptive channel width based on volume

**Features:**
- Larger steps on high volume
- VWAP as dynamic S/R
- OBV accumulation/distribution signals

### 5. trend_impulse_adaptive.py
**Volatility-Adaptive Strategy**
- Detects volatility regimes
- Adjusts parameters dynamically
- Market structure detection (trending/ranging)
- Regime-specific signal generation

**Adaptations:**
- Low volatility: Tighter parameters
- High volatility: Wider channels
- Trending: Favor continuation
- Ranging: More conservative

### 6. trend_impulse_multi_tf.py
**Multi-Timeframe Confirmation**
- Higher timeframe trend direction
- Medium timeframe momentum
- Lower timeframe precise entries
- Alignment scoring system

**Timeframes:**
- HTF: 4x multiplier (4h if base is 1h)
- MTF: 2x multiplier
- LTF: Base timeframe

### 7. trend_impulse_final.py
**Simplified Working Version**
- Dual EMA crossover for trend
- ATR channels for entry timing
- Clean signal generation
- Reliable trade execution

**This version generates consistent trades and serves as the production-ready implementation.**

## Risk Management

All strategies implement:
- ATR-based stop losses
- Dynamic take profit levels
- Position sizing of 1,000,000 units
- Commission of 0.045%

## Data Compatibility

All strategies are designed to work with:
- 25+ data sources (Coinbase, IB, Yahoo)
- Multiple timeframes (1m to daily)
- Various asset classes (crypto, stocks, futures)

## Running the Strategies

### Single Backtest:
```bash
python trend_impulse_final.py
```

### Multi-Data Testing:
Each strategy automatically tests on all configured data sources when run directly.

### Results:
Results are saved to `./results/` folder in CSV format with comprehensive metrics.

## Performance Notes

- The `trend_impulse_final.py` is the most reliable for generating trades
- Performance varies significantly across different timeframes
- Best results typically on 1h-4h timeframes for crypto
- May need parameter optimization for specific assets

## Future Improvements

1. Add machine learning for parameter optimization
2. Implement portfolio-level risk management
3. Add correlation filters for multi-asset trading
4. Develop market regime detection for strategy selection