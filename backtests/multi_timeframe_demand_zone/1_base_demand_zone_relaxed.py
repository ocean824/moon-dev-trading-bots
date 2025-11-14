"""
MULTI-TIMEFRAME SWING LOW DEMAND ZONE STRATEGY - RELAXED BASE VERSION
=======================================================================
Created by: Moon Dev
Date: 2025-01-30

STRATEGY OVERVIEW:
This is a relaxed version of the multi-timeframe demand zone strategy that uses
less strict conditions to ensure trades are actually generated. It still uses
4-hour equivalent timeframe for trend and 30-minute equivalent for entry precision,
but with more lenient filters.

RELAXED ENTRY RULES FOR LONG:
1. Price is near support zone (within 3%)
2. Price has been below support recently (last 10 bars)
3. Current price is rising (close > previous close)
4. Optional: Bullish structure detected

RELAXED ENTRY RULES FOR SHORT:
1. Price is near resistance zone (within 3%)
2. Price has been above resistance recently (last 10 bars)
3. Current price is falling (close < previous close)
4. Optional: Bearish structure detected
"""

import pandas as pd
import numpy as np
import pandas_ta as ta
from backtesting import Backtest, Strategy
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Multi-Timeframe Demand Zone Strategy (Relaxed Base) Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters - More relaxed
SWING_PERIOD_4H = 20  # Reduced from 30
ZONE_SIZE_PERCENT = 3.0  # Increased from 2.0% for wider zones
RISK_REWARD_RATIO = 2.0
SUPPORT_LOOKBACK = 10  # How many bars to check for support/resistance touch

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class MultiTimeframeDemandZoneRelaxed(Strategy):
    # Strategy parameters
    swing_period = SWING_PERIOD_4H
    zone_size = ZONE_SIZE_PERCENT / 100
    risk_reward = RISK_REWARD_RATIO
    support_lookback = SUPPORT_LOOKBACK

    def init(self):
        """Initialize indicators for multi-timeframe analysis - simplified version"""
        # Calculate simple support and resistance using rolling min/max
        self.support = self.I(lambda x: pd.Series(x).rolling(self.swing_period).min().values,
                              self.data.Low)
        self.resistance = self.I(lambda x: pd.Series(x).rolling(self.swing_period).max().values,
                                self.data.High)

        # Calculate moving averages for trend direction
        self.sma_fast = self.I(ta.sma, pd.Series(self.data.Close), 10)
        self.sma_slow = self.I(ta.sma, pd.Series(self.data.Close), 30)

        # Calculate ATR for stop loss
        self.atr = self.I(ta.atr, pd.Series(self.data.High),
                         pd.Series(self.data.Low),
                         pd.Series(self.data.Close), 14)

        # Simple momentum indicator
        self.rsi = self.I(ta.rsi, pd.Series(self.data.Close), 14)

        print(f"✅ Moon Dev's relaxed indicators initialized - Swing Period: {self.swing_period}, Zone Size: {self.zone_size*100}%")

    def next(self):
        """Execute trading logic with relaxed conditions"""
        # Skip if we don't have enough data
        if len(self.data) < self.swing_period * 2:
            return

        current_price = self.data.Close[-1]
        prev_price = self.data.Close[-2] if len(self.data) > 1 else current_price

        # Get current indicators
        support = self.support[-1]
        resistance = self.resistance[-1]
        sma_fast = self.sma_fast[-1]
        sma_slow = self.sma_slow[-1]
        atr = self.atr[-1]
        rsi = self.rsi[-1]

        # Skip if indicators are not ready
        if np.isnan(support) or np.isnan(resistance) or np.isnan(atr) or np.isnan(rsi):
            return

        # Define demand and supply zones (wider for more trades)
        demand_zone_upper = support * (1 + self.zone_size)
        demand_zone_lower = support * (1 - self.zone_size/2)  # Asymmetric zone
        supply_zone_upper = resistance * (1 + self.zone_size/2)  # Asymmetric zone
        supply_zone_lower = resistance * (1 - self.zone_size)

        # Check if price touched support/resistance recently
        recent_lows = [self.data.Low[-i] for i in range(1, min(self.support_lookback + 1, len(self.data)))]
        recent_highs = [self.data.High[-i] for i in range(1, min(self.support_lookback + 1, len(self.data)))]

        touched_support = any(low <= support * 1.01 for low in recent_lows) if recent_lows else False
        touched_resistance = any(high >= resistance * 0.99 for high in recent_highs) if recent_highs else False

        if not self.position:
            # LONG ENTRY - RELAXED CONDITIONS
            # 1. Price near demand zone
            # 2. Price touched support recently OR RSI oversold
            # 3. Price rising OR fast MA above slow MA
            long_conditions = (
                demand_zone_lower <= current_price <= demand_zone_upper and
                (touched_support or rsi < 40) and
                (current_price > prev_price or sma_fast > sma_slow)
            )

            if long_conditions:
                # Calculate stop loss and take profit
                stop_loss = max(demand_zone_lower - (atr * 0.5), current_price * 0.95)  # Max 5% stop
                risk = current_price - stop_loss
                take_profit = current_price + (risk * self.risk_reward)

                # Enter long position
                self.buy(sl=stop_loss, tp=take_profit, size=1000000)

            # SHORT ENTRY - RELAXED CONDITIONS
            # 1. Price near supply zone
            # 2. Price touched resistance recently OR RSI overbought
            # 3. Price falling OR fast MA below slow MA
            short_conditions = (
                supply_zone_lower <= current_price <= supply_zone_upper and
                (touched_resistance or rsi > 60) and
                (current_price < prev_price or sma_fast < sma_slow)
            )

            if short_conditions:
                # Calculate stop loss and take profit
                stop_loss = min(supply_zone_upper + (atr * 0.5), current_price * 1.05)  # Max 5% stop
                risk = stop_loss - current_price
                take_profit = current_price - (risk * self.risk_reward)

                # Enter short position
                self.sell(sl=stop_loss, tp=take_profit, size=1000000)

# Run single backtest (default behavior)
bt = Backtest(data, MultiTimeframeDemandZoneRelaxed, cash=10000000, commission=0.00045)

print("\n🌙 ===== MULTI-TIMEFRAME DEMAND ZONE - RELAXED BASE VERSION ===== 🌙")
print(f"Swing Period: {SWING_PERIOD_4H}")
print(f"Zone Size: {ZONE_SIZE_PERCENT}%")
print(f"Risk:Reward Ratio: {RISK_REWARD_RATIO}:1")
print(f"Support Lookback: {SUPPORT_LOOKBACK} bars")

stats_default = bt.run()
print("\n📊 Backtest Results:")
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING MULTI-TIMEFRAME DEMAND ZONE (RELAXED BASE) ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(MultiTimeframeDemandZoneRelaxed, 'MTF_DemandZone_Relaxed')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/MTF_DemandZone_Relaxed.csv")