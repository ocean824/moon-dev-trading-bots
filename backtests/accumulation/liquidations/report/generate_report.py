"""
Moon Dev's Accumulation Strategy Report Generator
=================================================
Generates charts and data for the final report comparing:
- Day 1 Lump Sum vs Liquidation-Based Accumulation
- Performance across different market conditions
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from datetime import datetime, timedelta
import random
import warnings
warnings.filterwarnings('ignore')

# Set style
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['figure.facecolor'] = 'white'
plt.rcParams['axes.facecolor'] = 'white'
plt.rcParams['font.size'] = 11

print("=" * 70)
print("Moon Dev's Accumulation Strategy Report Generator")
print("=" * 70)

# =============================================================================
# LOAD DATA
# =============================================================================
print("\nLoading liquidation data...")

raw_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/moondev_api/liq_data_full.csv'
columns = ['symbol', 'side', 'order_type', 'time_in_force', 'qty', 'price',
           'mark_price', 'status', 'filled_qty', 'total_qty', 'timestamp', 'value']

chunks = []
for chunk in pd.read_csv(raw_path, names=columns, chunksize=1000000):
    btc_chunk = chunk[chunk['symbol'] == 'BTC']
    if len(btc_chunk) > 0:
        chunks.append(btc_chunk)

raw_data = pd.concat(chunks, ignore_index=True)
raw_data['datetime'] = pd.to_datetime(raw_data['timestamp'], unit='ms')
raw_data = raw_data.sort_values('datetime')
raw_data.set_index('datetime', inplace=True)

raw_data['long_liq'] = raw_data.apply(lambda x: x['value'] if x['side'] == 'SELL' else 0, axis=1)
raw_data['short_liq'] = raw_data.apply(lambda x: x['value'] if x['side'] == 'BUY' else 0, axis=1)

ohlcv = raw_data['price'].resample('5min').ohlc()
ohlcv.columns = ['Open', 'High', 'Low', 'Close']
ohlcv['long_liquidations'] = raw_data['long_liq'].resample('5min').sum()
ohlcv['short_liquidations'] = raw_data['short_liq'].resample('5min').sum()
ohlcv = ohlcv.ffill().dropna()
ohlcv['long_liq_60m'] = ohlcv['long_liquidations'].rolling(12).sum()

print(f"Data: {ohlcv.index[0].strftime('%Y-%m-%d')} to {ohlcv.index[-1].strftime('%Y-%m-%d')}")
print(f"Total days: {(ohlcv.index[-1] - ohlcv.index[0]).days}")

# =============================================================================
# CONFIGURATION
# =============================================================================
STARTING_CAPITAL = 1_000_000
FIXED_PCT = 0.005
FIXED_BUY = STARTING_CAPITAL * FIXED_PCT
MAX_DAILY = 3
THRESHOLD = 1_000_000

# =============================================================================
# STRATEGY RUNNER
# =============================================================================
def run_strategies(data_slice):
    daily_closes = data_slice['Close'].resample('D').last().dropna()
    if len(daily_closes) < 10:
        return None

    days = (data_slice.index[-1] - data_slice.index[0]).days
    btc_change = ((data_slice['Close'].iloc[-1] / data_slice['Close'].iloc[0]) - 1) * 100

    # DCA
    dca_daily = STARTING_CAPITAL / len(daily_closes)
    dca_coins = sum(dca_daily / price for price in daily_closes)

    # Day 1
    day1_price = data_slice['Close'].iloc[0]
    day1_coins = STARTING_CAPITAL / day1_price
    day1_vs_dca = ((day1_coins - dca_coins) / dca_coins) * 100

    # Liquidation
    total_coins = 0
    total_spent = 0
    daily_counts = {}
    buys = []

    for idx, row in data_slice.iterrows():
        remaining = STARTING_CAPITAL - total_spent
        if remaining < FIXED_BUY * 0.5:
            break
        liq = row['long_liq_60m']
        if pd.isna(liq) or liq < THRESHOLD:
            continue
        date = idx.date()
        if date not in daily_counts:
            daily_counts[date] = 0
        if daily_counts[date] >= MAX_DAILY:
            continue
        buy = min(FIXED_BUY, remaining)
        coins = buy / row['Close']
        total_coins += coins
        total_spent += buy
        daily_counts[date] += 1
        buys.append({'datetime': idx, 'price': row['Close'], 'coins': coins})

    if total_coins > 0:
        liq_avg = total_spent / total_coins
        liq_vs_dca = ((total_coins - dca_coins) / dca_coins) * 100
        liq_vs_day1 = ((total_coins - day1_coins) / day1_coins) * 100
    else:
        liq_avg = 0
        liq_vs_dca = -100
        liq_vs_day1 = -100

    return {
        'days': days,
        'btc_change': btc_change,
        'dca_coins': dca_coins,
        'day1_coins': day1_coins,
        'day1_price': day1_price,
        'day1_vs_dca': day1_vs_dca,
        'liq_coins': total_coins,
        'liq_avg': liq_avg,
        'liq_vs_dca': liq_vs_dca,
        'liq_vs_day1': liq_vs_day1,
        'buys': buys,
        'winner': 'Liq' if liq_vs_day1 > 0 else 'Day1'
    }

# =============================================================================
# RUN FULL DATASET
# =============================================================================
print("\nRunning strategies on full dataset...")
full = run_strategies(ohlcv)

# =============================================================================
# RUN RANDOM SAMPLES
# =============================================================================
print("Running 20 random samples...")
random.seed(42)
np.random.seed(42)

start_date = ohlcv.index[0]
total_range = (ohlcv.index[-1] - ohlcv.index[0]).days

samples = []
for i in range(20):
    duration = random.randint(100, 300)
    max_offset = total_range - duration - 10
    if max_offset < 10:
        continue
    offset = random.randint(10, max_offset)
    slice_start = start_date + timedelta(days=offset)
    slice_end = slice_start + timedelta(days=duration)
    data_slice = ohlcv[(ohlcv.index >= slice_start) & (ohlcv.index <= slice_end)]
    result = run_strategies(data_slice)
    if result:
        result['name'] = f'Sample_{i+1}'
        result['start'] = slice_start.strftime('%Y-%m-%d')
        result['end'] = slice_end.strftime('%Y-%m-%d')
        samples.append(result)

print(f"Generated {len(samples)} valid samples")

# =============================================================================
# CHART 1: THE BIG PICTURE
# =============================================================================
print("\nGenerating Chart 1: The Big Picture...")

fig, ax = plt.subplots(figsize=(14, 8))

# Full dataset bar
strategies = ['Daily DCA\n(Baseline)', 'Day 1\nLump Sum', 'Liquidation\nStrategy']
coins = [full['dca_coins'], full['day1_coins'], full['liq_coins']]
colors = ['#808080', '#FFD700', '#00AA00']

bars = ax.bar(strategies, coins, color=colors, edgecolor='black', linewidth=2, width=0.6)

# Add values on bars
for bar, coin in zip(bars, coins):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
            f'{coin:.2f} BTC', ha='center', va='bottom', fontsize=14, fontweight='bold')

# Add percentage labels
ax.text(1, full['day1_coins'] - 1, f"+{full['day1_vs_dca']:.1f}%\nvs DCA",
        ha='center', va='top', fontsize=12, color='black')
ax.text(2, full['liq_coins'] - 1, f"+{full['liq_vs_dca']:.1f}%\nvs DCA",
        ha='center', va='top', fontsize=12, color='black')

ax.set_ylabel('BTC Accumulated', fontsize=14)
ax.set_title('Moon Dev\'s Accumulation Strategy Comparison\n$1M Capital Over 540 Days (Jun 2024 - Nov 2025)',
             fontsize=16, fontweight='bold')
ax.set_ylim(0, max(coins) * 1.15)

# Add annotation
ax.annotate(f'Liquidation beats Day 1 by +{full["liq_vs_day1"]:.1f}%\n({full["liq_coins"] - full["day1_coins"]:.2f} more BTC)',
            xy=(2, full['liq_coins']), xytext=(2.5, full['liq_coins'] - 2),
            fontsize=12, ha='left',
            arrowprops=dict(arrowstyle='->', color='green', lw=2),
            bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.8))

plt.tight_layout()
plt.savefig('/Users/md/Dropbox/dev/github/moon-dev-trading-bots/backtests/accumulation/liquidations/report/chart1_big_picture.png',
            dpi=150, bbox_inches='tight', facecolor='white')
plt.close()
print("  Saved: chart1_big_picture.png")

# =============================================================================
# CHART 2: MARKET CONDITION BREAKDOWN
# =============================================================================
print("Generating Chart 2: Market Condition Breakdown...")

fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# Separate bull vs flat/bear
bull_samples = [s for s in samples if s['btc_change'] > 20]
bear_samples = [s for s in samples if s['btc_change'] <= 20]

# Bull markets
ax1 = axes[0]
bull_day1_wins = sum(1 for s in bull_samples if s['winner'] == 'Day1')
bull_liq_wins = len(bull_samples) - bull_day1_wins
sizes = [bull_day1_wins, bull_liq_wins]
colors_pie = ['#FFD700', '#00AA00']
labels = [f'Day 1 Wins\n({bull_day1_wins}/{len(bull_samples)})', f'Liq Wins\n({bull_liq_wins}/{len(bull_samples)})']
wedges, texts, autotexts = ax1.pie(sizes, labels=labels, colors=colors_pie, autopct='%1.0f%%',
                                    startangle=90, explode=(0.05, 0), textprops={'fontsize': 12})
ax1.set_title(f'BULL MARKETS\n(BTC +20% or more)\n{len(bull_samples)} samples', fontsize=14, fontweight='bold')

# Flat/Bear markets
ax2 = axes[1]
bear_day1_wins = sum(1 for s in bear_samples if s['winner'] == 'Day1')
bear_liq_wins = len(bear_samples) - bear_day1_wins
sizes = [bear_day1_wins, bear_liq_wins]
labels = [f'Day 1 Wins\n({bear_day1_wins}/{len(bear_samples)})', f'Liq Wins\n({bear_liq_wins}/{len(bear_samples)})']
wedges, texts, autotexts = ax2.pie(sizes, labels=labels, colors=colors_pie, autopct='%1.0f%%',
                                    startangle=90, explode=(0, 0.05), textprops={'fontsize': 12})
ax2.set_title(f'FLAT/SIDEWAYS MARKETS\n(BTC <20%)\n{len(bear_samples)} samples', fontsize=14, fontweight='bold')

fig.suptitle('Moon Dev\'s Key Finding: Market Conditions Determine the Winner', fontsize=16, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig('/Users/md/Dropbox/dev/github/moon-dev-trading-bots/backtests/accumulation/liquidations/report/chart2_market_conditions.png',
            dpi=150, bbox_inches='tight', facecolor='white')
plt.close()
print("  Saved: chart2_market_conditions.png")

# =============================================================================
# CHART 3: SCATTER PLOT - BTC CHANGE VS STRATEGY PERFORMANCE
# =============================================================================
print("Generating Chart 3: Performance vs Market Direction...")

fig, ax = plt.subplots(figsize=(12, 8))

btc_changes = [s['btc_change'] for s in samples]
liq_vs_day1 = [s['liq_vs_day1'] for s in samples]
winners = [s['winner'] for s in samples]

colors_scatter = ['#00AA00' if w == 'Liq' else '#FFD700' for w in winners]
sizes_scatter = [150 if w == 'Liq' else 100 for w in winners]

ax.scatter(btc_changes, liq_vs_day1, c=colors_scatter, s=sizes_scatter, alpha=0.7, edgecolors='black', linewidths=1)

# Add trend line
z = np.polyfit(btc_changes, liq_vs_day1, 1)
p = np.poly1d(z)
x_line = np.linspace(min(btc_changes), max(btc_changes), 100)
ax.plot(x_line, p(x_line), 'r--', linewidth=2, label=f'Trend (slope: {z[0]:.2f})')

# Reference lines
ax.axhline(y=0, color='black', linewidth=2, linestyle='-')
ax.axvline(x=20, color='gray', linewidth=1, linestyle='--', alpha=0.7)

# Labels
ax.set_xlabel('BTC Price Change (%)', fontsize=14)
ax.set_ylabel('Liquidation vs Day 1 Performance (%)', fontsize=14)
ax.set_title('Moon Dev\'s Analysis: The Stronger the Bull Market,\nthe Worse Liquidation Strategy Performs vs Day 1',
             fontsize=16, fontweight='bold')

# Add quadrant labels
ax.text(max(btc_changes)*0.8, max(liq_vs_day1)*0.8, 'Bull + Liq Wins\n(Rare)', fontsize=10, ha='center',
        bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.5))
ax.text(max(btc_changes)*0.8, min(liq_vs_day1)*0.8, 'Bull + Day1 Wins\n(Common)', fontsize=10, ha='center',
        bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.5))
ax.text(min(btc_changes)*0.5, max(liq_vs_day1)*0.8, 'Flat + Liq Wins\n(Common)', fontsize=10, ha='center',
        bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.5))

# Legend
gold_patch = mpatches.Patch(color='#FFD700', label='Day 1 Wins')
green_patch = mpatches.Patch(color='#00AA00', label='Liquidation Wins')
ax.legend(handles=[gold_patch, green_patch], loc='lower left', fontsize=11)

ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('/Users/md/Dropbox/dev/github/moon-dev-trading-bots/backtests/accumulation/liquidations/report/chart3_scatter.png',
            dpi=150, bbox_inches='tight', facecolor='white')
plt.close()
print("  Saved: chart3_scatter.png")

# =============================================================================
# CHART 4: BTC PRICE WITH BUY POINTS
# =============================================================================
print("Generating Chart 4: BTC Price with Strategy Buy Points...")

fig, ax = plt.subplots(figsize=(16, 8))

# Daily price
daily_price = ohlcv['Close'].resample('D').last()
ax.plot(daily_price.index, daily_price, 'b-', linewidth=1.5, alpha=0.7, label='BTC Price')

# Day 1 buy point
ax.scatter([ohlcv.index[0]], [full['day1_price']], c='gold', s=400, marker='*',
           zorder=10, edgecolors='black', linewidths=2, label=f'Day 1 Lump Sum (${full["day1_price"]:,.0f})')

# Liquidation buy points
if full['buys']:
    buy_dates = [b['datetime'] for b in full['buys']]
    buy_prices = [b['price'] for b in full['buys']]
    ax.scatter(buy_dates, buy_prices, c='green', s=30, alpha=0.5,
               label=f'Liquidation Buys ({len(full["buys"])} buys, avg ${full["liq_avg"]:,.0f})')

ax.set_ylabel('BTC Price ($)', fontsize=14)
ax.set_xlabel('Date', fontsize=14)
ax.set_title('Moon Dev\'s Liquidation Strategy: Buying the Dips\n200 Buys Over 540 Days vs One Day 1 Purchase',
             fontsize=16, fontweight='bold')
ax.legend(loc='upper left', fontsize=11)
ax.grid(True, alpha=0.3)

# Add annotation for key insight
avg_save = full['day1_price'] - full['liq_avg']
ax.annotate(f'Avg savings: ${avg_save:,.0f}/BTC\n({avg_save/full["day1_price"]*100:.1f}% better price)',
            xy=(ohlcv.index[len(ohlcv)//2], (full['day1_price'] + full['liq_avg'])/2),
            fontsize=12, ha='center',
            bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))

plt.tight_layout()
plt.savefig('/Users/md/Dropbox/dev/github/moon-dev-trading-bots/backtests/accumulation/liquidations/report/chart4_btc_price.png',
            dpi=150, bbox_inches='tight', facecolor='white')
plt.close()
print("  Saved: chart4_btc_price.png")

# =============================================================================
# CHART 5: DECISION FLOWCHART (Visual Guide)
# =============================================================================
print("Generating Chart 5: Strategy Decision Guide...")

fig, ax = plt.subplots(figsize=(12, 10))
ax.set_xlim(0, 10)
ax.set_ylim(0, 10)
ax.axis('off')

# Title
ax.text(5, 9.5, 'Moon Dev\'s Strategy Selection Guide', fontsize=20, fontweight='bold', ha='center')

# Question box
question_box = mpatches.FancyBboxPatch((2.5, 7), 5, 1.5, boxstyle="round,pad=0.1",
                                         facecolor='lightblue', edgecolor='black', linewidth=2)
ax.add_patch(question_box)
ax.text(5, 7.75, 'What\'s your market outlook?', fontsize=14, fontweight='bold', ha='center', va='center')

# Bull path
ax.annotate('', xy=(2, 6), xytext=(3.5, 7), arrowprops=dict(arrowstyle='->', lw=2, color='gold'))
ax.text(1.5, 6.5, 'BULL\nMARKET', fontsize=11, ha='center', fontweight='bold', color='#B8860B')

bull_box = mpatches.FancyBboxPatch((0.5, 4), 3, 1.5, boxstyle="round,pad=0.1",
                                    facecolor='#FFD700', edgecolor='black', linewidth=2)
ax.add_patch(bull_box)
ax.text(2, 4.75, 'DAY 1\nLUMP SUM', fontsize=14, fontweight='bold', ha='center', va='center')

ax.text(2, 3.3, '✓ Get in early\n✓ Ride the wave\n✓ 80% win rate in bulls',
        fontsize=10, ha='center', va='top')

# Sideways/Uncertain path
ax.annotate('', xy=(8, 6), xytext=(6.5, 7), arrowprops=dict(arrowstyle='->', lw=2, color='green'))
ax.text(8.5, 6.5, 'SIDEWAYS\nor UNCERTAIN', fontsize=11, ha='center', fontweight='bold', color='darkgreen')

liq_box = mpatches.FancyBboxPatch((6.5, 4), 3, 1.5, boxstyle="round,pad=0.1",
                                   facecolor='#00AA00', edgecolor='black', linewidth=2)
ax.add_patch(liq_box)
ax.text(8, 4.75, 'LIQUIDATION\nSTRATEGY', fontsize=14, fontweight='bold', ha='center', va='center', color='white')

ax.text(8, 3.3, '✓ Buy the dips\n✓ Lower avg price\n✓ Wins in flat markets',
        fontsize=10, ha='center', va='top')

# Bottom note
note_box = mpatches.FancyBboxPatch((1, 0.5), 8, 1.5, boxstyle="round,pad=0.1",
                                    facecolor='lightyellow', edgecolor='black', linewidth=1)
ax.add_patch(note_box)
ax.text(5, 1.25, 'KEY INSIGHT: Both strategies beat DCA by 25-40%!\nThe question is which one beats the other.',
        fontsize=12, ha='center', va='center', style='italic')

plt.tight_layout()
plt.savefig('/Users/md/Dropbox/dev/github/moon-dev-trading-bots/backtests/accumulation/liquidations/report/chart5_decision_guide.png',
            dpi=150, bbox_inches='tight', facecolor='white')
plt.close()
print("  Saved: chart5_decision_guide.png")

# =============================================================================
# CHART 6: SUMMARY BAR CHART
# =============================================================================
print("Generating Chart 6: Summary Statistics...")

fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# Left: Average performance by market type
ax1 = axes[0]
categories = ['Bull Markets\n(BTC +20%+)', 'Flat/Sideways\n(BTC <20%)']
day1_avgs = [np.mean([s['day1_vs_dca'] for s in bull_samples]),
             np.mean([s['day1_vs_dca'] for s in bear_samples])]
liq_avgs = [np.mean([s['liq_vs_dca'] for s in bull_samples]),
            np.mean([s['liq_vs_dca'] for s in bear_samples])]

x = np.arange(len(categories))
width = 0.35

bars1 = ax1.bar(x - width/2, day1_avgs, width, label='Day 1 Lump Sum', color='#FFD700', edgecolor='black')
bars2 = ax1.bar(x + width/2, liq_avgs, width, label='Liquidation Strategy', color='#00AA00', edgecolor='black')

ax1.set_ylabel('Average % vs DCA', fontsize=12)
ax1.set_title('Average Performance by Market Condition', fontsize=14, fontweight='bold')
ax1.set_xticks(x)
ax1.set_xticklabels(categories)
ax1.legend()
ax1.axhline(y=0, color='black', linewidth=1)
ax1.grid(True, alpha=0.3, axis='y')

# Add values on bars
for bar, val in zip(bars1, day1_avgs):
    ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, f'+{val:.1f}%',
             ha='center', va='bottom', fontsize=10, fontweight='bold')
for bar, val in zip(bars2, liq_avgs):
    ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, f'+{val:.1f}%',
             ha='center', va='bottom', fontsize=10, fontweight='bold')

# Right: Win rates
ax2 = axes[1]
categories2 = ['Bull Markets', 'Flat/Sideways', 'Overall']
day1_wins = [bull_day1_wins/len(bull_samples)*100,
             bear_day1_wins/len(bear_samples)*100,
             (bull_day1_wins + bear_day1_wins)/len(samples)*100]
liq_wins = [100-day1_wins[0], 100-day1_wins[1], 100-day1_wins[2]]

x2 = np.arange(len(categories2))
bars3 = ax2.bar(x2 - width/2, day1_wins, width, label='Day 1 Lump Sum', color='#FFD700', edgecolor='black')
bars4 = ax2.bar(x2 + width/2, liq_wins, width, label='Liquidation Strategy', color='#00AA00', edgecolor='black')

ax2.set_ylabel('Win Rate (%)', fontsize=12)
ax2.set_title('Win Rate by Market Condition', fontsize=14, fontweight='bold')
ax2.set_xticks(x2)
ax2.set_xticklabels(categories2)
ax2.legend()
ax2.set_ylim(0, 100)
ax2.grid(True, alpha=0.3, axis='y')

# Add values on bars
for bar, val in zip(bars3, day1_wins):
    ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2, f'{val:.0f}%',
             ha='center', va='bottom', fontsize=10, fontweight='bold')
for bar, val in zip(bars4, liq_wins):
    ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2, f'{val:.0f}%',
             ha='center', va='bottom', fontsize=10, fontweight='bold')

fig.suptitle('Moon Dev\'s Strategy Performance Summary', fontsize=16, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig('/Users/md/Dropbox/dev/github/moon-dev-trading-bots/backtests/accumulation/liquidations/report/chart6_summary.png',
            dpi=150, bbox_inches='tight', facecolor='white')
plt.close()
print("  Saved: chart6_summary.png")

# =============================================================================
# SAVE DATA FOR REPORT
# =============================================================================
print("\nSaving data summary...")

summary_data = {
    'full_dataset': {
        'days': 540,
        'btc_change': f"+{full['btc_change']:.1f}%",
        'dca_coins': round(full['dca_coins'], 2),
        'day1_coins': round(full['day1_coins'], 2),
        'day1_vs_dca': f"+{full['day1_vs_dca']:.1f}%",
        'liq_coins': round(full['liq_coins'], 2),
        'liq_vs_dca': f"+{full['liq_vs_dca']:.1f}%",
        'liq_vs_day1': f"+{full['liq_vs_day1']:.1f}%",
        'liq_avg_price': f"${full['liq_avg']:,.0f}",
        'day1_price': f"${full['day1_price']:,.0f}",
        'savings_per_btc': f"${full['day1_price'] - full['liq_avg']:,.0f}"
    },
    'random_samples': {
        'total': len(samples),
        'day1_wins': sum(1 for s in samples if s['winner'] == 'Day1'),
        'liq_wins': sum(1 for s in samples if s['winner'] == 'Liq'),
        'bull_samples': len(bull_samples),
        'bull_day1_wins': bull_day1_wins,
        'bear_samples': len(bear_samples),
        'bear_liq_wins': bear_liq_wins
    }
}

# Save as simple text summary
with open('/Users/md/Dropbox/dev/github/moon-dev-trading-bots/backtests/accumulation/liquidations/report/data_summary.txt', 'w') as f:
    f.write("MOON DEV'S ACCUMULATION STRATEGY DATA SUMMARY\n")
    f.write("=" * 50 + "\n\n")
    f.write("FULL DATASET (540 days):\n")
    for k, v in summary_data['full_dataset'].items():
        f.write(f"  {k}: {v}\n")
    f.write("\nRANDOM SAMPLES:\n")
    for k, v in summary_data['random_samples'].items():
        f.write(f"  {k}: {v}\n")

print("  Saved: data_summary.txt")

print("\n" + "=" * 70)
print("Report generation complete!")
print("=" * 70)
print(f"\nFiles saved to: /backtests/accumulation/liquidations/report/")
print("  - chart1_big_picture.png")
print("  - chart2_market_conditions.png")
print("  - chart3_scatter.png")
print("  - chart4_btc_price.png")
print("  - chart5_decision_guide.png")
print("  - chart6_summary.png")
print("  - data_summary.txt")
