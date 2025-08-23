import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy

print("🚀 Moon Dev's Consecutive Down + MFI Strategy (Long Only) Loading... 🌙")

class ConsecutiveDownMFIStrategy(Strategy):
    consecutive_bars = 4
    take_profit = 0.03  # 3%
    stop_loss = 0.02    # 2%
    mfi_period = 14
    mfi_oversold = 30
    
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
        
        # MFI (Money Flow Index)
        self.mfi = self.I(talib.MFI,
                          self.data.High,
                          self.data.Low,
                          self.data.Close,
                          self.data.Volume,
                          self.mfi_period)
        
        # Volume analysis
        self.volume_ma = self.I(talib.SMA, self.data.Volume, 20)
        self.volume_ratio = self.I(lambda: self.data.Volume / self.volume_ma)
    
    def next(self):
        if len(self.data) < max(self.consecutive_bars + 1, self.mfi_period, 20):
            return
        
        if pd.isna(self.mfi[-1]) or pd.isna(self.volume_ratio[-1]):
            return
        
        if not self.position:
            # Check for consecutive down bars
            consecutive_signal = self.consecutive_down[-1] >= self.consecutive_bars
            
            # MFI oversold condition
            mfi_signal = self.mfi[-1] < self.mfi_oversold
            
            # Volume confirmation (higher volume on down moves suggests capitulation)
            volume_signal = self.volume_ratio[-1] > 1.2
            
            if consecutive_signal and mfi_signal and volume_signal:
                current_price = self.data.Close[-1]
                sl_price = current_price * (1 - self.stop_loss)
                tp_price = current_price * (1 + self.take_profit)
                self.buy(sl=sl_price, tp=tp_price)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING CONSECUTIVE DOWN + MFI STRATEGY ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    # Test this strategy on all configured data sources
    results = test_on_all_data(ConsecutiveDownMFIStrategy, 'ConsecutiveDown_MFI')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/ConsecutiveDown_MFI_[timestamp].csv")