# Bull vs Bear Market Sessions Strategies

## Overview
This folder contains implementations of the Bull vs Bear Market Intraday Sessions trading strategy, originally inspired by a TradingView Pine Script indicator. The strategy divides trading periods into sessions and analyzes volume profiles to identify bull/bear dominance and Points of Control (POC).

## Strategy Concept
The core idea is to:
1. Divide the trading day into multiple sessions (default: 0-6, 6-12, 12-18, 18-24 hours)
2. Calculate volume profiles for each session
3. Identify Points of Control (POC) - price levels with highest volume
4. Calculate Value Areas (VA) - price ranges containing 70% of volume
5. Determine bull/bear dominance through delta calculations
6. Trade based on session transitions and volume imbalances

## Strategy Variations

### 1. BullBearSessionsSimple (`test_single_dataset.py`)
- **Status**: ✅ Working and tested
- **Description**: Simplified implementation for quick testing
- **Key Features**:
  - Basic bull/bear volume ratio calculation
  - SMA trend confirmation
  - Simple entry/exit rules
- **Performance**: 52% success rate across 25 markets

### 2. BullBearSessionsBase (`bull_bear_sessions_base.py`)
- **Status**: ⚠️ Implementation complete, optimization needed
- **Description**: Full session-based volume profile trading
- **Key Features**:
  - Complete session profile calculation
  - POC and Value Area identification
  - Session transition detection
  - Dynamic exit based on session changes

### 3. BullBearSessionsMFI (`bull_bear_sessions_mfi.py`)
- **Status**: ⚠️ Implementation complete, optimization needed
- **Description**: Base strategy + Money Flow Index confirmation
- **Key Features**:
  - MFI for volume-based signal confirmation
  - Divergence detection
  - Extreme MFI level entries

### 4. BullBearSessionsADX (`bull_bear_sessions_adx.py`)
- **Status**: ⚠️ Implementation complete, optimization needed
- **Description**: Base strategy + ADX for trend filtering
- **Key Features**:
  - ADX to filter for trending markets
  - Directional movement confirmation
  - Trend exhaustion reversal detection

### 5. BullBearSessionsKalman (`bull_bear_sessions_kalman.py`)
- **Status**: ⚠️ Implementation complete, optimization needed
- **Description**: Base strategy + Kalman filter for smoothed price action
- **Key Features**:
  - Kalman filter for noise reduction
  - Trend velocity tracking
  - Delta divergence detection

## Files Structure

```
bull_bear_sessions/
├── README.md                          # This file
├── bull_bear_sessions_base.py         # Base strategy implementation
├── bull_bear_sessions_mfi.py          # MFI variation
├── bull_bear_sessions_adx.py          # ADX variation
├── bull_bear_sessions_kalman.py       # Kalman filter variation
├── test_single_dataset.py             # Simplified working version
├── test_all_strategies.py             # Test all variations
├── compare_all_strategies.py          # Compare results
├── run_multi_test.py                  # Multi-data testing script
└── results/                           # Backtest results directory
    └── *.csv                          # Individual strategy results
```

## Usage

### Test Single Strategy
```bash
python test_single_dataset.py
```

### Run Multi-Data Test
```bash
python run_multi_test.py
```

### Compare All Strategies
```bash
python compare_all_strategies.py
```

## Key Parameters

### Common Parameters
- **Session Hours**: [6, 12, 18, 24] - Session boundaries
- **Volume Percentile**: 70% - For Value Area calculation
- **Min Session Volume**: 50% - Minimum volume for valid signals
- **Delta Threshold**: 55% - Bull volume threshold
- **Take Profit**: 3.0%
- **Stop Loss**: 2.0%

### Strategy-Specific Parameters

#### MFI Variation
- **MFI Period**: 14
- **MFI Oversold**: 30
- **MFI Overbought**: 70

#### ADX Variation
- **ADX Period**: 14
- **ADX Threshold**: 25
- **DI Threshold**: 5

#### Kalman Variation
- **Kalman Gain**: 0.01
- **Kalman Covariance**: 1.0
- **Trend Threshold**: 0.002

## Performance Summary

Based on testing across 25 different markets (crypto, stocks, futures):

### BullBearSessionsSimple (Working Version)
- **Success Rate**: 52% of markets profitable
- **Average Sortino Ratio**: 9.26
- **Average Sharpe Ratio**: 0.30
- **Average Win Rate**: 46.6%
- **Average Max Drawdown**: -50.1%

## Implementation Notes

1. **Session Calculation**: The strategy divides each day into 4 sessions by default, but this can be adjusted based on market hours and trading preferences.

2. **Volume Profile**: Uses a binning approach to create volume profiles with 10 price levels per session.

3. **POC Identification**: The Point of Control is the price level with the highest volume in each session.

4. **Value Area**: Expands from the POC until 70% of session volume is captured.

5. **Entry Signals**:
   - Bear to Bull transition with price near POC
   - Bull to Bear transition with price near POC
   - Strong session bias with volume confirmation

6. **Exit Signals**:
   - Session reversal
   - Stop loss/Take profit hits
   - Dynamic exits based on indicator conditions

## Future Improvements

1. **Optimize Session Hours**: Test different session divisions (e.g., 3-hour, 8-hour sessions)
2. **Adaptive Parameters**: Make parameters adjust based on market volatility
3. **Multi-Timeframe Analysis**: Combine daily and intraday session analysis
4. **Machine Learning**: Use ML to predict session transitions
5. **Risk Management**: Implement position sizing based on session strength

## Troubleshooting

### Common Issues

1. **Long Computation Time**: The full strategies take time to compute session profiles. Use the simplified version for quick testing.

2. **Memory Usage**: Large datasets may require significant memory for session calculations.

3. **Parameter Sensitivity**: The strategies are sensitive to session hour definitions and volume thresholds.

## Conclusion

The Bull vs Bear Market Sessions strategy provides a unique approach to trading based on volume profile analysis and session transitions. While the simplified version shows promise with a 52% success rate across diverse markets, the full implementations require further optimization to achieve their potential. The concept of dividing trading into sessions and analyzing volume distribution offers valuable insights into market structure and can be combined with other indicators for enhanced performance.