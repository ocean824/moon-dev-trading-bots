# TP/SL Optimization Analysis - Hour-Based SHORT Strategies

**Generated:** 2025-10-16

**Objective:** Optimize Take Profit and Stop Loss parameters (1-15% range) for the best performing hour-based SHORT strategies on SOLUSD and SUIUSD.

---

## Executive Summary

Tested **5 configurations** with **1,125 total backtests** (225 TP/SL combinations per config):
- **3 Single-Day Strategies:** Specific day-hour combinations
- **2 All-Days Strategies:** Same hour across all days (Mon-Sun)

### Key Findings:

1. **SUIUSD Monday 07:00 UTC** is the ABSOLUTE WINNER
   - **Return: 146.44%** | **Sharpe: 2.40** | **Max DD: -10.91%**
   - Best TP: 3% | Best SL: 5%
   - Win Rate: 86.5% with only 52 trades (highly selective)

2. **SOLUSD Thursday 11:00 UTC** is the runner-up
   - **Return: 378.42%** | **Sharpe: 0.89** | **Max DD: -30.01%**
   - Best TP: 13% | Best SL: 2%
   - Win Rate: 22.0% but massive profit factor of 1.57

3. **Tight TP/SL combinations dominate** - Most optimal configs use TP ≤ 5% and SL ≤ 5%

---

## 🏆 Top 5 Configurations by Return %

| Rank | Symbol | Strategy Type | Day/Days | Hour UTC | Best TP% | Best SL% | Return % | Sharpe | Max DD % | Trades | Win Rate % | Profit Factor |
|------|--------|---------------|----------|----------|----------|----------|----------|--------|----------|--------|------------|---------------|
| 1 | **SOLUSD** | Single-Day | Thursday | 11:00 | 13 | 2 | **378.42** | 0.890 | -30.01 | 218 | 22.0 | 1.568 |
| 2 | **SOLUSD** | Single-Day | Tuesday | 11:00 | 14 | 5 | **289.75** | 0.495 | -71.12 | 218 | 36.2 | 1.314 |
| 3 | **SUIUSD** | All-Days | Mon-Sun | 09:00 | 5 | 4 | **242.38** | 0.919 | -29.56 | 363 | 51.8 | 1.342 |
| 4 | **SUIUSD** | Single-Day | Monday | 07:00 | 3 | 5 | **146.44** | 2.397 | -10.91 | 52 | 86.5 | 3.763 |
| 5 | **SOLUSD** | All-Days | Mon-Sun | 11:00 | 1 | 5 | **90.16** | 0.383 | -33.56 | 1527 | 82.8 | 1.229 |

---

## 📊 Top 5 Configurations by Sharpe Ratio (Risk-Adjusted Returns)

| Rank | Symbol | Strategy Type | Day/Days | Hour UTC | Best TP% | Best SL% | Return % | Sharpe | Max DD % | Trades | Win Rate % | Profit Factor |
|------|--------|---------------|----------|----------|----------|----------|----------|--------|----------|--------|------------|---------------|
| 1 | **SUIUSD** | Single-Day | Monday | 07:00 | 3 | 5 | 146.44 | **2.397** | -10.91 | 52 | 86.5 | 3.763 |
| 2 | **SUIUSD** | All-Days | Mon-Sun | 09:00 | 5 | 4 | 242.38 | **0.919** | -29.56 | 363 | 51.8 | 1.342 |
| 3 | **SOLUSD** | Single-Day | Thursday | 11:00 | 13 | 2 | 378.42 | **0.890** | -30.01 | 218 | 22.0 | 1.568 |
| 4 | **SOLUSD** | Single-Day | Tuesday | 11:00 | 14 | 5 | 289.75 | **0.495** | -71.12 | 218 | 36.2 | 1.314 |
| 5 | **SOLUSD** | All-Days | Mon-Sun | 11:00 | 1 | 5 | 90.16 | **0.383** | -33.56 | 1527 | 82.8 | 1.229 |

---

## 🛡️ Top 5 Configurations by Max Drawdown (Best Risk Management)

| Rank | Symbol | Strategy Type | Day/Days | Hour UTC | Best TP% | Best SL% | Return % | Sharpe | Max DD % | Trades | Win Rate % | Profit Factor |
|------|--------|---------------|----------|----------|----------|----------|----------|--------|----------|--------|------------|---------------|
| 1 | **SUIUSD** | Single-Day | Monday | 07:00 | 3 | 5 | 146.44 | 2.397 | **-10.91** | 52 | 86.5 | 3.763 |
| 2 | **SUIUSD** | All-Days | Mon-Sun | 09:00 | 5 | 4 | 242.38 | 0.919 | **-29.56** | 363 | 51.8 | 1.342 |
| 3 | **SOLUSD** | Single-Day | Thursday | 11:00 | 13 | 2 | 378.42 | 0.890 | **-30.01** | 218 | 22.0 | 1.568 |
| 4 | **SOLUSD** | All-Days | Mon-Sun | 11:00 | 1 | 5 | 90.16 | 0.383 | **-33.56** | 1527 | 82.8 | 1.229 |
| 5 | **SOLUSD** | Single-Day | Tuesday | 11:00 | 14 | 5 | 289.75 | 0.495 | **-71.12** | 218 | 36.2 | 1.314 |

---

## 🎯 Deep Dive: Strategy-by-Strategy Analysis

### 1. SUIUSD Monday 07:00 UTC (Single-Day) ⭐⭐⭐⭐⭐

**THE GOLD STANDARD**

```
Optimal Parameters:
├─ Take Profit: 3%
├─ Stop Loss: 5%
└─ Risk/Reward Ratio: 1:0.6 (tight SL, quick TP)

Performance Metrics:
├─ Return: 146.44%
├─ Sharpe Ratio: 2.397 (EXCEPTIONAL)
├─ Max Drawdown: -10.91% (BEST)
├─ Total Trades: 52
├─ Win Rate: 86.5% (HIGHEST)
└─ Profit Factor: 3.763 (INCREDIBLE)
```

**Alpha Insights:**
- **Highest Sharpe Ratio (2.397)** - Best risk-adjusted returns across ALL configs
- **Shallowest drawdown (-10.91%)** - Superior risk management
- **86.5% win rate** - Most consistent performer
- **Low trade count (52)** - Highly selective, quality over quantity
- **Tight TP (3%)** - Takes profits quickly, doesn't overstay
- **TP < SL ratio** - Accepts smaller wins but protects capital aggressively

**Trading Edge:** Monday mornings at 7 UTC capture weekend gap momentum on SUIUSD with tight profit targets.

---

### 2. SOLUSD Thursday 11:00 UTC (Single-Day) ⭐⭐⭐⭐

**THE HIGH ROLLER**

```
Optimal Parameters:
├─ Take Profit: 13%
├─ Stop Loss: 2%
└─ Risk/Reward Ratio: 1:6.5 (AGGRESSIVE - let winners run!)

Performance Metrics:
├─ Return: 378.42% (HIGHEST RETURN)
├─ Sharpe Ratio: 0.890
├─ Max Drawdown: -30.01%
├─ Total Trades: 218
├─ Win Rate: 22.0% (LOWEST - but who cares!)
└─ Profit Factor: 1.568
```

**Alpha Insights:**
- **Highest absolute return (378.42%)** - Massive gains
- **Wide TP (13%) with tight SL (2%)** - Classic "cut losses, let winners run" strategy
- **Only 22% win rate** - Winners are HUGE, losers are tiny
- **6.5:1 reward/risk ratio** - When it hits, it PRINTS
- **Thursday timing** - Captures mid-week volatility before Friday

**Trading Edge:** Thursday 11 UTC on SOLANA catches directional moves with asymmetric risk/reward. Low win rate doesn't matter when winners are 6.5x larger than losers.

---

### 3. SUIUSD Hour 09:00 UTC (All-Days) ⭐⭐⭐⭐

**THE CONSISTENT GRINDER**

```
Optimal Parameters:
├─ Take Profit: 5%
├─ Stop Loss: 4%
└─ Risk/Reward Ratio: 1:1.25 (balanced)

Performance Metrics:
├─ Return: 242.38%
├─ Sharpe Ratio: 0.919
├─ Max Drawdown: -29.56%
├─ Total Trades: 363 (most trades)
├─ Win Rate: 51.8%
└─ Profit Factor: 1.342
```

**Alpha Insights:**
- **Balanced approach** - TP/SL nearly equal (5%/4%)
- **Most trades (363)** - Consistent daily opportunities
- **All-days strategy** - Doesn't rely on specific day-of-week edge
- **Good Sharpe (0.919)** - Second best risk-adjusted returns
- **Coin-flip win rate (51.8%)** but still highly profitable

**Trading Edge:** 9 UTC daily on SUIUSD = consistent edge regardless of day. Higher frequency = more compounding opportunities.

---

### 4. SOLUSD Tuesday 11:00 UTC (Single-Day) ⭐⭐⭐

**THE VOLATILE BEAST**

```
Optimal Parameters:
├─ Take Profit: 14%
├─ Stop Loss: 5%
└─ Risk/Reward Ratio: 1:2.8

Performance Metrics:
├─ Return: 289.75%
├─ Sharpe Ratio: 0.495
├─ Max Drawdown: -71.12% (WORST)
├─ Total Trades: 218
├─ Win Rate: 36.2%
└─ Profit Factor: 1.314
```

**Alpha Insights:**
- **Huge TP (14%)** - Swings for the fences
- **High volatility** - Largest drawdown at -71%
- **Not for the faint of heart** - Requires strong stomach
- **Still profitable** but rough ride

**Trading Edge:** Tuesday 11 UTC SOLANA has explosive potential but violent drawdowns. Only for aggressive risk tolerance.

---

### 5. SOLUSD Hour 11:00 UTC (All-Days) ⭐⭐⭐

**THE SAFE CHOICE**

```
Optimal Parameters:
├─ Take Profit: 1%
├─ Stop Loss: 5%
└─ Risk/Reward Ratio: 1:0.2 (EXTREMELY TIGHT TP)

Performance Metrics:
├─ Return: 90.16%
├─ Sharpe Ratio: 0.383
├─ Max Drawdown: -33.56%
├─ Total Trades: 1527 (MOST TRADES)
├─ Win Rate: 82.8%
└─ Profit Factor: 1.229
```

**Alpha Insights:**
- **Scalping strategy** - 1% TP means quick in/out
- **High win rate (82.8%)** - Very consistent
- **Most trades (1527)** - Daily at 11 UTC across all days
- **Lowest Sharpe** - Return doesn't compensate for risk as well

**Trading Edge:** Daily 11 UTC SOLANA scalp. High frequency, high consistency, but lowest risk-adjusted returns.

---

## 📈 TP/SL Pattern Analysis

### Optimal Parameter Ranges by Strategy Type:

**Single-Day Strategies (Specific day-hour combos):**
- Prefer **WIDER TP** (3-14%) and **TIGHTER or MODERATE SL** (2-5%)
- Embrace asymmetric risk/reward ratios
- Accept lower win rates for bigger winners

**All-Days Strategies (Same hour every day):**
- Prefer **TIGHTER TP** (1-5%) and **MODERATE SL** (4-5%)
- More balanced risk/reward
- Higher win rates, more trades

### Key Insight:
**TP ≤ 5% appeared in 3 out of 5 top configs** - Market doesn't give huge moves on hourly timeframes. Take profits quickly.

---

## 🔬 Symbol-Specific Behavior

### SUIUSD:
- **Newer token (52 weeks data)** vs SOLUSD (250 weeks)
- **Better Sharpe Ratios** - More efficient returns
- **Shallower drawdowns** - Better risk management
- **Prefers tighter TP/SL** (3-5% range)

### SOLUSD:
- **Longer history (250 weeks)** - More mature market
- **Higher absolute returns** but lower Sharpe
- **Accepts wider TP** (up to 14%) - More volatile swings
- **More data = more trades** but requires patience for drawdowns

---

## 💡 Actionable Trading Strategies

### Strategy A: "The Conservative Champion" ⭐ RECOMMENDED
**SUIUSD Monday 07:00 UTC | TP: 3% | SL: 5%**
- Trade once per week
- Highest Sharpe (2.40)
- Shallowest DD (-10.91%)
- 86.5% win rate
- **Use this if:** You want consistent, low-stress, high-probability trades

### Strategy B: "The Asymmetric Aggressor"
**SOLUSD Thursday 11:00 UTC | TP: 13% | SL: 2%**
- Trade once per week
- Highest return (378.42%)
- Accept 22% win rate for massive winners
- **Use this if:** You can handle volatility and love home runs

### Strategy C: "The Daily Grind"
**SUIUSD Every Day 09:00 UTC | TP: 5% | SL: 4%**
- Trade 7 days per week
- Most consistent edge (363 trades)
- Good Sharpe (0.92)
- **Use this if:** You want daily action with solid risk-adjusted returns

---

## ⚠️ Risk Considerations

1. **SOLUSD Tuesday has -71% drawdown** - Avoid unless extremely risk-tolerant
2. **All strategies are SHORT-only** - Performance depends on downtrends
3. **Hourly timeframe** - Requires precise timing and execution
4. **Backtested on historical data** - Forward test before going live
5. **95% position sizing** used in backtests - Consider scaling down for live trading

---

## 🎓 Key Learnings

1. **Tighter is often better** - Most optimal TPs were ≤ 5%
2. **Day-of-week matters** - Monday and Thursday showed strongest edges
3. **Win rate ≠ profitability** - Thursday SOLUSD: 22% WR but 378% return
4. **Sharpe is king** - SUIUSD Monday's 2.40 Sharpe >> everything else
5. **More trades ≠ better returns** - 52 trades (SUI Monday) beat 1527 trades (SOL all-days)

---

## 📊 Summary Statistics

| Metric | Best Performer | Value |
|--------|---------------|-------|
| Highest Return % | SOLUSD Thursday 11:00 | 378.42% |
| Best Sharpe Ratio | SUIUSD Monday 07:00 | 2.397 |
| Shallowest Drawdown | SUIUSD Monday 07:00 | -10.91% |
| Highest Win Rate | SUIUSD Monday 07:00 | 86.5% |
| Best Profit Factor | SUIUSD Monday 07:00 | 3.763 |
| Most Trades | SOLUSD All-Days 11:00 | 1,527 |
| Fewest Trades | SUIUSD Monday 07:00 | 52 |

---

## 🚀 Recommended Implementation Plan

**Phase 1: Validate "The Conservative Champion"**
- Forward test SUIUSD Monday 07:00 (TP: 3%, SL: 5%)
- Start with 10% position size
- Run for 8 weeks (8 trades)
- Target: 80%+ win rate, <15% drawdown

**Phase 2: Add "The Daily Grind"**
- If Phase 1 succeeds, add SUIUSD 09:00 daily (TP: 5%, SL: 4%)
- Combine both strategies (Mon 7am + Daily 9am)
- Monitor for correlation/overlap

**Phase 3: Test "The Aggressor" (Optional)**
- Only if comfortable with volatility
- SOLUSD Thursday 11:00 (TP: 13%, SL: 2%)
- Reduce position size to 5% max
- Accept 20-30% win rate

---

*Analysis completed by Moon Dev's TP/SL Optimizer 🌙*

**Total Backtests:** 1,125
**Optimization Range:** TP 1-15%, SL 1-15%
**Commission:** 0.045% per trade
**Position Size:** 95% of equity
