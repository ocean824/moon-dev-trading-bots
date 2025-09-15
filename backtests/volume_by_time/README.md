# Volume by Time Trading Strategies

This folder contains a suite of backtesting strategies based on the "Volume by Time" concept, which analyzes volume patterns at specific times and compares current volume to historical averages.

## Strategy Overview

The Volume by Time indicator tracks volume at each specific time period and calculates either the average or median of historical volumes at that time. It then compares current volume to the historical average/median to identify significant volume spikes that may indicate institutional activity.

## Strategy Variations

### 1. Volume by Time Base (`volume_by_time_base.py`)
- **Description**: Base strategy using volume spike detection
- **Entry Logic**:
  - Long: Volume spike (>1.1x average) + Bullish candle + Price above SMA20
  - Short: Volume spike (>1.1x average) + Bearish candle + Price below SMA20
- **Exit Logic**: Exit on price reversal or crossing SMA

### 2. Volume by Time with ADX (`volume_by_time_adx.py`)
- **Description**: Volume spikes filtered by ADX trend strength
- **Entry Logic**:
  - Requires ADX > 25 for trend confirmation
  - Uses +DI/-DI for trend direction validation
- **Exit Logic**: Exit when trend weakens (ADX < 20) or DI crosses

### 3. Volume by Time with VWAP (`volume_by_time_vwap.py`)
- **Description**: Volume spikes with VWAP for price action context
- **Entry Logic**:
  - Uses VWAP as dynamic support/resistance
  - Looks for volume spikes near VWAP bands
- **Exit Logic**: Exit on VWAP cross with volume confirmation

### 4. Volume by Time with MFI (`volume_by_time_mfi.py`)
- **Description**: Volume spikes confirmed by Money Flow Index
- **Entry Logic**:
  - Requires MFI confirmation (not overbought/oversold)
  - Looks for divergences between price and MFI
- **Exit Logic**: Exit on MFI extremes or divergence signals

## Key Parameters

All strategies share these core parameters:
- `lookback_days`: Number of days to calculate historical volume average (default: 20)
- `volume_threshold`: Multiplier for volume spike detection (default: 1.1-1.2x)
- `use_median`: Use median instead of mean for historical calculation
- `stop_loss_pct`: Stop loss percentage (default: 3%)
- `take_profit_pct`: Take profit percentage (default: 6%)

## Usage

### Running Individual Strategies
```bash
python backtests/volume_by_time/volume_by_time_base.py
python backtests/volume_by_time/volume_by_time_adx.py
python backtests/volume_by_time/volume_by_time_vwap.py
python backtests/volume_by_time/volume_by_time_mfi.py
```

### Running All Strategies
```bash
python backtests/volume_by_time/test_all_strategies.py
```

This will test all strategies across multiple data sources and generate a comparison report.

## Technical Implementation

The strategies use the backtesting.py framework with:
- pandas_ta for technical indicators
- Multi-timeframe data support
- Automatic data format detection (Coinbase, Yahoo, IB)
- Position sizing based on available capital

## Performance Notes

- Strategies work best with sufficient initial capital (>$100,000 for BTC)
- Volume patterns are more reliable on higher timeframes (daily, 4H)
- Best results when combined with trend filters (ADX, VWAP)
- Consider market conditions when interpreting volume spikes

## Files

- `volume_by_time_base.py` - Base strategy implementation
- `volume_by_time_adx.py` - ADX filtered variation
- `volume_by_time_vwap.py` - VWAP enhanced variation
- `volume_by_time_mfi.py` - MFI confirmed variation
- `test_all_strategies.py` - Multi-data testing script
- `debug_volume_test.py` - Debug script for signal analysis
- `simple_volume_test.py` - Simplified test implementation
- `results/` - Directory for backtest results and comparisons