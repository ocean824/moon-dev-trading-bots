import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy

print("🚀 Moon Dev's False Breakout with Kalman Filter Strategy Loading... 🌙")

# Load the data
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
LOOKBACK_PERIOD = 20           # Period to identify support/resistance
BREAKOUT_THRESHOLD = 0.0025    # 0.25% beyond support/resistance for breakout
REVERSAL_THRESHOLD = 0.0015    # 0.15% back inside range for reversal confirmation
KALMAN_Q = 0.01                # Process noise for Kalman filter
KALMAN_R = 0.1                 # Measurement noise for Kalman filter
KALMAN_DIVERGENCE = 0.02       # 2% divergence from Kalman indicates false breakout
VOLUME_THRESHOLD = 1.3         # Volume must be 1.3x average for valid signal
ATR_PERIOD = 14                # ATR for stop loss calculation
STOP_LOSS_ATR = 0.6            # Stop loss as ATR multiple
TARGET_RANGE_PCT = 0.6         # Target 60% of range
MAX_BARS_TO_REVERSAL = 4       # Max bars for reversal to occur

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class FalseBreakoutKalman(Strategy):
    # Strategy parameters
    lookback_period = LOOKBACK_PERIOD
    breakout_threshold = BREAKOUT_THRESHOLD
    reversal_threshold = REVERSAL_THRESHOLD
    kalman_q = KALMAN_Q
    kalman_r = KALMAN_R
    kalman_divergence = KALMAN_DIVERGENCE
    volume_threshold = VOLUME_THRESHOLD
    atr_period = ATR_PERIOD
    stop_loss_atr = STOP_LOSS_ATR
    target_range_pct = TARGET_RANGE_PCT
    max_bars_to_reversal = MAX_BARS_TO_REVERSAL
    
    def kalman_filter_1d(self, measurements, q=0.01, r=0.1):
        """
        Simple 1D Kalman filter for price smoothing
        q: Process noise
        r: Measurement noise
        """
        n = len(measurements)
        filtered = np.zeros(n)
        
        # Initial estimates
        x_est = measurements[0] if not pd.isna(measurements[0]) else 0
        p_est = 1.0
        
        for i in range(n):
            if pd.isna(measurements[i]):
                filtered[i] = x_est
                continue
                
            # Prediction step
            x_pred = x_est
            p_pred = p_est + q
            
            # Update step
            k_gain = p_pred / (p_pred + r)
            x_est = x_pred + k_gain * (measurements[i] - x_pred)
            p_est = (1 - k_gain) * p_pred
            
            filtered[i] = x_est
        
        return filtered
    
    def init(self):
        # Support and resistance levels
        self.resistance = self.I(talib.MAX, self.data.High, self.lookback_period)
        self.support = self.I(talib.MIN, self.data.Low, self.lookback_period)
        
        # Apply Kalman filter to smooth prices and identify true trend
        close_prices = self.data.Close
        self.kalman_price = self.I(lambda x=close_prices: self.kalman_filter_1d(x, self.kalman_q, self.kalman_r), close_prices)
        
        # Volume analysis
        self.volume_sma = self.I(talib.SMA, self.data.Volume, 20)
        
        # ATR for volatility-based stops
        self.atr = self.I(talib.ATR, self.data.High, self.data.Low, self.data.Close, self.atr_period)
        
        # Track potential false breakouts
        self.potential_false_breakout = None
        self.breakout_bar = None
        self.breakout_level = None
        self.breakout_direction = None
        self.kalman_at_breakout = None
        
    def next(self):
        # Skip if not enough data
        if len(self.data) < max(self.lookback_period, self.atr_period):
            return
            
        current_bar = len(self.data) - 1
        current_price = self.data.Close[-1]
        current_high = self.data.High[-1]
        current_low = self.data.Low[-1]
        current_volume = self.data.Volume[-1]
        current_atr = self.atr[-1]
        avg_volume = self.volume_sma[-1]
        kalman_estimate = self.kalman_price[-1]
        
        # Get support and resistance levels (from previous bar to avoid look-ahead)
        resistance_level = self.resistance[-2] if len(self.resistance) > 1 else None
        support_level = self.support[-2] if len(self.support) > 1 else None
        
        # Skip if invalid values
        if pd.isna(current_atr) or current_atr == 0:
            return
        if pd.isna(kalman_estimate):
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
        
        # Calculate divergence from Kalman estimate
        price_divergence = abs(current_price - kalman_estimate) / kalman_estimate if kalman_estimate != 0 else 0
        
        # Volume condition
        volume_spike = current_volume > avg_volume * self.volume_threshold
        
        # Track potential false breakouts
        if self.potential_false_breakout is None:
            # Detect potential false upside breakout
            # Price breaks out but Kalman doesn't follow strongly
            if current_high > resistance_level + breakout_amount:
                kalman_position = (kalman_estimate - support_level) / range_size if range_size > 0 else 0.5
                # If Kalman is still in middle/lower part of range, likely false breakout
                if kalman_position < 0.7 or price_divergence > self.kalman_divergence:
                    self.potential_false_breakout = 'upside'
                    self.breakout_bar = current_bar
                    self.breakout_level = resistance_level
                    self.breakout_direction = 'up'
                    self.kalman_at_breakout = kalman_estimate
                    
            # Detect potential false downside breakout
            elif current_low < support_level - breakout_amount:
                kalman_position = (kalman_estimate - support_level) / range_size if range_size > 0 else 0.5
                # If Kalman is still in middle/upper part of range, likely false breakout
                if kalman_position > 0.3 or price_divergence > self.kalman_divergence:
                    self.potential_false_breakout = 'downside'
                    self.breakout_bar = current_bar
                    self.breakout_level = support_level
                    self.breakout_direction = 'down'
                    self.kalman_at_breakout = kalman_estimate
        
        # Check for false breakout reversal
        if self.potential_false_breakout is not None:
            bars_since_breakout = current_bar - self.breakout_bar
            
            # Reset if too many bars have passed
            if bars_since_breakout > self.max_bars_to_reversal:
                self.potential_false_breakout = None
                self.breakout_bar = None
                self.breakout_level = None
                self.breakout_direction = None
                self.kalman_at_breakout = None
                return
            
            # Entry logic
            if not self.position:
                # Long entry: false downside breakout reverts above support
                if (self.potential_false_breakout == 'downside' and 
                    current_price > self.breakout_level + reversal_amount):
                    
                    # Kalman should confirm reversal direction
                    kalman_confirms = kalman_estimate > self.kalman_at_breakout
                    
                    # Enter if Kalman confirms and volume spike or rapid reversal
                    if kalman_confirms and (volume_spike or bars_since_breakout <= 2):
                        # Calculate targets
                        stop_loss_price = current_low - (current_atr * self.stop_loss_atr)
                        
                        # Target middle-upper part of range
                        range_middle = support_level + (range_size * self.target_range_pct)
                        take_profit_price = min(range_middle, resistance_level * 0.97)
                        
                        # Ensure profit target is reasonable
                        if (take_profit_price > current_price * 1.004 and
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
                            self.kalman_at_breakout = None
                
                # Short entry: false upside breakout reverts below resistance
                elif (self.potential_false_breakout == 'upside' and 
                      current_price < self.breakout_level - reversal_amount):
                    
                    # Kalman should confirm reversal direction
                    kalman_confirms = kalman_estimate < self.kalman_at_breakout
                    
                    # Enter if Kalman confirms and volume spike or rapid reversal
                    if kalman_confirms and (volume_spike or bars_since_breakout <= 2):
                        # Calculate targets
                        stop_loss_price = current_high + (current_atr * self.stop_loss_atr)
                        
                        # Target middle-lower part of range
                        range_target = resistance_level - (range_size * self.target_range_pct)
                        take_profit_price = max(range_target, support_level * 1.03)
                        
                        # Ensure profit target is reasonable
                        if (take_profit_price < current_price * 0.996 and
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
                            self.kalman_at_breakout = None

# Run single backtest
bt = Backtest(data, FalseBreakoutKalman, cash=10000000, commission=0.00045)

print("\n🌙 ===== FALSE BREAKOUT KALMAN - DEFAULT PARAMETERS ===== 🌙")
print(f"Lookback Period: {LOOKBACK_PERIOD}")
print(f"Breakout Threshold: {BREAKOUT_THRESHOLD * 100:.2f}%")
print(f"Reversal Threshold: {REVERSAL_THRESHOLD * 100:.2f}%")
print(f"Kalman Q (Process Noise): {KALMAN_Q}")
print(f"Kalman R (Measurement Noise): {KALMAN_R}")
print(f"Kalman Divergence: {KALMAN_DIVERGENCE * 100:.1f}%")
print(f"Volume Threshold: {VOLUME_THRESHOLD}x")
print(f"Stop Loss ATR: {STOP_LOSS_ATR}")
print(f"Target Range: {TARGET_RANGE_PCT * 100:.0f}%")

stats_default = bt.run()
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING FALSE BREAKOUT KALMAN ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    # Test this strategy on all configured data sources
    results = test_on_all_data(FalseBreakoutKalman, 'FalseBreakoutKalman')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/FalseBreakoutKalman_[timestamp].csv")