"""
Moon Dev's Bollinger Band Bounce Accumulation Strategy
======================================================
Buy when price touches or crosses the lower Bollinger Band!

THESIS: Lower Bollinger Band = 2 standard deviations below mean.
Statistically, price at lower band is oversold and likely to bounce.
"""

import pandas as pd
import numpy as np
import pandas_ta as ta
from backtesting import Backtest, Strategy

print("=" * 70)
print("🌙 Moon Dev's Bollinger Bounce Accumulator Loading... 🚀")
print("=" * 70)

# =============================================================================
# DATA CONFIGURATION
# =============================================================================
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1d-1000wks-data.csv'
ASSET_NAME = "BTC"

# data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/ETHUSD-1d-1000wks-data.csv'
# ASSET_NAME = "ETH"

data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/SOLUSD-1d-1000wks-data.csv'
ASSET_NAME = "SOL"

# =============================================================================
# STRATEGY PARAMETERS
# =============================================================================
STARTING_CAPITAL = 1_000_000
BUY_PERCENT = 0.05  # 5% per signal
BB_PERIOD = 20
BB_STD = 2.0

print(f"📊 Loading {ASSET_NAME} data from: {data_path}")
data = pd.read_csv(data_path, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} days | {data.index[0].strftime('%Y-%m-%d')} to {data.index[-1].strftime('%Y-%m-%d')}")
print("=" * 70)


class BollingerBounceAccumulator(Strategy):
    buy_percent = BUY_PERCENT
    bb_period = BB_PERIOD
    bb_std = BB_STD

    def init(self):
        close = pd.Series(self.data.Close)

        # Calculate Bollinger Bands
        bb = ta.bbands(close, length=self.bb_period, std=self.bb_std)
        lower_col = f'BBL_{self.bb_period}_{self.bb_std}'
        middle_col = f'BBM_{self.bb_period}_{self.bb_std}'

        self.bb_lower = self.I(lambda: bb[lower_col].values)
        self.bb_middle = self.I(lambda: bb[middle_col].values)

        # Tracking
        self.total_coins = 0
        self.total_spent = 0
        self.buy_count = 0
        self.buy_prices = []
        self.last_buy_bar = -3

    def next(self):
        if len(self.data) < self.bb_period + 1:
            return

        remaining = STARTING_CAPITAL - self.total_spent
        if remaining <= 0:
            return

        # Avoid clustering
        if len(self.data) - self.last_buy_bar < 2:
            return

        current_price = self.data.Close[-1]
        current_low = self.data.Low[-1]
        bb_lower = self.bb_lower[-1]
        bb_middle = self.bb_middle[-1]

        if pd.isna(bb_lower):
            return

        # Buy if price touches or crosses below lower band
        if current_low <= bb_lower or current_price <= bb_lower:
            # Calculate how far below the band (for scaling)
            distance_pct = (bb_lower - current_price) / bb_middle if bb_middle > 0 else 0
            multiplier = 1.0 + max(0, distance_pct * 10)  # Scale up if way below band
            multiplier = min(multiplier, 2.0)  # Cap at 2x

            buy_pct = self.buy_percent * multiplier
            buy_amount = min(remaining * buy_pct, remaining)
            coins = buy_amount / current_price

            self.total_coins += coins
            self.total_spent += buy_amount
            self.buy_count += 1
            self.buy_prices.append(current_price)
            self.last_buy_bar = len(self.data)

            if not self.position:
                self.buy(size=0.99)


# Run backtest
bt = Backtest(data, BollingerBounceAccumulator, cash=STARTING_CAPITAL, commission=0.001)
stats = bt.run()

# =============================================================================
# RESULTS ANALYSIS
# =============================================================================
strategy = stats._strategy
STRATEGY_NAME = f"BOLLINGER BOUNCE (BB{BB_PERIOD}, {BB_STD}std)"

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
    print("\n⚠️ No signals triggered")

print(f"\n{'='*70}")
print("🌙 Moon Dev's Bollinger Bounce Accumulation Complete! 🚀")
print(f"{'='*70}")
