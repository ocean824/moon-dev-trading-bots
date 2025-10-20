# SMA Strategy Variations - Best Results

## Top Performers by Sharpe Ratio (Risk-Adjusted Returns)

### 🥇 #1: VWAP Filter - HYPE 4H
**File:** [5_sma_vwap_filter.py](./5_sma_vwap_filter.py)
- **Return:** 9.28% | **Sharpe:** 4.62 | **Win Rate:** 100%
- **Max Drawdown:** -1.36% | **Trades:** 5
- Best for: Low-risk, high consistency on HYPE

### 🥈 #2: Basic SMA - HYPE Daily
**File:** [1_sma_basic.py](./1_sma_basic.py)
- **Return:** 5.24% | **Sharpe:** 3.64 | **Win Rate:** 100%
- **Max Drawdown:** 0% | **Trades:** 3
- **Params:** Fast SMA 15, Slow SMA 20, TP 2%, SL 6%

### 🥉 #3: MFI Filter - Housecoin 4H
**File:** [2_sma_mfi_filter.py](./2_sma_mfi_filter.py)
- **Return:** 29.20% | **Sharpe:** 2.37 | **Win Rate:** 77.8%
- **Max Drawdown:** -4.71% | **Trades:** 18
- **Params:** Fast SMA 20, Slow SMA 30, MFI 14, TP 3%, SL 3%

## Top Performers by Raw Return

### 💰 Long-Only - Housecoin 4H
**File:** [6_sma_long_only.py](./6_sma_long_only.py)
- **Return:** 1431.35% | **Win Rate:** 22.6%
- **Max Drawdown:** -87.83% | **Trades:** 62
- Insane returns but very high risk/volatility

### 🔥 Basic SMA - Housecoin Post-May 4H
**File:** [1_sma_basic.py](./1_sma_basic.py)
- **Return:** 78.46% | **Sharpe:** 1.51 | **Win Rate:** 70.3%
- **Max Drawdown:** -17.35% | **Trades:** 37
- **Params:** Fast SMA 20, Slow SMA 50, TP 5%, SL 6%
- Great balance of high returns with manageable risk

### 💎 Kalman Filter - Housecoin Post-May 4H
**File:** [3_sma_kalman_filter.py](./3_sma_kalman_filter.py)
- **Return:** 40.69% | **Sharpe:** 2.10 | **Win Rate:** 81.5%
- **Max Drawdown:** -5.66% | **Trades:** 27
- **Params:** Fast SMA 15, Slow SMA 20, Kalman MA 5, TP 3%, SL 5%

### 💵 VWAP Filter - Housecoin Post-May 4H
**File:** [5_sma_vwap_filter.py](./5_sma_vwap_filter.py)
- **Return:** 26.43% | **Sharpe:** 1.55 | **Win Rate:** 60%
- **Max Drawdown:** -9.29% | **Trades:** 25

### 🚀 Long-Only - HYPE Daily
**File:** [6_sma_long_only.py](./6_sma_long_only.py)
- **Return:** 22.69% | **Sharpe:** 1.55 | **Win Rate:** 50%
- **Max Drawdown:** -7.71% | **Trades:** 2
- **Best SMA Period:** 11

## Strategy Recommendations

**For Conservative Traders (Low Risk):**
- Use VWAP Filter on HYPE (Sharpe 4.62, only -1.36% max DD)

**For Balanced Risk/Reward:**
- **Basic SMA on Housecoin post-May** (78% return, -17% max DD, 70% win rate)
- MFI Filter or Kalman Filter on Housecoin post-May
- Good Sharpe ratios with manageable drawdowns

**For Aggressive Traders:**
- Long-Only strategy on Housecoin (1431% returns!)
- Warning: Extreme volatility and -87% max drawdown

## Data Filters Applied
- **Housecoin Post-May:** Data filtered to start from May 1, 2025 (removes early pump)
- **HYPE:** Full available data from Aug 21 - Oct 20, 2025
