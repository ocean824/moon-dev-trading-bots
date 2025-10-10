"""
Bollinger Bands + RSI + MFI Strategy
=====================================

Enhanced version of the base strategy adding Money Flow Index (MFI) for volume confirmation:
- Entry: RSI signal + BB signal + MFI confirmation
- MFI adds volume-weighted momentum analysis

MFI Parameters:
- Period: 14 (standard)
- Oversold: 20, Overbought: 80
"""

import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Bollinger + RSI + MFI Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
RSI_PERIOD = 6  # Very short RSI period (from Pine Script)
BB_PERIOD = 200  # Long-term Bollinger Bands
BB_STD = 2.0  # Standard deviations
RSI_OVERSOLD = 50  # Using 50 as both oversold/overbought
RSI_OVERBOUGHT = 50

# MFI parameters (enhancement)
MFI_PERIOD = 14
MFI_OVERSOLD = 20
MFI_OVERBOUGHT = 80

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class BollingerRSIMFI(Strategy):
    # Strategy parameters
    rsi_period = RSI_PERIOD
    bb_period = BB_PERIOD
    bb_std = BB_STD
    rsi_oversold = RSI_OVERSOLD
    rsi_overbought = RSI_OVERBOUGHT
    mfi_period = MFI_PERIOD
    mfi_oversold = MFI_OVERSOLD
    mfi_overbought = MFI_OVERBOUGHT

    def init(self):
        """Initialize indicators using talib"""
        # Calculate RSI
        self.rsi = self.I(talib.RSI, self.data.Close, self.rsi_period)

        # Calculate Bollinger Bands
        bb_result = talib.BBANDS(
            self.data.Close.s,  # Use .s to get numpy array
            timeperiod=self.bb_period,
            nbdevup=self.bb_std,
            nbdevdn=self.bb_std,
            matype=0
        )
        self.bb_upper = self.I(lambda: bb_result[0])
        self.bb_middle = self.I(lambda: bb_result[1])
        self.bb_lower = self.I(lambda: bb_result[2])

        # Calculate MFI (Money Flow Index)
        self.mfi = self.I(
            talib.MFI,
            self.data.High,
            self.data.Low,
            self.data.Close,
            self.data.Volume,
            self.mfi_period
        )

    def next(self):
        """Trading logic - combining RSI, BB, and MFI signals"""
        if len(self.data) < max(self.rsi_period, self.bb_period, self.mfi_period) + 1:
            return

        # Get current and previous values
        current_price = self.data.Close[-1]
        prev_price = self.data.Close[-2]

        current_rsi = self.rsi[-1]
        prev_rsi = self.rsi[-2]

        current_mfi = self.mfi[-1]

        current_bb_upper = self.bb_upper[-1]
        current_bb_lower = self.bb_lower[-1]
        current_bb_middle = self.bb_middle[-1]
        prev_bb_lower = self.bb_lower[-2]
        prev_bb_upper = self.bb_upper[-2]

        # Skip if we don't have valid values
        if pd.isna(current_bb_upper) or pd.isna(current_bb_lower) or pd.isna(current_rsi) or pd.isna(current_mfi):
            return

        # Base conditions - Modified for better signal generation
        # RSI crosses above 50 OR price near lower BB with RSI below 50
        rsi_cross_up = prev_rsi <= self.rsi_oversold and current_rsi > self.rsi_oversold
        price_near_lower = current_price <= current_bb_lower * 1.01  # Within 1% of lower BB
        rsi_oversold_zone = current_rsi < 45  # Slightly below 50

        # RSI crosses below 50 OR price near upper BB with RSI above 50
        rsi_cross_down = prev_rsi >= self.rsi_overbought and current_rsi < self.rsi_overbought
        price_near_upper = current_price >= current_bb_upper * 0.99  # Within 1% of upper BB
        rsi_overbought_zone = current_rsi > 55  # Slightly above 50

        # MFI confirmation conditions
        mfi_bullish = current_mfi < self.mfi_oversold + 15  # MFI in oversold zone or rising from it
        mfi_bearish = current_mfi > self.mfi_overbought - 15  # MFI in overbought zone or falling from it

        # Position management with MFI confirmation - simplified
        if not self.position:
            # LONG ENTRY: Price near lower BB AND RSI oversold AND MFI confirms
            if (current_price <= current_bb_lower * 1.02 and current_rsi <= 30 and
                current_mfi < self.mfi_oversold + 15):
                self.buy()

            # SHORT ENTRY: Price near upper BB AND RSI overbought AND MFI confirms
            elif (current_price >= current_bb_upper * 0.98 and current_rsi >= 70 and
                  current_mfi > self.mfi_overbought - 15):
                self.sell()

        else:
            # Exit conditions with MFI confirmation
            if self.position.is_long:
                # Exit long when price reaches middle band OR RSI overbought OR MFI extremely overbought
                if (current_price >= current_bb_middle or current_rsi >= 70 or
                    current_mfi > self.mfi_overbought + 5):
                    self.position.close()

            elif self.position.is_short:
                # Exit short when price reaches middle band OR RSI oversold OR MFI extremely oversold
                if (current_price <= current_bb_middle or current_rsi <= 30 or
                    current_mfi < self.mfi_oversold - 5):
                    self.position.close()


# Run single backtest (default behavior)
bt = Backtest(data, BollingerRSIMFI, cash=1000000, commission=0.00045)

print("\n🌙 ===== BOLLINGER + RSI + MFI STRATEGY ===== 🌙")
print(f"RSI Period: {RSI_PERIOD}")
print(f"Bollinger Period: {BB_PERIOD}")
print(f"Bollinger Std Dev: {BB_STD}")
print(f"MFI Period: {MFI_PERIOD}")
print(f"MFI Oversold/Overbought: {MFI_OVERSOLD}/{MFI_OVERBOUGHT}")

stats = bt.run()
print(stats)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING BOLLINGER + RSI + MFI ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(BollingerRSIMFI, 'BollingerRSIMFI')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/BollingerRSIMFI.csv")