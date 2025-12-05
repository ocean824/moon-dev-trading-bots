"""
Moon Dev's Full Liquidation Data Analysis
=========================================
Running ALL strategies from Phase 0/1/2 on liquidation data
Plus deep dive into why Long vs Short liq strategies are similar

This will answer:
1. How do all our 5-year winners perform on 476-day data?
2. Why are Long Liq and Short Liq so similar?
3. Where exactly are the buys happening?
"""

import pandas as pd
import numpy as np
import pandas_ta as ta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

print("=" * 70)
print("Moon Dev's Full Liquidation Data Analysis")
print("=" * 70)

# =============================================================================
# LOAD DATA
# =============================================================================
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/moondev_api/liq_data_BTC_5m_ohlcv.csv'
print(f"\nLoading: {data_path}")

raw_data = pd.read_csv(data_path, parse_dates=['datetime'], index_col='datetime')
raw_data = raw_data.sort_index()

# Resample to daily
daily_data = raw_data.resample('D').agg({
    'Open': 'first',
    'High': 'max',
    'Low': 'min',
    'Close': 'last',
    'Volume': 'sum',
    'total_liquidations': 'sum',
    'long_liquidations': 'sum',
    'short_liquidations': 'sum',
    'liquidation_count': 'sum'
}).dropna()

# Calculate indicators for strategies
daily_data['RSI'] = ta.rsi(daily_data['Close'], length=14)
daily_data['MA50'] = ta.sma(daily_data['Close'], length=50)

# Weekly low calculation
daily_data['week'] = daily_data.index.to_period('W')
weekly_min = daily_data.groupby('week')['Low'].transform('min')
daily_data['is_weekly_low'] = daily_data['Low'] == weekly_min

# Monthly low calculation
daily_data['month'] = daily_data.index.to_period('M')
monthly_min = daily_data.groupby('month')['Low'].transform('min')
daily_data['is_monthly_low'] = daily_data['Low'] == monthly_min

# ATR for volatility
daily_data['ATR'] = ta.atr(daily_data['High'], daily_data['Low'], daily_data['Close'], length=14)
daily_data['ATR_avg'] = daily_data['ATR'].rolling(50).mean()

first_price = daily_data['Close'].iloc[0]
last_price = daily_data['Close'].iloc[-1]
total_days = len(daily_data)

print(f"Date range: {daily_data.index[0]} to {daily_data.index[-1]}")
print(f"Total days: {total_days}")
print(f"BTC: ${first_price:,.2f} -> ${last_price:,.2f} ({((last_price/first_price)-1)*100:+.1f}%)")

# =============================================================================
# CONFIGURATION
# =============================================================================
STARTING_CAPITAL = 1_000_000
results = []
buy_logs = {}  # Store buy details for each strategy

# =============================================================================
# HELPER FUNCTION
# =============================================================================
def run_strategy(name, daily_data, buy_condition_func, buy_amount_func, min_days_between=1):
    """Generic strategy runner with buy logging"""
    total_coins = 0
    total_spent = 0
    buy_count = 0
    last_buy_idx = -999
    buys = []

    for i, (idx, row) in enumerate(daily_data.iterrows()):
        remaining = STARTING_CAPITAL - total_spent
        if remaining <= 0:
            break

        if i - last_buy_idx < min_days_between:
            continue

        if buy_condition_func(row, daily_data, i, total_coins, total_spent):
            buy_amount = buy_amount_func(row, daily_data, i, remaining, total_coins, total_spent)
            buy_amount = min(buy_amount, remaining)

            if buy_amount > 0:
                coins = buy_amount / row['Close']
                total_coins += coins
                total_spent += buy_amount
                buy_count += 1
                last_buy_idx = i

                buys.append({
                    'date': idx,
                    'price': row['Close'],
                    'amount': buy_amount,
                    'coins': coins,
                    'long_liq': row['long_liquidations'],
                    'short_liq': row['short_liquidations'],
                    'total_liq': row['total_liquidations'],
                    'cumulative_coins': total_coins,
                    'avg_price': total_spent / total_coins if total_coins > 0 else 0
                })

    buy_logs[name] = buys
    return total_coins, total_spent, buy_count

# =============================================================================
# BASELINE: Daily DCA
# =============================================================================
print("\n" + "="*70)
print("RUNNING ALL STRATEGIES")
print("="*70)

dca_daily = STARTING_CAPITAL / total_days
dca_coins = sum(dca_daily / row['Close'] for _, row in daily_data.iterrows())
dca_avg_price = STARTING_CAPITAL / dca_coins

results.append({
    'Strategy': 'Daily DCA',
    'Coins': dca_coins,
    'Avg_Price': dca_avg_price,
    'Buy_Count': total_days,
    'vs_DCA_Pct': 0.0,
    'Category': 'Baseline'
})
print(f"Daily DCA: {dca_coins:.4f} BTC")

# =============================================================================
# LIQUIDATION STRATEGIES (with detailed logging)
# =============================================================================

# Long Liq Accumulator
def long_liq_cond(row, data, i, coins, spent):
    return row['long_liquidations'] >= 500_000

def long_liq_amt(row, data, i, remaining, coins, spent):
    return remaining * 0.02

coins, spent, count = run_strategy('Long Liq Accumulator', daily_data, long_liq_cond, long_liq_amt)
vs_dca = ((coins - dca_coins) / dca_coins) * 100 if coins > 0 else -100
results.append({'Strategy': 'Long Liq Accumulator', 'Coins': coins, 'Avg_Price': spent/coins if coins > 0 else 0,
                'Buy_Count': count, 'vs_DCA_Pct': vs_dca, 'Category': 'Liquidation'})
print(f"Long Liq Accumulator: {coins:.4f} BTC ({vs_dca:+.1f}% vs DCA) - {count} buys")

# Short Liq Accumulator
def short_liq_cond(row, data, i, coins, spent):
    return row['short_liquidations'] >= 500_000

coins, spent, count = run_strategy('Short Liq Accumulator', daily_data, short_liq_cond, long_liq_amt)
vs_dca = ((coins - dca_coins) / dca_coins) * 100 if coins > 0 else -100
results.append({'Strategy': 'Short Liq Accumulator', 'Coins': coins, 'Avg_Price': spent/coins if coins > 0 else 0,
                'Buy_Count': count, 'vs_DCA_Pct': vs_dca, 'Category': 'Liquidation'})
print(f"Short Liq Accumulator: {coins:.4f} BTC ({vs_dca:+.1f}% vs DCA) - {count} buys")

# Total Liq Spike
def total_liq_cond(row, data, i, coins, spent):
    return row['total_liquidations'] >= 1_000_000

coins, spent, count = run_strategy('Total Liq Spike', daily_data, total_liq_cond, long_liq_amt)
vs_dca = ((coins - dca_coins) / dca_coins) * 100 if coins > 0 else -100
results.append({'Strategy': 'Total Liq Spike', 'Coins': coins, 'Avg_Price': spent/coins if coins > 0 else 0,
                'Buy_Count': count, 'vs_DCA_Pct': vs_dca, 'Category': 'Liquidation'})
print(f"Total Liq Spike: {coins:.4f} BTC ({vs_dca:+.1f}% vs DCA) - {count} buys")

# =============================================================================
# PHASE 0 STRATEGIES
# =============================================================================
print("\n--- Phase 0 Strategies ---")

# Weekly Low
def wl_cond(row, data, i, coins, spent):
    return row['is_weekly_low']

def wl_amt(row, data, i, remaining, coins, spent):
    return STARTING_CAPITAL * 0.01

coins, spent, count = run_strategy('Weekly Low', daily_data, wl_cond, wl_amt, min_days_between=5)
vs_dca = ((coins - dca_coins) / dca_coins) * 100 if coins > 0 else -100
results.append({'Strategy': 'Weekly Low', 'Coins': coins, 'Avg_Price': spent/coins if coins > 0 else 0,
                'Buy_Count': count, 'vs_DCA_Pct': vs_dca, 'Category': 'Phase 0'})
print(f"Weekly Low: {coins:.4f} BTC ({vs_dca:+.1f}% vs DCA) - {count} buys")

# RSI Oversold
def rsi_cond(row, data, i, coins, spent):
    return pd.notna(row['RSI']) and row['RSI'] < 30

def rsi_amt(row, data, i, remaining, coins, spent):
    return remaining * 0.05

coins, spent, count = run_strategy('RSI Oversold', daily_data, rsi_cond, rsi_amt)
vs_dca = ((coins - dca_coins) / dca_coins) * 100 if coins > 0 else -100
results.append({'Strategy': 'RSI Oversold', 'Coins': coins, 'Avg_Price': spent/coins if coins > 0 else 0,
                'Buy_Count': count, 'vs_DCA_Pct': vs_dca, 'Category': 'Phase 0'})
print(f"RSI Oversold: {coins:.4f} BTC ({vs_dca:+.1f}% vs DCA) - {count} buys")

# =============================================================================
# PHASE 1 STRATEGIES
# =============================================================================
print("\n--- Phase 1 Strategies ---")

# WL + Double Down
consecutive_lows = [0]  # Use list to allow modification in nested function

def wldd_cond(row, data, i, coins, spent):
    return row['is_weekly_low']

def wldd_amt(row, data, i, remaining, coins, spent):
    if coins > 0 and row['Close'] < spent / coins:
        consecutive_lows[0] += 1
    else:
        consecutive_lows[0] = 0
    multiplier = min(1.0 + (consecutive_lows[0] * 0.5), 2.0)
    return STARTING_CAPITAL * 0.01 * multiplier

consecutive_lows[0] = 0
coins, spent, count = run_strategy('WL + Double Down', daily_data, wldd_cond, wldd_amt, min_days_between=5)
vs_dca = ((coins - dca_coins) / dca_coins) * 100 if coins > 0 else -100
results.append({'Strategy': 'WL + Double Down', 'Coins': coins, 'Avg_Price': spent/coins if coins > 0 else 0,
                'Buy_Count': count, 'vs_DCA_Pct': vs_dca, 'Category': 'Phase 1'})
print(f"WL + Double Down: {coins:.4f} BTC ({vs_dca:+.1f}% vs DCA) - {count} buys")

# WL + Monthly Bonus
def wl_monthly_cond(row, data, i, coins, spent):
    return row['is_weekly_low']

def wl_monthly_amt(row, data, i, remaining, coins, spent):
    multiplier = 2.0 if row['is_monthly_low'] else 1.0
    return STARTING_CAPITAL * 0.01 * multiplier

coins, spent, count = run_strategy('WL + Monthly Bonus', daily_data, wl_monthly_cond, wl_monthly_amt, min_days_between=5)
vs_dca = ((coins - dca_coins) / dca_coins) * 100 if coins > 0 else -100
results.append({'Strategy': 'WL + Monthly Bonus', 'Coins': coins, 'Avg_Price': spent/coins if coins > 0 else 0,
                'Buy_Count': count, 'vs_DCA_Pct': vs_dca, 'Category': 'Phase 1'})
print(f"WL + Monthly Bonus: {coins:.4f} BTC ({vs_dca:+.1f}% vs DCA) - {count} buys")

# WL + Volatility Scale
def wl_vol_cond(row, data, i, coins, spent):
    return row['is_weekly_low']

def wl_vol_amt(row, data, i, remaining, coins, spent):
    if pd.notna(row['ATR']) and pd.notna(row['ATR_avg']) and row['ATR_avg'] > 0:
        atr_ratio = row['ATR'] / row['ATR_avg']
        multiplier = min(max(atr_ratio, 0.5), 2.0)
    else:
        multiplier = 1.0
    return STARTING_CAPITAL * 0.01 * multiplier

coins, spent, count = run_strategy('WL + Volatility Scale', daily_data, wl_vol_cond, wl_vol_amt, min_days_between=5)
vs_dca = ((coins - dca_coins) / dca_coins) * 100 if coins > 0 else -100
results.append({'Strategy': 'WL + Volatility Scale', 'Coins': coins, 'Avg_Price': spent/coins if coins > 0 else 0,
                'Buy_Count': count, 'vs_DCA_Pct': vs_dca, 'Category': 'Phase 1'})
print(f"WL + Volatility Scale: {coins:.4f} BTC ({vs_dca:+.1f}% vs DCA) - {count} buys")

# RSI Consecutive
rsi_consec_count = [0]

def rsi_consec_cond(row, data, i, coins, spent):
    if pd.notna(row['RSI']) and row['RSI'] < 30:
        rsi_consec_count[0] += 1
    else:
        rsi_consec_count[0] = 0
    return rsi_consec_count[0] >= 2

rsi_consec_count[0] = 0
coins, spent, count = run_strategy('RSI Consecutive', daily_data, rsi_consec_cond, rsi_amt)
vs_dca = ((coins - dca_coins) / dca_coins) * 100 if coins > 0 else -100
results.append({'Strategy': 'RSI Consecutive', 'Coins': coins, 'Avg_Price': spent/coins if coins > 0 else 0,
                'Buy_Count': count, 'vs_DCA_Pct': vs_dca, 'Category': 'Phase 1'})
print(f"RSI Consecutive: {coins:.4f} BTC ({vs_dca:+.1f}% vs DCA) - {count} buys")

# =============================================================================
# PHASE 2 STRATEGIES
# =============================================================================
print("\n--- Phase 2 Strategies ---")

# WL+DD + MACD
daily_data['MACD_hist'] = ta.macd(daily_data['Close'])['MACDh_12_26_9']

def wldd_macd_cond(row, data, i, coins, spent):
    return row['is_weekly_low'] and pd.notna(row['MACD_hist']) and row['MACD_hist'] < 0

consecutive_lows[0] = 0
coins, spent, count = run_strategy('WL+DD + MACD', daily_data, wldd_macd_cond, wldd_amt, min_days_between=5)
vs_dca = ((coins - dca_coins) / dca_coins) * 100 if coins > 0 else -100
results.append({'Strategy': 'WL+DD + MACD', 'Coins': coins, 'Avg_Price': spent/coins if coins > 0 else 0,
                'Buy_Count': count, 'vs_DCA_Pct': vs_dca, 'Category': 'Phase 2'})
print(f"WL+DD + MACD: {coins:.4f} BTC ({vs_dca:+.1f}% vs DCA) - {count} buys")

# WL+DD + ATR Scale
def wldd_atr_cond(row, data, i, coins, spent):
    return row['is_weekly_low']

def wldd_atr_amt(row, data, i, remaining, coins, spent):
    if coins > 0 and row['Close'] < spent / coins:
        consecutive_lows[0] += 1
    else:
        consecutive_lows[0] = 0

    base_mult = min(1.0 + (consecutive_lows[0] * 0.5), 2.0)

    if pd.notna(row['ATR']) and pd.notna(row['ATR_avg']) and row['ATR_avg'] > 0:
        atr_mult = min(max(row['ATR'] / row['ATR_avg'], 0.5), 2.5)
    else:
        atr_mult = 1.0

    return STARTING_CAPITAL * 0.01 * base_mult * atr_mult

consecutive_lows[0] = 0
coins, spent, count = run_strategy('WL+DD + ATR Scale', daily_data, wldd_atr_cond, wldd_atr_amt, min_days_between=5)
vs_dca = ((coins - dca_coins) / dca_coins) * 100 if coins > 0 else -100
results.append({'Strategy': 'WL+DD + ATR Scale', 'Coins': coins, 'Avg_Price': spent/coins if coins > 0 else 0,
                'Buy_Count': count, 'vs_DCA_Pct': vs_dca, 'Category': 'Phase 2'})
print(f"WL+DD + ATR Scale: {coins:.4f} BTC ({vs_dca:+.1f}% vs DCA) - {count} buys")

# =============================================================================
# RESULTS SUMMARY
# =============================================================================
df_results = pd.DataFrame(results)
df_results = df_results.sort_values('vs_DCA_Pct', ascending=False)

print("\n" + "="*70)
print("FULL RESULTS - ALL STRATEGIES ON 476-DAY LIQUIDATION DATA")
print("="*70)

print(f"\n{'Strategy':<25} {'vs DCA':>10} {'Coins':>12} {'Avg Price':>12} {'Buys':>8} {'Category':>12}")
print("-" * 85)
for _, row in df_results.iterrows():
    print(f"{row['Strategy']:<25} {row['vs_DCA_Pct']:>+9.1f}% {row['Coins']:>12.4f} ${row['Avg_Price']:>10,.0f} {row['Buy_Count']:>8} {row['Category']:>12}")

# Save results
df_results.to_csv('/Users/md/Dropbox/dev/github/moon-dev-trading-bots/backtests/accumulation/liquidations/full_comparison_results.csv', index=False)

# =============================================================================
# DEEP DIVE: WHY ARE LONG AND SHORT LIQ SIMILAR?
# =============================================================================
print("\n" + "="*70)
print("DEEP DIVE: LONG vs SHORT LIQUIDATION ANALYSIS")
print("="*70)

long_buys = pd.DataFrame(buy_logs.get('Long Liq Accumulator', []))
short_buys = pd.DataFrame(buy_logs.get('Short Liq Accumulator', []))

if len(long_buys) > 0 and len(short_buys) > 0:
    print(f"\nLong Liq Accumulator: {len(long_buys)} buys")
    print(f"Short Liq Accumulator: {len(short_buys)} buys")

    # Find overlapping days
    long_dates = set(long_buys['date'].dt.date)
    short_dates = set(short_buys['date'].dt.date)
    overlap = long_dates & short_dates

    print(f"\nOverlapping buy days: {len(overlap)} ({len(overlap)/max(len(long_dates), len(short_dates))*100:.1f}%)")
    print(f"Long-only days: {len(long_dates - short_dates)}")
    print(f"Short-only days: {len(short_dates - long_dates)}")

    # Daily liquidation stats
    print("\n--- Daily Liquidation Statistics ---")
    print(f"Days with Long Liq > $500k: {(daily_data['long_liquidations'] >= 500_000).sum()}")
    print(f"Days with Short Liq > $500k: {(daily_data['short_liquidations'] >= 500_000).sum()}")
    print(f"Days with BOTH > $500k: {((daily_data['long_liquidations'] >= 500_000) & (daily_data['short_liquidations'] >= 500_000)).sum()}")

    # Correlation
    print(f"\nCorrelation between daily long and short liquidations: {daily_data['long_liquidations'].corr(daily_data['short_liquidations']):.3f}")

    # Average liquidations on buy days
    print("\n--- Average Liquidations on Buy Days ---")
    print(f"Long Liq buys - Avg Long Liq: ${long_buys['long_liq'].mean():,.0f}")
    print(f"Long Liq buys - Avg Short Liq: ${long_buys['short_liq'].mean():,.0f}")
    print(f"Short Liq buys - Avg Long Liq: ${short_buys['long_liq'].mean():,.0f}")
    print(f"Short Liq buys - Avg Short Liq: ${short_buys['short_liq'].mean():,.0f}")

    # Price comparison
    print("\n--- Price Analysis ---")
    print(f"Long Liq - Avg buy price: ${long_buys['price'].mean():,.2f}")
    print(f"Short Liq - Avg buy price: ${short_buys['price'].mean():,.2f}")
    print(f"Difference: ${abs(long_buys['price'].mean() - short_buys['price'].mean()):,.2f}")

# =============================================================================
# CHARTS
# =============================================================================
print("\n" + "="*70)
print("GENERATING CHARTS")
print("="*70)

fig, axes = plt.subplots(4, 1, figsize=(16, 20))
fig.suptitle("Moon Dev's Liquidation Accumulation Analysis", fontsize=16, fontweight='bold')

# Chart 1: BTC Price with Buy Points
ax1 = axes[0]
ax1.plot(daily_data.index, daily_data['Close'], 'b-', alpha=0.7, label='BTC Price')

# Plot buy points for key strategies
colors = {'Long Liq Accumulator': 'green', 'Short Liq Accumulator': 'red',
          'WL + Double Down': 'purple', 'Daily DCA': 'gray'}

for strat, color in colors.items():
    if strat in buy_logs and len(buy_logs[strat]) > 0:
        buys = pd.DataFrame(buy_logs[strat])
        if strat == 'Daily DCA':
            continue  # Skip DCA - too many points
        ax1.scatter(buys['date'], buys['price'], c=color, s=30, alpha=0.6, label=f'{strat} buys')

ax1.set_title('BTC Price with Strategy Buy Points')
ax1.set_ylabel('Price ($)')
ax1.legend(loc='upper left')
ax1.grid(True, alpha=0.3)

# Chart 2: Daily Liquidations
ax2 = axes[1]
ax2.bar(daily_data.index, daily_data['long_liquidations']/1e6, alpha=0.7, label='Long Liquidations', color='red')
ax2.bar(daily_data.index, -daily_data['short_liquidations']/1e6, alpha=0.7, label='Short Liquidations', color='green')
ax2.axhline(y=0.5, color='red', linestyle='--', alpha=0.5, label='$500k threshold')
ax2.axhline(y=-0.5, color='green', linestyle='--', alpha=0.5)
ax2.set_title('Daily Liquidations (Long positive, Short negative)')
ax2.set_ylabel('Liquidations ($M)')
ax2.legend()
ax2.grid(True, alpha=0.3)

# Chart 3: Cumulative Coins Accumulated
ax3 = axes[2]
for strat in ['Long Liq Accumulator', 'Short Liq Accumulator', 'WL + Double Down']:
    if strat in buy_logs and len(buy_logs[strat]) > 0:
        buys = pd.DataFrame(buy_logs[strat])
        ax3.plot(buys['date'], buys['cumulative_coins'], label=strat, linewidth=2)

# Add DCA line
dca_cumulative = []
cumsum = 0
for idx, row in daily_data.iterrows():
    cumsum += dca_daily / row['Close']
    dca_cumulative.append({'date': idx, 'coins': cumsum})
dca_df = pd.DataFrame(dca_cumulative)
ax3.plot(dca_df['date'], dca_df['coins'], 'k--', label='Daily DCA', linewidth=2)

ax3.set_title('Cumulative BTC Accumulated Over Time')
ax3.set_ylabel('BTC')
ax3.legend()
ax3.grid(True, alpha=0.3)

# Chart 4: Strategy Comparison Bar Chart
ax4 = axes[3]
df_sorted = df_results.sort_values('vs_DCA_Pct', ascending=True)
colors_bar = ['green' if x > 0 else 'red' for x in df_sorted['vs_DCA_Pct']]
bars = ax4.barh(df_sorted['Strategy'], df_sorted['vs_DCA_Pct'], color=colors_bar, alpha=0.7)
ax4.axvline(x=0, color='black', linewidth=1)
ax4.set_xlabel('% vs DCA')
ax4.set_title('All Strategies Performance vs Daily DCA')
ax4.grid(True, alpha=0.3, axis='x')

# Add value labels
for bar, val in zip(bars, df_sorted['vs_DCA_Pct']):
    ax4.text(val + (1 if val >= 0 else -1), bar.get_y() + bar.get_height()/2,
             f'{val:+.1f}%', va='center', fontsize=9)

plt.tight_layout()
plt.savefig('/Users/md/Dropbox/dev/github/moon-dev-trading-bots/backtests/accumulation/liquidations/analysis_charts.png', dpi=150, bbox_inches='tight')
print("Charts saved to: analysis_charts.png")
plt.show()

# =============================================================================
# PRINT SAMPLE BUY LOGS
# =============================================================================
print("\n" + "="*70)
print("SAMPLE BUY LOGS - FIRST 10 BUYS")
print("="*70)

for strat in ['Long Liq Accumulator', 'Short Liq Accumulator', 'WL + Double Down']:
    if strat in buy_logs and len(buy_logs[strat]) > 0:
        print(f"\n--- {strat} ---")
        buys = pd.DataFrame(buy_logs[strat]).head(10)
        for _, b in buys.iterrows():
            print(f"  {b['date'].strftime('%Y-%m-%d')}: ${b['amount']:,.0f} @ ${b['price']:,.0f} = {b['coins']:.6f} BTC | Long: ${b['long_liq']:,.0f} | Short: ${b['short_liq']:,.0f}")

print("\n" + "="*70)
print("Moon Dev's Full Analysis Complete!")
print("="*70)
