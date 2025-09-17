import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
import sys
import os

print("🚀 Moon Dev's Fair Value Gap (FVG) + MFI Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
FVG_MIN_GAP_PERCENT = 0.5  # Minimum gap size as percentage (0.5%)
VOLUME_FILTER_PERIOD = 20  # Period for volume average
VOLUME_THRESHOLD = 1.2  # Volume must be 1.2x average
BULL_VOLUME_RATIO = 0.6  # 60% buy volume for bullish confirmation
BEAR_VOLUME_RATIO = 0.4  # 40% buy volume (60% sell) for bearish confirmation
MFI_PERIOD = 14  # Money Flow Index period
MFI_OVERBOUGHT = 70  # MFI overbought level
MFI_OVERSOLD = 30  # MFI oversold level
MFI_NEUTRAL_LOW = 40  # Lower bound of neutral zone
MFI_NEUTRAL_HIGH = 60  # Upper bound of neutral zone
TAKE_PROFIT_PERCENT = 3.5
STOP_LOSS_PERCENT = 2.0
GAP_MITIGATION_PERCENT = 50  # Exit when gap is 50% filled

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class FVGMFI(Strategy):
    """
    Fair Value Gap (FVG) + Money Flow Index (MFI) Strategy

    This strategy enhances the base FVG strategy with MFI for:
    - Money flow confirmation of gap strength
    - Overbought/oversold filtering for better entries
    - Volume-price relationship validation
    - Enhanced exit conditions based on money flow divergence
    """

    # Strategy parameters
    min_gap_percent = FVG_MIN_GAP_PERCENT / 100
    volume_filter_period = VOLUME_FILTER_PERIOD
    volume_threshold = VOLUME_THRESHOLD
    bull_volume_ratio = BULL_VOLUME_RATIO
    bear_volume_ratio = BEAR_VOLUME_RATIO
    mfi_period = MFI_PERIOD
    mfi_overbought = MFI_OVERBOUGHT
    mfi_oversold = MFI_OVERSOLD
    mfi_neutral_low = MFI_NEUTRAL_LOW
    mfi_neutral_high = MFI_NEUTRAL_HIGH
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100
    gap_mitigation_percent = GAP_MITIGATION_PERCENT / 100

    def init(self):
        # Volume moving average for filtering
        self.volume_ma = self.I(talib.SMA, self.data.Volume, timeperiod=self.volume_filter_period)

        # Money Flow Index for volume-price relationship
        self.mfi = self.I(talib.MFI, self.data.High, self.data.Low,
                          self.data.Close, self.data.Volume, timeperiod=self.mfi_period)

        # MFI Rate of Change for momentum
        def calculate_mfi_roc(mfi, period=5):
            """Calculate rate of change of MFI"""
            roc = np.zeros(len(mfi))
            for i in range(period, len(mfi)):
                if mfi[i-period] != 0:
                    roc[i] = ((mfi[i] - mfi[i-period]) / mfi[i-period]) * 100
            return roc

        self.mfi_roc = self.I(calculate_mfi_roc, self.mfi, 5)

        # ATR for dynamic gap validation
        self.atr = self.I(talib.ATR, self.data.High, self.data.Low, self.data.Close, timeperiod=14)

        # Calculate bull/bear volume ratio
        def calculate_volume_ratio(high, low, close, volume):
            """
            Calculate the ratio of bull vs bear volume for each candle
            Enhanced with MFI weighting
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
        self.entry_mfi = None   # MFI at entry

    def detect_bullish_fvg(self, idx):
        """
        Detect Bullish Fair Value Gap with MFI confirmation
        """
        if idx < 2:
            return False, None, None

        current_low = self.data.Low[idx]
        two_bars_ago_high = self.data.High[idx - 2]
        current_mfi = self.mfi[idx]
        mfi_roc = self.mfi_roc[idx]

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
                        # MFI confirmation for bullish FVG
                        # Best: MFI oversold or rising from oversold
                        if current_mfi <= self.mfi_oversold:
                            return True, current_low, two_bars_ago_high
                        # Good: MFI in neutral zone with positive momentum
                        elif (self.mfi_neutral_low <= current_mfi <= self.mfi_neutral_high
                              and mfi_roc > 0):
                            return True, current_low, two_bars_ago_high
                        # Alternative: Strong positive MFI momentum
                        elif mfi_roc > 10:
                            return True, current_low, two_bars_ago_high

        return False, None, None

    def detect_bearish_fvg(self, idx):
        """
        Detect Bearish Fair Value Gap with MFI confirmation
        """
        if idx < 2:
            return False, None, None

        current_high = self.data.High[idx]
        two_bars_ago_low = self.data.Low[idx - 2]
        current_mfi = self.mfi[idx]
        mfi_roc = self.mfi_roc[idx]

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
                        # MFI confirmation for bearish FVG
                        # Best: MFI overbought or falling from overbought
                        if current_mfi >= self.mfi_overbought:
                            return True, two_bars_ago_low, current_high
                        # Good: MFI in neutral zone with negative momentum
                        elif (self.mfi_neutral_low <= current_mfi <= self.mfi_neutral_high
                              and mfi_roc < 0):
                            return True, two_bars_ago_low, current_high
                        # Alternative: Strong negative MFI momentum
                        elif mfi_roc < -10:
                            return True, two_bars_ago_low, current_high

        return False, None, None

    def is_gap_mitigated(self, gap_high, gap_low, current_price, gap_type):
        """
        Check if a gap has been mitigated (filled)
        Enhanced with MFI divergence check
        """
        if gap_high is None or gap_low is None:
            return False

        gap_midpoint = (gap_high + gap_low) / 2
        current_mfi = self.mfi[-1]

        if gap_type == 'bullish':
            # Bullish gap is mitigated when price goes below midpoint
            # OR when MFI shows bearish divergence (price up, MFI down)
            price_mitigation = current_price <= gap_midpoint
            mfi_divergence = (current_mfi < self.entry_mfi - 10 if self.entry_mfi else False)
            return price_mitigation or mfi_divergence
        else:
            # Bearish gap is mitigated when price goes above midpoint
            # OR when MFI shows bullish divergence (price down, MFI up)
            price_mitigation = current_price >= gap_midpoint
            mfi_divergence = (current_mfi > self.entry_mfi + 10 if self.entry_mfi else False)
            return price_mitigation or mfi_divergence

    def next(self):
        # Skip if we don't have enough data
        if len(self.data) < max(self.volume_filter_period, self.mfi_period * 2):
            return

        # Get current index and values
        idx = len(self.data) - 1
        current_price = self.data.Close[-1]
        current_mfi = self.mfi[-1]

        # Check if we have a position
        if self.position:
            # Exit logic with MFI enhancement
            if self.position.is_long:
                # Dynamic take profit based on MFI
                dynamic_tp = self.take_profit * (1 + max(0, (70 - current_mfi) / 100))

                # Check for take profit
                if current_price >= self.entry_price * (1 + dynamic_tp):
                    self.position.close()
                    self.entry_price = None
                    self.entry_type = None
                    self.entry_mfi = None
                    self.bullish_fvg_high = None
                    self.bullish_fvg_low = None
                # Check for stop loss
                elif current_price <= self.entry_price * (1 - self.stop_loss):
                    self.position.close()
                    self.entry_price = None
                    self.entry_type = None
                    self.entry_mfi = None
                    self.bullish_fvg_high = None
                    self.bullish_fvg_low = None
                # Check for gap mitigation or MFI exit signal
                elif (self.is_gap_mitigated(self.bullish_fvg_high, self.bullish_fvg_low,
                                           current_price, 'bullish') or
                      current_mfi >= self.mfi_overbought):
                    self.position.close()
                    self.entry_price = None
                    self.entry_type = None
                    self.entry_mfi = None
                    self.bullish_fvg_high = None
                    self.bullish_fvg_low = None

            elif self.position.is_short:
                # Dynamic take profit based on MFI
                dynamic_tp = self.take_profit * (1 + max(0, (current_mfi - 30) / 100))

                # Check for take profit
                if current_price <= self.entry_price * (1 - dynamic_tp):
                    self.position.close()
                    self.entry_price = None
                    self.entry_type = None
                    self.entry_mfi = None
                    self.bearish_fvg_high = None
                    self.bearish_fvg_low = None
                # Check for stop loss
                elif current_price >= self.entry_price * (1 + self.stop_loss):
                    self.position.close()
                    self.entry_price = None
                    self.entry_type = None
                    self.entry_mfi = None
                    self.bearish_fvg_high = None
                    self.bearish_fvg_low = None
                # Check for gap mitigation or MFI exit signal
                elif (self.is_gap_mitigated(self.bearish_fvg_high, self.bearish_fvg_low,
                                           current_price, 'bearish') or
                      current_mfi <= self.mfi_oversold):
                    self.position.close()
                    self.entry_price = None
                    self.entry_type = None
                    self.entry_mfi = None
                    self.bearish_fvg_high = None
                    self.bearish_fvg_low = None
        else:
            # Entry logic - Look for new FVGs with MFI confirmation

            # Check for bullish FVG
            is_bullish_fvg, gap_high, gap_low = self.detect_bullish_fvg(idx)
            if is_bullish_fvg:
                # Enter long position
                self.buy()
                self.entry_price = current_price
                self.entry_type = 'bullish'
                self.entry_mfi = current_mfi
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
                self.entry_mfi = current_mfi
                self.bearish_fvg_high = gap_high
                self.bearish_fvg_low = gap_low

# Run single backtest
bt = Backtest(data, FVGMFI, cash=1000000, commission=0.00045)

print("\n🌙 ===== FVG + MFI STRATEGY - DEFAULT PARAMETERS ===== 🌙")
print(f"Min Gap: {FVG_MIN_GAP_PERCENT}%")
print(f"Volume Threshold: {VOLUME_THRESHOLD}x average")
print(f"MFI Period: {MFI_PERIOD}")
print(f"MFI Overbought: {MFI_OVERBOUGHT}")
print(f"MFI Oversold: {MFI_OVERSOLD}")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")

stats_default = bt.run()
print(stats_default)

# Optimization
print("\n🚀 Optimizing FVG + MFI Strategy...")
optimization_results = bt.optimize(
    min_gap_percent=[i / 1000 for i in range(3, 11, 2)],  # 0.3% to 1.0%
    volume_threshold=[1.0, 1.2, 1.5],
    mfi_oversold=[25, 30, 35],
    mfi_overbought=[65, 70, 75],
    take_profit=[i / 1000 for i in range(25, 51, 10)],
    stop_loss=[i / 1000 for i in range(10, 26, 5)],
    maximize='Sortino Ratio',
    constraint=lambda p: p.take_profit > p.stop_loss
)

print("\n🚀 ===== OPTIMIZATION RESULTS ===== 🚀")
print(optimization_results)

print("\n🏆 BEST PARAMETERS:")
print(f"Min Gap: {optimization_results._strategy.min_gap_percent * 100:.1f}%")
print(f"Volume Threshold: {optimization_results._strategy.volume_threshold}x")
print(f"MFI Oversold: {optimization_results._strategy.mfi_oversold}")
print(f"MFI Overbought: {optimization_results._strategy.mfi_overbought}")
print(f"Take Profit: {optimization_results._strategy.take_profit * 100:.1f}%")
print(f"Stop Loss: {optimization_results._strategy.stop_loss * 100:.1f}%")

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING FVG + MFI STRATEGY ON ALL DATA SOURCES")
    print("="*80)

    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(FVGMFI, 'FVG_MFI')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/FVG_MFI_[timestamp].csv")