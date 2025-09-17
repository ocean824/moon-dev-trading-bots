"""
RSI Radar Multi Time Frame Working Strategy
============================================
A working implementation of the RSI Radar concept that actually generates trades.
Uses multiple RSI periods with relaxed thresholds for better signal generation.

Moon Dev's Implementation 🌙
"""

import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's RSI Radar Working Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
# Use last 20000 rows for faster testing
data = data.tail(20000)
print(f"✅ Data loaded! {len(data)} rows 🌙")

class RSIRadarWorking(Strategy):
    """
    RSI Radar Working Strategy

    Implements the multi-timeframe RSI concept from the TradingView indicator:
    - Uses 6 different RSI periods (5, 9, 14, 21, 34, 55) to simulate timeframes
    - Generates signals when multiple RSIs align
    - More relaxed thresholds for better trade generation
    """

    # RSI periods (simulating different timeframes)
    rsi_p1 = 5   # Very fast (1min equivalent)
    rsi_p2 = 9   # Fast (15min equivalent)
    rsi_p3 = 14  # Standard (1hr - current)
    rsi_p4 = 21  # Medium (4hr equivalent)
    rsi_p5 = 34  # Slow (daily equivalent)
    rsi_p6 = 55  # Very slow (weekly equivalent)

    # Trading thresholds - more relaxed
    rsi_oversold = 45
    rsi_overbought = 55
    strong_oversold = 30
    strong_overbought = 70

    # Risk management
    take_profit = 0.02  # 2%
    stop_loss = 0.015   # 1.5%

    def init(self):
        # Initialize RSI indicators
        self.rsi1 = self.I(talib.RSI, self.data.Close, self.rsi_p1)
        self.rsi2 = self.I(talib.RSI, self.data.Close, self.rsi_p2)
        self.rsi3 = self.I(talib.RSI, self.data.Close, self.rsi_p3)
        self.rsi4 = self.I(talib.RSI, self.data.Close, self.rsi_p4)
        self.rsi5 = self.I(talib.RSI, self.data.Close, self.rsi_p5)
        self.rsi6 = self.I(talib.RSI, self.data.Close, self.rsi_p6)

    def get_rsi_signal(self):
        """
        Analyze RSI values across all timeframes
        Returns: 'long', 'short', or None
        """
        rsi_values = []

        # Collect all RSI values
        for rsi in [self.rsi1[-1], self.rsi2[-1], self.rsi3[-1],
                   self.rsi4[-1], self.rsi5[-1], self.rsi6[-1]]:
            if not np.isnan(rsi):
                rsi_values.append(rsi)

        if len(rsi_values) < 4:  # Need at least 4 valid RSIs
            return None

        # Count conditions
        oversold = sum(1 for r in rsi_values if r < self.rsi_oversold)
        overbought = sum(1 for r in rsi_values if r > self.rsi_overbought)
        strong_os = sum(1 for r in rsi_values if r < self.strong_oversold)
        strong_ob = sum(1 for r in rsi_values if r > self.strong_overbought)

        avg_rsi = np.mean(rsi_values)

        # Signal generation logic
        # Long signal: Multiple oversold OR strong oversold present
        if (oversold >= 3) or (strong_os >= 1 and avg_rsi < 50):
            return 'long'

        # Short signal: Multiple overbought OR strong overbought present
        if (overbought >= 3) or (strong_ob >= 1 and avg_rsi > 50):
            return 'short'

        return None

    def next(self):
        # Skip if not enough data
        if len(self.data) < 60:
            return

        price = self.data.Close[-1]
        if price <= 0:
            return

        signal = self.get_rsi_signal()

        # Entry logic
        if not self.position and signal:
            if signal == 'long':
                sl = price * (1 - self.stop_loss)
                tp = price * (1 + self.take_profit)
                self.buy(sl=sl, tp=tp, size=1000000)

            elif signal == 'short':
                sl = price * (1 + self.stop_loss)
                tp = price * (1 - self.take_profit)
                self.sell(sl=sl, tp=tp, size=1000000)

        # Exit on opposite signal
        elif self.position:
            if self.position.is_long and signal == 'short':
                self.position.close()
            elif self.position.is_short and signal == 'long':
                self.position.close()

# Run backtest
bt = Backtest(data, RSIRadarWorking, cash=1000000, commission=0.00045)

print("\n🌙 ===== RSI RADAR WORKING - BACKTEST RESULTS ===== 🌙")
stats = bt.run()
print(stats)

# Quick optimization
print("\n🚀 Running quick optimization...")
opt_stats = bt.optimize(
    rsi_oversold=[40, 45],
    rsi_overbought=[55, 60],
    take_profit=[0.015, 0.02, 0.025],
    stop_loss=[0.01, 0.015],
    maximize='Sharpe Ratio',
    constraint=lambda p: p.take_profit > p.stop_loss
)

print("\n🏆 OPTIMIZATION RESULTS:")
print(f"Best Oversold: {opt_stats._strategy.rsi_oversold}")
print(f"Best Overbought: {opt_stats._strategy.rsi_overbought}")
print(f"Best Take Profit: {opt_stats._strategy.take_profit * 100:.1f}%")
print(f"Best Stop Loss: {opt_stats._strategy.stop_loss * 100:.1f}%")
print(f"\nOptimized Performance:")
print(f"Return: {opt_stats['Return [%]']:.2f}%")
print(f"Sharpe: {opt_stats['Sharpe Ratio']:.3f}" if not np.isnan(opt_stats['Sharpe Ratio']) else "Sharpe: N/A")
print(f"Win Rate: {opt_stats['Win Rate [%]']:.1f}%" if not np.isnan(opt_stats['Win Rate [%]']) else "Win Rate: N/A")

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING RSI RADAR WORKING ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(RSIRadarWorking, 'RSIRadar_Working')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/RSIRadar_Working.csv")