import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
import sys
import os

print("🚀 Moon Dev's Fair Value Gap (FVG) + ADX Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
FVG_MIN_GAP_PERCENT = 0.5  # Minimum gap size as percentage (0.5%)
VOLUME_FILTER_PERIOD = 20  # Period for volume average
VOLUME_THRESHOLD = 1.2  # Volume must be 1.2x average
BULL_VOLUME_RATIO = 0.6  # 60% buy volume for bullish confirmation
BEAR_VOLUME_RATIO = 0.4  # 40% buy volume (60% sell) for bearish confirmation
ADX_PERIOD = 14  # ADX period
ADX_THRESHOLD = 25  # Minimum ADX for trend strength
ADX_STRONG = 40  # Strong trend threshold
DI_DIFFERENCE = 5  # Minimum difference between +DI and -DI
TAKE_PROFIT_PERCENT = 3.5
STOP_LOSS_PERCENT = 2.0
GAP_MITIGATION_PERCENT = 50  # Exit when gap is 50% filled

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class FVGADX(Strategy):
    """
    Fair Value Gap (FVG) + ADX Strategy

    This strategy enhances the base FVG strategy with ADX for:
    - Trend strength validation before entering gaps
    - Directional movement confirmation (+DI/-DI)
    - Dynamic position sizing based on trend strength
    - Enhanced exit conditions based on trend weakening
    """

    # Strategy parameters
    min_gap_percent = FVG_MIN_GAP_PERCENT / 100
    volume_filter_period = VOLUME_FILTER_PERIOD
    volume_threshold = VOLUME_THRESHOLD
    bull_volume_ratio = BULL_VOLUME_RATIO
    bear_volume_ratio = BEAR_VOLUME_RATIO
    adx_period = ADX_PERIOD
    adx_threshold = ADX_THRESHOLD
    adx_strong = ADX_STRONG
    di_difference = DI_DIFFERENCE
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100
    gap_mitigation_percent = GAP_MITIGATION_PERCENT / 100

    def init(self):
        # Volume moving average for filtering
        self.volume_ma = self.I(talib.SMA, self.data.Volume, timeperiod=self.volume_filter_period)

        # ADX for trend strength
        self.adx = self.I(talib.ADX, self.data.High, self.data.Low, self.data.Close, timeperiod=self.adx_period)

        # Directional Indicators
        self.plus_di = self.I(talib.PLUS_DI, self.data.High, self.data.Low, self.data.Close, timeperiod=self.adx_period)
        self.minus_di = self.I(talib.MINUS_DI, self.data.High, self.data.Low, self.data.Close, timeperiod=self.adx_period)

        # ADX Rate of Change for trend acceleration
        def calculate_adx_roc(adx, period=5):
            """Calculate rate of change of ADX"""
            roc = np.zeros(len(adx))
            for i in range(period, len(adx)):
                if adx[i-period] != 0:
                    roc[i] = adx[i] - adx[i-period]
            return roc

        self.adx_roc = self.I(calculate_adx_roc, self.adx, 5)

        # ATR for dynamic gap validation and position sizing
        self.atr = self.I(talib.ATR, self.data.High, self.data.Low, self.data.Close, timeperiod=14)

        # Calculate bull/bear volume ratio
        def calculate_volume_ratio(high, low, close, volume):
            """
            Calculate the ratio of bull vs bear volume for each candle
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
        self.entry_adx = None   # ADX at entry
        self.entry_di_diff = None  # DI difference at entry

    def detect_bullish_fvg(self, idx):
        """
        Detect Bullish Fair Value Gap with ADX confirmation
        """
        if idx < 2:
            return False, None, None

        current_low = self.data.Low[idx]
        two_bars_ago_high = self.data.High[idx - 2]
        current_adx = self.adx[idx]
        plus_di = self.plus_di[idx]
        minus_di = self.minus_di[idx]
        adx_roc = self.adx_roc[idx]

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
                        # ADX confirmation for bullish FVG
                        # Best: Strong trend with bullish direction
                        if (current_adx >= self.adx_strong and
                            plus_di > minus_di + self.di_difference):
                            return True, current_low, two_bars_ago_high
                        # Good: Moderate trend with bullish direction and strengthening
                        elif (current_adx >= self.adx_threshold and
                              plus_di > minus_di and
                              adx_roc > 0):
                            return True, current_low, two_bars_ago_high
                        # Alternative: Emerging trend with strong bullish direction
                        elif (current_adx >= 20 and
                              plus_di > minus_di + self.di_difference * 2):
                            return True, current_low, two_bars_ago_high

        return False, None, None

    def detect_bearish_fvg(self, idx):
        """
        Detect Bearish Fair Value Gap with ADX confirmation
        """
        if idx < 2:
            return False, None, None

        current_high = self.data.High[idx]
        two_bars_ago_low = self.data.Low[idx - 2]
        current_adx = self.adx[idx]
        plus_di = self.plus_di[idx]
        minus_di = self.minus_di[idx]
        adx_roc = self.adx_roc[idx]

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
                        # ADX confirmation for bearish FVG
                        # Best: Strong trend with bearish direction
                        if (current_adx >= self.adx_strong and
                            minus_di > plus_di + self.di_difference):
                            return True, two_bars_ago_low, current_high
                        # Good: Moderate trend with bearish direction and strengthening
                        elif (current_adx >= self.adx_threshold and
                              minus_di > plus_di and
                              adx_roc > 0):
                            return True, two_bars_ago_low, current_high
                        # Alternative: Emerging trend with strong bearish direction
                        elif (current_adx >= 20 and
                              minus_di > plus_di + self.di_difference * 2):
                            return True, two_bars_ago_low, current_high

        return False, None, None

    def is_gap_mitigated(self, gap_high, gap_low, current_price, gap_type):
        """
        Check if a gap has been mitigated (filled)
        Enhanced with trend strength analysis
        """
        if gap_high is None or gap_low is None:
            return False

        gap_midpoint = (gap_high + gap_low) / 2
        current_adx = self.adx[-1]
        plus_di = self.plus_di[-1]
        minus_di = self.minus_di[-1]

        if gap_type == 'bullish':
            # Bullish gap is mitigated when price goes below midpoint
            # OR when trend reverses (ADX drops or DI flips)
            price_mitigation = current_price <= gap_midpoint
            trend_reversal = (current_adx < self.entry_adx - 10 or
                            minus_di > plus_di + self.di_difference
                            if self.entry_adx else False)
            return price_mitigation or trend_reversal
        else:
            # Bearish gap is mitigated when price goes above midpoint
            # OR when trend reverses (ADX drops or DI flips)
            price_mitigation = current_price >= gap_midpoint
            trend_reversal = (current_adx < self.entry_adx - 10 or
                            plus_di > minus_di + self.di_difference
                            if self.entry_adx else False)
            return price_mitigation or trend_reversal

    def calculate_dynamic_sizing(self, adx_value):
        """
        Calculate position size multiplier based on ADX strength
        """
        if adx_value >= self.adx_strong:
            return 1.0  # Full size for strong trends
        elif adx_value >= self.adx_threshold:
            return 0.75  # Reduced size for moderate trends
        else:
            return 0.5  # Half size for weak trends

    def next(self):
        # Skip if we don't have enough data
        if len(self.data) < max(self.volume_filter_period, self.adx_period * 2):
            return

        # Get current index and values
        idx = len(self.data) - 1
        current_price = self.data.Close[-1]
        current_adx = self.adx[-1]
        plus_di = self.plus_di[-1]
        minus_di = self.minus_di[-1]
        current_atr = self.atr[-1]

        # Check if we have a position
        if self.position:
            # Exit logic with ADX enhancement
            if self.position.is_long:
                # Dynamic take profit based on ADX strength
                dynamic_tp = self.take_profit * (1 + max(0, (current_adx - 25) / 50))
                # Dynamic stop loss based on ATR
                dynamic_sl = self.stop_loss * (current_atr / self.entry_price if self.entry_price else 1)

                # Check for take profit
                if current_price >= self.entry_price * (1 + dynamic_tp):
                    self.position.close()
                    self.entry_price = None
                    self.entry_type = None
                    self.entry_adx = None
                    self.entry_di_diff = None
                    self.bullish_fvg_high = None
                    self.bullish_fvg_low = None
                # Check for stop loss
                elif current_price <= self.entry_price * (1 - dynamic_sl):
                    self.position.close()
                    self.entry_price = None
                    self.entry_type = None
                    self.entry_adx = None
                    self.entry_di_diff = None
                    self.bullish_fvg_high = None
                    self.bullish_fvg_low = None
                # Check for gap mitigation or trend weakness
                elif (self.is_gap_mitigated(self.bullish_fvg_high, self.bullish_fvg_low,
                                           current_price, 'bullish') or
                      current_adx < 20):  # Exit on very weak trend
                    self.position.close()
                    self.entry_price = None
                    self.entry_type = None
                    self.entry_adx = None
                    self.entry_di_diff = None
                    self.bullish_fvg_high = None
                    self.bullish_fvg_low = None

            elif self.position.is_short:
                # Dynamic take profit based on ADX strength
                dynamic_tp = self.take_profit * (1 + max(0, (current_adx - 25) / 50))
                # Dynamic stop loss based on ATR
                dynamic_sl = self.stop_loss * (current_atr / self.entry_price if self.entry_price else 1)

                # Check for take profit
                if current_price <= self.entry_price * (1 - dynamic_tp):
                    self.position.close()
                    self.entry_price = None
                    self.entry_type = None
                    self.entry_adx = None
                    self.entry_di_diff = None
                    self.bearish_fvg_high = None
                    self.bearish_fvg_low = None
                # Check for stop loss
                elif current_price >= self.entry_price * (1 + dynamic_sl):
                    self.position.close()
                    self.entry_price = None
                    self.entry_type = None
                    self.entry_adx = None
                    self.entry_di_diff = None
                    self.bearish_fvg_high = None
                    self.bearish_fvg_low = None
                # Check for gap mitigation or trend weakness
                elif (self.is_gap_mitigated(self.bearish_fvg_high, self.bearish_fvg_low,
                                           current_price, 'bearish') or
                      current_adx < 20):  # Exit on very weak trend
                    self.position.close()
                    self.entry_price = None
                    self.entry_type = None
                    self.entry_adx = None
                    self.entry_di_diff = None
                    self.bearish_fvg_high = None
                    self.bearish_fvg_low = None
        else:
            # Entry logic - Look for new FVGs with ADX confirmation

            # Only consider entries when there's some trend strength
            if current_adx >= 20:
                # Check for bullish FVG
                is_bullish_fvg, gap_high, gap_low = self.detect_bullish_fvg(idx)
                if is_bullish_fvg:
                    # Enter long position with dynamic sizing
                    size_multiplier = self.calculate_dynamic_sizing(current_adx)
                    self.buy(size=size_multiplier)
                    self.entry_price = current_price
                    self.entry_type = 'bullish'
                    self.entry_adx = current_adx
                    self.entry_di_diff = plus_di - minus_di
                    self.bullish_fvg_high = gap_high
                    self.bullish_fvg_low = gap_low
                    return

                # Check for bearish FVG
                is_bearish_fvg, gap_high, gap_low = self.detect_bearish_fvg(idx)
                if is_bearish_fvg:
                    # Enter short position with dynamic sizing
                    size_multiplier = self.calculate_dynamic_sizing(current_adx)
                    self.sell(size=size_multiplier)
                    self.entry_price = current_price
                    self.entry_type = 'bearish'
                    self.entry_adx = current_adx
                    self.entry_di_diff = minus_di - plus_di
                    self.bearish_fvg_high = gap_high
                    self.bearish_fvg_low = gap_low

# Run single backtest
bt = Backtest(data, FVGADX, cash=1000000, commission=0.00045)

print("\n🌙 ===== FVG + ADX STRATEGY - DEFAULT PARAMETERS ===== 🌙")
print(f"Min Gap: {FVG_MIN_GAP_PERCENT}%")
print(f"Volume Threshold: {VOLUME_THRESHOLD}x average")
print(f"ADX Period: {ADX_PERIOD}")
print(f"ADX Threshold: {ADX_THRESHOLD}")
print(f"ADX Strong: {ADX_STRONG}")
print(f"DI Difference: {DI_DIFFERENCE}")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")

stats_default = bt.run()
print(stats_default)

# Optimization
print("\n🚀 Optimizing FVG + ADX Strategy...")
optimization_results = bt.optimize(
    min_gap_percent=[i / 1000 for i in range(3, 11, 2)],  # 0.3% to 1.0%
    volume_threshold=[1.0, 1.2, 1.5],
    adx_threshold=[20, 25, 30],
    adx_strong=[35, 40, 45],
    take_profit=[i / 1000 for i in range(25, 51, 10)],
    stop_loss=[i / 1000 for i in range(10, 26, 5)],
    maximize='Sortino Ratio',
    constraint=lambda p: p.take_profit > p.stop_loss and p.adx_threshold < p.adx_strong
)

print("\n🚀 ===== OPTIMIZATION RESULTS ===== 🚀")
print(optimization_results)

print("\n🏆 BEST PARAMETERS:")
print(f"Min Gap: {optimization_results._strategy.min_gap_percent * 100:.1f}%")
print(f"Volume Threshold: {optimization_results._strategy.volume_threshold}x")
print(f"ADX Threshold: {optimization_results._strategy.adx_threshold}")
print(f"ADX Strong: {optimization_results._strategy.adx_strong}")
print(f"Take Profit: {optimization_results._strategy.take_profit * 100:.1f}%")
print(f"Stop Loss: {optimization_results._strategy.stop_loss * 100:.1f}%")

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING FVG + ADX STRATEGY ON ALL DATA SOURCES")
    print("="*80)

    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(FVGADX, 'FVG_ADX')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/FVG_ADX_[timestamp].csv")