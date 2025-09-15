import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
from backtesting.lib import crossover

print("🚀 Moon Dev's Dynamic Swing VWAP + ADX Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
SWING_PERIOD = 50  # prd in Pine Script
BASE_APT = 20      # baseAPT - Adaptive Price Tracking
USE_ADAPT = False  # useAdapt - Adapt APT by ATR ratio
VOL_BIAS = 10.0    # volBias - Volatility Bias

# ADX parameters
ADX_PERIOD = 14
ADX_THRESHOLD = 25  # Minimum ADX for trend strength
DI_DIFF_THRESHOLD = 5  # Minimum difference between +DI and -DI

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class DynamicSwingVWAPADXStrategy(Strategy):
    # Strategy parameters
    swing_period = SWING_PERIOD
    base_apt = BASE_APT
    use_adapt = USE_ADAPT
    vol_bias = VOL_BIAS
    atr_len = 50
    
    # ADX parameters
    adx_period = ADX_PERIOD
    adx_threshold = ADX_THRESHOLD
    di_diff_threshold = DI_DIFF_THRESHOLD
    
    # Risk management
    stop_loss = 0.02  # 2%
    take_profit = 0.03  # 3%
    
    def init(self):
        print("🔧 Dynamic Swing VWAP + ADX Strategy Initializing... 🌙")
        
        # Initialize swing point detection
        self.swing_high = self.I(self.calculate_swing_high)
        self.swing_low = self.I(self.calculate_swing_low)
        
        # ATR for adaptation
        self.atr = self.I(talib.ATR, self.data.High, self.data.Low, self.data.Close, self.atr_len)
        self.atr_avg = self.I(talib.SMA, self.atr, self.atr_len)
        
        # Track current direction and VWAP
        self.direction = self.I(self.calculate_direction)
        self.vwap = self.I(self.calculate_dynamic_vwap)
        
        # ADX indicators
        self.adx = self.I(talib.ADX, self.data.High, self.data.Low, self.data.Close, self.adx_period)
        self.plus_di = self.I(talib.PLUS_DI, self.data.High, self.data.Low, self.data.Close, self.adx_period)
        self.minus_di = self.I(talib.MINUS_DI, self.data.High, self.data.Low, self.data.Close, self.adx_period)
        
        print("📈 Dynamic Swing VWAP + ADX indicators calculated! Ready to trade! 🚀")
    
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
        if len(self.data) < max(self.swing_period * 2, self.atr_len, self.adx_period):
            return
        
        current_price = self.data.Close[-1]
        current_vwap = self.vwap[-1]
        current_direction = self.direction[-1]
        current_adx = self.adx[-1]
        current_plus_di = self.plus_di[-1]
        current_minus_di = self.minus_di[-1]
        
        # Skip if no valid VWAP or indicators
        if current_vwap == 0 or np.isnan(current_vwap) or np.isnan(current_adx):
            return
        
        # Enhanced entry logic with ADX confirmation
        # Long conditions:
        # 1. Swing direction is up
        # 2. ADX shows strong trend (above threshold)
        # 3. +DI > -DI with sufficient difference (bullish momentum)
        # 4. Price is above VWAP (additional confirmation)
        if (not self.position and 
            current_direction > 0 and
            current_adx > self.adx_threshold and
            current_plus_di > current_minus_di + self.di_diff_threshold and
            current_price > current_vwap):
            
            print(f"🚀 ADX-Confirmed LONG Entry! Price: ${current_price:.2f}, VWAP: ${current_vwap:.2f}, ADX: {current_adx:.2f} 🌙")
            
            # Calculate stop loss and take profit levels
            sl_price = current_price * (1 - self.stop_loss)
            tp_price = current_price * (1 + self.take_profit)
            
            self.buy(sl=sl_price, tp=tp_price)
        
        # Close conditions with ADX:
        # 1. Direction changes to down
        # 2. OR ADX drops below threshold (trend weakening)
        # 3. OR -DI crosses above +DI (bearish momentum shift)
        elif self.position and (
            current_direction < 0 or
            current_adx < self.adx_threshold * 0.8 or  # 20% buffer for exit
            current_minus_di > current_plus_di):
            
            print(f"📉 ADX Exit Signal! Price: ${current_price:.2f}, ADX: {current_adx:.2f}")
            self.position.close()

# Run single backtest
bt = Backtest(data, DynamicSwingVWAPADXStrategy, cash=10000000, commission=0.00045)

print("\n🌙 ===== DYNAMIC SWING VWAP + ADX STRATEGY ===== 🌙")
print(f"Swing Period: {SWING_PERIOD}")
print(f"Base APT: {BASE_APT}")
print(f"ADX Period: {ADX_PERIOD}")
print(f"ADX Threshold: {ADX_THRESHOLD}")
print(f"DI Difference Threshold: {DI_DIFF_THRESHOLD}")

stats_default = bt.run()
print(stats_default)

# Optional: Show plot (commented out for multi-data testing)
# bt.plot()

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING DYNAMIC SWING VWAP + ADX STRATEGY ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    # Test this strategy on all configured data sources
    results = test_on_all_data(DynamicSwingVWAPADXStrategy, 'DynamicSwingVWAP_ADX')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/DynamicSwingVWAP_ADX.csv")