import pandas as pd
import numpy as np
import talib
from backtesting import Strategy

print("🚀 Moon Dev's Nadaraya-Watson Reversal + Kalman Filter Strategy Loading... 🌙")

class NadarayaWatsonReversalKalman(Strategy):
    # Parameters
    bandwidth = 100
    kernel_type = 'gaussian'
    
    # Kalman filter parameters
    kalman_gain = 0.05  # How much to trust new measurements vs predictions
    process_variance = 0.01  # Process noise
    measurement_variance = 0.1  # Measurement noise
    
    atr_period = 14
    atr_multiplier_stop = 2.0
    atr_multiplier_target = 3.0
    volume_confirm_period = 20
    volume_threshold = 1.2
    min_distance = 0.001
    
    def init(self):
        # Calculate ATR for stops
        self.atr = self.I(talib.ATR, self.data.High, self.data.Low, self.data.Close, timeperiod=self.atr_period)
        
        # Calculate volume MA for confirmation
        self.volume_ma = self.I(talib.SMA, self.data.Volume, timeperiod=self.volume_confirm_period)
        
        # Apply Kalman filter to prices first
        def kalman_filter(prices, gain=0.05, process_var=0.01, measure_var=0.1):
            filtered = np.zeros(len(prices))
            prices_array = np.array(prices)
            
            # Initialize
            filtered[0] = prices_array[0]
            error_estimate = 1.0
            
            for i in range(1, len(prices)):
                # Prediction step
                prediction = filtered[i-1]
                error_prediction = error_estimate + process_var
                
                # Update step
                kalman_gain = error_prediction / (error_prediction + measure_var)
                filtered[i] = prediction + kalman_gain * (prices_array[i] - prediction)
                error_estimate = (1 - kalman_gain) * error_prediction
            
            return filtered
        
        # Apply Kalman filter to close prices
        self.kalman_prices = self.I(kalman_filter, self.data.Close, 
                                   self.kalman_gain, self.process_variance, self.measurement_variance)
        
        # Calculate Nadaraya-Watson estimator on Kalman filtered prices
        def nadaraya_watson(prices, bandwidth=100, kernel='gaussian'):
            nw_line = np.zeros(len(prices))
            prices_array = np.array(prices)
            
            for i in range(len(prices)):
                if i < bandwidth:
                    nw_line[i] = prices_array[i]
                else:
                    weights = []
                    values = []
                    
                    for j in range(max(0, i - bandwidth), i + 1):
                        distance = abs(i - j)
                        
                        if kernel == 'gaussian':
                            weight = np.exp(-(distance**2) / (2 * (bandwidth/4)**2))
                        else:
                            weight = 1.0 if distance <= bandwidth else 0.0
                        
                        weights.append(weight)
                        values.append(prices_array[j])
                    
                    weights = np.array(weights)
                    values = np.array(values)
                    
                    if weights.sum() > 0:
                        nw_line[i] = (weights * values).sum() / weights.sum()
                    else:
                        nw_line[i] = prices_array[i]
            
            return nw_line
        
        # Apply NW to Kalman filtered prices for smoother signals
        self.nw_line = self.I(nadaraya_watson, self.kalman_prices, self.bandwidth, self.kernel_type)
        
        # Calculate distance from actual price to NW line (not Kalman price)
        def calc_distance(close, nw):
            return (close - nw) / nw
        
        self.distance = self.I(calc_distance, self.data.Close, self.nw_line)
        
        # Track entry details
        self.entry_price = None
        self.entry_atr = None
        self.is_long = None
    
    def next(self):
        # Skip if we don't have enough data
        if len(self.data) < self.bandwidth:
            return
        
        # Current values
        current_price = self.data.Close[-1]
        current_kalman = self.kalman_prices[-1]
        current_nw = self.nw_line[-1]
        current_distance = self.distance[-1]
        prev_distance = self.distance[-2] if len(self.distance) > 1 else 0
        current_volume = self.data.Volume[-1]
        volume_avg = self.volume_ma[-1]
        current_atr = self.atr[-1]
        
        # Check if we have a position
        if self.position:
            # Exit logic based on position type
            if self.is_long:
                # Long exit conditions
                stop_price = self.entry_price - (self.entry_atr * self.atr_multiplier_stop)
                target_price = self.entry_price + (self.entry_atr * self.atr_multiplier_target)
                
                if current_price <= stop_price:
                    self.position.close()
                    self.entry_price = None
                    self.is_long = None
                elif current_price >= target_price:
                    self.position.close()
                    self.entry_price = None
                    self.is_long = None
                # Exit if Kalman price diverges too much from NW line
                elif abs(current_kalman - current_nw) / current_nw > 0.03:
                    self.position.close()
                    self.entry_price = None
                    self.is_long = None
            
            else:  # Short position
                # Short exit conditions
                stop_price = self.entry_price + (self.entry_atr * self.atr_multiplier_stop)
                target_price = self.entry_price - (self.entry_atr * self.atr_multiplier_target)
                
                if current_price >= stop_price:
                    self.position.close()
                    self.entry_price = None
                    self.is_long = None
                elif current_price <= target_price:
                    self.position.close()
                    self.entry_price = None
                    self.is_long = None
                # Exit if Kalman price diverges too much from NW line
                elif abs(current_kalman - current_nw) / current_nw > 0.03:
                    self.position.close()
                    self.entry_price = None
                    self.is_long = None
        
        else:
            # Entry logic - Cleaner signals due to double smoothing
            volume_confirm = current_volume > (volume_avg * self.volume_threshold)
            
            # Check Kalman and actual price agreement
            kalman_actual_close = abs(current_price - current_kalman) / current_kalman < 0.005  # Within 0.5%
            
            # Long entry - Price bouncing up from NW line
            if (prev_distance < -self.min_distance and  # Was below NW line
                current_distance > prev_distance and  # Moving back up
                abs(current_distance) < self.min_distance * 2 and  # Close to NW line
                kalman_actual_close and  # Kalman and actual price agree
                volume_confirm):  # Volume confirmation
                
                self.buy()
                self.entry_price = current_price
                self.entry_atr = current_atr
                self.is_long = True
            
            # Short entry - Price bouncing down from NW line
            elif (prev_distance > self.min_distance and  # Was above NW line
                  current_distance < prev_distance and  # Moving back down
                  abs(current_distance) < self.min_distance * 2 and  # Close to NW line
                  kalman_actual_close and  # Kalman and actual price agree
                  volume_confirm):  # Volume confirmation
                
                self.sell()
                self.entry_price = current_price
                self.entry_atr = current_atr
                self.is_long = False

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING NADARAYA-WATSON REVERSAL + KALMAN FILTER STRATEGY ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    results = test_on_all_data(NadarayaWatsonReversalKalman, 'NadarayaWatsonReversalKalman')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/NadarayaWatsonReversalKalman.csv")