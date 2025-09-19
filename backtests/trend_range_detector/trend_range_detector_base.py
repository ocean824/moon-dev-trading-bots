"""
Moon Dev's Trend Range Detector Base Strategy
==============================================
Implements the Zeiierman Trend Range Detector from TradingView.
Identifies consolidation ranges using weighted moving average and ATR-based boundaries.
Trades breakouts and breakdowns from established ranges.
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Trend Range Detector Base Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
WMA_PERIOD = 20  # Weighted MA period
ATR_PERIOD = 14
ATR_MULTIPLIER = 1.5  # Range box multiplier (reduced for more ranges)
MIN_RANGE_LENGTH = 20  # Minimum bars in range (further reduced for more signals)
BREAKOUT_CONFIRM_BARS = 2  # Bars to confirm breakout
STOP_LOSS_PERCENT = 2.0
TAKE_PROFIT_PERCENT = 4.0

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class TrendRangeDetectorBase(Strategy):
    """
    Trend Range Detector Strategy - Base Implementation
    - Calculates weighted moving average based on price deltas
    - Identifies range formation using ATR-based boundaries
    - Detects when price consolidates within range for minimum length
    - Enters long on breakout above range top
    - Enters short on breakdown below range bottom
    - Uses range width for position sizing
    """

    # Core parameters
    wma_period = WMA_PERIOD
    atr_period = ATR_PERIOD
    atr_multiplier = ATR_MULTIPLIER
    min_range_length = MIN_RANGE_LENGTH
    breakout_confirm = BREAKOUT_CONFIRM_BARS

    # Risk management
    stop_loss_pct = STOP_LOSS_PERCENT / 100
    take_profit_pct = TAKE_PROFIT_PERCENT / 100


    def init(self):
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)

        # Calculate ATR
        self.atr = self.I(ta.atr, high, low, close, self.atr_period)

        # Calculate simple moving average for range center
        self.sma = self.I(ta.sma, close, self.wma_period)

        # We'll detect ranges dynamically in next()

    def next(self):
        # Skip if not enough data
        if len(self.data.Close) < self.atr_period + self.wma_period + self.min_range_length:
            return

        # Get current ATR value
        current_atr = self.atr[-1]
        if current_atr == 0 or np.isnan(current_atr):
            return

        current_price = self.data.Close[-1]
        current_sma = self.sma[-1]

        # Calculate current range boundaries
        range_size = current_atr * self.atr_multiplier
        range_top = current_sma + range_size / 2
        range_bottom = current_sma - range_size / 2

        # Look back to see if we've been in a range
        lookback_prices = self.data.Close[-self.min_range_length:]
        lookback_sma = list(self.sma)[-self.min_range_length:]

        if len(lookback_prices) >= self.min_range_length:
            # Calculate range for the lookback period
            avg_sma = np.mean(lookback_sma)
            avg_atr = np.mean(list(self.atr)[-self.min_range_length:])

            if avg_atr > 0:
                lookback_range_size = avg_atr * self.atr_multiplier
                lookback_top = avg_sma + lookback_range_size / 2
                lookback_bottom = avg_sma - lookback_range_size / 2

                # Check if most prices were in range
                prices_in_range = sum(1 for p in lookback_prices[:-1] if lookback_bottom <= p <= lookback_top)

                # If we had consolidation and now breaking out
                if prices_in_range >= len(lookback_prices) * 0.7:
                    position_size = 1000000

                    if not self.position:
                        # Breakout above range
                        if current_price > lookback_top and lookback_prices[-2] <= lookback_top:
                            sl_price = avg_sma
                            tp_price = current_price + (current_price - lookback_bottom)
                            self.buy(size=position_size, sl=sl_price, tp=tp_price)

                        # Breakdown below range
                        elif current_price < lookback_bottom and lookback_prices[-2] >= lookback_bottom:
                            sl_price = avg_sma
                            tp_price = current_price - (lookback_top - current_price)
                            self.sell(size=position_size, sl=sl_price, tp=tp_price)

# Run single backtest
bt = Backtest(data, TrendRangeDetectorBase, cash=10000000, commission=0.00045)

print("\n🌙 ===== TREND RANGE DETECTOR BASE - DEFAULT PARAMETERS ===== 🌙")
print(f"WMA Period: {WMA_PERIOD}")
print(f"ATR Period: {ATR_PERIOD}")
print(f"ATR Multiplier: {ATR_MULTIPLIER}")
print(f"Min Range Length: {MIN_RANGE_LENGTH} bars")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")

stats_default = bt.run()
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING TREND RANGE DETECTOR BASE ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(TrendRangeDetectorBase, 'TrendRangeDetectorBase')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/TrendRangeDetectorBase.csv")