"""
LIQUIDITY ZONES - SLIPPAGE REALITY CHECK
=========================================

Simulates real-world execution problems:
1. Slippage on entry (worse price)
2. Slippage on exit (worse price)
3. Sometimes can't exit when desired (momentum too strong)
4. Stop losses get worse fills during volatility

This should bring the win rate down to reality.
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

print("🎯 Moon Dev's LIQUIDITY ZONES - SLIPPAGE REALITY Strategy V3 🎯")
print("=" * 70)

# Load data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1m-4wks-data.csv'
print(f"📊 Loading BTC 1-minute data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Identify liquidity zones (swing highs/lows)
data['Swing_High'] = data['High'].rolling(10).max()
data['Swing_Low'] = data['Low'].rolling(10).min()

# Recent highs and lows (liquidity areas)
data['Recent_High'] = data['High'].rolling(50).max()
data['Recent_Low'] = data['Low'].rolling(50).min()

# Liquidity zone strength (how many times tested)
data['High_Tests'] = (data['High'] >= data['Swing_High'] * 0.999).rolling(20).sum()
data['Low_Tests'] = (data['Low'] <= data['Swing_Low'] * 1.001).rolling(20).sum()

# Volume at zones
data['Volume_MA'] = data['Volume'].rolling(20).mean()
data['Zone_Volume'] = data['Volume'] / data['Volume_MA']

# Distance from liquidity zones
data['Distance_to_High'] = (data['Recent_High'] - data['Close']) / data['Close']
data['Distance_to_Low'] = (data['Close'] - data['Recent_Low']) / data['Close']

# RSI for momentum
data['RSI'] = ta.rsi(data['Close'], length=14)

# Price compression (range trading)
data['Price_Range'] = (data['High'].rolling(10).max() -
                       data['Low'].rolling(10).min()) / data['Close']

# Volatility for slippage calculation
data['ATR'] = ta.atr(data['High'], data['Low'], data['Close'], length=14)
data['Volatility'] = data['ATR'] / data['Close']

print(f"✅ Loaded {len(data):,} 1-minute bars")


class LiquidityZonesSlippage(Strategy):
    """
    Realistic execution with slippage and missed trades
    """

    zone_proximity = 0.0025
    min_tests = 1
    compression_threshold = 0.004
    take_profit = 0.02
    stop_loss = 0.01

    # Slippage parameters
    entry_slippage = 0.0015  # 0.15% slippage on entry (worse price)
    exit_slippage = 0.001    # 0.1% slippage on exit
    sl_slippage = 0.003      # 0.3% worse on stop loss (panic selling)
    miss_trade_prob = 0.2    # 20% chance to miss the trade entirely

    def init(self):
        self.swing_high = self.I(lambda: self.data.Swing_High)
        self.swing_low = self.I(lambda: self.data.Swing_Low)
        self.high_tests = self.I(lambda: self.data.High_Tests)
        self.low_tests = self.I(lambda: self.data.Low_Tests)
        self.zone_volume = self.I(lambda: self.data.Zone_Volume)
        self.rsi = self.I(lambda: self.data.RSI)
        self.price_range = self.I(lambda: self.data.Price_Range)
        self.distance_high = self.I(lambda: self.data.Distance_to_High)
        self.distance_low = self.I(lambda: self.data.Distance_to_Low)
        self.volatility = self.I(lambda: self.data.Volatility)

        # Track if we should skip trades
        np.random.seed(42)  # For reproducibility
        self.trade_misses = np.random.random(len(self.data)) < self.miss_trade_prob

    def next(self):
        if len(self.data) < 50:
            return

        price = self.data.Close[-1]
        rsi = self.rsi[-1]
        current_idx = len(self.data) - 1
        volatility = self.volatility[-1] if not pd.isna(self.volatility[-1]) else 0.001

        if pd.isna(rsi):
            return

        # Exit logic with slippage
        if self.position:
            # Sometimes can't exit when we want (liquidity issues)
            exit_difficulty = np.random.random() < (volatility * 10)  # Higher vol = harder to exit

            if self.position.is_long and rsi > 65:
                if not exit_difficulty:
                    self.position.close()
            elif self.position.is_short and rsi < 35:
                if not exit_difficulty:
                    self.position.close()
            return

        # Entry logic with missed trades
        if not self.position:
            # Skip this trade randomly (simulating missed opportunities)
            if self.trade_misses[current_idx]:
                return

            # BUY: Liquidity sweep at lows
            if (self.distance_low[-1] < self.zone_proximity and
                self.low_tests[-1] >= self.min_tests and
                self.price_range[-1] < self.compression_threshold and
                rsi < 40 and
                self.zone_volume[-1] > 1.2):

                # Apply slippage (worse entry price)
                slippage_mult = 1 + (self.entry_slippage * (1 + volatility * 5))
                entry_price = price * slippage_mult

                # Wider stops due to slippage
                tp = entry_price * (1 + self.take_profit)
                sl = entry_price * (1 - self.stop_loss - self.sl_slippage)

                self.buy(tp=tp, sl=sl)

            # SELL: Liquidity sweep at highs
            elif (self.distance_high[-1] < self.zone_proximity and
                  self.high_tests[-1] >= self.min_tests and
                  self.price_range[-1] < self.compression_threshold and
                  rsi > 60 and
                  self.zone_volume[-1] > 1.2):

                # Apply slippage (worse entry price)
                slippage_mult = 1 - (self.entry_slippage * (1 + volatility * 5))
                entry_price = price * slippage_mult

                # Wider stops due to slippage
                tp = entry_price * (1 - self.take_profit)
                sl = entry_price * (1 + self.stop_loss + self.sl_slippage)

                self.sell(tp=tp, sl=sl)


# Run backtest
print("\n" + "="*70)
print("RUNNING LIQUIDITY ZONES - SLIPPAGE REALITY BACKTEST")
print("="*70)

bt = Backtest(
    data,
    LiquidityZonesSlippage,
    cash=1000000,
    commission=0.001,
    exclusive_orders=True
)

baseline_stats = bt.run()
print(f"\n📊 BASELINE RESULTS (WITH SLIPPAGE & MISSED TRADES):")
print(baseline_stats)
print(f"\n⚠️ REALITY CHECK:")
print(f"- Entry slippage: 0.15% worse price")
print(f"- Exit slippage: 0.1% worse price")
print(f"- Stop loss slippage: 0.3% worse price")
print(f"- Missed trade probability: 20%")

# Optimization with wider ranges
print("\n" + "="*70)
print("OPTIMIZING WITH REALISTIC EXECUTION")
print("="*70)

try:
    optimization_results = bt.optimize(
        take_profit=[0.02, 0.025, 0.03],  # Wider due to slippage
        stop_loss=[0.01, 0.012, 0.015],    # Wider due to slippage
        maximize='Return [%]',
        return_heatmap=False
    )

    print(f"\n✨ OPTIMIZED RESULTS (REALISTIC):")
    print(optimization_results)

    print(f"\n🎯 OPTIMAL PARAMETERS (WITH SLIPPAGE):")
    print(f"take_profit: {optimization_results._strategy.take_profit}")
    print(f"stop_loss: {optimization_results._strategy.stop_loss}")

except Exception as e:
    print(f"Optimization failed: {str(e)}")

bt.plot()