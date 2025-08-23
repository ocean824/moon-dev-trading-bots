import pandas as pd
import numpy as np
import talib
from backtesting import Strategy

print("🚀 Moon Dev's OBV/Accumulation-Distribution Divergence Loading... 🌙")

class OBVDivergenceExhaustion(Strategy):
    # Parameters
    take_profit = 0.03
    stop_loss = 0.02
    lookback = 20
    divergence_threshold = 0.02  # 2% divergence required
    
    def init(self):
        # Calculate OBV
        self.obv = self.I(talib.OBV, self.data.Close, self.data.Volume)
        
        # Calculate Accumulation/Distribution
        self.ad = self.I(talib.AD, self.data.High, self.data.Low, self.data.Close, self.data.Volume)
        
        # Normalize OBV and AD for comparison
        def normalize_indicator(indicator, period):
            ma = talib.SMA(indicator, timeperiod=period)
            std = talib.STDDEV(indicator, timeperiod=period)
            # Avoid division by zero warning with proper masking
            with np.errstate(divide='ignore', invalid='ignore'):
                normalized = np.where(std > 0, (indicator - ma) / std, 0)
            return normalized
        
        self.obv_norm = self.I(normalize_indicator, self.obv, self.lookback)
        self.ad_norm = self.I(normalize_indicator, self.ad, self.lookback)
        
        # Detect divergence
        def detect_divergence(close, obv_norm, ad_norm, lookback):
            divergence = np.zeros(len(close))
            
            for i in range(lookback, len(close)):
                # Price making lower lows
                price_slope = (close[i] - close[i-lookback]) / close[i-lookback]
                
                # OBV trending higher
                obv_slope = obv_norm[i] - obv_norm[i-lookback]
                
                # AD trending higher
                ad_slope = ad_norm[i] - ad_norm[i-lookback]
                
                # Bullish divergence: price down, indicators up
                if price_slope < -self.divergence_threshold:
                    if obv_slope > 0.5 or ad_slope > 0.5:
                        divergence[i] = 1.0
            
            return divergence
        
        self.divergence_signal = self.I(detect_divergence,
                                       self.data.Close,
                                       self.obv_norm,
                                       self.ad_norm,
                                       self.lookback)
        
        # RSI for additional confirmation
        self.rsi = self.I(talib.RSI, self.data.Close, timeperiod=14)
        
        # Track entry price for exits
        self.entry_price = None
    
    def next(self):
        # Skip if we don't have enough data
        if len(self.data) < self.lookback * 2:
            return
        
        # Check if we have a position
        if self.position:
            # Exit logic
            current_price = self.data.Close[-1]
            
            # Take profit
            if current_price >= self.entry_price * (1 + self.take_profit):
                self.position.close()
                self.entry_price = None
            
            # Stop loss
            elif current_price <= self.entry_price * (1 - self.stop_loss):
                self.position.close()
                self.entry_price = None
        
        else:
            # Entry logic - OBV/AD divergence
            if self.divergence_signal[-1] > 0:
                # Additional confirmation: oversold conditions
                if self.rsi[-1] < 40:
                    # Make sure we're at a recent low
                    recent_low = min(self.data.Low[-self.lookback:])
                    if self.data.Low[-1] <= recent_low * 1.01:
                        self.buy()
                        self.entry_price = self.data.Close[-1]

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING OBV/AD DIVERGENCE EXHAUSTION ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    results = test_on_all_data(OBVDivergenceExhaustion, 'OBVDivergenceExhaustion')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/OBVDivergenceExhaustion.csv")