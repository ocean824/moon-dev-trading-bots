"""
RSI Radar Multi Time Frame Strategy
=====================================
Based on the TradingView Pine Script indicator "RSI Radar Multi Time Frame"
Uses RSI values from multiple timeframes to generate trading signals.

The strategy implements a voting system where signals are stronger when
multiple timeframes agree on oversold/overbought conditions.

Moon Dev's Implementation 🌙
"""

import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's RSI Radar Multi Time Frame Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
RSI_PERIOD = 14
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
VOTING_THRESHOLD = 3  # Minimum number of timeframes that must agree
TAKE_PROFIT_PERCENT = 3.0
STOP_LOSS_PERCENT = 2.0

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

def resample_ohlc(data, timeframe):
    """Resample OHLC data to a different timeframe"""
    return data.resample(timeframe).agg({
        'Open': 'first',
        'High': 'max',
        'Low': 'min',
        'Close': 'last',
        'Volume': 'sum'
    }).dropna()

class RSIRadarStrategy(Strategy):
    """
    RSI Radar Multi Time Frame Strategy

    Uses RSI from multiple timeframes to generate trading signals:
    - Current timeframe (1H as base)
    - 15 minutes (higher resolution)
    - 1 hour (current)
    - 4 hours (medium term)
    - 1 day (long term)
    - 1 week (very long term)

    Generates buy signals when multiple timeframes show oversold conditions
    Generates sell signals when multiple timeframes show overbought conditions
    """

    # Strategy parameters
    rsi_period = RSI_PERIOD
    rsi_oversold = RSI_OVERSOLD
    rsi_overbought = RSI_OVERBOUGHT
    voting_threshold = VOTING_THRESHOLD
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100

    def init(self):
        print("🎯 Initializing RSI Radar Multi Time Frame indicators...")

        # Calculate RSI for current timeframe (1H)
        self.rsi_current = self.I(talib.RSI, self.data.Close, self.rsi_period)

        # For backtesting, we'll simulate multiple timeframes by using different RSI periods
        # This is a common approach when actual multi-timeframe data isn't available
        # Shorter periods = more sensitive (simulating higher timeframe)
        # Longer periods = less sensitive (simulating lower timeframe)

        # Simulate 15-minute RSI (more sensitive)
        self.rsi_15m = self.I(talib.RSI, self.data.Close, max(7, self.rsi_period // 2))

        # Current 1H RSI (already calculated)
        self.rsi_1h = self.rsi_current

        # Simulate 4H RSI (less sensitive)
        self.rsi_4h = self.I(talib.RSI, self.data.Close, self.rsi_period * 2)

        # Simulate Daily RSI (even less sensitive)
        self.rsi_daily = self.I(talib.RSI, self.data.Close, self.rsi_period * 4)

        # Simulate Weekly RSI (least sensitive)
        self.rsi_weekly = self.I(talib.RSI, self.data.Close, self.rsi_period * 7)

        # Store all RSI indicators in a list for easy iteration
        self.rsi_indicators = [
            ('15m', self.rsi_15m),
            ('1h', self.rsi_1h),
            ('4h', self.rsi_4h),
            ('1d', self.rsi_daily),
            ('1w', self.rsi_weekly)
        ]

        print(f"✨ RSI Radar initialized with {len(self.rsi_indicators)} timeframes!")

    def get_rsi_votes(self):
        """
        Count how many timeframes are oversold or overbought
        Returns: (oversold_count, overbought_count, rsi_values)
        """
        oversold_count = 0
        overbought_count = 0
        rsi_values = {}

        for name, rsi_indicator in self.rsi_indicators:
            if len(rsi_indicator) > 0 and not np.isnan(rsi_indicator[-1]):
                rsi_value = rsi_indicator[-1]
                rsi_values[name] = rsi_value

                if rsi_value < self.rsi_oversold:
                    oversold_count += 1
                elif rsi_value > self.rsi_overbought:
                    overbought_count += 1

        return oversold_count, overbought_count, rsi_values

    def next(self):
        # Skip if we don't have enough data
        if len(self.data) < self.rsi_period * 7:
            return

        price = self.data.Close[-1]

        if price <= 0:
            return

        # Get RSI votes from all timeframes
        oversold_votes, overbought_votes, rsi_values = self.get_rsi_votes()

        # Calculate stop loss and take profit levels
        sl_price_long = price * (1 - self.stop_loss)
        tp_price_long = price * (1 + self.take_profit)
        sl_price_short = price * (1 + self.stop_loss)
        tp_price_short = price * (1 - self.take_profit)

        # Entry conditions based on voting system
        if not self.position:
            # Long entry: Multiple timeframes showing oversold
            if oversold_votes >= self.voting_threshold:
                rsi_str = ', '.join([f"{k}:{v:.1f}" for k, v in rsi_values.items()])
                print(f"🚀 LONG Entry - Price: {price:.2f}, Oversold votes: {oversold_votes}/5")
                print(f"   RSI Values: {rsi_str}")
                print(f"   SL: {sl_price_long:.2f}, TP: {tp_price_long:.2f}")
                self.buy(sl=sl_price_long, tp=tp_price_long, size=1000000)

            # Short entry: Multiple timeframes showing overbought
            elif overbought_votes >= self.voting_threshold:
                rsi_str = ', '.join([f"{k}:{v:.1f}" for k, v in rsi_values.items()])
                print(f"🔻 SHORT Entry - Price: {price:.2f}, Overbought votes: {overbought_votes}/5")
                print(f"   RSI Values: {rsi_str}")
                print(f"   SL: {sl_price_short:.2f}, TP: {tp_price_short:.2f}")
                self.sell(sl=sl_price_short, tp=tp_price_short, size=1000000)

        # Exit conditions: Opposite signal or weakening trend
        elif self.position.is_long:
            # Exit long if multiple timeframes become overbought
            if overbought_votes >= self.voting_threshold - 1:
                print(f"🎯 Closing LONG - Price: {price:.2f}, Overbought votes: {overbought_votes}/5")
                self.position.close()

        elif self.position.is_short:
            # Exit short if multiple timeframes become oversold
            if oversold_votes >= self.voting_threshold - 1:
                print(f"🎯 Closing SHORT - Price: {price:.2f}, Oversold votes: {oversold_votes}/5")
                self.position.close()

# Run single backtest (default behavior)
bt = Backtest(data, RSIRadarStrategy, cash=1000000, commission=0.00045)

print("\n🌙 ===== RSI RADAR STRATEGY - DEFAULT PARAMETERS ===== 🌙")
print(f"RSI Period: {RSI_PERIOD}")
print(f"Oversold Level: {RSI_OVERSOLD}")
print(f"Overbought Level: {RSI_OVERBOUGHT}")
print(f"Voting Threshold: {VOTING_THRESHOLD}/5 timeframes")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")

stats_default = bt.run()
print(stats_default)

# Optimization
print("\n🚀 Optimizing RSI Radar Strategy...")
optimization_results = bt.optimize(
    rsi_period=range(10, 21, 2),
    voting_threshold=range(2, 5),
    take_profit=[i / 1000 for i in range(20, 51, 5)],
    stop_loss=[i / 1000 for i in range(10, 31, 5)],
    maximize='Sortino Ratio',
    constraint=lambda p: p.take_profit > p.stop_loss
)

print("\n🚀 ===== OPTIMIZATION RESULTS ===== 🚀")
print(optimization_results)

print("\n🏆 BEST PARAMETERS:")
print(f"RSI Period: {optimization_results._strategy.rsi_period}")
print(f"Voting Threshold: {optimization_results._strategy.voting_threshold}/5 timeframes")
print(f"Take Profit: {optimization_results._strategy.take_profit * 100:.1f}%")
print(f"Stop Loss: {optimization_results._strategy.stop_loss * 100:.1f}%")

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING RSI RADAR MULTI TIME FRAME ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(RSIRadarStrategy, 'RSIRadar_MTF')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/RSIRadar_MTF.csv")