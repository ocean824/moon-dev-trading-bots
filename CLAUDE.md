# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is Moon Dev's Trading Bot Collection implementing the RBI Framework (Research, Backtest, Implement) for systematic algorithmic trading across cryptocurrency and stock markets.

## Common Development Commands

### Running Backtests
```bash
# Run a specific backtest strategy
python backtests/rsi_guppy.py
python backtests/directional_index.py
python backtests/64_intrashort.py
```

### Running Live Trading Bots
```bash
# Hyperliquid bots (run from project root)
python -m bots.hyperliquid.ppls_positions
python -m bots.hyperliquid.dune_data
python -m bots.hyperliquid.mm
python -m bots.hyperliquid.liq_statarb

# Interactive Brokers bots
python bots/interactive_brokers/market_order.py
python bots/interactive_brokers/bracket_order.py

# Solana bots
python bots/solana/timer.py
python bots/solana/quick_buysell.py
```

### Data Collection
```bash
# Download Coinbase data
python coinbase_data_2025.py

# Download Yahoo Finance data
python data/yahoo_daily_data_dl.py
python data/yahoo_hourly_data.py

# Download Hyperliquid data
python hyperliquid_data.py
```

### Machine Learning Research
```bash
# Run ML models for liquidation prediction
python research/machine_learning/RF_liquidation.py
python research/machine_learning/LSTM_liquidation.py

# Hyperparameter optimization
python research/machine_learning/rf_param_optimizer.py
python research/machine_learning/lstm_param_optimizer.py
```

## Code Architecture

### Project Structure
The codebase follows the RBI Framework with three main directories:

1. **`/backtests`** - Strategy validation using backtesting.py framework
   - Each file contains a complete trading strategy with entry/exit rules
   - Uses historical OHLCV data from `/data` directory
   - Outputs performance metrics and visualizations

2. **`/bots`** - Production trading bot implementations
   - **Hyperliquid**: Advanced position tracking, market making, liquidation arbitrage
   - **Interactive Brokers**: Stock/futures trading with bracket orders
   - **Solana**: Token trading with timing strategies
   - Each exchange has its own `nice_funcs.py` for utility functions

3. **`/data`** - Historical price data and downloaders
   - Coinbase, Yahoo Finance, Hyperliquid, Interactive Brokers data
   - Data processing utilities and CSV storage
   - Machine learning datasets for research

4. **`/research`** - Experimental strategies and ML models
   - **Machine Learning**: Liquidation prediction models (LSTM, Random Forest)
   - **Backtesting**: Strategy research and validation
   - Parameter optimization and model evaluation

### Key Integration Points

**Backtesting Framework**: All strategies use `backtesting.py` library with consistent structure:
- Strategy class inheriting from `backtesting.Strategy`
- `init()` for indicator setup
- `next()` for trading logic
- Standard performance metrics output

**API Integrations**:
- Hyperliquid: Uses `eth-account` for signing, custom API wrapper
- Interactive Brokers: Uses proprietary API with order management
- Coinbase: Uses `coinbase-advanced-py` SDK
- Solana: Web3 integration for token trading

**Position Management**: 
- Always starts with minimal positions ($10-$25)
- Implements position size checks before trading
- Handles decimal precision for each exchange

**Data Flow**:
1. Historical data downloaded to `/data`
2. Research phase explores strategies in `/research`
3. Backtests validate strategies using `/backtests`
4. Successful strategies implemented as production bots in `/bots`
5. Bots use real-time data from exchange APIs

**Security Considerations**:
- Private keys stored in `dontshare.py` (never commit to git)
- Interactive Brokers user IDs must be hidden in all outputs
- Use environment variables for API keys via `.env` file

## Environment Variables

Create a `.env` file in the project root with:
```
# For Dune Analytics (Hyperliquid whale tracking)
DUNE_KEY=your_dune_api_key

# Exchange API keys (as needed)
# Add exchange-specific keys here
```

## Testing and Code Quality

### Code Quality Standards
- Use `conda activate tflow` environment (don't create new virtual environments)
- Keep files under 800 lines of code - create new files if longer
- Update `requirements.txt` when adding new packages
- Never move files without asking - create new ones instead
- Never change existing code notes/comments

### Backtesting Requirements
- Use `backtesting.py` framework but NOT their indicators
- Use `pandas_ta` or `talib` for technical indicators instead
- Always print full backtest stats with `print(stats)` - never partial results
- Show plots but DO NOT save .html files
- Hide Interactive Brokers user ID in all outputs

### Machine Learning Workflow
- Start local testing with `LOCAL_MODE = True` for faster iteration
- Use reduced data samples (`SAMPLE_FRACTION = 0.1`) for local testing
- Only move to Lambda Labs cloud training after local validation
- Target minimum AUC of 0.65 for trading models (0.7+ preferred)
- Focus on direction prediction rather than exact price prediction

## Dependencies

Install all dependencies:
```bash
conda activate tflow  # Use existing conda environment
pip install -r requirements.txt
```

Key packages:
- `backtesting>=0.3.3` - Core backtesting framework
- `pandas>=1.3.0`, `numpy>=1.20.0` - Data processing
- `ta-lib>=0.4.24`, `pandas-ta>=0.3.14b0` - Technical indicators
- `tensorflow>=2.13.0`, `scikit-learn>=1.3.0` - Machine learning
- `eth-account==0.8.0` - Hyperliquid wallet management
- `coinbase-advanced-py>=1.0.2` - Coinbase Advanced Trading SDK
- `fastapi==0.109.2`, `uvicorn==0.27.1` - API services

## Important Notes

- The RBI Framework is mandatory: Research → Backtest → Implement
- Start all live trading with minimal position sizes ($10)
- Each exchange has different decimal precision requirements
- Monitor bots regularly and keep detailed trade logs
- Risk management is built into each strategy
- Never save backtest HTML files - show plots only