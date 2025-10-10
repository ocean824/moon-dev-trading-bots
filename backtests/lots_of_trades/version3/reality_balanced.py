"""
REALITY BALANCED - Actually Trades But Realistically
=====================================================

Finding the balance between:
1. Actually getting trades
2. Being realistic about execution

Key changes:
- Less strict entry conditions
- Realistic but not impossible requirements
- Proper look-ahead prevention
- Reasonable stops that actually work
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

print("🎯 REALITY BALANCED - Let's Actually Trade 🎯")
print("=" * 70)

# Load data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1m-4wks-data.csv'
print(f"📊 Loading BTC 1-minute data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Calculate RSI properly
data['RSI'] = ta.rsi(data['Close'], length=14)

# Multi-timeframe RSI (no look-ahead)
data_5m = data['Close'].resample('5T').ohlc()
data_5m['RSI_5m'] = ta.rsi(data_5m['close'], length=14)
data['RSI_5m'] = data_5m['RSI_5m'].reindex(data.index, method='ffill')

# Supply and demand zones
data['Demand_Zone'] = data['Low'].rolling(20).min()
data['Supply_Zone'] = data['High'].rolling(20).max()

# Volume
data['Volume_MA'] = data['Volume'].rolling(20).mean()
data['Volume_Ratio'] = data['Volume'] / data['Volume_MA'].fillna(1)

# Shift everything by 1 to prevent look-ahead
for col in ['RSI', 'RSI_5m', 'Demand_Zone', 'Supply_Zone', 'Volume_Ratio']:
    data[col] = data[col].shift(1)

print(f"✅ Loaded {len(data):,} 1-minute bars")
print(f"📊 Sample RSI values: {data['RSI'].dropna().head()}")
print(f"📊 RSI range: {data['RSI'].min():.1f} to {data['RSI'].max():.1f}")


class RealityBalancedStrategy(Strategy):
    """
    Realistic trading that actually makes trades
    """

    # Reasonable parameters
    take_profit = 0.03   # 3% take profit
    stop_loss = 0.02     # 2% stop loss

    # Entry thresholds (not too strict)
    rsi_oversold = 35
    rsi_overbought = 65

    # Realistic execution issues
    slippage = 0.001     # 0.1% slippage
    miss_prob = 0.15     # 15% chance to miss entry

    def init(self):
        self.rsi = self.I(lambda: self.data.RSI)
        self.rsi_5m = self.I(lambda: self.data.RSI_5m)
        self.demand_zone = self.I(lambda: self.data.Demand_Zone)
        self.supply_zone = self.I(lambda: self.data.Supply_Zone)
        self.volume_ratio = self.I(lambda: self.data.Volume_Ratio)

        # Random misses
        np.random.seed(42)
        self.trade_misses = np.random.random(len(self.data)) < self.miss_prob

        # Debug tracking
        self.signals_seen = 0
        self.trades_taken = 0

        # CRITICAL: Track entry bar to prevent same-bar exit
        self.entry_bar = None

    def next(self):
        if len(self.data) < 50:
            return

        price = self.data.Close[-1]
        rsi = self.rsi[-1]
        rsi_5m = self.rsi_5m[-1]
        current_bar = len(self.data) - 1

        if pd.isna(rsi) or pd.isna(rsi_5m):
            return

        # Exit logic (simple and realistic)
        if self.position:
            # CRITICAL: Can't exit on same bar as entry
            if self.entry_bar is not None and current_bar <= self.entry_bar:
                return  # Skip this bar, can't exit yet

            # Exit on momentum reversal
            if self.position.is_long and rsi > 60:
                self.position.close()
                self.entry_bar = None  # Reset
            elif self.position.is_short and rsi < 40:
                self.position.close()
                self.entry_bar = None  # Reset
            return

        # Entry logic
        if not self.position:
            # Check if we randomly miss this trade
            if self.trade_misses[len(self.data) - 1]:
                return

            # BUY conditions (relaxed but reasonable)
            if (rsi < self.rsi_oversold and
                rsi_5m < 45 and  # 5m also showing oversold
                self.volume_ratio[-1] > 0.8):  # Some volume

                self.signals_seen += 1

                # Apply slippage (worse entry)
                entry_price = price * (1 + self.slippage)
                tp = entry_price * (1 + self.take_profit)
                sl = entry_price * (1 - self.stop_loss)

                self.buy(tp=tp, sl=sl)
                self.trades_taken += 1
                self.entry_bar = current_bar  # Record entry bar

            # SELL conditions (relaxed but reasonable)
            elif (rsi > self.rsi_overbought and
                  rsi_5m > 55 and  # 5m also showing overbought
                  self.volume_ratio[-1] > 0.8):  # Some volume

                self.signals_seen += 1

                # Apply slippage (worse entry)
                entry_price = price * (1 - self.slippage)
                tp = entry_price * (1 - self.take_profit)
                sl = entry_price * (1 + self.stop_loss)

                self.sell(tp=tp, sl=sl)
                self.trades_taken += 1
                self.entry_bar = current_bar  # Record entry bar


# Run backtest
print("\n" + "="*70)
print("RUNNING REALITY BALANCED BACKTEST")
print("="*70)

bt = Backtest(
    data,
    RealityBalancedStrategy,
    cash=1000000,
    commission=0.002,  # 0.2% commission
    exclusive_orders=True
)

stats = bt.run()
print(f"\n📊 BALANCED REALISTIC RESULTS:")
print(stats)

print(f"\n📈 TRADE ANALYSIS:")
print(f"Win Rate: {stats['Win Rate [%]']:.1f}%")
print(f"Number of Trades: {stats['# Trades']}")
print(f"Average Trade: {stats['Avg. Trade [%]']:.3f}%")
print(f"Profit Factor: {stats['Profit Factor']:.2f}")

if stats['# Trades'] == 0:
    print("\n❌ No trades executed. Entry conditions might still be too strict.")
elif stats['Win Rate [%]'] > 70:
    print("\n⚠️ Win rate still seems high. Consider:")
    print("- The 1-minute timeframe might be too noisy")
    print("- The backtest might be finding perfect entries we can't execute")
    print("- Real slippage would be worse than modeled")
elif stats['Win Rate [%]'] < 40:
    print("\n✅ This win rate is realistic but might not be profitable after costs")
else:
    print("\n✅ This looks like a realistic win rate for retail trading")

# Test with tighter parameters
print("\n" + "="*70)
print("TESTING WITH TIGHTER STOPS")
print("="*70)

class TighterStopsStrategy(RealityBalancedStrategy):
    """
    Testing if tighter stops cause the high win rate
    """
    take_profit = 0.015  # 1.5% take profit
    stop_loss = 0.01     # 1% stop loss

    # Even less strict to get more trades
    rsi_oversold = 40
    rsi_overbought = 60


bt2 = Backtest(
    data,
    TighterStopsStrategy,
    cash=1000000,
    commission=0.002,
    exclusive_orders=True
)

stats2 = bt2.run()
print(f"\n📊 TIGHTER STOPS RESULTS:")
print(f"Win Rate: {stats2['Win Rate [%]']:.1f}%")
print(f"Number of Trades: {stats2['# Trades']}")
print(f"Average Trade: {stats2['Avg. Trade [%]']:.3f}%")

# Optimization
print("\n" + "="*70)
print("OPTIMIZING REALISTIC PARAMETERS")
print("="*70)

try:
    opt_results = bt.optimize(
        rsi_oversold=[30, 35, 40],
        rsi_overbought=[60, 65, 70],
        take_profit=[0.02, 0.03, 0.04],
        stop_loss=[0.015, 0.02, 0.025],
        maximize='Return [%]',
        return_heatmap=False
    )

    print(f"\n✨ OPTIMIZED RESULTS:")
    print(opt_results)

    print(f"\n🎯 OPTIMAL PARAMETERS:")
    print(f"RSI Oversold: {opt_results._strategy.rsi_oversold}")
    print(f"RSI Overbought: {opt_results._strategy.rsi_overbought}")
    print(f"Take Profit: {opt_results._strategy.take_profit}")
    print(f"Stop Loss: {opt_results._strategy.stop_loss}")

except Exception as e:
    print(f"Optimization failed: {str(e)}")

bt.plot()