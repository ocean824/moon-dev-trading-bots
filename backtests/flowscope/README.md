# FlowScope Volume Profile Strategies

This folder contains backtesting strategies based on the FlowScope Pine Script indicator concept. These strategies create volume profiles showing buy/sell volume distribution at different price levels within candles or groups of candles.

## Core Concept

The FlowScope strategies work by:
1. Creating volume profiles that show volume distribution at different price levels
2. Calculating buy volume (close-low)/(high-low) and sell volume (high-close)/(high-low)
3. Identifying the Point of Control (POC) - the price level with maximum volume
4. Trading based on buy/sell volume imbalances at these key levels

## Strategy Variations

### 1. FlowScopeBase (`flowscope_base.py`)
- Core volume profile strategy using POC and buy/sell imbalances
- Enters long when buy volume significantly exceeds sell volume at POC (65%+ buy volume)
- Enters short when sell volume significantly exceeds buy volume at POC (35% or less buy volume)
- Uses 3% take profit and 2% stop loss

### 2. FlowScopeADX (`flowscope_adx.py`)
- Adds ADX (Average Directional Index) for trend strength confirmation
- Only trades when ADX > 25 (trending market)
- Uses +DI and -DI to confirm trend direction
- Exits positions if trend weakens (ADX drops below threshold)

### 3. FlowScopeVWAP (`flowscope_vwap.py`)
- Incorporates VWAP (Volume Weighted Average Price) for additional price context
- Uses VWAP bands (2 standard deviations) for support/resistance levels
- Enters longs when POC shows buy imbalance near VWAP lower band
- Enters shorts when POC shows sell imbalance near VWAP upper band

### 4. FlowScopeMFI (`flowscope_mfi.py`)
- Uses Money Flow Index (MFI) for volume/price confirmation
- Trades buy imbalances when MFI is oversold (<30)
- Trades sell imbalances when MFI is overbought (>70)
- Includes MFI divergence detection for stronger signals

## Key Parameters

All strategies share these core parameters:
- `profile_period`: Number of candles in volume profile (default: 20)
- `volume_bins`: Number of price levels in profile (default: 10)
- `imbalance_threshold`: Buy/sell volume threshold (default: 0.65 or 65%)
- `take_profit`: Profit target (default: 0.03 or 3%)
- `stop_loss`: Stop loss level (default: 0.02 or 2%)

## Testing

### Quick Test on Single Dataset
```bash
python test_single_dataset.py
```

### Full Test on All Datasets
```bash
python test_all_strategies.py
```

### Individual Strategy Test
```bash
python flowscope_base.py
```

## Performance Notes

The strategies are computationally intensive due to the volume profile calculations. They work best on:
- Higher timeframe data (1h, 4h, daily)
- Liquid markets with consistent volume
- Trending markets (especially the ADX variant)

## Risk Management

All strategies implement:
- Fixed percentage stop loss (2%)
- Fixed percentage take profit (3%)
- Position sizing based on available capital
- Exit conditions based on indicator signals