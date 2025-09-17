"""
RSI Radar Adaptive Multi Time Frame Strategy
=============================================
Enhanced version of the RSI Radar strategy with adaptive voting thresholds
and better multi-timeframe simulation.

This version uses a weighted voting system where longer timeframes
have more influence on the decision.

Moon Dev's Implementation 🌙
"""

import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's RSI Radar Adaptive Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
RSI_PERIOD = 14
RSI_OVERSOLD = 35  # Slightly less strict
RSI_OVERBOUGHT = 65  # Slightly less strict
MIN_SCORE = 2.0  # Minimum weighted score needed for signal
TAKE_PROFIT_PERCENT = 2.5
STOP_LOSS_PERCENT = 1.5

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class RSIRadarAdaptive(Strategy):
    """
    RSI Radar Adaptive Strategy with Weighted Voting

    Uses RSI from simulated multiple timeframes with weighted voting:
    - Very short term (5 period RSI) - weight 0.5
    - Short term (10 period RSI) - weight 0.75
    - Current (14 period RSI) - weight 1.0
    - Medium term (21 period RSI) - weight 1.25
    - Long term (28 period RSI) - weight 1.5

    The strategy uses a scoring system where:
    - Oversold conditions add positive scores
    - Overbought conditions add negative scores
    - Trades are taken when the absolute score exceeds the threshold
    """

    # Strategy parameters
    rsi_oversold = RSI_OVERSOLD
    rsi_overbought = RSI_OVERBOUGHT
    min_score = MIN_SCORE
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100

    def init(self):
        print("🎯 Initializing RSI Radar Adaptive indicators...")

        # Create RSI indicators with different periods to simulate different timeframes
        # Each tuple contains (name, period, weight)
        timeframe_configs = [
            ('Very Short', 5, 0.5),
            ('Short', 10, 0.75),
            ('Current', 14, 1.0),
            ('Medium', 21, 1.25),
            ('Long', 28, 1.5)
        ]

        self.rsi_indicators = []
        for name, period, weight in timeframe_configs:
            rsi = self.I(talib.RSI, self.data.Close, period)
            self.rsi_indicators.append((name, rsi, weight))

        print(f"✨ RSI Radar Adaptive initialized with {len(self.rsi_indicators)} weighted timeframes!")

    def calculate_rsi_score(self):
        """
        Calculate weighted score based on RSI values
        Positive score indicates bullish (oversold) conditions
        Negative score indicates bearish (overbought) conditions
        """
        total_score = 0.0
        rsi_values = {}

        for name, rsi_indicator, weight in self.rsi_indicators:
            if len(rsi_indicator) > 0 and not np.isnan(rsi_indicator[-1]):
                rsi_value = rsi_indicator[-1]
                rsi_values[name] = rsi_value

                # Calculate score based on RSI level
                if rsi_value < self.rsi_oversold:
                    # The more oversold, the higher the score
                    oversold_strength = (self.rsi_oversold - rsi_value) / self.rsi_oversold
                    total_score += weight * oversold_strength

                elif rsi_value > self.rsi_overbought:
                    # The more overbought, the more negative the score
                    overbought_strength = (rsi_value - self.rsi_overbought) / (100 - self.rsi_overbought)
                    total_score -= weight * overbought_strength

        return total_score, rsi_values

    def next(self):
        # Skip if we don't have enough data
        if len(self.data) < 30:
            return

        price = self.data.Close[-1]

        if price <= 0:
            return

        # Calculate weighted RSI score
        rsi_score, rsi_values = self.calculate_rsi_score()

        # Calculate stop loss and take profit levels
        sl_price_long = price * (1 - self.stop_loss)
        tp_price_long = price * (1 + self.take_profit)
        sl_price_short = price * (1 + self.stop_loss)
        tp_price_short = price * (1 - self.take_profit)

        # Entry conditions based on weighted scoring
        if not self.position:
            # Long entry: Strong oversold signal (positive score)
            if rsi_score >= self.min_score:
                rsi_str = ', '.join([f"{k}:{v:.1f}" for k, v in rsi_values.items()])
                print(f"🚀 LONG Entry - Price: {price:.2f}, Score: {rsi_score:.2f}")
                print(f"   RSI Values: {rsi_str}")
                print(f"   SL: {sl_price_long:.2f}, TP: {tp_price_long:.2f}")
                self.buy(sl=sl_price_long, tp=tp_price_long, size=1000000)

            # Short entry: Strong overbought signal (negative score)
            elif rsi_score <= -self.min_score:
                rsi_str = ', '.join([f"{k}:{v:.1f}" for k, v in rsi_values.items()])
                print(f"🔻 SHORT Entry - Price: {price:.2f}, Score: {rsi_score:.2f}")
                print(f"   RSI Values: {rsi_str}")
                print(f"   SL: {sl_price_short:.2f}, TP: {tp_price_short:.2f}")
                self.sell(sl=sl_price_short, tp=tp_price_short, size=1000000)

        # Exit conditions: Score reversal
        elif self.position.is_long:
            # Exit long if score becomes negative (trend reversal)
            if rsi_score < -self.min_score * 0.5:  # Use half threshold for exits
                print(f"🎯 Closing LONG - Price: {price:.2f}, Score: {rsi_score:.2f}")
                self.position.close()

        elif self.position.is_short:
            # Exit short if score becomes positive (trend reversal)
            if rsi_score > self.min_score * 0.5:  # Use half threshold for exits
                print(f"🎯 Closing SHORT - Price: {price:.2f}, Score: {rsi_score:.2f}")
                self.position.close()

# Run single backtest (default behavior)
bt = Backtest(data, RSIRadarAdaptive, cash=1000000, commission=0.00045)

print("\n🌙 ===== RSI RADAR ADAPTIVE - DEFAULT PARAMETERS ===== 🌙")
print(f"RSI Oversold Level: {RSI_OVERSOLD}")
print(f"RSI Overbought Level: {RSI_OVERBOUGHT}")
print(f"Minimum Score Threshold: {MIN_SCORE}")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")

stats_default = bt.run()
print(stats_default)

# Optimization
print("\n🚀 Optimizing RSI Radar Adaptive Strategy...")
optimization_results = bt.optimize(
    rsi_oversold=range(25, 40, 5),
    rsi_overbought=range(60, 75, 5),
    min_score=[1.0, 1.5, 2.0, 2.5],
    take_profit=[i / 1000 for i in range(15, 36, 5)],
    stop_loss=[i / 1000 for i in range(10, 26, 5)],
    maximize='Sortino Ratio',
    constraint=lambda p: p.take_profit > p.stop_loss
)

print("\n🚀 ===== OPTIMIZATION RESULTS ===== 🚀")
print(optimization_results)

print("\n🏆 BEST PARAMETERS:")
print(f"RSI Oversold: {optimization_results._strategy.rsi_oversold}")
print(f"RSI Overbought: {optimization_results._strategy.rsi_overbought}")
print(f"Min Score: {optimization_results._strategy.min_score}")
print(f"Take Profit: {optimization_results._strategy.take_profit * 100:.1f}%")
print(f"Stop Loss: {optimization_results._strategy.stop_loss * 100:.1f}%")

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING RSI RADAR ADAPTIVE ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(RSIRadarAdaptive, 'RSIRadar_Adaptive')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/RSIRadar_Adaptive.csv")