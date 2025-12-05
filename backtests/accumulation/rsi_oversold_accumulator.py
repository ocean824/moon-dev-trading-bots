"""
Moon Dev's RSI Oversold Accumulation Strategy
=============================================
Accumulation strategy for funds/whales that only BUY - never sell.

THESIS: Michael Saylor / MicroStrategy style accumulation could be 20-30%+
more efficient with algorithmic patience instead of market buying.

STRATEGY LOGIC:
- Only BUY when RSI shows oversold conditions (RSI < 30)
- This indicates fear / panic = good accumulation opportunity
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
print("🌙 Moon Dev's RSI Oversold Accumulation Strategy Loading... 🚀")
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
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/SOLUSD-1d-1000wks-data.csv'
ASSET_NAME = "SOL"

# =============================================================================
# STRATEGY PARAMETERS
# =============================================================================
STARTING_CAPITAL = 1_000_000  # $1M starting capital
BUY_PERCENT = 0.05  # Buy 5% of remaining capital per signal
RSI_PERIOD = 14  # Standard RSI period
RSI_OVERSOLD = 30  # RSI threshold for oversold (buy signal)
MIN_DAYS_BETWEEN_BUYS = 1  # Minimum days between buys to avoid clustering

print(f"📊 Loading {ASSET_NAME} data from: {data_path}")

# Load and prepare data
data = pd.read_csv(data_path, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()  # Ensure chronological order
data = data.dropna()

print(f"✅ Data loaded! {len(data)} days of data")
print(f"📅 Date range: {data.index[0].strftime('%Y-%m-%d')} to {data.index[-1].strftime('%Y-%m-%d')}")
print(f"💰 Starting capital: ${STARTING_CAPITAL:,.0f}")
print(f"📈 Buy {BUY_PERCENT*100:.0f}% per signal | RSI < {RSI_OVERSOLD} = Buy")
print("=" * 70)


class RSIOversoldAccumulator(Strategy):
    """
    RSI Oversold Accumulation Strategy
    - Only buys, never sells
    - Buys when: RSI drops below oversold threshold (default 30)
    - Deploys X% of remaining capital per signal
    """

    # Parameters (can be optimized)
    buy_percent = BUY_PERCENT
    rsi_period = RSI_PERIOD
    rsi_oversold = RSI_OVERSOLD
    min_days_between = MIN_DAYS_BETWEEN_BUYS

    def init(self):
        print(f"🔧 Moon Dev Initializing {ASSET_NAME} RSI Accumulator...")

        # Calculate RSI
        self.rsi = self.I(
            ta.rsi,
            pd.Series(self.data.Close),
            length=self.rsi_period
        )

        # Track accumulation metrics
        self.total_coins = 0
        self.total_spent = 0
        self.buy_count = 0
        self.buy_prices = []
        self.buy_dates = []
        self.buy_amounts = []
        self.last_buy_bar = -999  # Track last buy to avoid clustering

        print("✅ RSI indicator ready! Looking for oversold opportunities...")

    def next(self):
        # Skip if not enough data for RSI
        if len(self.data) < self.rsi_period + 1:
            return

        # Skip if we've spent all capital
        remaining_capital = STARTING_CAPITAL - self.total_spent
        if remaining_capital <= 0:
            return

        # Get current values
        current_rsi = self.rsi[-1]
        current_price = self.data.Close[-1]
        current_bar = len(self.data)

        # Skip if RSI not ready
        if pd.isna(current_rsi):
            return

        # Check minimum days between buys
        bars_since_last_buy = current_bar - self.last_buy_bar
        if bars_since_last_buy < self.min_days_between:
            return

        # ACCUMULATION SIGNAL:
        # RSI drops below oversold threshold
        if current_rsi < self.rsi_oversold:
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
            self.last_buy_bar = current_bar

            # Also execute in backtesting framework for visualization
            if not self.position:
                self.buy(size=0.99)  # Small position just for tracking

            # Print buy signal
            print(f"🟢 BUY #{self.buy_count}: {coins_to_buy:.6f} {ASSET_NAME} @ ${current_price:,.2f} | "
                  f"RSI: {current_rsi:.1f} | "
                  f"Spent: ${self.total_spent:,.0f}")


# Run the backtest
bt = Backtest(
    data,
    RSIOversoldAccumulator,
    cash=STARTING_CAPITAL,
    commission=0.001,  # 0.1% commission
    exclusive_orders=True
)

print("\n" + "=" * 70)
print("🚀 Moon Dev Running RSI Oversold Accumulation Backtest...")
print("=" * 70 + "\n")

stats = bt.run()

# =============================================================================
# ACCUMULATION ANALYSIS - The Important Part!
# =============================================================================
print("\n" + "=" * 70)
print("📊 MOON DEV'S ACCUMULATION RESULTS")
print("=" * 70)

# Get strategy instance to access accumulation data
strategy = stats._strategy

# KEY PRICES
first_day_price = data['Close'].iloc[0]
final_price = data['Close'].iloc[-1]
first_date = data.index[0].strftime('%Y-%m-%d')
last_date = data.index[-1].strftime('%Y-%m-%d')

# =============================================================================
# COMPARISON 1: Day 1 Lump Sum (bought everything on first day)
# =============================================================================
day1_coins = STARTING_CAPITAL / first_day_price
day1_final_value = day1_coins * final_price

# =============================================================================
# COMPARISON 2: Daily DCA (spread evenly across all days)
# =============================================================================
total_days = len(data)
dca_daily_amount = STARTING_CAPITAL / total_days
dca_coins = (dca_daily_amount / data['Close']).sum()
dca_avg_price = STARTING_CAPITAL / dca_coins
dca_final_value = dca_coins * final_price

# =============================================================================
# OUR STRATEGY RESULTS
# =============================================================================
if strategy.total_coins > 0:
    our_avg_price = strategy.total_spent / strategy.total_coins
    our_final_value = strategy.total_coins * final_price
    capital_deployed_pct = (strategy.total_spent / STARTING_CAPITAL) * 100

    print(f"\n{'='*70}")
    print(f"🎯 RSI OVERSOLD ACCUMULATOR - {ASSET_NAME}")
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

    print(f"\n3️⃣  🌙 THIS STRATEGY (RSI < {RSI_OVERSOLD} = Buy):")
    print(f"    💰 {ASSET_NAME} Accumulated: {strategy.total_coins:,.6f}")
    print(f"    📊 Average Price: ${our_avg_price:,.2f}")
    print(f"    💵 Value Today: ${our_final_value:,.0f}")
    print(f"    📈 Buy Signals: {strategy.buy_count} | Capital Used: {capital_deployed_pct:.1f}%")

    print(f"\n{'='*70}")
    print(f"🏆 WINNER COMPARISON")
    print(f"{'='*70}")

    # vs Day 1
    vs_day1_coins = strategy.total_coins - day1_coins
    vs_day1_pct = ((strategy.total_coins - day1_coins) / day1_coins) * 100
    vs_day1_value = our_final_value - day1_final_value

    # vs DCA
    vs_dca_coins = strategy.total_coins - dca_coins
    vs_dca_pct = ((strategy.total_coins - dca_coins) / dca_coins) * 100
    vs_dca_value = our_final_value - dca_final_value

    print(f"\n📊 Strategy vs Day 1 Lump Sum:")
    print(f"    {ASSET_NAME} Difference: {vs_day1_coins:+,.6f} ({vs_day1_pct:+.1f}%)")
    print(f"    Value Difference: ${vs_day1_value:+,.0f}")

    print(f"\n📊 Strategy vs Daily DCA:")
    print(f"    {ASSET_NAME} Difference: {vs_dca_coins:+,.6f} ({vs_dca_pct:+.1f}%)")
    print(f"    Value Difference: ${vs_dca_value:+,.0f}")

    # Determine winner
    all_coins = {'Day 1 Lump Sum': day1_coins, 'Daily DCA': dca_coins, 'This Strategy': strategy.total_coins}
    winner = max(all_coins, key=all_coins.get)
    print(f"\n🏆 MOST {ASSET_NAME} ACCUMULATED: {winner} with {all_coins[winner]:,.6f} {ASSET_NAME}!")

else:
    print("\n⚠️ No accumulation signals triggered!")
    print("   Try adjusting parameters:")
    print(f"   - Raise rsi_oversold threshold (current: {RSI_OVERSOLD})")

print("\n" + "=" * 70)
print("🌙 Moon Dev's RSI Oversold Accumulation Complete! 🚀")
print("=" * 70)

# Show the plot
bt.plot(open_browser=False)
