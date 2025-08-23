import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy

print("🚀 Moon Dev's Consecutive Down Strategy (Long Only) Loading... 🌙")

class ConsecutiveDownStrategy(Strategy):
    consecutive_bars = 4
    take_profit = 0.03  # 3%
    stop_loss = 0.02    # 2%
    
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
    
    def next(self):
        if len(self.data) < self.consecutive_bars + 1:
            return
        
        if not self.position:
            if self.consecutive_down[-1] >= self.consecutive_bars:
                current_price = self.data.Close[-1]
                sl_price = current_price * (1 - self.stop_loss)
                tp_price = current_price * (1 + self.take_profit)
                self.buy(sl=sl_price, tp=tp_price)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING CONSECUTIVE DOWN BASE STRATEGY ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    # Test this strategy on all configured data sources
    results = test_on_all_data(ConsecutiveDownStrategy, 'ConsecutiveDown_Base')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/ConsecutiveDown_Base.csv")