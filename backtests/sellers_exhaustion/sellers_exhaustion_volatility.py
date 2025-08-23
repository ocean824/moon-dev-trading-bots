import pandas as pd
import numpy as np
import talib
from backtesting import Strategy

print("🚀 Moon Dev's Volatility + Volume Divergence Loading... 🌙")

class VolatilityVolumeExhaustion(Strategy):
    # Parameters
    take_profit = 0.03
    stop_loss = 0.02
    atr_period = 14
    atr_spike_multiplier = 1.5
    volume_lookback = 20
    
    def init(self):
        # Calculate ATR for volatility
        self.atr = self.I(talib.ATR, self.data.High, self.data.Low, self.data.Close, timeperiod=self.atr_period)
        self.atr_ma = self.I(talib.SMA, self.atr, timeperiod=self.atr_period)
        
        # Volume analysis
        self.volume_ma = self.I(talib.SMA, self.data.Volume, timeperiod=self.volume_lookback)
        
        # Detect volatility exhaustion pattern
        def detect_volatility_exhaustion(high, low, close, open_, atr, atr_ma, volume, volume_ma):
            pattern = np.zeros(len(close))
            
            for i in range(2, len(close)):
                # Check for ATR spike on red candle
                atr_spike = atr[i-1] > atr_ma[i-1] * self.atr_spike_multiplier
                big_red = close[i-1] < open_[i-1] and (open_[i-1] - close[i-1]) > atr[i-1] * 0.5
                
                # Then ATR contraction
                atr_contracting = atr[i] < atr[i-1] * 0.9
                
                # While price tries to push lower but fails
                lower_attempt = low[i] < low[i-1]
                failed_breakdown = close[i] > low[i] + (high[i] - low[i]) * 0.4
                
                # Volume also declining
                volume_declining = volume[i] < volume_ma[i]
                
                if atr_spike and big_red and atr_contracting and lower_attempt and failed_breakdown and volume_declining:
                    pattern[i] = 1.0
            
            return pattern
        
        self.exhaustion_signal = self.I(detect_volatility_exhaustion,
                                       self.data.High,
                                       self.data.Low,
                                       self.data.Close,
                                       self.data.Open,
                                       self.atr,
                                       self.atr_ma,
                                       self.data.Volume,
                                       self.volume_ma)
        
        # Track entry price for exits
        self.entry_price = None
    
    def next(self):
        # Skip if we don't have enough data
        if len(self.data) < self.atr_period * 2:
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
            # Entry logic - Volatility exhaustion pattern
            if self.exhaustion_signal[-1] > 0:
                # Additional confirmation: price near recent lows
                recent_low = min(self.data.Low[-self.volume_lookback:])
                if self.data.Low[-1] <= recent_low * 1.02:
                    self.buy()
                    self.entry_price = self.data.Close[-1]

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING VOLATILITY + VOLUME DIVERGENCE ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    results = test_on_all_data(VolatilityVolumeExhaustion, 'VolatilityVolumeExhaustion')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/VolatilityVolumeExhaustion.csv")