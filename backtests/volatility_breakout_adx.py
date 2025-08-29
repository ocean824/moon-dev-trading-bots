import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy

print("🚀 Moon Dev's Volatility Breakout with ADX Strategy Loading... 🌙")

# Load the data
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
ATR_PERIOD = 14                # ATR calculation period
ATR_MULTIPLIER_HIGH = 2.0      # ATR multiplier for high breakout
ATR_MULTIPLIER_LOW = 2.0       # ATR multiplier for low breakout  
LOOKBACK_PERIOD = 20           # Period for recent highs/lows
STOP_LOSS_ATR_FRACTION = 1.0   # Stop loss as fraction of ATR
TAKE_PROFIT_ATR_MULTIPLE = 3.0 # Take profit as multiple of ATR
ADX_PERIOD = 14                # ADX calculation period
ADX_THRESHOLD = 25             # Minimum ADX for strong trend
DI_CONFIRMATION = True         # Use +DI/-DI for directional confirmation

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class VolatilityBreakoutADX(Strategy):
    # Strategy parameters
    atr_period = ATR_PERIOD
    atr_multiplier_high = ATR_MULTIPLIER_HIGH
    atr_multiplier_low = ATR_MULTIPLIER_LOW
    lookback_period = LOOKBACK_PERIOD
    stop_loss_atr_fraction = STOP_LOSS_ATR_FRACTION
    take_profit_atr_multiple = TAKE_PROFIT_ATR_MULTIPLE
    adx_period = ADX_PERIOD
    adx_threshold = ADX_THRESHOLD
    di_confirmation = DI_CONFIRMATION
    
    def init(self):
        # Calculate ATR for volatility measurement
        self.atr = self.I(talib.ATR, self.data.High, self.data.Low, self.data.Close, self.atr_period)
        
        # Calculate ADX and directional indicators
        self.adx = self.I(talib.ADX, self.data.High, self.data.Low, self.data.Close, self.adx_period)
        self.plus_di = self.I(talib.PLUS_DI, self.data.High, self.data.Low, self.data.Close, self.adx_period)
        self.minus_di = self.I(talib.MINUS_DI, self.data.High, self.data.Low, self.data.Close, self.adx_period)
        
        # Calculate recent highs and lows
        self.recent_high = self.I(talib.MAX, self.data.High, self.lookback_period)
        self.recent_low = self.I(talib.MIN, self.data.Low, self.lookback_period)
        
        # Volume for confirmation
        self.volume_sma = self.I(talib.SMA, self.data.Volume, 20)
        
        # Track breakout levels
        self.breakout_high_level = None
        self.breakout_low_level = None
        self.bars_since_adjustment = 0
        self.breakout_confirmation_count = 0
        self.last_breakout_direction = None
        
    def next(self):
        # Skip if not enough data
        if len(self.data) < max(self.atr_period, self.lookback_period, self.adx_period):
            return
            
        current_price = self.data.Close[-1]
        current_high = self.data.High[-1]
        current_low = self.data.Low[-1]
        current_atr = self.atr[-1]
        current_adx = self.adx[-1]
        current_plus_di = self.plus_di[-1]
        current_minus_di = self.minus_di[-1]
        current_volume = self.data.Volume[-1]
        avg_volume = self.volume_sma[-1]
        
        # Skip if invalid values
        if pd.isna(current_atr) or current_atr == 0:
            return
        if pd.isna(current_adx):
            return
        if pd.isna(current_plus_di) or pd.isna(current_minus_di):
            return
        if pd.isna(avg_volume) or avg_volume == 0:
            avg_volume = 1  # Prevent division by zero
            
        # Update bars since last adjustment
        self.bars_since_adjustment += 1
        
        # Regularly adjust breakout levels based on ATR changes
        if self.bars_since_adjustment >= 10 or self.breakout_high_level is None:
            recent_high = self.recent_high[-1]
            recent_low = self.recent_low[-1]
            
            if not pd.isna(recent_high) and not pd.isna(recent_low):
                self.breakout_high_level = recent_high + (current_atr * self.atr_multiplier_high)
                self.breakout_low_level = recent_low - (current_atr * self.atr_multiplier_low)
                self.bars_since_adjustment = 0
        
        # Skip if breakout levels not set
        if self.breakout_high_level is None or self.breakout_low_level is None:
            return
            
        # Check for breakout conditions
        high_breakout = current_high > self.breakout_high_level
        low_breakout = current_low < self.breakout_low_level
        
        # ADX confirmation - only trade in strong trends
        strong_trend = current_adx > self.adx_threshold
        
        # Directional confirmation using +DI/-DI
        bullish_direction = current_plus_di > current_minus_di
        bearish_direction = current_minus_di > current_plus_di
        
        # Volume confirmation
        volume_confirmation = current_volume > avg_volume * 1.2
        
        # Entry logic
        if not self.position:
            # Long entry: price exceeds high + ATR multiple with ADX confirmation
            if high_breakout and strong_trend:
                # Additional check: +DI should be dominant for long
                if not self.di_confirmation or bullish_direction:
                    # Track confirmation
                    if self.last_breakout_direction == 'long':
                        self.breakout_confirmation_count += 1
                    else:
                        self.breakout_confirmation_count = 1
                        self.last_breakout_direction = 'long'
                    
                    # Enter if confirmed or strong volume
                    if self.breakout_confirmation_count >= 2 or volume_confirmation:
                        stop_loss_price = current_price - (current_atr * self.stop_loss_atr_fraction)
                        take_profit_price = current_price + (current_atr * self.take_profit_atr_multiple)
                        
                        self.buy(
                            sl=stop_loss_price,
                            tp=take_profit_price
                        )
                        
                        # Reset breakout levels after entry
                        self.bars_since_adjustment = 10
                        self.breakout_confirmation_count = 0
                    
            # Short entry: price falls below low - ATR multiple with ADX confirmation
            elif low_breakout and strong_trend:
                # Additional check: -DI should be dominant for short
                if not self.di_confirmation or bearish_direction:
                    # Track confirmation
                    if self.last_breakout_direction == 'short':
                        self.breakout_confirmation_count += 1
                    else:
                        self.breakout_confirmation_count = 1
                        self.last_breakout_direction = 'short'
                    
                    # Enter if confirmed or strong volume
                    if self.breakout_confirmation_count >= 2 or volume_confirmation:
                        stop_loss_price = current_price + (current_atr * self.stop_loss_atr_fraction)
                        take_profit_price = current_price - (current_atr * self.take_profit_atr_multiple)
                        
                        self.sell(
                            sl=stop_loss_price,
                            tp=take_profit_price
                        )
                        
                        # Reset breakout levels after entry
                        self.bars_since_adjustment = 10
                        self.breakout_confirmation_count = 0
            else:
                # No breakout or weak trend, reset confirmation
                if not high_breakout and not low_breakout:
                    self.breakout_confirmation_count = 0

# Run single backtest
bt = Backtest(data, VolatilityBreakoutADX, cash=10000000, commission=0.00045)

print("\n🌙 ===== VOLATILITY BREAKOUT ADX - DEFAULT PARAMETERS ===== 🌙")
print(f"ATR Period: {ATR_PERIOD}")
print(f"ATR Multiplier (High): {ATR_MULTIPLIER_HIGH}")
print(f"ATR Multiplier (Low): {ATR_MULTIPLIER_LOW}")
print(f"Lookback Period: {LOOKBACK_PERIOD}")
print(f"ADX Period: {ADX_PERIOD}")
print(f"ADX Threshold: {ADX_THRESHOLD}")
print(f"DI Confirmation: {DI_CONFIRMATION}")
print(f"Stop Loss ATR Fraction: {STOP_LOSS_ATR_FRACTION}")
print(f"Take Profit ATR Multiple: {TAKE_PROFIT_ATR_MULTIPLE}")

stats_default = bt.run()
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING VOLATILITY BREAKOUT ADX ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    # Test this strategy on all configured data sources
    results = test_on_all_data(VolatilityBreakoutADX, 'VolatilityBreakoutADX')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/VolatilityBreakoutADX_[timestamp].csv")