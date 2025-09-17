"""
RSI Radar Multi Time Frame Final Strategy
==========================================
Optimized RSI Radar strategy based on the TradingView indicator concept.
Uses multiple RSI timeframes with a voting system for robust signals.

Moon Dev's Implementation 🌙
"""

import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's RSI Radar Final Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class RSIRadarFinal(Strategy):
    """
    RSI Radar Final Strategy

    Implements a multi-timeframe RSI approach inspired by the TradingView indicator:
    - Uses 6 different RSI periods to simulate different timeframes
    - Employs a weighted voting system for entry signals
    - Includes dynamic exit conditions based on RSI momentum

    The radar concept visualizes RSI values from multiple timeframes,
    helping identify strong convergence of oversold/overbought conditions.
    """

    # RSI Configuration
    rsi_1min = 5      # Very fast RSI (simulates 1-minute)
    rsi_15min = 7     # Fast RSI (simulates 15-minute)
    rsi_1hr = 14      # Standard RSI (current timeframe - 1 hour)
    rsi_4hr = 28      # Medium RSI (simulates 4-hour)
    rsi_daily = 50    # Slow RSI (simulates daily)
    rsi_weekly = 100  # Very slow RSI (simulates weekly)

    # Signal thresholds
    rsi_oversold = 35
    rsi_overbought = 65
    extreme_oversold = 25
    extreme_overbought = 75

    # Risk management
    take_profit = 0.025  # 2.5%
    stop_loss = 0.015    # 1.5%

    # Voting requirements
    min_votes_entry = 2  # Minimum votes to enter
    min_votes_exit = 1   # Minimum votes to exit

    def init(self):
        print("🎯 Initializing RSI Radar with 6 timeframes...")

        # Initialize all RSI indicators
        self.rsi1 = self.I(talib.RSI, self.data.Close, self.rsi_1min)
        self.rsi2 = self.I(talib.RSI, self.data.Close, self.rsi_15min)
        self.rsi3 = self.I(talib.RSI, self.data.Close, self.rsi_1hr)
        self.rsi4 = self.I(talib.RSI, self.data.Close, self.rsi_4hr)
        self.rsi5 = self.I(talib.RSI, self.data.Close, self.rsi_daily)
        self.rsi6 = self.I(talib.RSI, self.data.Close, self.rsi_weekly)

        # Store all RSIs with weights for voting
        # Shorter timeframes have less weight, longer have more
        self.rsi_indicators = [
            (self.rsi1, 0.5, '1min'),
            (self.rsi2, 0.75, '15min'),
            (self.rsi3, 1.0, '1hr'),
            (self.rsi4, 1.25, '4hr'),
            (self.rsi5, 1.5, 'daily'),
            (self.rsi6, 1.75, 'weekly')
        ]

        print("✨ RSI Radar initialized with 6 simulated timeframes!")

    def calculate_radar_signal(self):
        """
        Calculate the RSI Radar signal based on multiple timeframes
        Returns: (weighted_oversold_score, weighted_overbought_score, rsi_dict)
        """
        oversold_score = 0
        overbought_score = 0
        rsi_values = {}

        for rsi_indicator, weight, name in self.rsi_indicators:
            if len(rsi_indicator) > 0 and not np.isnan(rsi_indicator[-1]):
                rsi_val = rsi_indicator[-1]
                rsi_values[name] = rsi_val

                # Calculate weighted scores
                if rsi_val < self.extreme_oversold:
                    oversold_score += weight * 2  # Double weight for extreme
                elif rsi_val < self.rsi_oversold:
                    oversold_score += weight

                if rsi_val > self.extreme_overbought:
                    overbought_score += weight * 2  # Double weight for extreme
                elif rsi_val > self.rsi_overbought:
                    overbought_score += weight

        return oversold_score, overbought_score, rsi_values

    def next(self):
        # Skip if we don't have enough data
        if len(self.data) < self.rsi_weekly + 1:
            return

        price = self.data.Close[-1]
        if price <= 0:
            return

        # Calculate radar signals
        oversold_score, overbought_score, rsi_values = self.calculate_radar_signal()

        # Calculate average RSI for additional confirmation
        avg_rsi = np.mean(list(rsi_values.values())) if rsi_values else 50

        # Entry logic
        if not self.position:
            # Long entry: Strong oversold signal
            if oversold_score >= self.min_votes_entry and avg_rsi < 45:
                sl = price * (1 - self.stop_loss)
                tp = price * (1 + self.take_profit)
                self.buy(sl=sl, tp=tp, size=1000000)

            # Short entry: Strong overbought signal
            elif overbought_score >= self.min_votes_entry and avg_rsi > 55:
                sl = price * (1 + self.stop_loss)
                tp = price * (1 - self.take_profit)
                self.sell(sl=sl, tp=tp, size=1000000)

        # Exit logic
        elif self.position.is_long:
            # Exit long if overbought signal appears
            if overbought_score >= self.min_votes_exit or avg_rsi > 70:
                self.position.close()

        elif self.position.is_short:
            # Exit short if oversold signal appears
            if oversold_score >= self.min_votes_exit or avg_rsi < 30:
                self.position.close()

# Run backtest with full data
bt = Backtest(data, RSIRadarFinal, cash=1000000, commission=0.00045)

print("\n🌙 ===== RSI RADAR FINAL - RUNNING BACKTEST ===== 🌙")
print("Strategy uses 6 simulated timeframes with weighted voting system")
stats = bt.run()
print(stats)

# Quick optimization on key parameters
print("\n🚀 Quick Optimization...")
opt_stats = bt.optimize(
    rsi_oversold=range(30, 41, 5),
    rsi_overbought=range(60, 71, 5),
    min_votes_entry=[1, 2, 3],
    take_profit=[0.02, 0.025, 0.03],
    stop_loss=[0.01, 0.015, 0.02],
    maximize='Sharpe Ratio',
    constraint=lambda p: p.take_profit > p.stop_loss,
    max_tries=100
)

print("\n🏆 BEST PARAMETERS:")
print(opt_stats)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING RSI RADAR FINAL ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(RSIRadarFinal, 'RSIRadar_Final')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/RSIRadar_Final.csv")