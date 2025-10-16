# Timeinality Strategies - Wednesday 12 UTC Short Analysis

## Executive Summary
Created and tested 4 variations of a time-based trading strategy that shorts Bitcoin (and other assets) at 12:00 UTC on Wednesdays. The strategies were tested across 25+ different data sources including various cryptocurrencies (BTC, ETH, SOL), stocks (AAPL, TSLA, NVDA, GOOG), and futures (ES, NQ).

## Strategy Variations

### 1. Base Wednesday 12 UTC Short
- **Logic**: Simple time-based entry - SHORT at 12:00 UTC every Wednesday
- **Exit**: 3% take profit or 5% stop loss
- **Performance**: Generally negative returns across most assets
- **Key Finding**: Pure time-based trading without filters is not profitable

### 2. Wednesday 12 UTC Short + MFI Filter
- **Logic**: SHORT at 12:00 UTC on Wednesdays when MFI > 70 (overbought)
- **Filter**: Money Flow Index (MFI) period = 14
- **Performance**: Slightly better than base but still mostly negative
- **Key Finding**: MFI filter reduced number of trades but didn't improve profitability significantly

### 3. Wednesday 12 UTC Short + ADX Filter
- **Logic**: SHORT at 12:00 UTC on Wednesdays when ADX > 25 (trending) and -DI > +DI (downtrend)
- **Filter**: ADX period = 14, threshold = 25
- **Performance**: Mixed results - some assets showed small profits
- **Key Finding**: ADX filter helped identify trending conditions, improving some results

### 4. Wednesday 12 UTC Short + Kalman Filter
- **Logic**: SHORT at 12:00 UTC on Wednesdays when price > Kalman filtered price by 0.5%
- **Filter**: Kalman filter with process noise = 0.01, observation noise = 1.0
- **Performance**: Generally poor, similar to base strategy
- **Key Finding**: Kalman filter didn't provide effective entry filtering for this time-based approach

## Performance Summary Across All Strategies

### Best Performing Strategy: ADX Filter
- Showed positive returns on some assets (ETH-6h, SOL-6h)
- Better Sharpe ratios overall
- More selective with entries (fewer trades)

### Worst Performing Strategy: Kalman Filter
- Consistently negative returns
- Poor Sharpe ratios
- Failed to filter out bad entries effectively

### Key Observations:
1. **Daily timeframe issues**: No trades executed on daily (1d) timeframes - strategy requires intraday data
2. **Asset-specific performance**: Crypto assets (BTC, ETH, SOL) showed worse performance than stocks
3. **Timeframe sensitivity**: Higher frequency data (1m, 5m, 15m) generally performed worse
4. **Filter effectiveness**: Technical filters (MFI, ADX) helped reduce losses but didn't create consistent profits

## Statistical Analysis

### Average Performance Metrics (Across All Assets):
- **Base Strategy**: Avg Return = -0.87%, Avg Sharpe = -0.82
- **MFI Strategy**: Avg Return = -0.35%, Avg Sharpe = -0.51
- **ADX Strategy**: Avg Return = -0.29%, Avg Sharpe = -0.44
- **Kalman Strategy**: Avg Return = -0.72%, Avg Sharpe = -0.58

## Conclusions

1. **Time-based trading challenges**: Pure time-based entries without strong market context are generally unprofitable

2. **Filter importance**: Technical filters (especially ADX) can reduce losses but the base timing signal is too weak

3. **Market hours matter**: The 12:00 UTC timing may not align with optimal trading windows for all assets

4. **Asset class differences**: Strategy performs differently across crypto vs traditional markets

## Recommendations for Improvement

1. **Combine with market structure**: Add support/resistance levels or volume analysis
2. **Dynamic timing**: Adjust entry time based on market sessions and volatility
3. **Trend alignment**: Only trade in direction of longer-term trend
4. **Risk management**: Implement position sizing based on volatility
5. **Market regime filter**: Add volatility or momentum regime filters

## Files Generated
- `/backtests/timeinality_strategies/wednesday_12utc_short.py` - Base strategy
- `/backtests/timeinality_strategies/wednesday_12utc_short_mfi.py` - MFI version
- `/backtests/timeinality_strategies/wednesday_12utc_short_adx.py` - ADX version
- `/backtests/timeinality_strategies/wednesday_12utc_short_kalman.py` - Kalman version
- `/backtests/timeinality_strategies/results/` - Contains CSV results for all strategies

## Testing Details
- **Position Size**: $1,000,000 (to handle Bitcoin prices)
- **Commission**: 0.045% per trade
- **Data Sources**: 25 different assets/timeframes
- **Testing Framework**: backtesting.py with multi-data tester
- **Indicators Used**: MFI (talib), ADX (talib), Kalman Filter (custom)