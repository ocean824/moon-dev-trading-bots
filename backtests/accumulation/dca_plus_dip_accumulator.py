"""
Moon Dev's DCA Plus Dip Boost Accumulation Strategy
===================================================
Regular monthly DCA + extra buying on significant dips!

THESIS: Combine the consistency of DCA with opportunistic dip buying.
Base amount every month + bonus buys when price drops significantly.
Best of both worlds approach.
"""

import pandas as pd
import numpy as np
import pandas_ta as ta
from backtesting import Backtest, Strategy

print("=" * 70)
print("🌙 Moon Dev's DCA + Dip Boost Accumulator Loading... 🚀")
print("=" * 70)

# =============================================================================
# DATA CONFIGURATION
# =============================================================================
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1d-1000wks-data.csv'
ASSET_NAME = "BTC"

# data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/ETHUSD-1d-1000wks-data.csv'
# ASSET_NAME = "ETH"

# data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/SOLUSD-1d-1000wks-data.csv'
# ASSET_NAME = "SOL"

# =============================================================================
# STRATEGY PARAMETERS
# =============================================================================
STARTING_CAPITAL = 1_000_000
MONTHLY_DCA_PERCENT = 0.005  # 0.5% of starting capital per month (base DCA)
DIP_THRESHOLD = 0.05  # 5% daily drop triggers dip buy
DIP_BUY_PERCENT = 0.02  # 2% extra on dips
RESERVE_FOR_DIPS = 0.30  # Reserve 30% of capital specifically for dips

print(f"📊 Loading {ASSET_NAME} data from: {data_path}")
data = pd.read_csv(data_path, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} days | {data.index[0].strftime('%Y-%m-%d')} to {data.index[-1].strftime('%Y-%m-%d')}")
print("=" * 70)


class DCAPlusDipAccumulator(Strategy):
    monthly_dca = MONTHLY_DCA_PERCENT
    dip_threshold = DIP_THRESHOLD
    dip_buy_pct = DIP_BUY_PERCENT
    dip_reserve = RESERVE_FOR_DIPS

    def init(self):
        close = pd.Series(self.data.Close)

        # Calculate daily returns
        self.daily_return = self.I(lambda x: x.pct_change().values, close)

        # Track month changes
        months = pd.Series(self.data.index).dt.month.values
        month_change = np.zeros(len(months))
        for i in range(1, len(months)):
            if months[i] != months[i-1]:
                month_change[i] = 1
        self.new_month = self.I(lambda: month_change)

        # Tracking
        self.total_coins = 0
        self.total_spent = 0
        self.buy_count = 0
        self.dca_buys = 0
        self.dip_buys = 0
        self.buy_prices = []

        # Separate budgets
        self.dca_budget = STARTING_CAPITAL * (1 - self.dip_reserve)
        self.dip_budget = STARTING_CAPITAL * self.dip_reserve
        self.dca_spent = 0
        self.dip_spent = 0

    def next(self):
        if len(self.data) < 5:
            return

        current_price = self.data.Close[-1]
        daily_ret = self.daily_return[-1]
        is_new_month = self.new_month[-1]

        # 1. MONTHLY DCA BUY
        if is_new_month > 0 and self.dca_spent < self.dca_budget:
            buy_amount = min(STARTING_CAPITAL * self.monthly_dca, self.dca_budget - self.dca_spent)
            if buy_amount > 0:
                coins = buy_amount / current_price
                self.total_coins += coins
                self.total_spent += buy_amount
                self.dca_spent += buy_amount
                self.buy_count += 1
                self.dca_buys += 1
                self.buy_prices.append(current_price)

        # 2. DIP BUYING
        if not pd.isna(daily_ret) and daily_ret < -self.dip_threshold:
            if self.dip_spent < self.dip_budget:
                # Scale buy with dip size
                dip_magnitude = abs(daily_ret)
                multiplier = min(dip_magnitude / self.dip_threshold, 3.0)

                buy_amount = min(
                    STARTING_CAPITAL * self.dip_buy_pct * multiplier,
                    self.dip_budget - self.dip_spent
                )

                if buy_amount > 0:
                    coins = buy_amount / current_price
                    self.total_coins += coins
                    self.total_spent += buy_amount
                    self.dip_spent += buy_amount
                    self.buy_count += 1
                    self.dip_buys += 1
                    self.buy_prices.append(current_price)

        # Update position for visualization
        if self.buy_count > 0 and not self.position:
            self.buy(size=0.99)


# Run backtest
bt = Backtest(data, DCAPlusDipAccumulator, cash=STARTING_CAPITAL, commission=0.001)
stats = bt.run()

# =============================================================================
# RESULTS ANALYSIS
# =============================================================================
strategy = stats._strategy
STRATEGY_NAME = f"DCA + DIP BOOST (monthly + {int(DIP_THRESHOLD*100)}% dip buys)"

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
    print(f"    📈 Total Buys: {strategy.buy_count} (DCA: {strategy.dca_buys}, Dips: {strategy.dip_buys})")
    print(f"    💰 Capital Used: {capital_deployed_pct:.1f}% (DCA: ${strategy.dca_spent:,.0f}, Dips: ${strategy.dip_spent:,.0f})")

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
print("🌙 Moon Dev's DCA + Dip Boost Accumulation Complete! 🚀")
print(f"{'='*70}")
