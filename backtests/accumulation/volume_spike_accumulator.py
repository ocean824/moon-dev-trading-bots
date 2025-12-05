"""
Moon Dev's Volume Spike Accumulation Strategy
==============================================
Accumulation strategy for funds/whales that only BUY - never sell.

THESIS: Michael Saylor / MicroStrategy style accumulation could be 20-30%+
more efficient with algorithmic patience instead of market buying.

STRATEGY LOGIC:
- Only BUY when price is dropping AND volume spikes (5x+ average)
- This indicates capitulation / panic selling = good accumulation opportunity
- Deploy X% of remaining capital per signal
- Track total coins accumulated vs simple DCA comparison

KEY METRICS:
- Total coins accumulated
- Average purchase price
- Coins accumulated vs DCA baseline
- Efficiency gain percentage
"""

import pandas as pd
import numpy as np
import pandas_ta as ta
from backtesting import Backtest, Strategy
from datetime import datetime

print("=" * 70)
print("🌙 Moon Dev's Volume Spike Accumulation Strategy Loading... 🚀")
print("=" * 70)

# =============================================================================
# DATA CONFIGURATION - Uncomment the asset you want to test
# =============================================================================
# BTC Daily Data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1d-1000wks-data.csv'
ASSET_NAME = "BTC"

# ETH Daily Data
# data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/ETHUSD-1d-1000wks-data.csv'
# ASSET_NAME = "ETH"

# SOL Daily Data
# data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/SOLUSD-1d-1000wks-data.csv'
# ASSET_NAME = "SOL"

# =============================================================================
# STRATEGY PARAMETERS
# =============================================================================
STARTING_CAPITAL = 1_000_000  # $1M starting capital
BUY_PERCENT = 0.05  # Buy 5% of remaining capital per signal
VOLUME_MULTIPLIER = 2.0  # Volume must be 2x the average (more signals)
VOLUME_LOOKBACK = 20  # 20-day average volume
PRICE_DROP_THRESHOLD = -0.02  # Price must drop at least 2%

print(f"📊 Loading {ASSET_NAME} data from: {data_path}")

# Load and prepare data
data = pd.read_csv(data_path, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()  # Ensure chronological order
data = data.dropna()

print(f"✅ Data loaded! {len(data)} days of data")
print(f"📅 Date range: {data.index[0].strftime('%Y-%m-%d')} to {data.index[-1].strftime('%Y-%m-%d')}")
print(f"💰 Starting capital: ${STARTING_CAPITAL:,.0f}")
print(f"📈 Buy {BUY_PERCENT*100:.0f}% per signal | Volume spike: {VOLUME_MULTIPLIER}x")
print("=" * 70)


class VolumeSpikeAccumulator(Strategy):
    """
    Volume Spike Accumulation Strategy
    - Only buys, never sells
    - Buys when: price dropping + volume spike (5x average)
    - Deploys X% of remaining capital per signal
    """

    # Parameters (can be optimized)
    buy_percent = BUY_PERCENT
    volume_mult = VOLUME_MULTIPLIER
    volume_lookback = VOLUME_LOOKBACK
    price_drop_pct = PRICE_DROP_THRESHOLD

    def init(self):
        print(f"🔧 Moon Dev Initializing {ASSET_NAME} Accumulator...")

        # Calculate average volume (20-day SMA)
        self.avg_volume = self.I(
            ta.sma,
            pd.Series(self.data.Volume),
            length=self.volume_lookback
        )

        # Calculate daily returns
        close_series = pd.Series(self.data.Close)
        self.daily_return = self.I(lambda x: x.pct_change().values, close_series)

        # Track accumulation metrics
        self.total_coins = 0
        self.total_spent = 0
        self.buy_count = 0
        self.buy_prices = []
        self.buy_dates = []
        self.buy_amounts = []

        print("✅ Indicators ready! Looking for volume spike opportunities...")

    def next(self):
        # Skip if not enough data for volume average
        if len(self.data) < self.volume_lookback + 1:
            return

        # Skip if we've spent all capital
        remaining_capital = STARTING_CAPITAL - self.total_spent
        if remaining_capital <= 0:
            return

        # Get current values
        current_volume = self.data.Volume[-1]
        avg_vol = self.avg_volume[-1]
        daily_ret = self.daily_return[-1]
        current_price = self.data.Close[-1]

        # Skip if indicators not ready
        if pd.isna(avg_vol) or pd.isna(daily_ret) or avg_vol == 0:
            return

        # ACCUMULATION SIGNAL:
        # 1. Price is dropping (negative daily return)
        # 2. Volume is spiking (5x+ average)
        volume_spike = current_volume >= (avg_vol * self.volume_mult)
        price_dropping = daily_ret < self.price_drop_pct

        if volume_spike and price_dropping:
            # Calculate buy amount (X% of remaining capital)
            buy_amount_usd = remaining_capital * self.buy_percent
            coins_to_buy = buy_amount_usd / current_price

            # Execute the buy (we track manually since this is accumulation)
            self.total_coins += coins_to_buy
            self.total_spent += buy_amount_usd
            self.buy_count += 1
            self.buy_prices.append(current_price)
            self.buy_dates.append(self.data.index[-1])
            self.buy_amounts.append(coins_to_buy)

            # Also execute in backtesting framework for visualization
            if not self.position:
                self.buy(size=0.99)  # Small position just for tracking

            # Print buy signal
            vol_ratio = current_volume / avg_vol
            print(f"🟢 BUY #{self.buy_count}: {coins_to_buy:.6f} {ASSET_NAME} @ ${current_price:,.2f} | "
                  f"Vol: {vol_ratio:.1f}x | Drop: {daily_ret*100:.2f}% | "
                  f"Spent: ${self.total_spent:,.0f}")


# Run the backtest
bt = Backtest(
    data,
    VolumeSpikeAccumulator,
    cash=STARTING_CAPITAL,
    commission=0.001,  # 0.1% commission
    exclusive_orders=True
)

print("\n" + "=" * 70)
print("🚀 Moon Dev Running Volume Spike Accumulation Backtest...")
print("=" * 70 + "\n")

stats = bt.run()

# =============================================================================
# RESULTS ANALYSIS
# =============================================================================
strategy = stats._strategy
STRATEGY_NAME = f"VOLUME SPIKE ({VOLUME_MULTIPLIER}x vol + {int(abs(PRICE_DROP_THRESHOLD)*100)}% drop)"

# KEY PRICES
first_day_price = data['Close'].iloc[0]
final_price = data['Close'].iloc[-1]
first_date = data.index[0].strftime('%Y-%m-%d')
last_date = data.index[-1].strftime('%Y-%m-%d')
total_days = len(data)

# COMPARISON 1: Day 1 Lump Sum
day1_coins = STARTING_CAPITAL / first_day_price
day1_final_value = day1_coins * final_price

# COMPARISON 2: Daily DCA
dca_daily_amount = STARTING_CAPITAL / total_days
dca_coins = (dca_daily_amount / data['Close']).sum()
dca_avg_price = STARTING_CAPITAL / dca_coins
dca_final_value = dca_coins * final_price

print(f"\n{'='*70}")
print(f"🎯 {STRATEGY_NAME} - {ASSET_NAME}")
print(f"{'='*70}")
print(f"📅 Data: {first_date} to {last_date} ({total_days} days)")
print(f"💵 Starting Capital: ${STARTING_CAPITAL:,.0f}")
print(f"📈 {ASSET_NAME} Price: ${first_day_price:,.2f} (start) → ${final_price:,.2f} (end)")

print(f"\n{'='*70}")
print(f"📊 HOW MANY {ASSET_NAME} WOULD YOU HAVE?")
print(f"{'='*70}")

print(f"\n1️⃣  DAY 1 LUMP SUM (bought ${STARTING_CAPITAL:,.0f} on {first_date}):")
print(f"    💰 {ASSET_NAME} Accumulated: {day1_coins:,.6f}")
print(f"    📊 Purchase Price: ${first_day_price:,.2f}")
print(f"    💵 Value Today: ${day1_final_value:,.0f}")

print(f"\n2️⃣  DAILY DCA (${dca_daily_amount:,.2f}/day for {total_days} days):")
print(f"    💰 {ASSET_NAME} Accumulated: {dca_coins:,.6f}")
print(f"    📊 Average Price: ${dca_avg_price:,.2f}")
print(f"    💵 Value Today: ${dca_final_value:,.0f}")

if strategy.total_coins > 0:
    our_avg_price = strategy.total_spent / strategy.total_coins
    our_final_value = strategy.total_coins * final_price
    capital_deployed_pct = (strategy.total_spent / STARTING_CAPITAL) * 100

    print(f"\n3️⃣  🌙 THIS STRATEGY ({STRATEGY_NAME}):")
    print(f"    💰 {ASSET_NAME} Accumulated: {strategy.total_coins:,.6f}")
    print(f"    📊 Average Price: ${our_avg_price:,.2f}")
    print(f"    💵 Value Today: ${our_final_value:,.0f}")
    print(f"    📈 Buy Signals: {strategy.buy_count} | Capital Used: {capital_deployed_pct:.1f}%")

    print(f"\n{'='*70}")
    print(f"🏆 WINNER COMPARISON")
    print(f"{'='*70}")

    vs_day1_pct = ((strategy.total_coins - day1_coins) / day1_coins) * 100
    vs_dca_pct = ((strategy.total_coins - dca_coins) / dca_coins) * 100

    print(f"\n📊 Strategy vs Day 1 Lump Sum:")
    print(f"    {ASSET_NAME} Difference: {strategy.total_coins - day1_coins:+,.6f} ({vs_day1_pct:+.1f}%)")
    print(f"    Value Difference: ${our_final_value - day1_final_value:+,.0f}")

    print(f"\n📊 Strategy vs Daily DCA:")
    print(f"    {ASSET_NAME} Difference: {strategy.total_coins - dca_coins:+,.6f} ({vs_dca_pct:+.1f}%)")
    print(f"    Value Difference: ${our_final_value - dca_final_value:+,.0f}")

    all_coins = {'Day 1 Lump Sum': day1_coins, 'Daily DCA': dca_coins, 'This Strategy': strategy.total_coins}
    winner = max(all_coins, key=all_coins.get)
    print(f"\n🏆 MOST {ASSET_NAME} ACCUMULATED: {winner} with {all_coins[winner]:,.6f} {ASSET_NAME}!")
else:
    print("\n⚠️ No accumulation signals triggered!")
    print("   Try adjusting parameters:")
    print(f"   - Lower volume_mult (current: {VOLUME_MULTIPLIER}x)")
    print(f"   - Adjust price_drop_pct (current: {PRICE_DROP_THRESHOLD*100}%)")

print(f"\n{'='*70}")
print("🌙 Moon Dev's Volume Spike Accumulation Complete! 🚀")
print(f"{'='*70}")
