"""
Moon Dev's Random Sampling Liquidation Test
============================================
Testing liquidation accumulation strategies on random time slices
to validate robustness across different market conditions.

Data: 540 days of BTC liquidation data (Jun 2024 - Nov 2025)
Method: Create 10 random time slices, compare Day 1 Lump Sum vs Liquidation strategies
"""

import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print("=" * 70)
print("Moon Dev's Random Sampling Liquidation Test")
print("=" * 70)

# =============================================================================
# LOAD AND PROCESS RAW LIQUIDATION DATA
# =============================================================================
print("\nLoading raw liquidation data (this may take a moment)...")

raw_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/moondev_api/liq_data_full.csv'

# Column names based on the data structure
columns = ['symbol', 'side', 'order_type', 'time_in_force', 'qty', 'price',
           'mark_price', 'status', 'filled_qty', 'total_qty', 'timestamp', 'value']

# Load only BTC data to save memory
chunks = []
for chunk in pd.read_csv(raw_path, names=columns, chunksize=1000000):
    btc_chunk = chunk[chunk['symbol'] == 'BTC']
    if len(btc_chunk) > 0:
        chunks.append(btc_chunk)
    print(f"  Processed chunk... BTC rows so far: {sum(len(c) for c in chunks):,}")

raw_data = pd.concat(chunks, ignore_index=True)
print(f"\nLoaded {len(raw_data):,} BTC liquidation records")

# Convert timestamp to datetime
raw_data['datetime'] = pd.to_datetime(raw_data['timestamp'], unit='ms')
raw_data = raw_data.sort_values('datetime')

print(f"Date range: {raw_data['datetime'].min()} to {raw_data['datetime'].max()}")
total_days = (raw_data['datetime'].max() - raw_data['datetime'].min()).days
print(f"Total days: {total_days}")

# =============================================================================
# RESAMPLE TO 5-MINUTE OHLCV WITH LIQUIDATIONS
# =============================================================================
print("\nResampling to 5-minute bars with liquidation data...")

raw_data.set_index('datetime', inplace=True)

# Separate long and short liquidations
# SELL orders = long liquidations (longs getting closed = selling)
# BUY orders = short liquidations (shorts getting closed = buying)
raw_data['long_liq'] = raw_data.apply(lambda x: x['value'] if x['side'] == 'SELL' else 0, axis=1)
raw_data['short_liq'] = raw_data.apply(lambda x: x['value'] if x['side'] == 'BUY' else 0, axis=1)

# Resample to 5-minute bars
ohlcv = raw_data['price'].resample('5min').ohlc()
ohlcv.columns = ['Open', 'High', 'Low', 'Close']
ohlcv['long_liquidations'] = raw_data['long_liq'].resample('5min').sum()
ohlcv['short_liquidations'] = raw_data['short_liq'].resample('5min').sum()
ohlcv['total_liquidations'] = ohlcv['long_liquidations'] + ohlcv['short_liquidations']

# Forward fill missing OHLC data
ohlcv = ohlcv.ffill().dropna()

# Calculate 60-minute rolling sums (12 x 5-min bars)
ohlcv['long_liq_60m'] = ohlcv['long_liquidations'].rolling(12).sum()
ohlcv['short_liq_60m'] = ohlcv['short_liquidations'].rolling(12).sum()

print(f"Created {len(ohlcv):,} 5-minute bars")
print(f"Date range: {ohlcv.index[0]} to {ohlcv.index[-1]}")

first_price = ohlcv['Close'].iloc[0]
last_price = ohlcv['Close'].iloc[-1]
print(f"BTC: ${first_price:,.2f} -> ${last_price:,.2f} ({((last_price/first_price)-1)*100:+.1f}%)")

# =============================================================================
# CONFIGURATION
# =============================================================================
STARTING_CAPITAL = 1_000_000
FIXED_PCT = 0.005  # 0.5% = $5,000 per buy
FIXED_BUY = STARTING_CAPITAL * FIXED_PCT
MAX_DAILY = 3
THRESHOLD = 1_000_000  # $1M in 60-min window

# =============================================================================
# STRATEGY RUNNER
# =============================================================================
def run_strategies_on_slice(data_slice, slice_name):
    """
    Run Day 1 Lump Sum vs Liquidation strategies on a data slice
    """
    if len(data_slice) < 100:
        return None

    # Get daily closes for DCA
    daily_closes = data_slice['Close'].resample('D').last().dropna()
    if len(daily_closes) < 10:
        return None

    days_in_slice = (data_slice.index[-1] - data_slice.index[0]).days

    # BASELINE 1: Daily DCA
    dca_daily_amount = STARTING_CAPITAL / len(daily_closes)
    dca_coins = sum(dca_daily_amount / price for price in daily_closes)
    dca_avg_price = STARTING_CAPITAL / dca_coins

    # BASELINE 2: Day 1 Lump Sum
    day1_price = data_slice['Close'].iloc[0]
    day1_coins = STARTING_CAPITAL / day1_price
    day1_vs_dca = ((day1_coins - dca_coins) / dca_coins) * 100

    # STRATEGY: Fixed 0.5% Long Liquidation 3x Daily
    total_coins = 0
    total_spent = 0
    daily_buy_counts = {}

    for idx, row in data_slice.iterrows():
        remaining = STARTING_CAPITAL - total_spent
        if remaining < FIXED_BUY * 0.5:
            break

        liq_value = row['long_liq_60m']
        if pd.isna(liq_value):
            continue

        if liq_value >= THRESHOLD:
            current_date = idx.date()
            if current_date not in daily_buy_counts:
                daily_buy_counts[current_date] = 0

            if daily_buy_counts[current_date] >= MAX_DAILY:
                continue

            buy_amount = min(FIXED_BUY, remaining)
            coins = buy_amount / row['Close']
            total_coins += coins
            total_spent += buy_amount
            daily_buy_counts[current_date] += 1

    if total_coins > 0:
        liq_avg_price = total_spent / total_coins
        liq_vs_dca = ((total_coins - dca_coins) / dca_coins) * 100
        liq_vs_day1 = ((total_coins - day1_coins) / day1_coins) * 100
    else:
        liq_avg_price = 0
        liq_vs_dca = -100
        liq_vs_day1 = -100

    pct_deployed = (total_spent / STARTING_CAPITAL) * 100

    return {
        'Slice': slice_name,
        'Start': data_slice.index[0].strftime('%Y-%m-%d'),
        'End': data_slice.index[-1].strftime('%Y-%m-%d'),
        'Days': days_in_slice,
        'BTC_Start': day1_price,
        'BTC_End': data_slice['Close'].iloc[-1],
        'BTC_Change': ((data_slice['Close'].iloc[-1] / day1_price) - 1) * 100,
        'DCA_Coins': dca_coins,
        'DCA_Avg': dca_avg_price,
        'Day1_Coins': day1_coins,
        'Day1_vs_DCA': day1_vs_dca,
        'Liq_Coins': total_coins,
        'Liq_Avg': liq_avg_price,
        'Liq_vs_DCA': liq_vs_dca,
        'Liq_vs_Day1': liq_vs_day1,
        'Liq_Spent': total_spent,
        'Liq_Pct_Deployed': pct_deployed,
        'Winner': 'Liq' if liq_vs_day1 > 0 else 'Day1'
    }

# =============================================================================
# RUN ON FULL DATASET
# =============================================================================
print("\n" + "=" * 70)
print("TEST 1: FULL DATASET")
print("=" * 70)

full_result = run_strategies_on_slice(ohlcv, 'FULL')
if full_result:
    print(f"\nFull Dataset: {full_result['Start']} to {full_result['End']} ({full_result['Days']} days)")
    print(f"BTC: ${full_result['BTC_Start']:,.0f} -> ${full_result['BTC_End']:,.0f} ({full_result['BTC_Change']:+.1f}%)")
    print(f"\n{'Strategy':<20} {'Coins':>12} {'Avg Price':>12} {'vs DCA':>10}")
    print("-" * 60)
    print(f"{'Daily DCA':<20} {full_result['DCA_Coins']:>12.4f} ${full_result['DCA_Avg']:>10,.0f} {0:>+9.1f}%")
    print(f"{'Day 1 Lump Sum':<20} {full_result['Day1_Coins']:>12.4f} ${full_result['BTC_Start']:>10,.0f} {full_result['Day1_vs_DCA']:>+9.1f}%")
    print(f"{'Liq 0.5% 3x':<20} {full_result['Liq_Coins']:>12.4f} ${full_result['Liq_Avg']:>10,.0f} {full_result['Liq_vs_DCA']:>+9.1f}%")
    print(f"\nLiq vs Day1: {full_result['Liq_vs_Day1']:+.1f}% | Winner: {full_result['Winner']}")

# =============================================================================
# GENERATE RANDOM SAMPLES
# =============================================================================
print("\n" + "=" * 70)
print("TEST 2: RANDOM TIME SLICES (10 samples)")
print("=" * 70)

# Get date range
start_date = ohlcv.index[0]
end_date = ohlcv.index[-1]
total_range = (end_date - start_date).days

# Random seed for reproducibility
random.seed(42)
np.random.seed(42)

results = [full_result] if full_result else []

print("\nGenerating 10 random time slices...")
print("(Different start points, different durations)")
print("NOTE: Liquidation strategy needs ~100-200 days to fully deploy capital!")

for i in range(10):
    # Random duration: 100-300 days (need enough time to deploy capital)
    duration_days = random.randint(100, 300)

    # Random start: must allow for duration
    max_start_offset = total_range - duration_days - 10
    if max_start_offset < 10:
        continue

    start_offset = random.randint(10, max_start_offset)

    slice_start = start_date + timedelta(days=start_offset)
    slice_end = slice_start + timedelta(days=duration_days)

    # Get the data slice
    data_slice = ohlcv[(ohlcv.index >= slice_start) & (ohlcv.index <= slice_end)]

    slice_name = f"Sample_{i+1}"
    result = run_strategies_on_slice(data_slice, slice_name)

    if result:
        results.append(result)
        print(f"  {slice_name}: {result['Start']} to {result['End']} ({result['Days']}d) | BTC {result['BTC_Change']:+.1f}% | Winner: {result['Winner']}")

# =============================================================================
# RESULTS SUMMARY
# =============================================================================
print("\n" + "=" * 70)
print("RESULTS SUMMARY")
print("=" * 70)

df = pd.DataFrame(results)

print(f"\n{'Slice':<12} {'Days':>5} {'BTC%':>8} {'Day1 vs DCA':>12} {'Liq vs DCA':>12} {'Liq vs Day1':>12} {'% Deployed':>11} {'Winner':>8}")
print("-" * 95)

for _, row in df.iterrows():
    print(f"{row['Slice']:<12} {row['Days']:>5} {row['BTC_Change']:>+7.1f}% {row['Day1_vs_DCA']:>+11.1f}% {row['Liq_vs_DCA']:>+11.1f}% {row['Liq_vs_Day1']:>+11.1f}% {row['Liq_Pct_Deployed']:>10.0f}% {row['Winner']:>8}")

# =============================================================================
# WIN RATE ANALYSIS
# =============================================================================
print("\n" + "=" * 70)
print("WIN RATE ANALYSIS")
print("=" * 70)

samples_only = df[df['Slice'] != 'FULL']
liq_wins = (samples_only['Winner'] == 'Liq').sum()
day1_wins = (samples_only['Winner'] == 'Day1').sum()
total_samples = len(samples_only)

print(f"\nAcross {total_samples} random samples:")
print(f"  Liquidation Strategy Wins: {liq_wins} ({liq_wins/total_samples*100:.0f}%)")
print(f"  Day 1 Lump Sum Wins: {day1_wins} ({day1_wins/total_samples*100:.0f}%)")

print(f"\nAverage Performance:")
print(f"  Day 1 Lump Sum vs DCA: {samples_only['Day1_vs_DCA'].mean():+.1f}% (std: {samples_only['Day1_vs_DCA'].std():.1f}%)")
print(f"  Liquidation vs DCA:    {samples_only['Liq_vs_DCA'].mean():+.1f}% (std: {samples_only['Liq_vs_DCA'].std():.1f}%)")
print(f"  Liquidation vs Day 1:  {samples_only['Liq_vs_Day1'].mean():+.1f}% (std: {samples_only['Liq_vs_Day1'].std():.1f}%)")

# =============================================================================
# BY MARKET CONDITION
# =============================================================================
print("\n" + "=" * 70)
print("PERFORMANCE BY MARKET CONDITION")
print("=" * 70)

# Bull markets (BTC up >20%)
bull = samples_only[samples_only['BTC_Change'] > 20]
# Bear/flat markets (BTC up <20%)
bear = samples_only[samples_only['BTC_Change'] <= 20]

if len(bull) > 0:
    print(f"\nBull Markets (BTC +20% or more): {len(bull)} samples")
    print(f"  Day 1 avg: {bull['Day1_vs_DCA'].mean():+.1f}% | Liq avg: {bull['Liq_vs_DCA'].mean():+.1f}%")
    print(f"  Liq vs Day1: {bull['Liq_vs_Day1'].mean():+.1f}%")
    print(f"  Liq wins: {(bull['Winner'] == 'Liq').sum()}/{len(bull)}")

if len(bear) > 0:
    print(f"\nFlat/Bear Markets (BTC <20%): {len(bear)} samples")
    print(f"  Day 1 avg: {bear['Day1_vs_DCA'].mean():+.1f}% | Liq avg: {bear['Liq_vs_DCA'].mean():+.1f}%")
    print(f"  Liq vs Day1: {bear['Liq_vs_Day1'].mean():+.1f}%")
    print(f"  Liq wins: {(bear['Winner'] == 'Liq').sum()}/{len(bear)}")

# Save results
output_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/backtests/accumulation/liquidations/random_sample_results.csv'
df.to_csv(output_path, index=False)
print(f"\nResults saved to: {output_path}")

print("\n" + "=" * 70)
print("Moon Dev's Random Sampling Test Complete!")
print("=" * 70)
