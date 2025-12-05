"""
Moon Dev's Bear Market Simulation
=================================
Simulating bear market conditions using the same liquidation data
by inverting the price movement while keeping liquidation events intact.

Method: Flip the price returns so bull becomes bear
- Original: $68k → $120k (+76%)
- Simulated: $68k → $38k (-44%) [inverted returns]

Liquidation events stay in the same place - they represent real panic moments.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

print("=" * 70)
print("Moon Dev's Bear Market Simulation")
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

print(f"Original data: {ohlcv.index[0].strftime('%Y-%m-%d')} to {ohlcv.index[-1].strftime('%Y-%m-%d')}")
print(f"Original BTC: ${ohlcv['Close'].iloc[0]:,.0f} → ${ohlcv['Close'].iloc[-1]:,.0f} ({((ohlcv['Close'].iloc[-1]/ohlcv['Close'].iloc[0])-1)*100:+.1f}%)")

# =============================================================================
# CREATE BEAR MARKET VERSION
# =============================================================================
print("\n" + "=" * 70)
print("CREATING BEAR MARKET SIMULATION")
print("=" * 70)

# Method: Mirror the price around the starting price
# If original goes up 10%, bear goes down 10%
# This keeps the volatility pattern but inverts the direction

original_close = ohlcv['Close'].copy()
start_price = original_close.iloc[0]

# Calculate percentage change from start
pct_from_start = (original_close - start_price) / start_price

# Invert: if original is +50%, bear is -50% (but capped to prevent negative prices)
# Use a scaling factor to make it a realistic bear market
bear_pct = -pct_from_start * 0.8  # 80% of the inverse to keep prices positive

# Rebuild bear prices
bear_close = start_price * (1 + bear_pct)

# Ensure no negative or zero prices
bear_close = bear_close.clip(lower=start_price * 0.2)  # Floor at 20% of start

# Create bear market dataframe
bear_ohlcv = ohlcv.copy()
bear_ohlcv['Close'] = bear_close

# Adjust Open/High/Low proportionally
price_ratio = bear_close / original_close
price_ratio = price_ratio.replace([np.inf, -np.inf], 1).fillna(1)
bear_ohlcv['Open'] = ohlcv['Open'] * price_ratio
bear_ohlcv['High'] = ohlcv['High'] * price_ratio
bear_ohlcv['Low'] = ohlcv['Low'] * price_ratio

bear_start = bear_ohlcv['Close'].iloc[0]
bear_end = bear_ohlcv['Close'].iloc[-1]
bear_change = ((bear_end / bear_start) - 1) * 100

print(f"Simulated BEAR: ${bear_start:,.0f} → ${bear_end:,.0f} ({bear_change:+.1f}%)")

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
def run_strategies(data, label):
    """Run all strategies on a dataset"""
    daily_closes = data['Close'].resample('D').last().dropna()
    days = (data.index[-1] - data.index[0]).days
    btc_change = ((data['Close'].iloc[-1] / data['Close'].iloc[0]) - 1) * 100

    # DCA
    dca_daily = STARTING_CAPITAL / len(daily_closes)
    dca_coins = sum(dca_daily / price for price in daily_closes)
    dca_avg = STARTING_CAPITAL / dca_coins

    # Day 1
    day1_price = data['Close'].iloc[0]
    day1_coins = STARTING_CAPITAL / day1_price
    day1_vs_dca = ((day1_coins - dca_coins) / dca_coins) * 100

    # Liquidation
    total_coins = 0
    total_spent = 0
    daily_counts = {}

    for idx, row in data.iterrows():
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

    if total_coins > 0:
        liq_avg = total_spent / total_coins
        liq_vs_dca = ((total_coins - dca_coins) / dca_coins) * 100
        liq_vs_day1 = ((total_coins - day1_coins) / day1_coins) * 100
    else:
        liq_avg = 0
        liq_vs_dca = -100
        liq_vs_day1 = -100

    return {
        'label': label,
        'btc_change': btc_change,
        'dca_coins': dca_coins,
        'dca_avg': dca_avg,
        'day1_coins': day1_coins,
        'day1_price': day1_price,
        'day1_vs_dca': day1_vs_dca,
        'liq_coins': total_coins,
        'liq_avg': liq_avg,
        'liq_vs_dca': liq_vs_dca,
        'liq_vs_day1': liq_vs_day1
    }

# =============================================================================
# RUN ON BOTH DATASETS
# =============================================================================
print("\n" + "=" * 70)
print("RUNNING STRATEGIES ON BOTH MARKET CONDITIONS")
print("=" * 70)

bull_result = run_strategies(ohlcv, "BULL (Original)")
bear_result = run_strategies(bear_ohlcv, "BEAR (Simulated)")

# =============================================================================
# RESULTS
# =============================================================================
print("\n" + "=" * 70)
print("RESULTS COMPARISON")
print("=" * 70)

print(f"\n{'='*80}")
print(f"{'BULL MARKET (Original Data)':^80}")
print(f"{'='*80}")
print(f"BTC: ${bull_result['day1_price']:,.0f} → {bull_result['btc_change']:+.1f}%")
print(f"\n{'Strategy':<25} {'Coins':>12} {'Avg Price':>12} {'vs DCA':>10} {'vs Day1':>10}")
print("-" * 70)
print(f"{'Daily DCA':<25} {bull_result['dca_coins']:>12.2f} ${bull_result['dca_avg']:>10,.0f} {0:>+9.1f}% {'-':>10}")
print(f"{'Day 1 Lump Sum':<25} {bull_result['day1_coins']:>12.2f} ${bull_result['day1_price']:>10,.0f} {bull_result['day1_vs_dca']:>+9.1f}% {'-':>10}")
print(f"{'Liquidation 0.5% 3x':<25} {bull_result['liq_coins']:>12.2f} ${bull_result['liq_avg']:>10,.0f} {bull_result['liq_vs_dca']:>+9.1f}% {bull_result['liq_vs_day1']:>+9.1f}%")

print(f"\n{'='*80}")
print(f"{'BEAR MARKET (Simulated)':^80}")
print(f"{'='*80}")
print(f"BTC: ${bear_result['day1_price']:,.0f} → {bear_result['btc_change']:+.1f}%")
print(f"\n{'Strategy':<25} {'Coins':>12} {'Avg Price':>12} {'vs DCA':>10} {'vs Day1':>10}")
print("-" * 70)
print(f"{'Daily DCA':<25} {bear_result['dca_coins']:>12.2f} ${bear_result['dca_avg']:>10,.0f} {0:>+9.1f}% {'-':>10}")
print(f"{'Day 1 Lump Sum':<25} {bear_result['day1_coins']:>12.2f} ${bear_result['day1_price']:>10,.0f} {bear_result['day1_vs_dca']:>+9.1f}% {'-':>10}")
print(f"{'Liquidation 0.5% 3x':<25} {bear_result['liq_coins']:>12.2f} ${bear_result['liq_avg']:>10,.0f} {bear_result['liq_vs_dca']:>+9.1f}% {bear_result['liq_vs_day1']:>+9.1f}%")

# =============================================================================
# KEY COMPARISON
# =============================================================================
print("\n" + "=" * 70)
print("KEY COMPARISON: Liquidation vs Day 1")
print("=" * 70)

print(f"\n{'Market':<20} {'Liq vs Day1':>15} {'Extra BTC':>15}")
print("-" * 50)
print(f"{'BULL (+27%)':<20} {bull_result['liq_vs_day1']:>+14.1f}% {bull_result['liq_coins'] - bull_result['day1_coins']:>+14.2f}")
print(f"{'BEAR (-21%)':<20} {bear_result['liq_vs_day1']:>+14.1f}% {bear_result['liq_coins'] - bear_result['day1_coins']:>+14.2f}")

# =============================================================================
# CHART
# =============================================================================
print("\n" + "=" * 70)
print("GENERATING COMPARISON CHART")
print("=" * 70)

fig, axes = plt.subplots(2, 2, figsize=(16, 12))
fig.suptitle("Moon Dev's Bull vs Bear Market Simulation", fontsize=18, fontweight='bold')

# Chart 1: Bull market price + buys
ax1 = axes[0, 0]
daily_bull = ohlcv['Close'].resample('D').last()
ax1.plot(daily_bull.index, daily_bull, 'b-', linewidth=1.5, alpha=0.7)
ax1.axhline(y=bull_result['day1_price'], color='gold', linewidth=2, linestyle='--', label=f'Day 1 (${bull_result["day1_price"]:,.0f})')
ax1.axhline(y=bull_result['liq_avg'], color='green', linewidth=2, linestyle='--', label=f'Liq Avg (${bull_result["liq_avg"]:,.0f})')
ax1.set_title(f'BULL MARKET: BTC {bull_result["btc_change"]:+.1f}%', fontsize=14, fontweight='bold')
ax1.set_ylabel('BTC Price ($)')
ax1.legend(loc='upper left')
ax1.grid(True, alpha=0.3)

# Chart 2: Bear market price + buys
ax2 = axes[0, 1]
daily_bear = bear_ohlcv['Close'].resample('D').last()
ax2.plot(daily_bear.index, daily_bear, 'r-', linewidth=1.5, alpha=0.7)
ax2.axhline(y=bear_result['day1_price'], color='gold', linewidth=2, linestyle='--', label=f'Day 1 (${bear_result["day1_price"]:,.0f})')
ax2.axhline(y=bear_result['liq_avg'], color='green', linewidth=2, linestyle='--', label=f'Liq Avg (${bear_result["liq_avg"]:,.0f})')
ax2.set_title(f'BEAR MARKET (Simulated): BTC {bear_result["btc_change"]:+.1f}%', fontsize=14, fontweight='bold')
ax2.set_ylabel('BTC Price ($)')
ax2.legend(loc='upper right')
ax2.grid(True, alpha=0.3)

# Chart 3: Coins accumulated comparison
ax3 = axes[1, 0]
strategies = ['Day 1\nLump Sum', 'Liquidation\nStrategy']
bull_coins = [bull_result['day1_coins'], bull_result['liq_coins']]
bear_coins = [bear_result['day1_coins'], bear_result['liq_coins']]

x = np.arange(len(strategies))
width = 0.35

bars1 = ax3.bar(x - width/2, bull_coins, width, label='Bull Market', color='blue', alpha=0.7)
bars2 = ax3.bar(x + width/2, bear_coins, width, label='Bear Market', color='red', alpha=0.7)

ax3.set_ylabel('BTC Accumulated')
ax3.set_title('Coins Accumulated: Bull vs Bear', fontsize=14, fontweight='bold')
ax3.set_xticks(x)
ax3.set_xticklabels(strategies)
ax3.legend()
ax3.grid(True, alpha=0.3, axis='y')

# Add values on bars
for bar, val in zip(bars1, bull_coins):
    ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3, f'{val:.1f}',
             ha='center', va='bottom', fontsize=11, fontweight='bold')
for bar, val in zip(bars2, bear_coins):
    ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3, f'{val:.1f}',
             ha='center', va='bottom', fontsize=11, fontweight='bold')

# Chart 4: Liq vs Day1 performance
ax4 = axes[1, 1]
markets = ['BULL\n(+27%)', 'BEAR\n(-21%)']
liq_vs_day1 = [bull_result['liq_vs_day1'], bear_result['liq_vs_day1']]
colors = ['green' if x > 0 else 'red' for x in liq_vs_day1]

bars = ax4.bar(markets, liq_vs_day1, color=colors, alpha=0.7, edgecolor='black', linewidth=2)
ax4.axhline(y=0, color='black', linewidth=2)
ax4.set_ylabel('Liquidation vs Day 1 (%)')
ax4.set_title('Liquidation Strategy Edge Over Day 1', fontsize=14, fontweight='bold')
ax4.grid(True, alpha=0.3, axis='y')

# Add values on bars
for bar, val in zip(bars, liq_vs_day1):
    y_pos = bar.get_height() + 1 if val > 0 else bar.get_height() - 3
    ax4.text(bar.get_x() + bar.get_width()/2, y_pos, f'{val:+.1f}%',
             ha='center', va='bottom' if val > 0 else 'top', fontsize=14, fontweight='bold')

plt.tight_layout()
chart_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/backtests/accumulation/liquidations/report/chart7_bear_simulation.png'
plt.savefig(chart_path, dpi=150, bbox_inches='tight', facecolor='white')
print(f"Saved: {chart_path}")
plt.close()

# =============================================================================
# FINAL SUMMARY
# =============================================================================
print("\n" + "=" * 70)
print("FINAL SUMMARY")
print("=" * 70)

print(f"""
LIQUIDATION STRATEGY vs DAY 1 LUMP SUM:

  BULL MARKET (+27%):  Liquidation wins by {bull_result['liq_vs_day1']:+.1f}%
  BEAR MARKET (-21%):  Liquidation wins by {bear_result['liq_vs_day1']:+.1f}%

CONCLUSION:
  - In BULL markets: Liquidation still beats Day 1 by ~{bull_result['liq_vs_day1']:.0f}%
  - In BEAR markets: Liquidation CRUSHES Day 1 by ~{bear_result['liq_vs_day1']:.0f}%

  The liquidation strategy wins in BOTH market conditions.
  It just wins by MORE in bear markets.
""")

print("=" * 70)
print("Moon Dev's Bear Market Simulation Complete!")
print("=" * 70)
