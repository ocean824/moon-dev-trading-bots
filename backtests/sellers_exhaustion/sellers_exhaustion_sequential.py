import pandas as pd
import numpy as np
import talib
from backtesting import Strategy

print("🚀 Moon Dev's Sequential Decline Detection Loading... 🌙")

class SequentialDeclineExhaustion(Strategy):
    # Parameters
    take_profit = 0.03
    stop_loss = 0.02
    min_consecutive = 4  # Minimum consecutive down closes
    max_consecutive = 9  # Maximum before expecting reversal
    volume_spike_multiplier = 2.0
    
    def init(self):
        # Count consecutive down closes
        def count_consecutive_declines(close):
            consecutive = np.zeros(len(close))
            count = 0
            
            for i in range(1, len(close)):
                if close[i] < close[i-1]:
                    count += 1
                else:
                    count = 0
                consecutive[i] = count
            
            return consecutive
        
        self.consecutive_down = self.I(count_consecutive_declines, self.data.Close)
        
        # Volume analysis
        self.volume_ma = self.I(talib.SMA, self.data.Volume, timeperiod=20)
        
        # RSI for oversold confirmation
        self.rsi = self.I(talib.RSI, self.data.Close, timeperiod=14)
        
        # Detect exhaustion after sequential declines
        def detect_sequential_exhaustion(consecutive, volume, volume_ma, close, low):
            signal = np.zeros(len(consecutive))
            
            for i in range(1, len(consecutive)):
                # Check for sufficient consecutive declines
                if self.min_consecutive <= consecutive[i] <= self.max_consecutive:
                    # Volume spike on potential reversal
                    volume_spike = volume[i] > volume_ma[i] * self.volume_spike_multiplier
                    
                    # Price shows signs of reversal (hammer, doji, or bullish engulfing)
                    candle_range = close[i] - low[i]
                    prev_range = abs(close[i-1] - close[i])
                    
                    # Reversal candle patterns
                    reversal_sign = (candle_range > prev_range * 0.5) or (close[i] > close[i-1])
                    
                    if volume_spike and reversal_sign:
                        signal[i] = 1.0
            
            return signal
        
        self.exhaustion_signal = self.I(detect_sequential_exhaustion,
                                       self.consecutive_down,
                                       self.data.Volume,
                                       self.volume_ma,
                                       self.data.Close,
                                       self.data.Low)
        
        # Track entry price for exits
        self.entry_price = None
    
    def next(self):
        # Skip if we don't have enough data
        if len(self.data) < 30:
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
            # Entry logic - Sequential decline exhaustion
            if self.exhaustion_signal[-1] > 0:
                # Additional confirmation: RSI oversold
                if self.rsi[-1] < 35:
                    # Near recent lows
                    recent_low = min(self.data.Low[-20:])
                    if self.data.Low[-1] <= recent_low * 1.01:
                        self.buy()
                        self.entry_price = self.data.Close[-1]

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING SEQUENTIAL DECLINE EXHAUSTION ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    results = test_on_all_data(SequentialDeclineExhaustion, 'SequentialDeclineExhaustion')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/SequentialDeclineExhaustion.csv")