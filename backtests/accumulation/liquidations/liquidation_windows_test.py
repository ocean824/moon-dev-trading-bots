"""
Moon Dev's Liquidation Window Testing
=====================================
Testing liquidation accumulation with PROPER time windows

Tests:
- $1M threshold sweet spot
- Compare fixed allocation sizes: 0.5%, 1%, 2%
- Compare against Day 1 Lump Sum
- Track when capital runs out!

This uses the RAW 5-minute data, not daily aggregates!
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import timedelta
import warnings
warnings.filterwarnings('ignore')

print("=" * 70)
print("Moon Dev's Liquidation Window Testing")
print("Using PROPER time windows (not daily aggregates)")
print("=" * 70)

# =============================================================================
# LOAD RAW 5-MINUTE DATA
# =============================================================================
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/moondev_api/liq_data_BTC_5m_ohlcv.csv'
print(f"\nLoading 5-minute data: {data_path}")

data = pd.read_csv(data_path, parse_dates=['datetime'], index_col='datetime')
data = data.sort_index()

print(f"Total 5-min bars: {len(data):,}")
print(f"Date range: {data.index[0]} to {data.index[-1]}")

first_price = data['Close'].iloc[0]
last_price = data['Close'].iloc[-1]
total_days = (data.index[-1] - data.index[0]).days

print(f"BTC: ${first_price:,.2f} -> ${last_price:,.2f} ({((last_price/first_price)-1)*100:+.1f}%)")
print(f"Total days: {total_days}")

# =============================================================================
# CREATE 60-MINUTE ROLLING SUMS
# =============================================================================
print("\nCalculating 60-minute rolling liquidation sums...")

# 60 minutes = 12 x 5-minute bars
data['long_liq_60m'] = data['long_liquidations'].rolling(12).sum()
data['short_liq_60m'] = data['short_liquidations'].rolling(12).sum()
data['total_liq_60m'] = data['total_liquidations'].rolling(12).sum()

# =============================================================================
# CONFIGURATION
# =============================================================================
STARTING_CAPITAL = 1_000_000

# Fixed allocation sizes to test
FIXED_ALLOCATIONS = {
    '0.5%': 0.005,   # $5,000 per buy (200 buys max)
    '1%': 0.01,      # $10,000 per buy (100 buys max)
    '2%': 0.02,      # $20,000 per buy (50 buys max)
}

results = []
buy_logs = {}

# =============================================================================
# BASELINE: Daily DCA
# =============================================================================
print("\n" + "="*70)
print("CALCULATING BASELINE (Daily DCA)")
print("="*70)

# Get daily closes for DCA
daily_closes = data['Close'].resample('D').last().dropna()
dca_daily_amount = STARTING_CAPITAL / len(daily_closes)
dca_coins = sum(dca_daily_amount / price for price in daily_closes)
dca_avg_price = STARTING_CAPITAL / dca_coins

results.append({
    'Strategy': 'Daily DCA',
    'Window': '-',
    'Threshold': '-',
    'Liq_Type': '-',
    'Max_Daily': '-',
    'Allocation': '-',
    'Coins': dca_coins,
    'Avg_Price': dca_avg_price,
    'Buy_Count': len(daily_closes),
    'Total_Spent': STARTING_CAPITAL,
    'vs_DCA_Pct': 0.0,
    'Signals_Found': len(daily_closes)
})

print(f"Daily DCA: {dca_coins:.4f} BTC @ ${dca_avg_price:,.2f} avg")

# =============================================================================
# LIQUIDATION STRATEGY RUNNER
# =============================================================================
def run_liq_strategy(name, data, window, threshold, liq_type, max_daily, fixed_pct=0.005):
    """
    Run a liquidation accumulation strategy with FIXED allocation

    Args:
        name: Strategy name
        data: 5-minute dataframe
        window: '5m' or '60m'
        threshold: Dollar threshold for liquidations
        liq_type: 'long', 'short', or 'total'
        max_daily: Max buys per day (1, 2, 3, 4, 5)
        fixed_pct: Fixed percentage of starting capital per buy
    """
    # Select the right column based on window and type
    if window == '5m':
        if liq_type == 'long':
            liq_col = 'long_liquidations'
        elif liq_type == 'short':
            liq_col = 'short_liquidations'
        else:
            liq_col = 'total_liquidations'
    else:  # 60m
        if liq_type == 'long':
            liq_col = 'long_liq_60m'
        elif liq_type == 'short':
            liq_col = 'short_liq_60m'
        else:
            liq_col = 'total_liq_60m'

    total_coins = 0
    total_spent = 0
    buy_count = 0
    buys = []
    capital_depleted_date = None

    # Track buys per day
    daily_buy_counts = {}
    signals_found = 0

    # Fixed buy amount
    fixed_buy_amount = STARTING_CAPITAL * fixed_pct

    for idx, row in data.iterrows():
        remaining = STARTING_CAPITAL - total_spent
        if remaining < fixed_buy_amount * 0.5:  # Less than half a buy left
            if capital_depleted_date is None:
                capital_depleted_date = idx
            break

        liq_value = row[liq_col]
        if pd.isna(liq_value):
            continue

        # Check if liquidation exceeds threshold
        if liq_value >= threshold:
            signals_found += 1
            current_date = idx.date()

            # Check daily buy limit
            if current_date not in daily_buy_counts:
                daily_buy_counts[current_date] = 0

            if daily_buy_counts[current_date] >= max_daily:
                continue

            # Calculate buy amount
            buy_amount = min(fixed_buy_amount, remaining)

            coins = buy_amount / row['Close']
            total_coins += coins
            total_spent += buy_amount
            buy_count += 1
            daily_buy_counts[current_date] += 1

            buys.append({
                'datetime': idx,
                'price': row['Close'],
                'amount': buy_amount,
                'coins': coins,
                'liq_value': liq_value,
                'long_liq': row['long_liquidations'],
                'short_liq': row['short_liquidations']
            })

    buy_logs[name] = buys

    # Calculate days until capital depleted
    if buys:
        first_buy_date = buys[0]['datetime']
        last_buy_date = buys[-1]['datetime']
        days_active = (last_buy_date - first_buy_date).days
    else:
        days_active = 0

    if total_coins > 0:
        avg_price = total_spent / total_coins
        vs_dca = ((total_coins - dca_coins) / dca_coins) * 100
    else:
        avg_price = 0
        vs_dca = -100

    return {
        'Strategy': name,
        'Fixed_Pct': f'{fixed_pct*100:.1f}%',
        'Buy_Size': f'${fixed_buy_amount:,.0f}',
        'Liq_Type': liq_type,
        'Max_Daily': max_daily,
        'Coins': total_coins,
        'Avg_Price': avg_price,
        'Buy_Count': buy_count,
        'Total_Spent': total_spent,
        'Days_Active': days_active,
        'First_Buy': buys[0]['datetime'].strftime('%Y-%m-%d') if buys else '-',
        'Last_Buy': buys[-1]['datetime'].strftime('%Y-%m-%d') if buys else '-',
        'vs_DCA_Pct': vs_dca,
        'Signals_Found': signals_found
    }

# =============================================================================
# RUN ALL TEST COMBINATIONS
# =============================================================================
print("\n" + "="*70)
print("RUNNING ALL TEST COMBINATIONS - $1M THRESHOLD SWEET SPOT")
print("="*70)

# =============================================================================
# BASELINE: DAY 1 LUMP SUM
# =============================================================================
print("\n" + "="*70)
print("BASELINE: DAY 1 LUMP SUM (Buy everything on first day)")
print("="*70)

day1_price = data['Close'].iloc[0]
day1_coins = STARTING_CAPITAL / day1_price
day1_vs_dca = ((day1_coins - dca_coins) / dca_coins) * 100

results.append({
    'Strategy': 'Day1_LumpSum',
    'Fixed_Pct': '100%',
    'Buy_Size': '$1,000,000',
    'Liq_Type': '-',
    'Max_Daily': '-',
    'Coins': day1_coins,
    'Avg_Price': day1_price,
    'Buy_Count': 1,
    'Total_Spent': STARTING_CAPITAL,
    'Days_Active': 0,
    'First_Buy': data.index[0].strftime('%Y-%m-%d'),
    'Last_Buy': data.index[0].strftime('%Y-%m-%d'),
    'vs_DCA_Pct': day1_vs_dca,
    'Signals_Found': 1
})

print(f"Day 1 Lump Sum: {day1_coins:.4f} BTC @ ${day1_price:,.2f}")
print(f"  vs DCA: {day1_vs_dca:+.1f}%")
print(f"  Date: {data.index[0].strftime('%Y-%m-%d')}")

# =============================================================================
# TEST FIXED ALLOCATIONS: 0.5%, 1%, 2%
# =============================================================================
for alloc_name, alloc_pct in FIXED_ALLOCATIONS.items():
    buy_size = STARTING_CAPITAL * alloc_pct
    max_buys = int(STARTING_CAPITAL / buy_size)

    print(f"\n" + "="*70)
    print(f"FIXED {alloc_name} = ${buy_size:,.0f} per buy ({max_buys} buys max)")
    print("="*70)

    for liq_type in ['long', 'short']:
        print(f"\n--- {liq_type.upper()} Liquidations ---")
        for max_daily in [1, 2, 3, 4, 5]:
            name = f"FIX_{alloc_name}_{liq_type}_{max_daily}x"
            result = run_liq_strategy(name, data, '60m', 1_000_000, liq_type, max_daily, alloc_pct)
            results.append(result)
            emoji = "+" if result['vs_DCA_Pct'] > 0 else ""
            print(f"  {max_daily}x/day: {emoji}{result['vs_DCA_Pct']:>6.1f}% vs DCA | {result['Coins']:.4f} BTC | {result['Buy_Count']:>3} buys | {result['Days_Active']:>3} days | {result['First_Buy']} -> {result['Last_Buy']}")

# =============================================================================
# RESULTS SUMMARY
# =============================================================================
df = pd.DataFrame(results)
df = df.sort_values('vs_DCA_Pct', ascending=False)

print("\n" + "="*100)
print("FULL RESULTS - SORTED BY PERFORMANCE")
print("="*100)

print(f"\n{'Strategy':<25} {'Buy Size':>10} {'Type':>6} {'Daily':>6} {'vs DCA':>9} {'Coins':>10} {'Buys':>5} {'Days':>5} {'Last Buy':>12}")
print("-" * 100)

for _, row in df.iterrows():
    print(f"{row['Strategy']:<25} {row['Buy_Size']:>10} {row['Liq_Type']:>6} {str(row['Max_Daily']):>6} {row['vs_DCA_Pct']:>+8.1f}% {row['Coins']:>10.4f} {row['Buy_Count']:>5} {row['Days_Active']:>5} {row['Last_Buy']:>12}")

# Save results
output_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/backtests/accumulation/liquidations/window_test_results.csv'
df.to_csv(output_path, index=False)
print(f"\nResults saved to: {output_path}")

# =============================================================================
# ANALYSIS BY CATEGORY
# =============================================================================
print("\n" + "="*70)
print("ANALYSIS BY ALLOCATION SIZE")
print("="*70)

# Best by allocation size
print("\n--- Best Strategy per Allocation Size ---")
for alloc_name in ['0.5%', '1%', '2%']:
    alloc_df = df[df['Fixed_Pct'] == alloc_name]
    if len(alloc_df) > 0:
        best = alloc_df.iloc[0]
        print(f"{alloc_name} ({best['Buy_Size']}): {best['Strategy']} ({best['vs_DCA_Pct']:+.1f}%) - {best['Days_Active']} days active")

# Compare baselines
print("\n" + "="*70)
print("KEY COMPARISON: Day 1 Lump Sum vs Best Liquidation Strategies")
print("="*70)

day1_row = df[df['Strategy'] == 'Day1_LumpSum'].iloc[0]
dca_row = df[df['Strategy'] == 'Daily DCA'].iloc[0]
best_strat = df.iloc[0]

print(f"\n{'Strategy':<30} {'vs DCA':>10} {'Coins':>12} {'Avg Price':>12} {'Days':>8}")
print("-" * 80)
print(f"{'Day 1 Lump Sum':<30} {day1_row['vs_DCA_Pct']:>+9.1f}% {day1_row['Coins']:>12.4f} ${day1_row['Avg_Price']:>10,.0f} {day1_row['Days_Active']:>8}")
print(f"{'Daily DCA':<30} {dca_row['vs_DCA_Pct']:>+9.1f}% {dca_row['Coins']:>12.4f} ${dca_row['Avg_Price']:>10,.0f} {'-':>8}")
print(f"{best_strat['Strategy']:<30} {best_strat['vs_DCA_Pct']:>+9.1f}% {best_strat['Coins']:>12.4f} ${best_strat['Avg_Price']:>10,.0f} {best_strat['Days_Active']:>8}")

# Summary table by allocation size
print("\n" + "="*70)
print("COMPARISON BY ALLOCATION SIZE (Best 3x Daily for each)")
print("="*70)

for alloc_name in ['0.5%', '1%', '2%']:
    alloc_df = df[(df['Fixed_Pct'] == alloc_name) & (df['Max_Daily'] == 3)]
    if len(alloc_df) > 0:
        print(f"\n--- {alloc_name} Fixed Allocation (3x daily) ---")
        for _, row in alloc_df.iterrows():
            print(f"  {row['Liq_Type']:>5}: {row['vs_DCA_Pct']:>+6.1f}% | {row['Coins']:.4f} BTC | {row['Buy_Count']:>3} buys | {row['Days_Active']:>3} days | ends {row['Last_Buy']}")

# =============================================================================
# SIGNAL ANALYSIS
# =============================================================================
print("\n" + "="*70)
print("SIGNAL FREQUENCY ANALYSIS")
print("="*70)

print("\n--- 60-Minute Window Signal Counts at $1M Threshold ---")
long_signals = (data['long_liq_60m'] >= 1_000_000).sum()
short_signals = (data['short_liq_60m'] >= 1_000_000).sum()
print(f"$1M threshold: Long={long_signals:,} signals, Short={short_signals:,} signals")
print(f"Total days in dataset: {total_days}")
print(f"Avg signals per day: Long={long_signals/total_days:.1f}, Short={short_signals/total_days:.1f}")

# =============================================================================
# TOP 5 STRATEGIES DETAIL
# =============================================================================
print("\n" + "="*70)
print("TOP 5 STRATEGIES - DETAILED")
print("="*70)

top5 = df.head(6)  # Include DCA
for _, row in top5.iterrows():
    print(f"\n{row['Strategy']}")
    print(f"  vs DCA: {row['vs_DCA_Pct']:+.1f}%")
    print(f"  Coins: {row['Coins']:.4f} BTC")
    print(f"  Avg Price: ${row['Avg_Price']:,.2f}")
    print(f"  Buy Count: {row['Buy_Count']}")
    print(f"  Signals Found: {row['Signals_Found']}")

# =============================================================================
# SAMPLE BUY LOGS FOR TOP STRATEGIES
# =============================================================================
print("\n" + "="*70)
print("SAMPLE BUY LOGS - TOP LONG LIQ STRATEGY")
print("="*70)

# Find best long strategy
long_df = df[df['Liq_Type'] == 'long']
if len(long_df) > 0:
    best_long = long_df.iloc[0]['Strategy']
    if best_long in buy_logs and len(buy_logs[best_long]) > 0:
        print(f"\n--- {best_long} (First 15 buys) ---")
        for buy in buy_logs[best_long][:15]:
            print(f"  {buy['datetime']}: ${buy['amount']:,.0f} @ ${buy['price']:,.0f} = {buy['coins']:.6f} BTC | Liq: ${buy['liq_value']:,.0f}")

# =============================================================================
# CHARTS
# =============================================================================
print("\n" + "="*70)
print("GENERATING CHARTS")
print("="*70)

fig, axes = plt.subplots(2, 2, figsize=(16, 12))
fig.suptitle("Moon Dev's Liquidation Accumulation: Fixed Allocation Comparison", fontsize=16, fontweight='bold')

# Chart 1: All strategies ranked
ax1 = axes[0, 0]
plot_df = df[~df['Strategy'].isin(['Daily DCA'])].head(15)
colors = ['gold' if 'Day1' in str(x) else ('green' if y > 0 else 'red') for x, y in zip(plot_df['Strategy'], plot_df['vs_DCA_Pct'])]
ax1.barh(range(len(plot_df)), plot_df['vs_DCA_Pct'], color=colors, alpha=0.7)
ax1.set_yticks(range(len(plot_df)))
ax1.set_yticklabels(plot_df['Strategy'], fontsize=8)
ax1.axvline(x=0, color='black', linewidth=1)
ax1.axvline(x=day1_vs_dca, color='gold', linewidth=2, linestyle='--', label=f'Day 1 Lump Sum ({day1_vs_dca:+.1f}%)')
ax1.set_xlabel('% vs DCA')
ax1.set_title('All Strategies vs DCA (Gold = Day 1 Lump Sum)')
ax1.legend(loc='lower right')
ax1.grid(True, alpha=0.3, axis='x')
ax1.invert_yaxis()

# Chart 2: Comparison by allocation size (3x daily, short liq)
ax2 = axes[0, 1]
alloc_labels = ['0.5%\n($5k)', '1%\n($10k)', '2%\n($20k)']
alloc_coins = []
alloc_days = []
for alloc in ['0.5%', '1%', '2%']:
    row = df[(df['Fixed_Pct'] == alloc) & (df['Max_Daily'] == 3) & (df['Liq_Type'] == 'short')]
    if len(row) > 0:
        alloc_coins.append(row.iloc[0]['Coins'])
        alloc_days.append(row.iloc[0]['Days_Active'])
    else:
        alloc_coins.append(0)
        alloc_days.append(0)

x = range(len(alloc_labels))
bars = ax2.bar(x, alloc_coins, color=['blue', 'green', 'orange'], alpha=0.7)
ax2.axhline(y=dca_coins, color='red', linestyle='--', linewidth=2, label=f'DCA ({dca_coins:.2f} BTC)')
ax2.axhline(y=day1_coins, color='gold', linestyle='--', linewidth=2, label=f'Day 1 ({day1_coins:.2f} BTC)')
ax2.set_xticks(x)
ax2.set_xticklabels(alloc_labels)
ax2.set_ylabel('BTC Accumulated')
ax2.set_title('Short Liq 3x Daily: Coins by Allocation Size')
ax2.legend()
ax2.grid(True, alpha=0.3, axis='y')

# Add days labels on bars
for i, (coins, days) in enumerate(zip(alloc_coins, alloc_days)):
    ax2.text(i, coins + 0.2, f'{days}d', ha='center', fontsize=10, fontweight='bold')

# Chart 3: Timeline - when does capital run out?
ax3 = axes[1, 0]
daily_price = data['Close'].resample('D').last()
ax3.plot(daily_price.index, daily_price, 'b-', alpha=0.5, label='BTC Price', linewidth=1)

# Plot end points for each allocation
colors_alloc = {'0.5%': 'blue', '1%': 'green', '2%': 'orange'}
for alloc in ['0.5%', '1%', '2%']:
    row = df[(df['Fixed_Pct'] == alloc) & (df['Max_Daily'] == 3) & (df['Liq_Type'] == 'short')]
    if len(row) > 0:
        strat_name = row.iloc[0]['Strategy']
        if strat_name in buy_logs and len(buy_logs[strat_name]) > 0:
            last_buy = buy_logs[strat_name][-1]
            ax3.axvline(x=last_buy['datetime'], color=colors_alloc[alloc], linestyle='--', linewidth=2,
                       label=f'{alloc} depleted ({row.iloc[0]["Days_Active"]}d)')
            ax3.scatter([last_buy['datetime']], [last_buy['price']], c=colors_alloc[alloc], s=100, zorder=5, marker='X')

ax3.set_ylabel('BTC Price ($)')
ax3.set_title('When Does Capital Run Out? (3x Daily, Short Liq)')
ax3.legend(loc='upper left', fontsize=9)
ax3.grid(True, alpha=0.3)

# Chart 4: BTC price with buy points for best strategy
ax4 = axes[1, 1]
ax4.plot(daily_price.index, daily_price, 'b-', alpha=0.5, label='BTC Price', linewidth=1)

# Plot Day 1 lump sum
ax4.scatter([data.index[0]], [day1_price], c='gold', s=200, marker='*', zorder=10, label=f'Day 1 Lump Sum (${day1_price:,.0f})')

# Plot best strategy buys
best_strat_name = df.iloc[0]['Strategy']
if best_strat_name in buy_logs and len(buy_logs[best_strat_name]) > 0:
    buys_df = pd.DataFrame(buy_logs[best_strat_name])
    ax4.scatter(buys_df['datetime'], buys_df['price'], c='green', s=30, alpha=0.6,
                label=f'{best_strat_name} ({len(buys_df)} buys, avg ${df.iloc[0]["Avg_Price"]:,.0f})', zorder=5)

ax4.set_ylabel('Price ($)')
ax4.set_title(f'Best Strategy: {best_strat_name}')
ax4.legend(loc='upper left', fontsize=9)
ax4.grid(True, alpha=0.3)

plt.tight_layout()
chart_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/backtests/accumulation/liquidations/window_analysis_charts.png'
plt.savefig(chart_path, dpi=150, bbox_inches='tight')
print(f"Charts saved to: {chart_path}")
plt.show()

print("\n" + "="*70)
print("Moon Dev's Liquidation Window Analysis Complete!")
print("="*70)
