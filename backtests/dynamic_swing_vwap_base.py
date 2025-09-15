import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
from backtesting.lib import crossover

print("🚀 Moon Dev's Dynamic Swing Anchored VWAP Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters based on Pine Script
SWING_PERIOD = 50  # prd in Pine Script
BASE_APT = 20      # baseAPT - Adaptive Price Tracking
USE_ADAPT = False  # useAdapt - Adapt APT by ATR ratio
VOL_BIAS = 10.0    # volBias - Volatility Bias

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class DynamicSwingVWAPStrategy(Strategy):
    # Strategy parameters
    swing_period = SWING_PERIOD
    base_apt = BASE_APT
    use_adapt = USE_ADAPT
    vol_bias = VOL_BIAS
    atr_len = 50
    
    def init(self):
        print("🔧 Dynamic Swing VWAP Strategy Initializing... 🌙")
        
        # Initialize swing point detection
        self.swing_high = self.I(self.calculate_swing_high)
        self.swing_low = self.I(self.calculate_swing_low)
        
        # ATR for adaptation
        self.atr = self.I(talib.ATR, self.data.High, self.data.Low, self.data.Close, self.atr_len)
        self.atr_avg = self.I(talib.SMA, self.atr, self.atr_len)
        
        # Track current direction and VWAP
        self.direction = self.I(self.calculate_direction)
        self.vwap = self.I(self.calculate_dynamic_vwap)
        
        print("📈 Dynamic Swing VWAP indicators calculated! Ready to trade! 🚀")
    
    def calculate_swing_high(self):
        """Calculate swing highs - highest point in swing_period bars"""
        high_values = pd.Series(self.data.High)
        swing_highs = np.zeros(len(high_values))
        
        for i in range(self.swing_period, len(high_values) - self.swing_period):
            # Check if current high is the highest in the window
            window_start = max(0, i - self.swing_period)
            window_end = min(len(high_values), i + self.swing_period + 1)
            
            if high_values.iloc[i] == high_values.iloc[window_start:window_end].max():
                swing_highs[i] = high_values.iloc[i]
            else:
                swing_highs[i] = np.nan
        
        # Forward fill to maintain last swing high
        return pd.Series(swing_highs).fillna(method='ffill').values
    
    def calculate_swing_low(self):
        """Calculate swing lows - lowest point in swing_period bars"""
        low_values = pd.Series(self.data.Low)
        swing_lows = np.zeros(len(low_values))
        
        for i in range(self.swing_period, len(low_values) - self.swing_period):
            # Check if current low is the lowest in the window
            window_start = max(0, i - self.swing_period)
            window_end = min(len(low_values), i + self.swing_period + 1)
            
            if low_values.iloc[i] == low_values.iloc[window_start:window_end].min():
                swing_lows[i] = low_values.iloc[i]
            else:
                swing_lows[i] = np.nan
        
        # Forward fill to maintain last swing low
        return pd.Series(swing_lows).fillna(method='ffill').values
    
    def calculate_direction(self):
        """Calculate market direction based on swing points"""
        directions = np.zeros(len(self.data))
        last_swing_high_idx = -1
        last_swing_low_idx = -1
        
        swing_highs = self.swing_high.values if hasattr(self.swing_high, 'values') else self.swing_high
        swing_lows = self.swing_low.values if hasattr(self.swing_low, 'values') else self.swing_low
        
        for i in range(len(self.data)):
            # Check for new swing high
            if not np.isnan(swing_highs[i]) and swing_highs[i] != (swing_highs[i-1] if i > 0 else np.nan):
                last_swing_high_idx = i
            
            # Check for new swing low
            if not np.isnan(swing_lows[i]) and swing_lows[i] != (swing_lows[i-1] if i > 0 else np.nan):
                last_swing_low_idx = i
            
            # Determine direction: 1 if last swing was low (uptrend), -1 if last swing was high (downtrend)
            if last_swing_low_idx > last_swing_high_idx:
                directions[i] = 1
            elif last_swing_high_idx > last_swing_low_idx:
                directions[i] = -1
            else:
                directions[i] = 0
        
        return directions
    
    def calculate_apt(self, i):
        """Calculate Adaptive Price Tracking value"""
        if self.use_adapt and i >= self.atr_len:
            atr_val = self.atr.values[i] if hasattr(self.atr, 'values') else self.atr[i]
            atr_avg_val = self.atr_avg.values[i] if hasattr(self.atr_avg, 'values') else self.atr_avg[i]
            
            if atr_avg_val > 0:
                ratio = atr_val / atr_avg_val
            else:
                ratio = 1.0
            
            apt_raw = self.base_apt / (ratio ** self.vol_bias)
            apt_clamped = max(5.0, min(300.0, apt_raw))
            return round(apt_clamped)
        else:
            return self.base_apt
    
    def alpha_from_apt(self, apt):
        """Convert APT to EWMA alpha (half-life to alpha conversion)"""
        decay = np.exp(-np.log(2.0) / max(1.0, apt))
        return 1.0 - decay
    
    def calculate_dynamic_vwap(self):
        """Calculate dynamic VWAP that resets on swing point changes"""
        vwap_values = np.zeros(len(self.data))
        p = 0  # Price * Volume accumulator
        vol = 0  # Volume accumulator
        last_direction = 0
        
        directions = self.direction.values if hasattr(self.direction, 'values') else self.direction
        
        for i in range(len(self.data)):
            current_direction = directions[i]
            
            # Check for direction change (new swing point)
            if current_direction != last_direction and current_direction != 0:
                # Reset VWAP on direction change
                if current_direction > 0:
                    # New uptrend - use swing low as anchor
                    anchor_price = self.data.Low[i]
                else:
                    # New downtrend - use swing high as anchor
                    anchor_price = self.data.High[i]
                
                p = anchor_price * self.data.Volume[i]
                vol = self.data.Volume[i]
                vwap_values[i] = anchor_price
                last_direction = current_direction
            else:
                # Continue calculating VWAP with adaptive smoothing
                apt = self.calculate_apt(i)
                alpha = self.alpha_from_apt(apt)
                
                # Typical price (HLC/3)
                typical_price = (self.data.High[i] + self.data.Low[i] + self.data.Close[i]) / 3
                pxv = typical_price * self.data.Volume[i]
                
                # Update accumulators with EWMA
                p = (1.0 - alpha) * p + alpha * pxv
                vol = (1.0 - alpha) * vol + alpha * self.data.Volume[i]
                
                if vol > 0:
                    vwap_values[i] = p / vol
                else:
                    vwap_values[i] = typical_price
        
        return vwap_values
    
    def next(self):
        # Skip if not enough data
        if len(self.data) < max(self.swing_period * 2, self.atr_len):
            return
        
        current_price = self.data.Close[-1]
        current_vwap = self.vwap[-1]
        current_direction = self.direction[-1]
        
        # Skip if no valid VWAP
        if current_vwap == 0 or np.isnan(current_vwap):
            return
        
        # Entry logic based on Pine Script
        # Long when direction is up (1) and we're not already in a position
        if not self.position and current_direction > 0:
            print(f"🚀 LONG Entry! Price: ${current_price:.2f}, VWAP: ${current_vwap:.2f} 🌙")
            self.buy()
        
        # Close long when direction changes to down
        elif self.position and current_direction < 0:
            print(f"📉 Closing LONG! Price: ${current_price:.2f}, VWAP: ${current_vwap:.2f}")
            self.position.close()

# Run single backtest
bt = Backtest(data, DynamicSwingVWAPStrategy, cash=10000000, commission=0.00045)

print("\n🌙 ===== DYNAMIC SWING VWAP STRATEGY - BASE ===== 🌙")
print(f"Swing Period: {SWING_PERIOD}")
print(f"Base APT: {BASE_APT}")
print(f"Use Adaptive: {USE_ADAPT}")
print(f"Volatility Bias: {VOL_BIAS}")

stats_default = bt.run()
print(stats_default)

# Optional: Show plot (commented out for multi-data testing)
# bt.plot()

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING DYNAMIC SWING VWAP BASE STRATEGY ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    # Test this strategy on all configured data sources
    results = test_on_all_data(DynamicSwingVWAPStrategy, 'DynamicSwingVWAP_Base')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/DynamicSwingVWAP_Base.csv")