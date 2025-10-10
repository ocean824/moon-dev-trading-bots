"""
LIQUIDITY ZONES WIDER - 2 BAR MINIMUM HOLD
===========================================

Based on the successful Liquidity Zones strategy with 343% return.
Using wider stop loss and take profit targets for realistic execution.
MUST HOLD FOR AT LEAST 2 FULL BARS BEFORE CLOSING (except SL/TP)

Original optimal params: TP=0.008 (0.8%), SL=0.004 (0.4%)
New wider ranges: TP=0.015-0.025 (1.5-2.5%), SL=0.008-0.012 (0.8-1.2%)
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

print("🎯 Moon Dev's LIQUIDITY ZONES WIDER - 2 BAR HOLD Strategy V3 🎯")
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


class LiquidityZonesWider2Bar(Strategy):
    """
    Trade liquidity grab and sweep patterns with wider SL/TP
    MUST HOLD FOR MINIMUM 2 BARS
    """

    zone_proximity = 0.0025  # From optimization
    min_tests = 1  # From optimization
    compression_threshold = 0.004  # From optimization
    take_profit = 0.02  # WIDER: 2% (was 0.8%)
    stop_loss = 0.01   # WIDER: 1% (was 0.4%)
    min_hold_bars = 2  # MUST HOLD FOR AT LEAST 2 BARS

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

        # Track entry bar
        self.entry_bar = None

    def next(self):
        if len(self.data) < 50:
            return

        price = self.data.Close[-1]
        rsi = self.rsi[-1]
        current_bar = len(self.data) - 1

        if pd.isna(rsi):
            return

        # Exit logic with minimum hold period
        if self.position:
            bars_held = current_bar - self.entry_bar

            # Only allow exit after minimum hold period (SL/TP still work immediately)
            if bars_held >= self.min_hold_bars:
                if self.position.is_long and rsi > 65:
                    self.position.close()
                elif self.position.is_short and rsi < 35:
                    self.position.close()
            return

        # Entry logic (same as optimized version)
        if not self.position:
            # BUY: Liquidity sweep at lows
            if (self.distance_low[-1] < self.zone_proximity and
                self.low_tests[-1] >= self.min_tests and
                self.price_range[-1] < self.compression_threshold and
                rsi < 40 and
                self.zone_volume[-1] > 1.2):

                # WIDER targets for realistic execution
                tp = price * (1 + self.take_profit)
                sl = price * (1 - self.stop_loss)
                self.buy(tp=tp, sl=sl)
                self.entry_bar = current_bar

            # SELL: Liquidity sweep at highs
            elif (self.distance_high[-1] < self.zone_proximity and
                  self.high_tests[-1] >= self.min_tests and
                  self.price_range[-1] < self.compression_threshold and
                  rsi > 60 and
                  self.zone_volume[-1] > 1.2):

                # WIDER targets for realistic execution
                tp = price * (1 - self.take_profit)
                sl = price * (1 + self.stop_loss)
                self.sell(tp=tp, sl=sl)
                self.entry_bar = current_bar


# Run backtest
print("\n" + "="*70)
print("RUNNING LIQUIDITY ZONES WIDER - 2 BAR HOLD BACKTEST")
print("="*70)

bt = Backtest(
    data,
    LiquidityZonesWider2Bar,
    cash=1000000,
    commission=0.001,
    exclusive_orders=True
)

baseline_stats = bt.run()
print(f"\n📊 BASELINE RESULTS (2% TP, 1% SL, 2-bar min hold):")
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

    print(f"\n🎯 OPTIMAL PARAMETERS (WIDER + 2-BAR HOLD):")
    print(f"zone_proximity: {optimization_results._strategy.zone_proximity}")
    print(f"min_tests: {optimization_results._strategy.min_tests}")
    print(f"compression_threshold: {optimization_results._strategy.compression_threshold}")
    print(f"take_profit: {optimization_results._strategy.take_profit}")
    print(f"stop_loss: {optimization_results._strategy.stop_loss}")
    print(f"min_hold_bars: {optimization_results._strategy.min_hold_bars}")

except Exception as e:
    print(f"Optimization failed: {str(e)}")

bt.plot()