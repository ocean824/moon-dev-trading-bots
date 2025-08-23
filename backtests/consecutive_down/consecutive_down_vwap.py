import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy

print("🚀 Moon Dev's Consecutive Down + VWAP Strategy (Long Only) Loading... 🌙")

class ConsecutiveDownVWAPStrategy(Strategy):
    consecutive_bars = 4
    take_profit = 0.03  # 3%
    stop_loss = 0.02    # 2%
    vwap_period = 20
    
    def init(self):
        close_values = pd.Series(self.data.Close)
        
        def count_consecutive_down():
            consecutive = np.zeros(len(close_values))
            count = 0
            for i in range(1, len(close_values)):
                if close_values.iloc[i] < close_values.iloc[i-1]:
                    count += 1
                else:
                    count = 0
                consecutive[i] = count
            return consecutive
        
        self.consecutive_down = self.I(count_consecutive_down)
        
        # Calculate VWAP
        def calculate_vwap():
            typical_price = (self.data.High + self.data.Low + self.data.Close) / 3
            vwap_values = np.zeros(len(self.data))
            
            for i in range(self.vwap_period, len(self.data)):
                volume_slice = self.data.Volume[i-self.vwap_period+1:i+1]
                tp_slice = typical_price[i-self.vwap_period+1:i+1]
                
                if volume_slice.sum() > 0:
                    vwap_values[i] = (tp_slice * volume_slice).sum() / volume_slice.sum()
                else:
                    vwap_values[i] = typical_price[i]
            
            return vwap_values
        
        self.vwap = self.I(calculate_vwap)
        
        # RSI for additional confirmation
        self.rsi = self.I(talib.RSI, self.data.Close, 14)
        
        # Volume analysis
        self.volume_ma = self.I(talib.SMA, self.data.Volume, 20)
    
    def next(self):
        if len(self.data) < max(self.consecutive_bars + 1, self.vwap_period, 20):
            return
        
        if pd.isna(self.vwap[-1]) or pd.isna(self.rsi[-1]) or self.vwap[-1] == 0:
            return
        
        if not self.position:
            # Check for consecutive down bars
            consecutive_signal = self.consecutive_down[-1] >= self.consecutive_bars
            
            # Price below VWAP (oversold relative to volume-weighted average)
            vwap_signal = self.data.Close[-1] < self.vwap[-1] * 0.98
            
            # RSI oversold for additional confirmation
            rsi_signal = self.rsi[-1] < 35
            
            # Volume above average (capitulation volume)
            volume_signal = self.data.Volume[-1] > self.volume_ma[-1] * 1.1
            
            if consecutive_signal and vwap_signal and (rsi_signal or volume_signal):
                current_price = self.data.Close[-1]
                sl_price = current_price * (1 - self.stop_loss)
                tp_price = current_price * (1 + self.take_profit)
                self.buy(sl=sl_price, tp=tp_price)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING CONSECUTIVE DOWN + VWAP STRATEGY ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    # Test this strategy on all configured data sources
    results = test_on_all_data(ConsecutiveDownVWAPStrategy, 'ConsecutiveDown_VWAP')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/ConsecutiveDown_VWAP_[timestamp].csv")