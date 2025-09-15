import pandas as pd
import numpy as np
import talib
from backtesting import Strategy

print("🚀 Moon Dev's Nadaraya-Watson Envelope + Kalman Filter Strategy Loading... 🌙")

class NadarayaWatsonEnvelopeKalman(Strategy):
    # Parameters
    bandwidth = 100
    kernel_type = 'gaussian'
    
    # Kalman filter parameters
    kalman_gain = 0.05
    process_variance = 0.01
    measurement_variance = 0.1
    
    atr_period = 14
    band_multiplier = 2.0
    exit_at_middle = True
    volume_confirm_period = 20
    volume_threshold = 1.1
    
    def init(self):
        # Calculate ATR for band width
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
        
        # Apply NW to Kalman filtered prices
        self.nw_line = self.I(nadaraya_watson, self.kalman_prices, self.bandwidth, self.kernel_type)
        
        # Calculate envelope bands using ATR (tighter bands due to cleaner signal)
        def calc_upper_band(nw, atr, multiplier):
            return nw + (atr * multiplier * 0.9)  # Slightly tighter due to Kalman smoothing
        
        def calc_lower_band(nw, atr, multiplier):
            return nw - (atr * multiplier * 0.9)  # Slightly tighter due to Kalman smoothing
        
        self.upper_band = self.I(calc_upper_band, self.nw_line, self.atr, self.band_multiplier)
        self.lower_band = self.I(calc_lower_band, self.nw_line, self.atr, self.band_multiplier)
        
        # Track entry details
        self.entry_price = None
        self.is_long = None
    
    def next(self):
        # Skip if we don't have enough data
        if len(self.data) < self.bandwidth:
            return
        
        # Current values
        current_price = self.data.Close[-1]
        current_high = self.data.High[-1]
        current_low = self.data.Low[-1]
        current_kalman = self.kalman_prices[-1]
        current_nw = self.nw_line[-1]
        current_upper = self.upper_band[-1]
        current_lower = self.lower_band[-1]
        current_volume = self.data.Volume[-1]
        volume_avg = self.volume_ma[-1]
        
        # Check if we have a position
        if self.position:
            # Exit logic based on position type
            if self.is_long:
                # Long exit conditions
                if self.exit_at_middle:
                    # Exit at middle line or upper band
                    if current_kalman >= current_nw:  # Use Kalman price for cleaner exit
                        self.position.close()
                        self.entry_price = None
                        self.is_long = None
                else:
                    # Exit only at upper band
                    if current_price >= current_upper:
                        self.position.close()
                        self.entry_price = None
                        self.is_long = None
                
                # Stop loss if price goes below lower band
                if current_price < current_lower * 0.98:
                    self.position.close()
                    self.entry_price = None
                    self.is_long = None
            
            else:  # Short position
                # Short exit conditions
                if self.exit_at_middle:
                    # Exit at middle line or lower band
                    if current_kalman <= current_nw:  # Use Kalman price for cleaner exit
                        self.position.close()
                        self.entry_price = None
                        self.is_long = None
                else:
                    # Exit only at lower band
                    if current_price <= current_lower:
                        self.position.close()
                        self.entry_price = None
                        self.is_long = None
                
                # Stop loss if price goes above upper band
                if current_price > current_upper * 1.02:
                    self.position.close()
                    self.entry_price = None
                    self.is_long = None
        
        else:
            # Entry logic - Cleaner band touches due to double filtering
            volume_confirm = current_volume > (volume_avg * self.volume_threshold)
            
            # Check if Kalman price confirms the band touch
            kalman_near_lower = abs(current_kalman - current_lower) / current_lower < 0.005  # Within 0.5%
            kalman_near_upper = abs(current_kalman - current_upper) / current_upper < 0.005  # Within 0.5%
            
            # Long entry - Price touches lower band with Kalman confirmation
            if (current_low <= current_lower and  # Low touched lower band
                current_price > current_lower and  # Closing above it
                kalman_near_lower and  # Kalman confirms we're at lower band
                volume_confirm):  # Volume confirmation
                
                self.buy()
                self.entry_price = current_price
                self.is_long = True
            
            # Short entry - Price touches upper band with Kalman confirmation
            elif (current_high >= current_upper and  # High touched upper band
                  current_price < current_upper and  # Closing below it
                  kalman_near_upper and  # Kalman confirms we're at upper band
                  volume_confirm):  # Volume confirmation
                
                self.sell()
                self.entry_price = current_price
                self.is_long = False

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING NADARAYA-WATSON ENVELOPE + KALMAN FILTER STRATEGY ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    results = test_on_all_data(NadarayaWatsonEnvelopeKalman, 'NadarayaWatsonEnvelopeKalman')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/NadarayaWatsonEnvelopeKalman.csv")