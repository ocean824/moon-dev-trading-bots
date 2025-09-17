import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
import sys
import os

print("🚀 Moon Dev's Fair Value Gap (FVG) Base Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
FVG_MIN_GAP_PERCENT = 0.5  # Minimum gap size as percentage (0.5%)
VOLUME_FILTER_PERIOD = 20  # Period for volume average
VOLUME_THRESHOLD = 1.2  # Volume must be 1.2x average
BULL_VOLUME_RATIO = 0.6  # 60% buy volume for bullish confirmation
BEAR_VOLUME_RATIO = 0.4  # 40% buy volume (60% sell) for bearish confirmation
TAKE_PROFIT_PERCENT = 3.0
STOP_LOSS_PERCENT = 2.0
GAP_MITIGATION_PERCENT = 50  # Exit when gap is 50% filled

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class FVGBase(Strategy):
    """
    Fair Value Gap (FVG) Base Strategy

    This strategy identifies and trades Fair Value Gaps using:
    - 3-bar pattern recognition for gap detection
    - Volume analysis for gap strength validation
    - Bull/Bear volume ratio for directional bias
    - Gap mitigation tracking for exit signals
    """

    # Strategy parameters
    min_gap_percent = FVG_MIN_GAP_PERCENT / 100
    volume_filter_period = VOLUME_FILTER_PERIOD
    volume_threshold = VOLUME_THRESHOLD
    bull_volume_ratio = BULL_VOLUME_RATIO
    bear_volume_ratio = BEAR_VOLUME_RATIO
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100
    gap_mitigation_percent = GAP_MITIGATION_PERCENT / 100

    def init(self):
        # Volume moving average for filtering
        self.volume_ma = self.I(talib.SMA, self.data.Volume, timeperiod=self.volume_filter_period)

        # ATR for dynamic gap validation
        self.atr = self.I(talib.ATR, self.data.High, self.data.Low, self.data.Close, timeperiod=14)

        # Calculate bull/bear volume ratio
        def calculate_volume_ratio(high, low, close, volume):
            """
            Calculate the ratio of bull vs bear volume for each candle
            Bull volume = volume * ((close - low) / (high - low))
            Bear volume = volume * ((high - close) / (high - low))
            """
            bull_ratio = np.zeros(len(high))

            for i in range(len(high)):
                if high[i] > low[i]:
                    # Calculate where close is within the candle's range
                    range_size = high[i] - low[i]
                    bull_portion = (close[i] - low[i]) / range_size
                    bull_ratio[i] = bull_portion
                else:
                    # If high equals low (doji), assume neutral (0.5)
                    bull_ratio[i] = 0.5

            return bull_ratio

        self.bull_volume_ratio = self.I(
            calculate_volume_ratio,
            self.data.High, self.data.Low, self.data.Close, self.data.Volume
        )

        # Track active FVGs
        self.bullish_fvg_high = None  # Top of bullish gap
        self.bullish_fvg_low = None   # Bottom of bullish gap
        self.bearish_fvg_high = None  # Top of bearish gap
        self.bearish_fvg_low = None   # Bottom of bearish gap

        # Track entry details
        self.entry_price = None
        self.entry_type = None  # 'bullish' or 'bearish'

    def detect_bullish_fvg(self, idx):
        """
        Detect Bullish Fair Value Gap
        Condition: Low of bar[i] > High of bar[i-2]
        """
        if idx < 2:
            return False, None, None

        current_low = self.data.Low[idx]
        two_bars_ago_high = self.data.High[idx - 2]

        # Check for bullish gap
        if current_low > two_bars_ago_high:
            gap_size = current_low - two_bars_ago_high
            price_level = (current_low + two_bars_ago_high) / 2
            gap_percent = gap_size / price_level

            # Validate gap size
            if gap_percent >= self.min_gap_percent:
                # Check volume conditions
                current_volume = self.data.Volume[idx]
                avg_volume = self.volume_ma[idx]

                if current_volume >= avg_volume * self.volume_threshold:
                    # Check bull volume ratio
                    if self.bull_volume_ratio[idx] >= self.bull_volume_ratio:
                        return True, current_low, two_bars_ago_high

        return False, None, None

    def detect_bearish_fvg(self, idx):
        """
        Detect Bearish Fair Value Gap
        Condition: High of bar[i] < Low of bar[i-2]
        """
        if idx < 2:
            return False, None, None

        current_high = self.data.High[idx]
        two_bars_ago_low = self.data.Low[idx - 2]

        # Check for bearish gap
        if current_high < two_bars_ago_low:
            gap_size = two_bars_ago_low - current_high
            price_level = (current_high + two_bars_ago_low) / 2
            gap_percent = gap_size / price_level

            # Validate gap size
            if gap_percent >= self.min_gap_percent:
                # Check volume conditions
                current_volume = self.data.Volume[idx]
                avg_volume = self.volume_ma[idx]

                if current_volume >= avg_volume * self.volume_threshold:
                    # Check bear volume ratio
                    if self.bull_volume_ratio[idx] <= self.bear_volume_ratio:
                        return True, two_bars_ago_low, current_high

        return False, None, None

    def is_gap_mitigated(self, gap_high, gap_low, current_price, gap_type):
        """
        Check if a gap has been mitigated (filled)
        """
        if gap_high is None or gap_low is None:
            return False

        gap_midpoint = (gap_high + gap_low) / 2

        if gap_type == 'bullish':
            # Bullish gap is mitigated when price goes below midpoint
            return current_price <= gap_midpoint
        else:
            # Bearish gap is mitigated when price goes above midpoint
            return current_price >= gap_midpoint

    def next(self):
        # Skip if we don't have enough data
        if len(self.data) < self.volume_filter_period:
            return

        # Get current index and values
        idx = len(self.data) - 1
        current_price = self.data.Close[-1]

        # Check if we have a position
        if self.position:
            # Exit logic
            if self.position.is_long:
                # Check for take profit
                if current_price >= self.entry_price * (1 + self.take_profit):
                    self.position.close()
                    self.entry_price = None
                    self.entry_type = None
                    self.bullish_fvg_high = None
                    self.bullish_fvg_low = None
                # Check for stop loss
                elif current_price <= self.entry_price * (1 - self.stop_loss):
                    self.position.close()
                    self.entry_price = None
                    self.entry_type = None
                    self.bullish_fvg_high = None
                    self.bullish_fvg_low = None
                # Check for gap mitigation
                elif self.is_gap_mitigated(self.bullish_fvg_high, self.bullish_fvg_low,
                                          current_price, 'bullish'):
                    self.position.close()
                    self.entry_price = None
                    self.entry_type = None
                    self.bullish_fvg_high = None
                    self.bullish_fvg_low = None

            elif self.position.is_short:
                # Check for take profit
                if current_price <= self.entry_price * (1 - self.take_profit):
                    self.position.close()
                    self.entry_price = None
                    self.entry_type = None
                    self.bearish_fvg_high = None
                    self.bearish_fvg_low = None
                # Check for stop loss
                elif current_price >= self.entry_price * (1 + self.stop_loss):
                    self.position.close()
                    self.entry_price = None
                    self.entry_type = None
                    self.bearish_fvg_high = None
                    self.bearish_fvg_low = None
                # Check for gap mitigation
                elif self.is_gap_mitigated(self.bearish_fvg_high, self.bearish_fvg_low,
                                          current_price, 'bearish'):
                    self.position.close()
                    self.entry_price = None
                    self.entry_type = None
                    self.bearish_fvg_high = None
                    self.bearish_fvg_low = None
        else:
            # Entry logic - Look for new FVGs

            # Check for bullish FVG
            is_bullish_fvg, gap_high, gap_low = self.detect_bullish_fvg(idx)
            if is_bullish_fvg:
                # Enter long position
                self.buy()
                self.entry_price = current_price
                self.entry_type = 'bullish'
                self.bullish_fvg_high = gap_high
                self.bullish_fvg_low = gap_low
                return

            # Check for bearish FVG
            is_bearish_fvg, gap_high, gap_low = self.detect_bearish_fvg(idx)
            if is_bearish_fvg:
                # Enter short position
                self.sell()
                self.entry_price = current_price
                self.entry_type = 'bearish'
                self.bearish_fvg_high = gap_high
                self.bearish_fvg_low = gap_low

# Run single backtest
bt = Backtest(data, FVGBase, cash=1000000, commission=0.00045)

print("\n🌙 ===== FVG BASE STRATEGY - DEFAULT PARAMETERS ===== 🌙")
print(f"Min Gap: {FVG_MIN_GAP_PERCENT}%")
print(f"Volume Threshold: {VOLUME_THRESHOLD}x average")
print(f"Bull Volume Ratio: {BULL_VOLUME_RATIO}")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")
print(f"Gap Mitigation: {GAP_MITIGATION_PERCENT}% filled")

stats_default = bt.run()
print(stats_default)

# Optimization
print("\n🚀 Optimizing FVG Base Strategy...")
optimization_results = bt.optimize(
    min_gap_percent=[i / 1000 for i in range(3, 11, 2)],  # 0.3% to 1.0%
    volume_threshold=[1.0, 1.2, 1.5, 1.8],
    bull_volume_ratio=[0.55, 0.60, 0.65, 0.70],
    take_profit=[i / 1000 for i in range(20, 51, 10)],
    stop_loss=[i / 1000 for i in range(10, 31, 5)],
    maximize='Sortino Ratio',
    constraint=lambda p: p.take_profit > p.stop_loss
)

print("\n🚀 ===== OPTIMIZATION RESULTS ===== 🚀")
print(optimization_results)

print("\n🏆 BEST PARAMETERS:")
print(f"Min Gap: {optimization_results._strategy.min_gap_percent * 100:.1f}%")
print(f"Volume Threshold: {optimization_results._strategy.volume_threshold}x")
print(f"Bull Volume Ratio: {optimization_results._strategy.bull_volume_ratio}")
print(f"Take Profit: {optimization_results._strategy.take_profit * 100:.1f}%")
print(f"Stop Loss: {optimization_results._strategy.stop_loss * 100:.1f}%")

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING FVG BASE STRATEGY ON ALL DATA SOURCES")
    print("="*80)

    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(FVGBase, 'FVG_Base')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/FVG_Base_[timestamp].csv")