# Liquidation Trading Strategies

## Quick Start

### 1. Preprocess Data First
```bash
# Generate BTC liquidation data (1m and 5m timeframes)
python preprocess_liquidation_data.py
```
This creates:
- `/data/moondev_api/liq_data_BTC_1m_ohlcv.csv`
- `/data/moondev_api/liq_data_BTC_5m_ohlcv.csv`

### 2. Run Strategies
```bash
# Pure liquidation strategies (best performers)
python pure_liquidation_momentum.py    # Follow the cascade
python pure_liquidation_contrarian.py  # Fade the liquidations

# Other strategies
python liquidation_adx_moondev.py      # ADX filtered
python liquidation_base_strategy.py    # Large liquidations only
```

## Strategy Performance

**Best Performer: Momentum Strategy**
- Theory: Trade WITH liquidations (follow the cascade)
- When longs liquidate → SELL (continue down)
- When shorts liquidate → BUY (continue up)
- Outperforms contrarian approach in trending markets

## Data Structure

Preprocessed data includes:
- `Open, High, Low, Close, Volume` - Standard OHLCV
- `long_liquidations` - Long position liquidations in USD
- `short_liquidations` - Short position liquidations in USD
- `total_liquidations` - Sum of all liquidations
- `liquidation_count` - Number of liquidation events

## Customization

### Change Symbol
Edit `preprocess_liquidation_data.py`:
```python
SYMBOL = 'ETH'  # Change from BTC to any symbol
```

### Adjust Timeframes
In any strategy file:
```python
# Option 1: 1-minute data
data_path = '.../liq_data_BTC_1m_ohlcv.csv'

# Option 2: 5-minute data (uncomment)
# data_path = '.../liq_data_BTC_5m_ohlcv.csv'
```

### Key Parameters
- `liquidation_threshold`: Minimum USD value to trigger trade ($100k-$2M)
- `take_profit`: Exit target (1-3%)
- `stop_loss`: Risk limit (0.5-2%)
- `max_hold_hours`: Time-based exit (6-48 hours)

## Notes
- All strategies auto-run optimization after baseline
- 5-minute data recommended for faster backtests
- Momentum strategy generates more trades than contrarian
- Large liquidations (>$500k) are most significant