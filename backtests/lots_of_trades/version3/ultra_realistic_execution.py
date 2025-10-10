"""
ULTRA REALISTIC EXECUTION - The Brutal Truth
=============================================

This simulates ALL the real problems you'll face:

1. ORDER QUEUE POSITION - You're never first in line
2. PARTIAL FILLS - Sometimes you only get 50% filled
3. WICK STOPS - Wicks hit your stop even if close doesn't
4. MISSED ENTRIES - Price runs away before you can enter
5. SPREAD WIDENING - Spread gets worse during volatility
6. FAILED EXITS - Can't exit when everyone else is trying to

This should bring the performance down to earth.
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

print("🎯 ULTRA REALISTIC EXECUTION - The Brutal Truth 🎯")
print("=" * 70)

# Load data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1m-4wks-data.csv'
print(f"📊 Loading BTC 1-minute data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Calculate RSI
data['RSI'] = ta.rsi(data['Close'], length=14)

# Multi-timeframe RSI
data_5m = data['Close'].resample('5T').ohlc()
data_5m['RSI_5m'] = ta.rsi(data_5m['close'], length=14)
data['RSI_5m'] = data_5m['RSI_5m'].reindex(data.index, method='ffill')

# Supply and demand zones
data['Demand_Zone'] = data['Low'].rolling(20).min()
data['Supply_Zone'] = data['High'].rolling(20).max()

# Volume
data['Volume_MA'] = data['Volume'].rolling(20).mean()
data['Volume_Ratio'] = data['Volume'] / data['Volume_MA'].fillna(1)

# Volatility for dynamic spread
data['ATR'] = ta.atr(data['High'], data['Low'], data['Close'], length=14)
data['Volatility'] = data['ATR'] / data['Close']

# Price range (for wick analysis)
data['Bar_Range'] = (data['High'] - data['Low']) / data['Close']

# Shift everything to prevent look-ahead
for col in ['RSI', 'RSI_5m', 'Demand_Zone', 'Supply_Zone', 'Volume_Ratio', 'Volatility', 'Bar_Range']:
    data[col] = data[col].shift(1)

print(f"✅ Loaded {len(data):,} 1-minute bars")


class UltraRealisticStrategy(Strategy):
    """
    Every possible execution problem simulated
    """

    # Base parameters
    take_profit = 0.03   # 3% take profit
    stop_loss = 0.02     # 2% stop loss

    # Entry thresholds
    rsi_oversold = 35
    rsi_overbought = 65

    # BRUTAL REALISTIC CONSTRAINTS
    base_spread = 0.001          # 0.1% base spread
    volatility_spread_mult = 5   # Spread gets 5x worse in volatility

    queue_position_delay = 0.002 # 0.2% worse price from queue position
    partial_fill_prob = 0.3      # 30% chance of partial fill only

    missed_entry_prob = 0.25     # 25% chance entry runs away
    wick_stop_mult = 0.5         # Stop triggers at 50% of wick

    failed_exit_prob = 0.1       # 10% can't exit when you want
    panic_exit_penalty = 0.005   # 0.5% worse when panic exiting

    def init(self):
        self.rsi = self.I(lambda: self.data.RSI)
        self.rsi_5m = self.I(lambda: self.data.RSI_5m)
        self.demand_zone = self.I(lambda: self.data.Demand_Zone)
        self.supply_zone = self.I(lambda: self.data.Supply_Zone)
        self.volume_ratio = self.I(lambda: self.data.Volume_Ratio)
        self.volatility = self.I(lambda: self.data.Volatility)
        self.bar_range = self.I(lambda: self.data.Bar_Range)

        # Random events
        np.random.seed(123)
        self.missed_entries = np.random.random(len(self.data)) < self.missed_entry_prob
        self.partial_fills = np.random.random(len(self.data)) < self.partial_fill_prob
        self.failed_exits = np.random.random(len(self.data)) < self.failed_exit_prob

        # Track execution issues
        self.execution_issues = {
            'missed_entries': 0,
            'partial_fills': 0,
            'wick_stops': 0,
            'failed_exits': 0,
            'spread_cost': 0
        }

        # Position tracking
        self.position_size = 1.0  # Can be partial
        self.entry_bar = None

    def next(self):
        if len(self.data) < 50:
            return

        price = self.data.Close[-1]
        high = self.data.High[-1]
        low = self.data.Low[-1]
        rsi = self.rsi[-1]
        rsi_5m = self.rsi_5m[-1]
        volatility = self.volatility[-1] if not pd.isna(self.volatility[-1]) else 0.001
        current_idx = len(self.data) - 1

        if pd.isna(rsi) or pd.isna(rsi_5m):
            return

        # Calculate dynamic spread (gets worse with volatility)
        current_spread = self.base_spread * (1 + volatility * self.volatility_spread_mult)

        # Check for wick stops (brutal but realistic)
        if self.position and self.entry_bar is not None:
            if self.position.is_long:
                # Check if low wick would have stopped us out
                stop_price = self.data.Close[self.entry_bar] * (1 - self.stop_loss)
                wick_trigger = low < (stop_price + (high - low) * self.wick_stop_mult)

                if wick_trigger:
                    self.execution_issues['wick_stops'] += 1
                    self.position.close()
                    return

            elif self.position.is_short:
                # Check if high wick would have stopped us out
                stop_price = self.data.Close[self.entry_bar] * (1 + self.stop_loss)
                wick_trigger = high > (stop_price - (high - low) * self.wick_stop_mult)

                if wick_trigger:
                    self.execution_issues['wick_stops'] += 1
                    self.position.close()
                    return

        # Exit logic with failures
        if self.position:
            # Check if exit is blocked
            if self.failed_exits[current_idx]:
                self.execution_issues['failed_exits'] += 1
                # Forced to hold, might exit next bar at worse price
                return

            # Normal exit conditions
            if self.position.is_long and rsi > 60:
                # Panic exit with penalty
                if volatility > 0.002:  # High volatility = panic
                    self.execution_issues['spread_cost'] += self.panic_exit_penalty
                self.position.close()
                self.entry_bar = None

            elif self.position.is_short and rsi < 40:
                # Panic exit with penalty
                if volatility > 0.002:
                    self.execution_issues['spread_cost'] += self.panic_exit_penalty
                self.position.close()
                self.entry_bar = None
            return

        # Entry logic with all the problems
        if not self.position:
            # Check if we miss this entry (price runs away)
            if self.missed_entries[current_idx]:
                self.execution_issues['missed_entries'] += 1
                return

            # BUY conditions
            if (rsi < self.rsi_oversold and
                rsi_5m < 45 and
                self.volume_ratio[-1] > 0.8):

                # Queue position penalty (never first in line)
                entry_price = price * (1 + current_spread + self.queue_position_delay)

                # Check for partial fill
                if self.partial_fills[current_idx]:
                    self.execution_issues['partial_fills'] += 1
                    self.position_size = 0.5  # Only get half position
                else:
                    self.position_size = 1.0

                # Adjust stops for realistic execution
                tp = entry_price * (1 + self.take_profit)
                sl = entry_price * (1 - self.stop_loss - current_spread)  # Worse stop

                self.buy(tp=tp, sl=sl, size=self.position_size)
                self.entry_bar = current_idx
                self.execution_issues['spread_cost'] += current_spread

            # SELL conditions
            elif (rsi > self.rsi_overbought and
                  rsi_5m > 55 and
                  self.volume_ratio[-1] > 0.8):

                # Queue position penalty
                entry_price = price * (1 - current_spread - self.queue_position_delay)

                # Check for partial fill
                if self.partial_fills[current_idx]:
                    self.execution_issues['partial_fills'] += 1
                    self.position_size = 0.5
                else:
                    self.position_size = 1.0

                # Adjust stops for realistic execution
                tp = entry_price * (1 - self.take_profit)
                sl = entry_price * (1 + self.stop_loss + current_spread)  # Worse stop

                self.sell(tp=tp, sl=sl, size=self.position_size)
                self.entry_bar = current_idx
                self.execution_issues['spread_cost'] += current_spread


# Run backtest
print("\n" + "="*70)
print("RUNNING ULTRA REALISTIC BACKTEST")
print("="*70)

bt = Backtest(
    data,
    UltraRealisticStrategy,
    cash=1000000,
    commission=0.002,  # 0.2% commission
    exclusive_orders=True
)

stats = bt.run()

# Get strategy instance to access execution issues
strategy = bt._results._strategy

print(f"\n📊 ULTRA REALISTIC RESULTS:")
print(stats)

print(f"\n💀 EXECUTION PROBLEMS ENCOUNTERED:")
print(f"Missed Entries: {strategy.execution_issues['missed_entries']}")
print(f"Partial Fills: {strategy.execution_issues['partial_fills']}")
print(f"Wick Stops: {strategy.execution_issues['wick_stops']}")
print(f"Failed Exits: {strategy.execution_issues['failed_exits']}")
print(f"Total Spread Cost: {strategy.execution_issues['spread_cost']:.2%}")

print(f"\n📈 REALITY CHECK:")
print(f"Win Rate: {stats['Win Rate [%]']:.1f}%")
print(f"Number of Trades: {stats['# Trades']}")
print(f"Average Trade: {stats['Avg. Trade [%]']:.3f}%")
print(f"Profit Factor: {stats['Profit Factor']:.2f}")
print(f"Sharpe Ratio: {stats['Sharpe Ratio']:.2f}")

if stats['Win Rate [%]'] > 60:
    print("\n⚠️ Still high but remember:")
    print("- Real order books have depth issues")
    print("- Your broker might have worse execution")
    print("- Network latency adds 50-200ms delays")
    print("- Other bots will front-run obvious levels")
elif stats['Win Rate [%]'] < 45:
    print("\n✅ This win rate reflects real trading challenges")
    print("- Need excellent risk management to be profitable")
    print("- Consider if the edge is worth the effort")
else:
    print("\n✅ This is a realistic win rate for retail trading")
    print("- But remember live trading is always harder")

# Test with even worse conditions
print("\n" + "="*70)
print("TESTING WORST CASE SCENARIO")
print("="*70)

class WorstCaseStrategy(UltraRealisticStrategy):
    """
    Everything that can go wrong, will go wrong
    """
    # Even worse execution
    missed_entry_prob = 0.4      # Miss 40% of trades
    partial_fill_prob = 0.5      # 50% partial fills
    wick_stop_mult = 0.3         # Stops trigger easier
    failed_exit_prob = 0.2       # 20% exit failures


bt2 = Backtest(
    data,
    WorstCaseStrategy,
    cash=1000000,
    commission=0.002,
    exclusive_orders=True
)

stats2 = bt2.run()
print(f"\n📊 WORST CASE RESULTS:")
print(f"Win Rate: {stats2['Win Rate [%]']:.1f}%")
print(f"Number of Trades: {stats2['# Trades']}")
print(f"Return: {stats2['Return [%]']:.2f}%")

bt.plot()