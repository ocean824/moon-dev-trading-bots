"""
LIQUIDITY ZONES - 2 BAR ENTRY DELAY + 2 BAR EXIT DELAY
========================================================

Based on the successful Liquidity Zones strategy with 343% return.
Using wider stop loss and take profit targets for realistic execution.
ENTERS 2 BARS LATE AND EXITS 2 BARS LATE (except SL/TP)
Simulates very slow execution for maximum realism.

Original optimal params: TP=0.008 (0.8%), SL=0.004 (0.4%)
New wider ranges: TP=0.015-0.025 (1.5-2.5%), SL=0.008-0.012 (0.8-1.2%)
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

print("🎯 Moon Dev's LIQUIDITY ZONES - 2 BAR ENTRY/EXIT DELAY Strategy V3 🎯")
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

print(f"✅ Loaded {len(data):,} 1-minute bars")


class LiquidityZones2BarDelay(Strategy):
    """
    Trade liquidity grab and sweep patterns with wider SL/TP
    ENTERS 2 BARS LATE (delayed entry)
    EXITS 2 BARS LATE (delayed exit except for SL/TP)
    """

    zone_proximity = 0.0025  # From optimization
    min_tests = 1  # From optimization
    compression_threshold = 0.004  # From optimization
    take_profit = 0.02  # WIDER: 2% (was 0.8%)
    stop_loss = 0.01   # WIDER: 1% (was 0.4%)
    entry_delay = 2  # DELAY ENTRY BY 2 BARS
    exit_delay = 2   # DELAY EXIT BY 2 BARS

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

        # Track pending signals with bar counters
        self.pending_buy_bars = 0
        self.pending_sell_bars = 0
        self.pending_exit_bars = 0

    def next(self):
        if len(self.data) < 50:
            return

        price = self.data.Close[-1]
        rsi = self.rsi[-1]

        if pd.isna(rsi):
            return

        # Handle delayed exits
        if self.position:
            # Check for exit signals (will execute after delay)
            if self.pending_exit_bars == 0:  # No pending exit yet
                if self.position.is_long and rsi > 65:
                    self.pending_exit_bars = self.exit_delay
                elif self.position.is_short and rsi < 35:
                    self.pending_exit_bars = self.exit_delay

            # Process delayed exit
            if self.pending_exit_bars > 0:
                self.pending_exit_bars -= 1
                if self.pending_exit_bars == 0:
                    self.position.close()
            return

        # Process delayed entries
        if not self.position:
            # Execute pending buy signal after delay
            if self.pending_buy_bars > 0:
                self.pending_buy_bars -= 1
                if self.pending_buy_bars == 0:
                    tp = price * (1 + self.take_profit)
                    sl = price * (1 - self.stop_loss)
                    self.buy(tp=tp, sl=sl)
                return

            # Execute pending sell signal after delay
            if self.pending_sell_bars > 0:
                self.pending_sell_bars -= 1
                if self.pending_sell_bars == 0:
                    tp = price * (1 - self.take_profit)
                    sl = price * (1 + self.stop_loss)
                    self.sell(tp=tp, sl=sl)
                return

        # Check for new signals (will execute after 2 bars)
        if not self.position and self.pending_buy_bars == 0 and self.pending_sell_bars == 0:
            # BUY SIGNAL: Liquidity sweep at lows
            if (self.distance_low[-1] < self.zone_proximity and
                self.low_tests[-1] >= self.min_tests and
                self.price_range[-1] < self.compression_threshold and
                rsi < 40 and
                self.zone_volume[-1] > 1.2):

                # Set pending buy signal (will execute after 2 bars)
                self.pending_buy_bars = self.entry_delay

            # SELL SIGNAL: Liquidity sweep at highs
            elif (self.distance_high[-1] < self.zone_proximity and
                  self.high_tests[-1] >= self.min_tests and
                  self.price_range[-1] < self.compression_threshold and
                  rsi > 60 and
                  self.zone_volume[-1] > 1.2):

                # Set pending sell signal (will execute after 2 bars)
                self.pending_sell_bars = self.entry_delay


# Run backtest
print("\n" + "="*70)
print("RUNNING LIQUIDITY ZONES - 2 BAR ENTRY/EXIT DELAY BACKTEST")
print("="*70)

bt = Backtest(
    data,
    LiquidityZones2BarDelay,
    cash=1000000,
    commission=0.001,
    exclusive_orders=True
)

baseline_stats = bt.run()
print(f"\n📊 BASELINE RESULTS (2% TP, 1% SL, 2-bar entry delay, 2-bar exit delay):")
print(baseline_stats)

# Optimization with wider ranges
print("\n" + "="*70)
print("OPTIMIZING WITH WIDER STOP LOSS AND TAKE PROFIT")
print("="*70)

try:
    optimization_results = bt.optimize(
        take_profit=[0.015, 0.02, 0.025],  # 1.5%, 2%, 2.5%
        stop_loss=[0.008, 0.01, 0.012],    # 0.8%, 1%, 1.2%
        maximize='Return [%]',
        return_heatmap=False
    )

    print(f"\n✨ OPTIMIZED RESULTS:")
    print(optimization_results)

    print(f"\n🎯 OPTIMAL PARAMETERS (2-BAR ENTRY/EXIT DELAY):")
    print(f"zone_proximity: {optimization_results._strategy.zone_proximity}")
    print(f"min_tests: {optimization_results._strategy.min_tests}")
    print(f"compression_threshold: {optimization_results._strategy.compression_threshold}")
    print(f"take_profit: {optimization_results._strategy.take_profit}")
    print(f"stop_loss: {optimization_results._strategy.stop_loss}")
    print(f"entry_delay: {optimization_results._strategy.entry_delay}")
    print(f"exit_delay: {optimization_results._strategy.exit_delay}")

except Exception as e:
    print(f"Optimization failed: {str(e)}")

bt.plot()