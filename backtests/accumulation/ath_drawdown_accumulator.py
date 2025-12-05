"""
Moon Dev's ATH Drawdown Accumulation Strategy
=============================================
Buy at specific drawdown levels from All-Time High!

THESIS: Buy more aggressively as price drops further from ATH.
20% drawdown = small buy, 30% = medium buy, 50%+ = large buy
This is how smart money accumulates during bear markets.
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy

print("=" * 70)
print("🌙 Moon Dev's ATH Drawdown Accumulator Loading... 🚀")
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

# Drawdown levels and corresponding buy percentages
DRAWDOWN_LEVELS = {
    0.20: 0.02,  # 20% drawdown = buy 2% of remaining
    0.30: 0.04,  # 30% drawdown = buy 4%
    0.40: 0.06,  # 40% drawdown = buy 6%
    0.50: 0.08,  # 50% drawdown = buy 8%
    0.60: 0.10,  # 60% drawdown = buy 10%
    0.70: 0.15,  # 70% drawdown = buy 15% (rare opportunity)
}

print(f"📊 Loading {ASSET_NAME} data from: {data_path}")
data = pd.read_csv(data_path, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} days | {data.index[0].strftime('%Y-%m-%d')} to {data.index[-1].strftime('%Y-%m-%d')}")
print("=" * 70)


class ATHDrawdownAccumulator(Strategy):
    drawdown_levels = DRAWDOWN_LEVELS

    def init(self):
        # Calculate running ATH
        close = pd.Series(self.data.Close)
        self.ath = self.I(lambda: close.cummax().values)

        # Calculate drawdown from ATH
        def calc_drawdown(close, ath):
            dd = np.zeros(len(close))
            for i in range(len(close)):
                if ath[i] > 0:
                    dd[i] = (ath[i] - close[i]) / ath[i]
            return dd

        close_arr = close.values
        ath_arr = close.cummax().values
        self.drawdown = self.I(lambda: calc_drawdown(close_arr, ath_arr))

        # Track which levels we've bought at for each ATH cycle
        self.levels_bought = set()
        self.last_ath = 0

        # Tracking
        self.total_coins = 0
        self.total_spent = 0
        self.buy_count = 0
        self.buy_prices = []
        self.buy_drawdowns = []

    def next(self):
        if len(self.data) < 10:
            return

        remaining = STARTING_CAPITAL - self.total_spent
        if remaining <= 0:
            return

        current_price = self.data.Close[-1]
        current_ath = self.ath[-1]
        current_dd = self.drawdown[-1]

        # Reset levels when we hit new ATH
        if current_ath > self.last_ath * 1.05:  # 5% higher ATH
            self.levels_bought = set()
            self.last_ath = current_ath

        # Check each drawdown level
        for dd_level, buy_pct in sorted(self.drawdown_levels.items()):
            # If we're at this drawdown level and haven't bought it yet
            if current_dd >= dd_level and dd_level not in self.levels_bought:
                buy_amount = min(remaining * buy_pct, remaining)
                coins = buy_amount / current_price

                self.total_coins += coins
                self.total_spent += buy_amount
                self.buy_count += 1
                self.buy_prices.append(current_price)
                self.buy_drawdowns.append(current_dd)
                self.levels_bought.add(dd_level)

                # Update remaining for potential multiple level hits
                remaining = STARTING_CAPITAL - self.total_spent

                if not self.position:
                    self.buy(size=0.99)

                # Only buy one level per bar
                break


# Run backtest
bt = Backtest(data, ATHDrawdownAccumulator, cash=STARTING_CAPITAL, commission=0.001)
stats = bt.run()

# =============================================================================
# RESULTS ANALYSIS
# =============================================================================
strategy = stats._strategy
STRATEGY_NAME = "ATH DRAWDOWN (20-70% levels)"

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
    if strategy.buy_drawdowns:
        avg_dd = np.mean(strategy.buy_drawdowns) * 100
        max_dd_bought = max(strategy.buy_drawdowns) * 100
        print(f"    📉 Avg Drawdown at Buy: {avg_dd:.1f}% | Max Drawdown Bought: {max_dd_bought:.1f}%")

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
print("🌙 Moon Dev's ATH Drawdown Accumulation Complete! 🚀")
print(f"{'='*70}")
