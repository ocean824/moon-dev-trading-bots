import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy

print("🚀 Moon Dev's False Breakout with MFI Strategy Loading... 🌙")

# Load the data
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
LOOKBACK_PERIOD = 20           # Period to identify support/resistance
BREAKOUT_THRESHOLD = 0.0025    # 0.25% beyond support/resistance for breakout
REVERSAL_THRESHOLD = 0.0015    # 0.15% back inside range for reversal confirmation
MFI_PERIOD = 14                # Money Flow Index period
MFI_DIVERGENCE_THRESHOLD = 15  # MFI must diverge by 15 points
MFI_OVERBOUGHT = 75            # MFI overbought level for false breakout
MFI_OVERSOLD = 25              # MFI oversold level for false breakout
VOLUME_THRESHOLD = 1.35        # Volume must be 1.35x average for valid signal
WICK_RATIO = 0.55              # Wick must be 55% of candle range for reversal
ATR_PERIOD = 14                # ATR for stop loss calculation
STOP_LOSS_ATR = 0.55           # Stop loss as ATR multiple
TARGET_RANGE_PCT = 0.5         # Target 50% of range
MAX_BARS_TO_REVERSAL = 4       # Max bars for reversal to occur

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class FalseBreakoutMFI(Strategy):
    # Strategy parameters
    lookback_period = LOOKBACK_PERIOD
    breakout_threshold = BREAKOUT_THRESHOLD
    reversal_threshold = REVERSAL_THRESHOLD
    mfi_period = MFI_PERIOD
    mfi_divergence_threshold = MFI_DIVERGENCE_THRESHOLD
    mfi_overbought = MFI_OVERBOUGHT
    mfi_oversold = MFI_OVERSOLD
    volume_threshold = VOLUME_THRESHOLD
    wick_ratio = WICK_RATIO
    atr_period = ATR_PERIOD
    stop_loss_atr = STOP_LOSS_ATR
    target_range_pct = TARGET_RANGE_PCT
    max_bars_to_reversal = MAX_BARS_TO_REVERSAL
    
    def init(self):
        # Support and resistance levels
        self.resistance = self.I(talib.MAX, self.data.High, self.lookback_period)
        self.support = self.I(talib.MIN, self.data.Low, self.lookback_period)
        
        # Money Flow Index
        self.mfi = self.I(talib.MFI, self.data.High, self.data.Low, self.data.Close, 
                          self.data.Volume, self.mfi_period)
        
        # Volume analysis
        self.volume_sma = self.I(talib.SMA, self.data.Volume, 20)
        
        # ATR for volatility-based stops
        self.atr = self.I(talib.ATR, self.data.High, self.data.Low, self.data.Close, self.atr_period)
        
        # Track potential false breakouts
        self.potential_false_breakout = None
        self.breakout_bar = None
        self.breakout_level = None
        self.breakout_direction = None
        self.mfi_at_breakout = None
        self.price_at_breakout = None
        
    def calculate_wick_ratio(self, open_price, high, low, close):
        """Calculate the wick ratio for reversal confirmation"""
        candle_range = high - low
        if candle_range == 0:
            return 0
            
        # For bullish reversal (false downside breakout)
        if close > open_price:
            lower_wick = min(open_price, close) - low
            return lower_wick / candle_range
        # For bearish reversal (false upside breakout)
        else:
            upper_wick = high - max(open_price, close)
            return upper_wick / candle_range
    
    def next(self):
        # Skip if not enough data
        if len(self.data) < max(self.lookback_period, self.atr_period, self.mfi_period):
            return
            
        current_bar = len(self.data) - 1
        current_price = self.data.Close[-1]
        current_high = self.data.High[-1]
        current_low = self.data.Low[-1]
        current_open = self.data.Open[-1]
        current_volume = self.data.Volume[-1]
        current_atr = self.atr[-1]
        current_mfi = self.mfi[-1]
        avg_volume = self.volume_sma[-1]
        
        # Get support and resistance levels (from previous bar to avoid look-ahead)
        resistance_level = self.resistance[-2] if len(self.resistance) > 1 else None
        support_level = self.support[-2] if len(self.support) > 1 else None
        
        # Skip if invalid values
        if pd.isna(current_atr) or current_atr == 0:
            return
        if pd.isna(current_mfi):
            return
        if pd.isna(avg_volume) or avg_volume == 0:
            avg_volume = 1  # Prevent division by zero
        if resistance_level is None or support_level is None:
            return
        if pd.isna(resistance_level) or pd.isna(support_level):
            return
            
        # Calculate range and breakout levels
        range_size = resistance_level - support_level
        if range_size <= 0:
            return
            
        breakout_amount = range_size * self.breakout_threshold
        reversal_amount = range_size * self.reversal_threshold
        
        # Calculate wick ratio for current candle
        wick_ratio = self.calculate_wick_ratio(current_open, current_high, current_low, current_price)
        
        # Check volume condition
        volume_spike = current_volume > avg_volume * self.volume_threshold
        
        # Track potential false breakouts
        if self.potential_false_breakout is None:
            # Detect potential false upside breakout
            # Price breaks out but MFI shows overbought or divergence
            if current_high > resistance_level + breakout_amount:
                # Check if MFI indicates false breakout (overbought or not confirming)
                if current_mfi > self.mfi_overbought or current_mfi < 50:
                    self.potential_false_breakout = 'upside'
                    self.breakout_bar = current_bar
                    self.breakout_level = resistance_level
                    self.breakout_direction = 'up'
                    self.mfi_at_breakout = current_mfi
                    self.price_at_breakout = current_high
                    
            # Detect potential false downside breakout
            # Price breaks down but MFI shows oversold or divergence
            elif current_low < support_level - breakout_amount:
                # Check if MFI indicates false breakout (oversold or not confirming)
                if current_mfi < self.mfi_oversold or current_mfi > 50:
                    self.potential_false_breakout = 'downside'
                    self.breakout_bar = current_bar
                    self.breakout_level = support_level
                    self.breakout_direction = 'down'
                    self.mfi_at_breakout = current_mfi
                    self.price_at_breakout = current_low
        
        # Check for false breakout reversal
        if self.potential_false_breakout is not None:
            bars_since_breakout = current_bar - self.breakout_bar
            
            # Reset if too many bars have passed
            if bars_since_breakout > self.max_bars_to_reversal:
                self.potential_false_breakout = None
                self.breakout_bar = None
                self.breakout_level = None
                self.breakout_direction = None
                self.mfi_at_breakout = None
                self.price_at_breakout = None
                return
            
            # Calculate MFI divergence
            mfi_divergence = abs(current_mfi - self.mfi_at_breakout)
            
            # Entry logic
            if not self.position:
                # Long entry: false downside breakout reverts above support
                if (self.potential_false_breakout == 'downside' and 
                    current_price > self.breakout_level + reversal_amount and
                    wick_ratio > self.wick_ratio):
                    
                    # MFI should show bullish divergence or recovery from oversold
                    mfi_confirms = (current_mfi > self.mfi_at_breakout + 5 or  # MFI rising
                                  current_mfi > self.mfi_oversold + 10 or     # Recovery from oversold
                                  mfi_divergence > self.mfi_divergence_threshold)  # Strong divergence
                    
                    # Enter if MFI confirms and (volume spike or rapid reversal)
                    if mfi_confirms and (volume_spike or bars_since_breakout <= 2):
                        # Calculate targets
                        stop_loss_price = current_low - (current_atr * self.stop_loss_atr)
                        
                        # Target middle of range or next resistance
                        range_middle = support_level + (range_size * self.target_range_pct)
                        take_profit_price = min(range_middle, resistance_level * 0.98)
                        
                        # Ensure profit target is reasonable
                        if (take_profit_price > current_price * 1.005 and
                            stop_loss_price < current_price):
                            self.buy(
                                sl=stop_loss_price,
                                tp=take_profit_price
                            )
                            
                            # Reset tracking
                            self.potential_false_breakout = None
                            self.breakout_bar = None
                            self.breakout_level = None
                            self.breakout_direction = None
                            self.mfi_at_breakout = None
                            self.price_at_breakout = None
                
                # Short entry: false upside breakout reverts below resistance
                elif (self.potential_false_breakout == 'upside' and 
                      current_price < self.breakout_level - reversal_amount and
                      wick_ratio > self.wick_ratio):
                    
                    # MFI should show bearish divergence or decline from overbought
                    mfi_confirms = (current_mfi < self.mfi_at_breakout - 5 or  # MFI falling
                                  current_mfi < self.mfi_overbought - 10 or    # Decline from overbought
                                  mfi_divergence > self.mfi_divergence_threshold)  # Strong divergence
                    
                    # Enter if MFI confirms and (volume spike or rapid reversal)
                    if mfi_confirms and (volume_spike or bars_since_breakout <= 2):
                        # Calculate targets
                        stop_loss_price = current_high + (current_atr * self.stop_loss_atr)
                        
                        # Target middle of range or next support
                        range_middle = resistance_level - (range_size * self.target_range_pct)
                        take_profit_price = max(range_middle, support_level * 1.02)
                        
                        # Ensure profit target is reasonable
                        if (take_profit_price < current_price * 0.995 and
                            stop_loss_price > current_price):
                            self.sell(
                                sl=stop_loss_price,
                                tp=take_profit_price
                            )
                            
                            # Reset tracking
                            self.potential_false_breakout = None
                            self.breakout_bar = None
                            self.breakout_level = None
                            self.breakout_direction = None
                            self.mfi_at_breakout = None
                            self.price_at_breakout = None

# Run single backtest
bt = Backtest(data, FalseBreakoutMFI, cash=10000000, commission=0.00045)

print("\n🌙 ===== FALSE BREAKOUT MFI - DEFAULT PARAMETERS ===== 🌙")
print(f"Lookback Period: {LOOKBACK_PERIOD}")
print(f"Breakout Threshold: {BREAKOUT_THRESHOLD * 100:.2f}%")
print(f"Reversal Threshold: {REVERSAL_THRESHOLD * 100:.2f}%")
print(f"MFI Period: {MFI_PERIOD}")
print(f"MFI Divergence Threshold: {MFI_DIVERGENCE_THRESHOLD}")
print(f"MFI Overbought: {MFI_OVERBOUGHT}")
print(f"MFI Oversold: {MFI_OVERSOLD}")
print(f"Volume Threshold: {VOLUME_THRESHOLD}x")
print(f"Wick Ratio: {WICK_RATIO * 100:.0f}%")
print(f"Stop Loss ATR: {STOP_LOSS_ATR}")
print(f"Target Range: {TARGET_RANGE_PCT * 100:.0f}%")

stats_default = bt.run()
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING FALSE BREAKOUT MFI ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    # Test this strategy on all configured data sources
    results = test_on_all_data(FalseBreakoutMFI, 'FalseBreakoutMFI')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/FalseBreakoutMFI_[timestamp].csv")