"""
Moon Dev's Liquidation-Based Accumulation Strategies
=====================================================
Using liquidation data to time accumulation buys

Data: BTC 5-minute liquidation data (June 2024 - Sept 2025)
Baseline: Daily DCA

Strategies:
1. Long Liquidation Accumulator - Buy when long liquidations spike (cascade down = buy dip)
2. Short Liquidation Accumulator - Buy when short liquidations spike (momentum continuation)
3. Liquidation Spike Accumulator - Buy on ANY large liquidation event
4. WL + Liquidation Combo - Weekly Low + Liquidation confirmation
5. WL+DD + Liquidation - Weekly Low Double Down + Liquidation filter
6. Liquidation Threshold Tiers - Scale buys by liquidation size
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print("=" * 70)
print("Moon Dev's Liquidation Accumulation Strategies")
print("=" * 70)

# =============================================================================
# CONFIGURATION
# =============================================================================
STARTING_CAPITAL = 1_000_000

# Load liquidation data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/moondev_api/liq_data_BTC_5m_ohlcv.csv'
print(f"Loading liquidation data from: {data_path}")

data = pd.read_csv(data_path, parse_dates=['datetime'], index_col='datetime')
data = data.sort_index()

# Get date range
first_date = data.index[0]
last_date = data.index[-1]
first_price = data['Close'].iloc[0]
last_price = data['Close'].iloc[-1]

print(f"Date range: {first_date} to {last_date}")
print(f"Price: ${first_price:,.2f} -> ${last_price:,.2f}")
print(f"Total 5-min bars: {len(data):,}")

# Resample to daily for accumulation strategies
daily_data = data.resample('D').agg({
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

total_days = len(daily_data)
print(f"Total days: {total_days}")

# =============================================================================
# RESULTS STORAGE
# =============================================================================
results = []

# =============================================================================
# BASELINE: Daily DCA
# =============================================================================
print("\nRunning Daily DCA baseline...")

dca_daily_amount = STARTING_CAPITAL / total_days
dca_coins = 0
for idx, row in daily_data.iterrows():
    dca_coins += dca_daily_amount / row['Close']

dca_avg_price = STARTING_CAPITAL / dca_coins
dca_final_value = dca_coins * last_price

results.append({
    'Strategy': 'Daily DCA',
    'Coins': dca_coins,
    'Avg_Price': dca_avg_price,
    'Capital_Used_Pct': 100.0,
    'Buy_Signals': total_days,
    'Final_Value': dca_final_value,
    'vs_DCA_Pct': 0.0,
})

print(f"  DCA: {dca_coins:.6f} BTC @ avg ${dca_avg_price:,.2f}")

# =============================================================================
# STRATEGY 1: Long Liquidation Accumulator
# Buy when long liquidations exceed threshold (buy the dip after cascade)
# =============================================================================
print("\nRunning Long Liquidation Accumulator...")

long_liq_threshold = 500_000  # $500k in long liquidations
buy_percent = 0.02  # 2% of remaining capital per signal

total_coins = 0
total_spent = 0
buy_count = 0
last_buy_date = None

for idx, row in daily_data.iterrows():
    remaining = STARTING_CAPITAL - total_spent
    if remaining <= 0:
        break

    # Buy when long liquidations spike (longs getting rekt = price dropping = buy opportunity)
    if row['long_liquidations'] >= long_liq_threshold:
        if last_buy_date is None or (idx - last_buy_date).days >= 1:
            buy_amount = min(remaining * buy_percent, remaining)
            coins = buy_amount / row['Close']
            total_coins += coins
            total_spent += buy_amount
            buy_count += 1
            last_buy_date = idx

if total_coins > 0:
    avg_price = total_spent / total_coins
    final_value = total_coins * last_price
    capital_pct = (total_spent / STARTING_CAPITAL) * 100
    vs_dca = ((total_coins - dca_coins) / dca_coins) * 100

    results.append({
        'Strategy': 'Long Liq Accumulator',
        'Coins': total_coins,
        'Avg_Price': avg_price,
        'Capital_Used_Pct': capital_pct,
        'Buy_Signals': buy_count,
        'Final_Value': final_value,
        'vs_DCA_Pct': vs_dca,
    })
    print(f"  {total_coins:.6f} BTC ({vs_dca:+.1f}% vs DCA)")
else:
    print("  No signals")

# =============================================================================
# STRATEGY 2: Short Liquidation Accumulator
# Buy when short liquidations exceed threshold (momentum continuation)
# =============================================================================
print("\nRunning Short Liquidation Accumulator...")

short_liq_threshold = 500_000
buy_percent = 0.02

total_coins = 0
total_spent = 0
buy_count = 0
last_buy_date = None

for idx, row in daily_data.iterrows():
    remaining = STARTING_CAPITAL - total_spent
    if remaining <= 0:
        break

    # Buy when short liquidations spike (shorts getting rekt = price rising = momentum)
    if row['short_liquidations'] >= short_liq_threshold:
        if last_buy_date is None or (idx - last_buy_date).days >= 1:
            buy_amount = min(remaining * buy_percent, remaining)
            coins = buy_amount / row['Close']
            total_coins += coins
            total_spent += buy_amount
            buy_count += 1
            last_buy_date = idx

if total_coins > 0:
    avg_price = total_spent / total_coins
    final_value = total_coins * last_price
    capital_pct = (total_spent / STARTING_CAPITAL) * 100
    vs_dca = ((total_coins - dca_coins) / dca_coins) * 100

    results.append({
        'Strategy': 'Short Liq Accumulator',
        'Coins': total_coins,
        'Avg_Price': avg_price,
        'Capital_Used_Pct': capital_pct,
        'Buy_Signals': buy_count,
        'Final_Value': final_value,
        'vs_DCA_Pct': vs_dca,
    })
    print(f"  {total_coins:.6f} BTC ({vs_dca:+.1f}% vs DCA)")
else:
    print("  No signals")

# =============================================================================
# STRATEGY 3: Total Liquidation Spike Accumulator
# Buy on ANY large liquidation event (market volatility = opportunity)
# =============================================================================
print("\nRunning Total Liquidation Spike...")

total_liq_threshold = 1_000_000  # $1M total liquidations
buy_percent = 0.02

total_coins = 0
total_spent = 0
buy_count = 0
last_buy_date = None

for idx, row in daily_data.iterrows():
    remaining = STARTING_CAPITAL - total_spent
    if remaining <= 0:
        break

    if row['total_liquidations'] >= total_liq_threshold:
        if last_buy_date is None or (idx - last_buy_date).days >= 1:
            buy_amount = min(remaining * buy_percent, remaining)
            coins = buy_amount / row['Close']
            total_coins += coins
            total_spent += buy_amount
            buy_count += 1
            last_buy_date = idx

if total_coins > 0:
    avg_price = total_spent / total_coins
    final_value = total_coins * last_price
    capital_pct = (total_spent / STARTING_CAPITAL) * 100
    vs_dca = ((total_coins - dca_coins) / dca_coins) * 100

    results.append({
        'Strategy': 'Total Liq Spike',
        'Coins': total_coins,
        'Avg_Price': avg_price,
        'Capital_Used_Pct': capital_pct,
        'Buy_Signals': buy_count,
        'Final_Value': final_value,
        'vs_DCA_Pct': vs_dca,
    })
    print(f"  {total_coins:.6f} BTC ({vs_dca:+.1f}% vs DCA)")
else:
    print("  No signals")

# =============================================================================
# STRATEGY 4: Weekly Low + Long Liquidation Combo
# =============================================================================
print("\nRunning Weekly Low + Long Liq Combo...")

# Calculate weekly lows
daily_data['week'] = daily_data.index.to_period('W')
weekly_min = daily_data.groupby('week')['Low'].transform('min')
daily_data['is_weekly_low'] = daily_data['Low'] == weekly_min

weekly_buy = 0.01
long_liq_threshold = 200_000  # Lower threshold for combo

total_coins = 0
total_spent = 0
buy_count = 0
last_buy_week = None

for idx, row in daily_data.iterrows():
    remaining = STARTING_CAPITAL - total_spent
    if remaining <= 0:
        break

    current_week = row['week']

    # Buy at weekly low when there's also significant long liquidations
    if row['is_weekly_low'] and row['long_liquidations'] >= long_liq_threshold:
        if last_buy_week is None or current_week != last_buy_week:
            buy_amount = min(STARTING_CAPITAL * weekly_buy, remaining)
            coins = buy_amount / row['Close']
            total_coins += coins
            total_spent += buy_amount
            buy_count += 1
            last_buy_week = current_week

if total_coins > 0:
    avg_price = total_spent / total_coins
    final_value = total_coins * last_price
    capital_pct = (total_spent / STARTING_CAPITAL) * 100
    vs_dca = ((total_coins - dca_coins) / dca_coins) * 100

    results.append({
        'Strategy': 'WL + Long Liq',
        'Coins': total_coins,
        'Avg_Price': avg_price,
        'Capital_Used_Pct': capital_pct,
        'Buy_Signals': buy_count,
        'Final_Value': final_value,
        'vs_DCA_Pct': vs_dca,
    })
    print(f"  {total_coins:.6f} BTC ({vs_dca:+.1f}% vs DCA)")
else:
    print("  No signals")

# =============================================================================
# STRATEGY 5: Weekly Low + Double Down + Liquidation
# =============================================================================
print("\nRunning WL+DD + Liquidation...")

weekly_buy = 0.01
liq_threshold = 100_000  # Any significant liquidation

total_coins = 0
total_spent = 0
buy_count = 0
last_buy_week = None
consecutive_lows = 0

for idx, row in daily_data.iterrows():
    remaining = STARTING_CAPITAL - total_spent
    if remaining <= 0:
        break

    current_week = row['week']

    # Weekly low + liquidation activity
    if row['is_weekly_low'] and row['total_liquidations'] >= liq_threshold:
        if last_buy_week is None or current_week != last_buy_week:
            # Double down logic
            if buy_count > 0 and row['Close'] < total_spent / total_coins:
                consecutive_lows += 1
            else:
                consecutive_lows = 0

            multiplier = min(1.0 + (consecutive_lows * 0.5), 2.0)
            buy_amount = min(STARTING_CAPITAL * weekly_buy * multiplier, remaining)
            coins = buy_amount / row['Close']
            total_coins += coins
            total_spent += buy_amount
            buy_count += 1
            last_buy_week = current_week

if total_coins > 0:
    avg_price = total_spent / total_coins
    final_value = total_coins * last_price
    capital_pct = (total_spent / STARTING_CAPITAL) * 100
    vs_dca = ((total_coins - dca_coins) / dca_coins) * 100

    results.append({
        'Strategy': 'WL+DD + Liq',
        'Coins': total_coins,
        'Avg_Price': avg_price,
        'Capital_Used_Pct': capital_pct,
        'Buy_Signals': buy_count,
        'Final_Value': final_value,
        'vs_DCA_Pct': vs_dca,
    })
    print(f"  {total_coins:.6f} BTC ({vs_dca:+.1f}% vs DCA)")
else:
    print("  No signals")

# =============================================================================
# STRATEGY 6: Liquidation Threshold Tiers
# Scale buys by liquidation size
# =============================================================================
print("\nRunning Liquidation Tier Accumulator...")

# Tiers: bigger liquidations = bigger buys
tiers = {
    500_000: 0.01,    # $500k = 1%
    1_000_000: 0.02,  # $1M = 2%
    2_000_000: 0.03,  # $2M = 3%
    5_000_000: 0.05,  # $5M = 5%
}

total_coins = 0
total_spent = 0
buy_count = 0
last_buy_date = None

for idx, row in daily_data.iterrows():
    remaining = STARTING_CAPITAL - total_spent
    if remaining <= 0:
        break

    total_liq = row['total_liquidations']

    # Find highest tier hit
    buy_pct = 0
    for threshold, pct in sorted(tiers.items(), reverse=True):
        if total_liq >= threshold:
            buy_pct = pct
            break

    if buy_pct > 0:
        if last_buy_date is None or (idx - last_buy_date).days >= 1:
            buy_amount = min(remaining * buy_pct, remaining)
            coins = buy_amount / row['Close']
            total_coins += coins
            total_spent += buy_amount
            buy_count += 1
            last_buy_date = idx

if total_coins > 0:
    avg_price = total_spent / total_coins
    final_value = total_coins * last_price
    capital_pct = (total_spent / STARTING_CAPITAL) * 100
    vs_dca = ((total_coins - dca_coins) / dca_coins) * 100

    results.append({
        'Strategy': 'Liq Tier Accumulator',
        'Coins': total_coins,
        'Avg_Price': avg_price,
        'Capital_Used_Pct': capital_pct,
        'Buy_Signals': buy_count,
        'Final_Value': final_value,
        'vs_DCA_Pct': vs_dca,
    })
    print(f"  {total_coins:.6f} BTC ({vs_dca:+.1f}% vs DCA)")
else:
    print("  No signals")

# =============================================================================
# STRATEGY 7: Weekly Low Base (for comparison)
# =============================================================================
print("\nRunning Weekly Low Base...")

weekly_buy = 0.01

total_coins = 0
total_spent = 0
buy_count = 0
last_buy_week = None

for idx, row in daily_data.iterrows():
    remaining = STARTING_CAPITAL - total_spent
    if remaining <= 0:
        break

    current_week = row['week']

    if row['is_weekly_low']:
        if last_buy_week is None or current_week != last_buy_week:
            buy_amount = min(STARTING_CAPITAL * weekly_buy, remaining)
            coins = buy_amount / row['Close']
            total_coins += coins
            total_spent += buy_amount
            buy_count += 1
            last_buy_week = current_week

if total_coins > 0:
    avg_price = total_spent / total_coins
    final_value = total_coins * last_price
    capital_pct = (total_spent / STARTING_CAPITAL) * 100
    vs_dca = ((total_coins - dca_coins) / dca_coins) * 100

    results.append({
        'Strategy': 'Weekly Low Base',
        'Coins': total_coins,
        'Avg_Price': avg_price,
        'Capital_Used_Pct': capital_pct,
        'Buy_Signals': buy_count,
        'Final_Value': final_value,
        'vs_DCA_Pct': vs_dca,
    })
    print(f"  {total_coins:.6f} BTC ({vs_dca:+.1f}% vs DCA)")
else:
    print("  No signals")

# =============================================================================
# STRATEGY 8: WL + Double Down Base (for comparison)
# =============================================================================
print("\nRunning WL+DD Base...")

weekly_buy = 0.01

total_coins = 0
total_spent = 0
buy_count = 0
last_buy_week = None
consecutive_lows = 0

for idx, row in daily_data.iterrows():
    remaining = STARTING_CAPITAL - total_spent
    if remaining <= 0:
        break

    current_week = row['week']

    if row['is_weekly_low']:
        if last_buy_week is None or current_week != last_buy_week:
            # Double down logic
            if buy_count > 0 and row['Close'] < total_spent / total_coins:
                consecutive_lows += 1
            else:
                consecutive_lows = 0

            multiplier = min(1.0 + (consecutive_lows * 0.5), 2.0)
            buy_amount = min(STARTING_CAPITAL * weekly_buy * multiplier, remaining)
            coins = buy_amount / row['Close']
            total_coins += coins
            total_spent += buy_amount
            buy_count += 1
            last_buy_week = current_week

if total_coins > 0:
    avg_price = total_spent / total_coins
    final_value = total_coins * last_price
    capital_pct = (total_spent / STARTING_CAPITAL) * 100
    vs_dca = ((total_coins - dca_coins) / dca_coins) * 100

    results.append({
        'Strategy': 'WL+DD Base',
        'Coins': total_coins,
        'Avg_Price': avg_price,
        'Capital_Used_Pct': capital_pct,
        'Buy_Signals': buy_count,
        'Final_Value': final_value,
        'vs_DCA_Pct': vs_dca,
    })
    print(f"  {total_coins:.6f} BTC ({vs_dca:+.1f}% vs DCA)")
else:
    print("  No signals")

# =============================================================================
# SAVE RESULTS
# =============================================================================
df = pd.DataFrame(results)
output_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/backtests/accumulation/liquidations/liquidation_results.csv'
df.to_csv(output_path, index=False)

print(f"\n{'='*70}")
print(f"RESULTS SAVED TO: {output_path}")
print(f"{'='*70}")

# =============================================================================
# SUMMARY
# =============================================================================
print(f"\n{'='*70}")
print("MOON DEV'S LIQUIDATION ACCUMULATION RESULTS")
print(f"{'='*70}")

print(f"\nTest Period: {first_date.strftime('%Y-%m-%d')} to {last_date.strftime('%Y-%m-%d')} ({total_days} days)")
print(f"BTC Price: ${first_price:,.2f} -> ${last_price:,.2f} ({((last_price/first_price)-1)*100:+.1f}%)")
print(f"Starting Capital: ${STARTING_CAPITAL:,}")

print(f"\nPerformance vs Daily DCA (sorted by best):")
print("-" * 60)

df_sorted = df.sort_values('vs_DCA_Pct', ascending=False)
for _, row in df_sorted.iterrows():
    emoji = "+" if row['vs_DCA_Pct'] > 0 else ""
    winner = " <-- WINNER!" if row['vs_DCA_Pct'] >= 20 else ""
    print(f"   {row['Strategy']:25s}: {emoji}{row['vs_DCA_Pct']:>6.1f}% | {row['Coins']:.4f} BTC | {row['Buy_Signals']} buys{winner}")

print(f"\n{'='*70}")
print("Moon Dev's Liquidation Accumulation Analysis Complete!")
print(f"{'='*70}")
