"""
RSI Radar Multi Time Frame Production Strategy
===============================================
Production-ready implementation of the RSI Radar concept.
Uses multiple RSI timeframes with proper signal generation.

Based on the TradingView "RSI Radar Multi Time Frame" indicator.

Moon Dev's Implementation 🌙
"""

import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's RSI Radar Production Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class RSIRadarProduction(Strategy):
    """
    RSI Radar Production Strategy

    The TradingView indicator shows RSI values from 6 timeframes on a radar chart:
    - Current, 1min, 15min, 1hr, 4hr, Daily

    For backtesting, we simulate this using different RSI periods:
    - RSI(7): Fast movements (simulates shorter timeframes)
    - RSI(14): Standard (current timeframe)
    - RSI(28): Slower movements (simulates longer timeframes)

    Entry Logic:
    - Long: When majority of RSIs are below 40
    - Short: When majority of RSIs are above 60
    """

    # RSI Configuration
    rsi_fast = 7
    rsi_standard = 14
    rsi_slow = 28

    # Signal thresholds (based on actual RSI distribution)
    rsi_buy_threshold = 40   # Enter long below this
    rsi_sell_threshold = 60  # Enter short above this

    # Exit thresholds
    rsi_exit_long = 55   # Exit long above this
    rsi_exit_short = 45  # Exit short below this

    # Risk management
    take_profit = 0.025  # 2.5%
    stop_loss = 0.015    # 1.5%

    # Minimum votes needed (out of 3 RSIs)
    min_votes = 2

    def init(self):
        print("🎯 Initializing RSI Radar indicators...")

        # Calculate RSI indicators
        self.rsi1 = self.I(talib.RSI, self.data.Close, self.rsi_fast)
        self.rsi2 = self.I(talib.RSI, self.data.Close, self.rsi_standard)
        self.rsi3 = self.I(talib.RSI, self.data.Close, self.rsi_slow)

        print(f"✨ RSI Radar initialized with periods: {self.rsi_fast}, {self.rsi_standard}, {self.rsi_slow}")

    def next(self):
        # Skip if not enough data
        if len(self.data) < self.rsi_slow + 1:
            return

        # Get current RSI values
        rsi_fast_val = self.rsi1[-1]
        rsi_standard_val = self.rsi2[-1]
        rsi_slow_val = self.rsi3[-1]

        # Check for valid values
        if np.isnan(rsi_fast_val) or np.isnan(rsi_standard_val) or np.isnan(rsi_slow_val):
            return

        # Count buy/sell votes
        buy_votes = 0
        sell_votes = 0

        # Check each RSI
        if rsi_fast_val < self.rsi_buy_threshold:
            buy_votes += 1
        elif rsi_fast_val > self.rsi_sell_threshold:
            sell_votes += 1

        if rsi_standard_val < self.rsi_buy_threshold:
            buy_votes += 1
        elif rsi_standard_val > self.rsi_sell_threshold:
            sell_votes += 1

        if rsi_slow_val < self.rsi_buy_threshold:
            buy_votes += 1
        elif rsi_slow_val > self.rsi_sell_threshold:
            sell_votes += 1

        price = self.data.Close[-1]

        # Entry logic
        if not self.position:
            # Long entry: Majority of RSIs oversold
            if buy_votes >= self.min_votes:
                sl = price * (1 - self.stop_loss)
                tp = price * (1 + self.take_profit)
                self.buy(sl=sl, tp=tp, size=1000000)

            # Short entry: Majority of RSIs overbought
            elif sell_votes >= self.min_votes:
                sl = price * (1 + self.stop_loss)
                tp = price * (1 - self.take_profit)
                self.sell(sl=sl, tp=tp, size=1000000)

        # Exit logic (using middle RSI for exits)
        elif self.position.is_long:
            # Exit long if RSI recovers
            if rsi_standard_val > self.rsi_exit_long:
                self.position.close()

        elif self.position.is_short:
            # Exit short if RSI drops
            if rsi_standard_val < self.rsi_exit_short:
                self.position.close()

# Run backtest
bt = Backtest(data, RSIRadarProduction, cash=1000000, commission=0.00045)

print("\n🌙 ===== RSI RADAR PRODUCTION - BACKTEST RESULTS ===== 🌙")
stats = bt.run()
print(stats)

# Optimization with reasonable parameter ranges
print("\n🚀 Optimizing RSI Radar Production Strategy...")
opt_stats = bt.optimize(
    rsi_buy_threshold=[35, 40, 45],
    rsi_sell_threshold=[55, 60, 65],
    min_votes=[1, 2],
    take_profit=[0.02, 0.025, 0.03],
    stop_loss=[0.01, 0.015, 0.02],
    maximize='Sortino Ratio',
    constraint=lambda p: (p.take_profit > p.stop_loss) and (p.rsi_sell_threshold > p.rsi_buy_threshold)
)

print("\n🏆 BEST PARAMETERS FOUND:")
print(f"Buy Threshold: RSI < {opt_stats._strategy.rsi_buy_threshold}")
print(f"Sell Threshold: RSI > {opt_stats._strategy.rsi_sell_threshold}")
print(f"Min Votes: {opt_stats._strategy.min_votes}/3")
print(f"Take Profit: {opt_stats._strategy.take_profit * 100:.1f}%")
print(f"Stop Loss: {opt_stats._strategy.stop_loss * 100:.1f}%")

print(f"\nOptimized Performance:")
print(f"Return: {opt_stats['Return [%]']:.2f}%")
print(f"Sharpe Ratio: {opt_stats['Sharpe Ratio']:.3f}" if not np.isnan(opt_stats['Sharpe Ratio']) else "Sharpe Ratio: N/A")
print(f"Max Drawdown: {opt_stats['Max. Drawdown [%]']:.2f}%")
print(f"Number of Trades: {opt_stats['# Trades']}")
print(f"Win Rate: {opt_stats['Win Rate [%]']:.1f}%" if not np.isnan(opt_stats['Win Rate [%]']) else "Win Rate: N/A")

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING RSI RADAR PRODUCTION ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(RSIRadarProduction, 'RSIRadar_Production')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/RSIRadar_Production.csv")