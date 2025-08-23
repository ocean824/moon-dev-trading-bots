import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy

print("🚀 Moon Dev's Consecutive Down + ADX Strategy (Long Only) Loading... 🌙")

class ConsecutiveDownADXStrategy(Strategy):
    consecutive_bars = 4
    take_profit = 0.03  # 3%
    stop_loss = 0.02    # 2%
    adx_period = 14
    adx_threshold = 25
    
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
        
        # ADX and DI indicators
        self.adx = self.I(talib.ADX, 
                          self.data.High, 
                          self.data.Low, 
                          self.data.Close, 
                          self.adx_period)
        
        self.plus_di = self.I(talib.PLUS_DI,
                              self.data.High,
                              self.data.Low,
                              self.data.Close,
                              self.adx_period)
        
        self.minus_di = self.I(talib.MINUS_DI,
                               self.data.High,
                               self.data.Low,
                               self.data.Close,
                               self.adx_period)
    
    def next(self):
        if len(self.data) < max(self.consecutive_bars + 1, self.adx_period):
            return
        
        if pd.isna(self.adx[-1]):
            return
        
        if not self.position:
            # Check for consecutive down bars
            consecutive_signal = self.consecutive_down[-1] >= self.consecutive_bars
            
            # ADX conditions: strong trend with bearish exhaustion turning bullish
            adx_signal = (self.adx[-1] > self.adx_threshold and 
                         self.minus_di[-1] > self.plus_di[-1] and
                         self.minus_di[-1] > 30)
            
            if consecutive_signal and adx_signal:
                current_price = self.data.Close[-1]
                sl_price = current_price * (1 - self.stop_loss)
                tp_price = current_price * (1 + self.take_profit)
                self.buy(sl=sl_price, tp=tp_price)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING CONSECUTIVE DOWN + ADX STRATEGY ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    # Test this strategy on all configured data sources
    results = test_on_all_data(ConsecutiveDownADXStrategy, 'ConsecutiveDown_ADX')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/ConsecutiveDown_ADX_[timestamp].csv")