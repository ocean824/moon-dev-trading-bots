"""
SORTINO RATIO DIAGNOSTIC
========================

That 1253 Sortino ratio is INSANE. Let's figure out what's going on.

Sortino Ratio = (Return - Risk Free Rate) / Downside Deviation
A high Sortino means almost no downside volatility.

Let's investigate:
1. Trade distribution
2. Downside movements
3. Whether we're catching perfect bottoms
4. If the calculation is broken
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

print("🔍 SORTINO RATIO DIAGNOSTIC 🔍")
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

# Volume
data['Volume_MA'] = data['Volume'].rolling(20).mean()
data['Volume_Ratio'] = data['Volume'] / data['Volume_MA'].fillna(1)

# Shift to prevent look-ahead
for col in ['RSI', 'RSI_5m', 'Volume_Ratio']:
    data[col] = data[col].shift(1)

print(f"✅ Loaded {len(data):,} 1-minute bars")


class DiagnosticStrategy(Strategy):
    """
    Same as RealityBalanced but with detailed tracking
    """

    take_profit = 0.03   # 3% take profit
    stop_loss = 0.02     # 2% stop loss

    rsi_oversold = 35
    rsi_overbought = 65

    slippage = 0.001
    miss_prob = 0.15

    def init(self):
        self.rsi = self.I(lambda: self.data.RSI)
        self.rsi_5m = self.I(lambda: self.data.RSI_5m)
        self.volume_ratio = self.I(lambda: self.data.Volume_Ratio)

        np.random.seed(42)
        self.trade_misses = np.random.random(len(self.data)) < self.miss_prob

        self.entry_bar = None

        # DIAGNOSTIC TRACKING
        self.trade_results = []
        self.entry_prices = []
        self.exit_prices = []
        self.max_adverse_excursions = []  # Track worst point during trade
        self.bars_in_trade = []

    def next(self):
        if len(self.data) < 50:
            return

        price = self.data.Close[-1]
        rsi = self.rsi[-1]
        rsi_5m = self.rsi_5m[-1]
        current_bar = len(self.data) - 1

        if pd.isna(rsi) or pd.isna(rsi_5m):
            return

        # Track max adverse excursion during trade
        if self.position and self.entry_bar is not None:
            entry_price = self.entry_prices[-1] if self.entry_prices else price

            if self.position.is_long:
                drawdown = (entry_price - price) / entry_price
            else:
                drawdown = (price - entry_price) / entry_price

            if len(self.max_adverse_excursions) > 0:
                self.max_adverse_excursions[-1] = max(self.max_adverse_excursions[-1], drawdown)

        # Exit logic
        if self.position:
            # Can't exit same bar
            if self.entry_bar is not None and current_bar <= self.entry_bar:
                return

            should_exit = False
            if self.position.is_long and rsi > 60:
                should_exit = True
            elif self.position.is_short and rsi < 40:
                should_exit = True

            if should_exit:
                # Record trade result
                if self.entry_prices:
                    entry_p = self.entry_prices[-1]
                    exit_p = price

                    if self.position.is_long:
                        pnl = (exit_p - entry_p) / entry_p
                    else:
                        pnl = (entry_p - exit_p) / entry_p

                    self.trade_results.append(pnl)
                    self.exit_prices.append(exit_p)
                    self.bars_in_trade.append(current_bar - self.entry_bar)

                self.position.close()
                self.entry_bar = None
            return

        # Entry logic
        if not self.position:
            if self.trade_misses[current_bar]:
                return

            # BUY
            if (rsi < self.rsi_oversold and
                rsi_5m < 45 and
                self.volume_ratio[-1] > 0.8):

                entry_price = price * (1 + self.slippage)
                tp = entry_price * (1 + self.take_profit)
                sl = entry_price * (1 - self.stop_loss)

                self.buy(tp=tp, sl=sl)
                self.entry_bar = current_bar
                self.entry_prices.append(entry_price)
                self.max_adverse_excursions.append(0)

            # SELL
            elif (rsi > self.rsi_overbought and
                  rsi_5m > 55 and
                  self.volume_ratio[-1] > 0.8):

                entry_price = price * (1 - self.slippage)
                tp = entry_price * (1 - self.take_profit)
                sl = entry_price * (1 + self.stop_loss)

                self.sell(tp=tp, sl=sl)
                self.entry_bar = current_bar
                self.entry_prices.append(entry_price)
                self.max_adverse_excursions.append(0)


# Run backtest
print("\n" + "="*70)
print("RUNNING DIAGNOSTIC BACKTEST")
print("="*70)

bt = Backtest(
    data,
    DiagnosticStrategy,
    cash=1000000,
    commission=0.002,
    exclusive_orders=True
)

stats = bt.run()
strategy = bt._results._strategy

print(f"\n📊 RESULTS:")
print(f"Return: {stats['Return [%]']:.2f}%")
print(f"Sharpe Ratio: {stats['Sharpe Ratio']:.2f}")
print(f"Sortino Ratio: {stats['Sortino Ratio']:.2f}")
print(f"Win Rate: {stats['Win Rate [%]']:.1f}%")
print(f"Number of Trades: {stats['# Trades']}")

# DIAGNOSTIC ANALYSIS
print("\n" + "="*70)
print("🔍 SORTINO DIAGNOSTIC ANALYSIS")
print("="*70)

if len(strategy.trade_results) > 0:
    trade_returns = np.array(strategy.trade_results) * 100  # Convert to percentage

    print(f"\n📈 TRADE DISTRIBUTION:")
    print(f"Average Trade: {np.mean(trade_returns):.3f}%")
    print(f"Median Trade: {np.median(trade_returns):.3f}%")
    print(f"Best Trade: {np.max(trade_returns):.3f}%")
    print(f"Worst Trade: {np.min(trade_returns):.3f}%")
    print(f"Std Dev: {np.std(trade_returns):.3f}%")

    # Calculate downside deviation (for Sortino)
    negative_returns = trade_returns[trade_returns < 0]
    if len(negative_returns) > 0:
        downside_dev = np.std(negative_returns)
        print(f"\n📉 DOWNSIDE ANALYSIS:")
        print(f"Number of Losing Trades: {len(negative_returns)}")
        print(f"Average Loss: {np.mean(negative_returns):.3f}%")
        print(f"Downside Deviation: {downside_dev:.3f}%")

        # Manual Sortino calculation
        avg_return = np.mean(trade_returns)
        manual_sortino = avg_return / downside_dev if downside_dev > 0 else np.inf
        print(f"Manual Sortino Calculation: {manual_sortino:.2f}")
    else:
        print("\n⚠️ NO LOSING TRADES! This explains the infinite Sortino!")

    # Analyze max adverse excursions
    if strategy.max_adverse_excursions:
        mae_array = np.array(strategy.max_adverse_excursions) * 100
        print(f"\n🎯 MAX ADVERSE EXCURSION (worst drawdown during trades):")
        print(f"Average MAE: {np.mean(mae_array):.3f}%")
        print(f"Worst MAE: {np.max(mae_array):.3f}%")
        print(f"Trades with MAE > 1%: {np.sum(mae_array > 1)}")

    # Time in trade analysis
    if strategy.bars_in_trade:
        print(f"\n⏱️ TIME IN TRADE:")
        print(f"Average bars in trade: {np.mean(strategy.bars_in_trade):.1f}")
        print(f"Max bars in trade: {np.max(strategy.bars_in_trade)}")
        print(f"Trades closed in < 5 bars: {np.sum(np.array(strategy.bars_in_trade) < 5)}")

print("\n" + "="*70)
print("🚨 SORTINO DIAGNOSIS:")
print("="*70)

if stats['Sortino Ratio'] > 100:
    print("EXTREMELY SUSPICIOUS SORTINO! Likely causes:")
    print("1. Almost no downside volatility (winning almost every trade)")
    print("2. Losses are tiny compared to wins")
    print("3. Perfect entry timing at exact reversals")
    print("4. The strategy might be implicitly using future information")
    print("\nThis is NOT realistic for live trading!")
elif stats['Sortino Ratio'] > 10:
    print("Very high Sortino - still suspicious")
    print("The strategy is likely catching perfect reversals")
else:
    print("Sortino ratio is within reasonable bounds")

bt.plot()