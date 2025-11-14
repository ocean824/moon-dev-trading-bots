"""
MULTI-TIMEFRAME SWING LOW DEMAND ZONE STRATEGY - ADX FILTER VERSION
=====================================================================
Created by: Moon Dev
Date: 2025-01-30

STRATEGY OVERVIEW:
This version enhances the base multi-timeframe demand zone strategy by adding
Average Directional Index (ADX) as a trend strength filter. ADX helps ensure
we only trade when there's sufficient trend strength and directional movement.

ADDITIONAL ADX RULES:
- ADX > 25: Strong trend present, good for entries
- ADX < 20: Weak trend, avoid entries
- +DI > -DI: Bullish directional movement for long entries
- -DI > +DI: Bearish directional movement for short entries
- ADX period: 14 bars for trend strength measurement

ENTRY RULES FOR LONG:
1. On 4H equivalent: Identify swing low that has dipped to support zone
2. On 30min equivalent: Look for bullish change of structure (ChoCH)
3. ADX Filter: ADX > 25 and +DI > -DI (strong bullish trend)
4. Entry: When price returns to demand zone with ADX confirmation
5. Stop Loss: Below the swing low / demand zone
6. Take Profit: Target previous swing high or 2:1 risk:reward ratio

ENTRY RULES FOR SHORT:
1. On 4H equivalent: Identify swing high that has hit resistance zone
2. On 30min equivalent: Look for bearish change of structure
3. ADX Filter: ADX > 25 and -DI > +DI (strong bearish trend)
4. Entry: When price returns to supply zone with ADX confirmation
5. Stop Loss: Above the swing high / supply zone
6. Take Profit: Target previous swing low or 2:1 risk:reward ratio
"""

import pandas as pd
import numpy as np
import pandas_ta as ta
from backtesting import Backtest, Strategy
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Multi-Timeframe Demand Zone Strategy (ADX Filter) Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
SWING_PERIOD_4H = 30  # 30 bars on 1h = ~30 hours for swing detection
SWING_PERIOD_30M = 10  # 10 bars for short-term structure
ZONE_SIZE_PERCENT = 2.0  # Size of demand/supply zones (2% range)
RISK_REWARD_RATIO = 2.0  # Risk:Reward ratio for take profit
MIN_SWING_STRENGTH = 3  # Minimum bars on each side of swing
ADX_PERIOD = 14  # ADX period for trend strength
ADX_THRESHOLD = 25  # Minimum ADX for strong trend
ADX_WEAK = 20  # ADX below this indicates weak trend

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class MultiTimeframeDemandZoneADX(Strategy):
    # Strategy parameters
    swing_period_4h = SWING_PERIOD_4H
    swing_period_30m = SWING_PERIOD_30M
    zone_size = ZONE_SIZE_PERCENT / 100
    risk_reward = RISK_REWARD_RATIO
    min_swing = MIN_SWING_STRENGTH
    adx_period = ADX_PERIOD
    adx_threshold = ADX_THRESHOLD
    adx_weak = ADX_WEAK

    def init(self):
        """Initialize indicators for multi-timeframe analysis with ADX"""
        # Calculate swing highs and lows for 4H timeframe
        self.swing_high_4h = self.I(self.calculate_swing_high,
                                    self.data.High,
                                    self.swing_period_4h,
                                    self.min_swing)
        self.swing_low_4h = self.I(self.calculate_swing_low,
                                   self.data.Low,
                                   self.swing_period_4h,
                                   self.min_swing)

        # Calculate swing highs and lows for 30M timeframe
        self.swing_high_30m = self.I(self.calculate_swing_high,
                                     self.data.High,
                                     self.swing_period_30m,
                                     2)
        self.swing_low_30m = self.I(self.calculate_swing_low,
                                    self.data.Low,
                                    self.swing_period_30m,
                                    2)

        # Calculate support and resistance zones
        self.support_zone = self.I(self.calculate_support_zone,
                                   self.data.Low,
                                   self.swing_period_4h)
        self.resistance_zone = self.I(self.calculate_resistance_zone,
                                     self.data.High,
                                     self.swing_period_4h)

        # Track change of structure
        self.bullish_choch = self.I(self.detect_bullish_choch,
                                    self.data.High,
                                    self.data.Low,
                                    self.swing_period_30m)
        self.bearish_choch = self.I(self.detect_bearish_choch,
                                    self.data.High,
                                    self.data.Low,
                                    self.swing_period_30m)

        # Calculate ADX and directional indicators
        adx_result = ta.adx(pd.Series(self.data.High),
                            pd.Series(self.data.Low),
                            pd.Series(self.data.Close),
                            self.adx_period)

        self.adx = self.I(lambda: adx_result[f'ADX_{self.adx_period}'].values)
        self.plus_di = self.I(lambda: adx_result[f'DMP_{self.adx_period}'].values)
        self.minus_di = self.I(lambda: adx_result[f'DMN_{self.adx_period}'].values)

        # Calculate ADX slope for trend acceleration
        self.adx_slope = self.I(self.calculate_adx_slope, self.adx, 5)

        # Calculate ATR for dynamic stop loss
        self.atr = self.I(ta.atr, pd.Series(self.data.High),
                         pd.Series(self.data.Low),
                         pd.Series(self.data.Close), 14)

        print(f"✅ Moon Dev's indicators with ADX initialized - ADX Period: {self.adx_period}, Threshold: {self.adx_threshold}")

    def calculate_swing_high(self, highs, period, min_strength):
        """Calculate swing highs with minimum strength requirement"""
        swing_highs = np.full(len(highs), np.nan)
        highs = np.array(highs)

        for i in range(min_strength, len(highs) - min_strength):
            if i < period:
                continue

            is_swing_high = True
            current_high = highs[i]

            for j in range(max(0, i - min_strength), i):
                if highs[j] >= current_high:
                    is_swing_high = False
                    break

            if is_swing_high:
                for j in range(i + 1, min(len(highs), i + min_strength + 1)):
                    if highs[j] > current_high:
                        is_swing_high = False
                        break

            if is_swing_high:
                swing_highs[i] = current_high

        for i in range(1, len(swing_highs)):
            if np.isnan(swing_highs[i]) and not np.isnan(swing_highs[i-1]):
                swing_highs[i] = swing_highs[i-1]

        return swing_highs

    def calculate_swing_low(self, lows, period, min_strength):
        """Calculate swing lows with minimum strength requirement"""
        swing_lows = np.full(len(lows), np.nan)
        lows = np.array(lows)

        for i in range(min_strength, len(lows) - min_strength):
            if i < period:
                continue

            is_swing_low = True
            current_low = lows[i]

            for j in range(max(0, i - min_strength), i):
                if lows[j] <= current_low:
                    is_swing_low = False
                    break

            if is_swing_low:
                for j in range(i + 1, min(len(lows), i + min_strength + 1)):
                    if lows[j] < current_low:
                        is_swing_low = False
                        break

            if is_swing_low:
                swing_lows[i] = current_low

        for i in range(1, len(swing_lows)):
            if np.isnan(swing_lows[i]) and not np.isnan(swing_lows[i-1]):
                swing_lows[i] = swing_lows[i-1]

        return swing_lows

    def calculate_support_zone(self, lows, period):
        """Calculate support zone based on recent swing lows"""
        lows = np.array(lows)
        support = np.full(len(lows), np.nan)

        for i in range(period, len(lows)):
            recent_lows = lows[i-period:i]
            support[i] = np.percentile(recent_lows, 20)

        return support

    def calculate_resistance_zone(self, highs, period):
        """Calculate resistance zone based on recent swing highs"""
        highs = np.array(highs)
        resistance = np.full(len(highs), np.nan)

        for i in range(period, len(highs)):
            recent_highs = highs[i-period:i]
            resistance[i] = np.percentile(recent_highs, 80)

        return resistance

    def detect_bullish_choch(self, highs, lows, period):
        """Detect bullish change of character"""
        highs = np.array(highs)
        lows = np.array(lows)
        choch = np.zeros(len(highs))

        for i in range(period * 2, len(highs)):
            recent_highs = highs[i-period:i]
            recent_lows = lows[i-period:i]
            prev_highs = highs[i-period*2:i-period]
            prev_lows = lows[i-period*2:i-period]

            if len(recent_highs) > 0 and len(prev_highs) > 0:
                current_high = np.max(recent_highs)
                prev_high = np.max(prev_highs)
                current_low = np.min(recent_lows)
                prev_low = np.min(prev_lows)

                if current_high > prev_high and prev_low < current_low:
                    choch[i] = 1

        return choch

    def detect_bearish_choch(self, highs, lows, period):
        """Detect bearish change of character"""
        highs = np.array(highs)
        lows = np.array(lows)
        choch = np.zeros(len(highs))

        for i in range(period * 2, len(lows)):
            recent_highs = highs[i-period:i]
            recent_lows = lows[i-period:i]
            prev_highs = highs[i-period*2:i-period]
            prev_lows = lows[i-period*2:i-period]

            if len(recent_lows) > 0 and len(prev_lows) > 0:
                current_low = np.min(recent_lows)
                prev_low = np.min(prev_lows)
                current_high = np.max(recent_highs)
                prev_high = np.max(prev_highs)

                if current_low < prev_low and prev_high > current_high:
                    choch[i] = 1

        return choch

    def calculate_adx_slope(self, adx, period):
        """Calculate ADX slope to detect trend acceleration"""
        adx = np.array(adx)
        slopes = np.zeros(len(adx))

        for i in range(period, len(adx)):
            if not np.isnan(adx[i]) and not np.isnan(adx[i-period]):
                slopes[i] = (adx[i] - adx[i-period]) / period

        return slopes

    def next(self):
        """Execute trading logic with ADX filter"""
        if len(self.data) < self.swing_period_4h * 2:
            return

        current_price = self.data.Close[-1]

        # Get current indicators
        swing_high_4h = self.swing_high_4h[-1]
        swing_low_4h = self.swing_low_4h[-1]
        support = self.support_zone[-1]
        resistance = self.resistance_zone[-1]
        bullish_choch = self.bullish_choch[-1]
        bearish_choch = self.bearish_choch[-1]
        adx = self.adx[-1]
        plus_di = self.plus_di[-1]
        minus_di = self.minus_di[-1]
        adx_slope = self.adx_slope[-1]
        atr = self.atr[-1]

        # Skip if indicators are not ready
        if (np.isnan(support) or np.isnan(resistance) or np.isnan(atr) or
            np.isnan(adx) or np.isnan(plus_di) or np.isnan(minus_di)):
            return

        # Define demand and supply zones
        demand_zone_upper = support * (1 + self.zone_size)
        demand_zone_lower = support * (1 - self.zone_size)
        supply_zone_upper = resistance * (1 + self.zone_size)
        supply_zone_lower = resistance * (1 - self.zone_size)

        if not self.position:
            # LONG ENTRY WITH ADX FILTER
            # Strong trend (ADX > threshold) and bullish direction (+DI > -DI)
            adx_long_signal = (adx > self.adx_threshold and
                              plus_di > minus_di and
                              (adx_slope > 0 or adx > 30))  # Trend accelerating or very strong

            if (demand_zone_lower <= current_price <= demand_zone_upper and
                bullish_choch > 0 and
                not np.isnan(swing_low_4h) and
                swing_low_4h <= support * 1.02 and
                adx_long_signal):  # ADX confirmation

                stop_loss = demand_zone_lower - (atr * 0.5)
                risk = current_price - stop_loss
                take_profit = current_price + (risk * self.risk_reward)

                self.buy(sl=stop_loss, tp=take_profit, size=1000000)

            # SHORT ENTRY WITH ADX FILTER
            # Strong trend (ADX > threshold) and bearish direction (-DI > +DI)
            adx_short_signal = (adx > self.adx_threshold and
                               minus_di > plus_di and
                               (adx_slope > 0 or adx > 30))  # Trend accelerating or very strong

            if (supply_zone_lower <= current_price <= supply_zone_upper and
                  bearish_choch > 0 and
                  not np.isnan(swing_high_4h) and
                  swing_high_4h >= resistance * 0.98 and
                  adx_short_signal):  # ADX confirmation

                stop_loss = supply_zone_upper + (atr * 0.5)
                risk = stop_loss - current_price
                take_profit = current_price - (risk * self.risk_reward)

                self.sell(sl=stop_loss, tp=take_profit, size=1000000)

# Run single backtest (default behavior)
bt = Backtest(data, MultiTimeframeDemandZoneADX, cash=10000000, commission=0.00045)

print("\n🌙 ===== MULTI-TIMEFRAME DEMAND ZONE - ADX FILTER ===== 🌙")
print(f"Swing Period 4H: {SWING_PERIOD_4H}")
print(f"Swing Period 30M: {SWING_PERIOD_30M}")
print(f"Zone Size: {ZONE_SIZE_PERCENT}%")
print(f"Risk:Reward Ratio: {RISK_REWARD_RATIO}:1")
print(f"ADX Period: {ADX_PERIOD}, Threshold: {ADX_THRESHOLD}")

stats_default = bt.run()
print("\n📊 Backtest Results:")
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING MULTI-TIMEFRAME DEMAND ZONE (ADX FILTER) ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(MultiTimeframeDemandZoneADX, 'MTF_DemandZone_ADX')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/MTF_DemandZone_ADX.csv")