import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy

print("🚀 Moon Dev's Consecutive Down + Kaufman Strategy (Long Only) Loading... 🌙")

class ConsecutiveDownKaufmanStrategy(Strategy):
    consecutive_bars = 4
    take_profit = 0.03  # 3%
    stop_loss = 0.02    # 2%
    kama_period = 10
    
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
        
        # Kaufman Adaptive Moving Average
        self.kama = self.I(talib.KAMA, self.data.Close, self.kama_period)
        
        # Efficiency Ratio for trend strength
        def calculate_efficiency_ratio():
            er_values = np.zeros(len(self.data))
            period = 10
            
            for i in range(period, len(self.data)):
                direction = abs(self.data.Close[i] - self.data.Close[i-period])
                volatility = sum([abs(self.data.Close[j] - self.data.Close[j-1]) 
                                for j in range(i-period+1, i+1)])
                
                if volatility != 0:
                    er_values[i] = direction / volatility
                else:
                    er_values[i] = 0
            
            return er_values
        
        self.efficiency_ratio = self.I(calculate_efficiency_ratio)
        
        # RSI for momentum
        self.rsi = self.I(talib.RSI, self.data.Close, 14)
        
        # ATR for volatility
        self.atr = self.I(talib.ATR, 
                          self.data.High, 
                          self.data.Low, 
                          self.data.Close, 
                          14)
        
        # Volume analysis
        self.volume_ma = self.I(talib.SMA, self.data.Volume, 20)
        self.volume_ratio = self.I(lambda: self.data.Volume / self.volume_ma)
    
    def next(self):
        if len(self.data) < max(self.consecutive_bars + 1, self.kama_period, 20):
            return
        
        if pd.isna(self.kama[-1]) or pd.isna(self.rsi[-1]) or pd.isna(self.atr[-1]):
            return
        
        if not self.position:
            # Check for consecutive down bars
            consecutive_signal = self.consecutive_down[-1] >= self.consecutive_bars
            
            # Kaufman filter: price below KAMA indicates downtrend
            kaufman_signal = self.data.Close[-1] < self.kama[-1]
            
            # Low efficiency ratio suggests choppy market (potential reversal)
            efficiency_signal = self.efficiency_ratio[-1] < 0.3
            
            # RSI oversold
            rsi_signal = self.rsi[-1] < 35
            
            # High volume on down move (capitulation)
            volume_signal = self.volume_ratio[-1] > 1.2
            
            # Combined signal
            if consecutive_signal and kaufman_signal and efficiency_signal and (rsi_signal or volume_signal):
                current_price = self.data.Close[-1]
                
                # Dynamic stop loss using ATR
                atr_stop = current_price - (self.atr[-1] * 2)
                percent_stop = current_price * (1 - self.stop_loss)
                sl_price = max(atr_stop, percent_stop)
                
                # Dynamic take profit
                tp_price = current_price * (1 + self.take_profit)
                
                self.buy(sl=sl_price, tp=tp_price)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING CONSECUTIVE DOWN + KAUFMAN STRATEGY ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    # Test this strategy on all configured data sources
    results = test_on_all_data(ConsecutiveDownKaufmanStrategy, 'ConsecutiveDown_Kaufman')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/ConsecutiveDown_Kaufman_[timestamp].csv")