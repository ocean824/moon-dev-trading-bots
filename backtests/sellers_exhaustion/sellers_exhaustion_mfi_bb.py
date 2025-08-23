import pandas as pd
import numpy as np
import talib
from backtesting import Strategy

print("🚀 Moon Dev's MFI + Bollinger Bands Exhaustion Loading... 🌙")

class MFIBollingerExhaustion(Strategy):
    # Parameters
    take_profit = 0.03
    stop_loss = 0.02
    mfi_period = 14
    mfi_oversold = 25
    bb_period = 20
    bb_stddev = 2.0
    
    def init(self):
        # Calculate MFI (Money Flow Index)
        self.mfi = self.I(talib.MFI, self.data.High, self.data.Low, self.data.Close, self.data.Volume, timeperiod=self.mfi_period)
        
        # Calculate Bollinger Bands
        bb_result = talib.BBANDS(self.data.Close, timeperiod=self.bb_period, nbdevup=self.bb_stddev, nbdevdn=self.bb_stddev)
        self.bb_upper = self.I(lambda: bb_result[0])
        self.bb_middle = self.I(lambda: bb_result[1])
        self.bb_lower = self.I(lambda: bb_result[2])
        
        # Calculate %B (position within Bollinger Bands)
        def calculate_bb_percent(close, upper, lower):
            bb_range = upper - lower
            # Avoid division by zero warning with proper masking
            with np.errstate(divide='ignore', invalid='ignore'):
                percent_b = np.where(bb_range > 0, (close - lower) / bb_range, 0.5)
            return percent_b
        
        self.bb_percent = self.I(calculate_bb_percent, self.data.Close, self.bb_upper, self.bb_lower)
        
        # ADX for trend strength
        self.adx = self.I(talib.ADX, self.data.High, self.data.Low, self.data.Close, timeperiod=14)
        
        # Detect exhaustion pattern
        def detect_mfi_bb_exhaustion(mfi, bb_percent, adx, close, low, bb_lower):
            signal = np.zeros(len(mfi))
            
            for i in range(1, len(mfi)):
                # MFI oversold
                mfi_oversold_signal = mfi[i] < self.mfi_oversold
                
                # Price at or below lower Bollinger Band
                bb_oversold = bb_percent[i] < 0.1 or close[i] <= bb_lower[i]
                
                # Weak trend (exhaustion more likely)
                weak_trend = adx[i] < 25
                
                # Price attempting to reverse (not making new lows)
                reversal_attempt = low[i] >= low[i-1] * 0.995
                
                if mfi_oversold_signal and bb_oversold and (weak_trend or reversal_attempt):
                    signal[i] = 1.0
            
            return signal
        
        self.exhaustion_signal = self.I(detect_mfi_bb_exhaustion,
                                       self.mfi,
                                       self.bb_percent,
                                       self.adx,
                                       self.data.Close,
                                       self.data.Low,
                                       self.bb_lower)
        
        # Volume confirmation
        self.volume_ma = self.I(talib.SMA, self.data.Volume, timeperiod=20)
        
        # Track entry price for exits
        self.entry_price = None
    
    def next(self):
        # Skip if we don't have enough data
        if len(self.data) < self.bb_period * 2:
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
            # Entry logic - MFI + BB exhaustion
            if self.exhaustion_signal[-1] > 0:
                # Additional confirmations
                volume_increasing = self.data.Volume[-1] > self.volume_ma[-1] * 1.2
                
                # Price showing reversal signs
                bullish_candle = self.data.Close[-1] > self.data.Open[-1]
                
                if volume_increasing or bullish_candle:
                    # Double check we're at oversold levels
                    if self.mfi[-1] < 30 and self.bb_percent[-1] < 0.2:
                        self.buy()
                        self.entry_price = self.data.Close[-1]

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING MFI + BOLLINGER BANDS EXHAUSTION ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    results = test_on_all_data(MFIBollingerExhaustion, 'MFIBollingerExhaustion')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/MFIBollingerExhaustion.csv")