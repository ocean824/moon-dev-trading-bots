import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy

print("🚀 Moon Dev's Volatility Breakout with Kalman Filter Strategy Loading... 🌙")

# Load the data
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
ATR_PERIOD = 14                # ATR calculation period
ATR_MULTIPLIER_HIGH = 1.8      # ATR multiplier for high breakout
ATR_MULTIPLIER_LOW = 1.8       # ATR multiplier for low breakout  
LOOKBACK_PERIOD = 20           # Period for recent highs/lows
STOP_LOSS_ATR_FRACTION = 0.8   # Stop loss as fraction of ATR
TAKE_PROFIT_ATR_MULTIPLE = 2.5 # Take profit as multiple of ATR
KALMAN_Q = 0.01                # Process noise for Kalman filter
KALMAN_R = 0.1                 # Measurement noise for Kalman filter
DIVERGENCE_THRESHOLD = 0.015   # 1.5% divergence from Kalman for signal

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class VolatilityBreakoutKalman(Strategy):
    # Strategy parameters
    atr_period = ATR_PERIOD
    atr_multiplier_high = ATR_MULTIPLIER_HIGH
    atr_multiplier_low = ATR_MULTIPLIER_LOW
    lookback_period = LOOKBACK_PERIOD
    stop_loss_atr_fraction = STOP_LOSS_ATR_FRACTION
    take_profit_atr_multiple = TAKE_PROFIT_ATR_MULTIPLE
    kalman_q = KALMAN_Q
    kalman_r = KALMAN_R
    divergence_threshold = DIVERGENCE_THRESHOLD
    
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
        # Calculate ATR for volatility measurement
        self.atr = self.I(talib.ATR, self.data.High, self.data.Low, self.data.Close, self.atr_period)
        
        # Apply Kalman filter to smooth prices
        close_prices = self.data.Close
        self.kalman_price = self.I(lambda x=close_prices: self.kalman_filter_1d(x, self.kalman_q, self.kalman_r), close_prices)
        
        # Calculate recent highs and lows on Kalman-filtered prices
        self.recent_high = self.I(talib.MAX, self.kalman_price, self.lookback_period)
        self.recent_low = self.I(talib.MIN, self.kalman_price, self.lookback_period)
        
        # Volume for confirmation
        self.volume_sma = self.I(talib.SMA, self.data.Volume, 20)
        
        # Track breakout levels
        self.breakout_high_level = None
        self.breakout_low_level = None
        self.bars_since_adjustment = 0
        
    def next(self):
        # Skip if not enough data
        if len(self.data) < max(self.atr_period, self.lookback_period):
            return
            
        current_price = self.data.Close[-1]
        current_high = self.data.High[-1]
        current_low = self.data.Low[-1]
        current_atr = self.atr[-1]
        kalman_estimate = self.kalman_price[-1]
        current_volume = self.data.Volume[-1]
        avg_volume = self.volume_sma[-1]
        
        # Skip if invalid values
        if pd.isna(current_atr) or current_atr == 0:
            return
        if pd.isna(kalman_estimate):
            return
        if pd.isna(avg_volume) or avg_volume == 0:
            avg_volume = 1  # Prevent division by zero
            
        # Calculate divergence from Kalman estimate
        price_divergence = (current_price - kalman_estimate) / kalman_estimate if kalman_estimate != 0 else 0
        
        # Update bars since last adjustment
        self.bars_since_adjustment += 1
        
        # Regularly adjust breakout levels based on Kalman-filtered highs/lows
        if self.bars_since_adjustment >= 10 or self.breakout_high_level is None:
            recent_high = self.recent_high[-1]
            recent_low = self.recent_low[-1]
            
            if not pd.isna(recent_high) and not pd.isna(recent_low):
                # Use Kalman-filtered levels for cleaner breakout signals
                self.breakout_high_level = recent_high + (current_atr * self.atr_multiplier_high)
                self.breakout_low_level = recent_low - (current_atr * self.atr_multiplier_low)
                self.bars_since_adjustment = 0
        
        # Skip if breakout levels not set
        if self.breakout_high_level is None or self.breakout_low_level is None:
            return
            
        # Check for breakout conditions with Kalman confirmation
        # Real price must breakout AND diverge significantly from Kalman estimate
        high_breakout = (current_high > self.breakout_high_level and 
                        price_divergence > self.divergence_threshold)
        low_breakout = (current_low < self.breakout_low_level and 
                       price_divergence < -self.divergence_threshold)
        
        # Volume confirmation
        volume_confirmation = current_volume > avg_volume * 1.2
        
        # Entry logic
        if not self.position:
            # Long entry: price exceeds high + ATR multiple with Kalman divergence
            if high_breakout and volume_confirmation:
                stop_loss_price = current_price - (current_atr * self.stop_loss_atr_fraction)
                take_profit_price = current_price + (current_atr * self.take_profit_atr_multiple)
                
                self.buy(
                    sl=stop_loss_price,
                    tp=take_profit_price
                )
                
                # Reset breakout levels after entry
                self.bars_since_adjustment = 10
                    
            # Short entry: price falls below low - ATR multiple with Kalman divergence
            elif low_breakout and volume_confirmation:
                stop_loss_price = current_price + (current_atr * self.stop_loss_atr_fraction)
                take_profit_price = current_price - (current_atr * self.take_profit_atr_multiple)
                
                self.sell(
                    sl=stop_loss_price,
                    tp=take_profit_price
                )
                
                # Reset breakout levels after entry
                self.bars_since_adjustment = 10

# Run single backtest
bt = Backtest(data, VolatilityBreakoutKalman, cash=10000000, commission=0.00045)

print("\n🌙 ===== VOLATILITY BREAKOUT KALMAN - DEFAULT PARAMETERS ===== 🌙")
print(f"ATR Period: {ATR_PERIOD}")
print(f"ATR Multiplier (High): {ATR_MULTIPLIER_HIGH}")
print(f"ATR Multiplier (Low): {ATR_MULTIPLIER_LOW}")
print(f"Lookback Period: {LOOKBACK_PERIOD}")
print(f"Kalman Q (Process Noise): {KALMAN_Q}")
print(f"Kalman R (Measurement Noise): {KALMAN_R}")
print(f"Divergence Threshold: {DIVERGENCE_THRESHOLD * 100:.1f}%")
print(f"Stop Loss ATR Fraction: {STOP_LOSS_ATR_FRACTION}")
print(f"Take Profit ATR Multiple: {TAKE_PROFIT_ATR_MULTIPLE}")

stats_default = bt.run()
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING VOLATILITY BREAKOUT KALMAN ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    # Test this strategy on all configured data sources
    results = test_on_all_data(VolatilityBreakoutKalman, 'VolatilityBreakoutKalman')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/VolatilityBreakoutKalman_[timestamp].csv")