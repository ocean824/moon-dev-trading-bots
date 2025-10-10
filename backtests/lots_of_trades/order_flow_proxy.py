"""
ORDER FLOW PROXY Strategy - Trade Bid/Ask Pressure
===================================================

Concept: Use price action and volume to proxy order flow.
Detect buying/selling pressure and trade with the flow.

Target: 4500+ trades following order flow
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import warnings
warnings.filterwarnings('ignore')

print("📊 Moon Dev's ORDER FLOW PROXY Strategy 📊")
print("=" * 70)

# Load data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1m-4wks-data.csv'
print(f"📊 Loading BTC 1-minute data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Order flow proxy calculations
# Buy pressure: Close in upper half of range
data['Buy_Pressure'] = (data['Close'] - data['Low']) / (data['High'] - data['Low'] + 0.00001)
data['Sell_Pressure'] = 1 - data['Buy_Pressure']

# Volume-weighted pressure
data['Buy_Volume'] = data['Volume'] * data['Buy_Pressure']
data['Sell_Volume'] = data['Volume'] * data['Sell_Pressure']

# Net order flow
data['Net_Flow'] = data['Buy_Volume'] - data['Sell_Volume']
data['Cumulative_Flow'] = data['Net_Flow'].rolling(10).sum()

# Delta divergence
data['Price_Change'] = data['Close'].pct_change()
data['Flow_Price_Divergence'] = np.sign(data['Net_Flow']) != np.sign(data['Price_Change'])

# Absorption detection (high volume, small price change)
data['Volume_MA'] = data['Volume'].rolling(20).mean()
data['Absorption'] = (data['Volume'] > data['Volume_MA'] * 1.5) & (abs(data['Price_Change']) < 0.001)

print(f"✅ Loaded {len(data):,} 1-minute bars")


class OrderFlowProxyStrategy(Strategy):
    """
    Trade based on order flow imbalances
    """
    
    # Parameters
    flow_threshold = 5000      # Minimum cumulative flow
    buy_pressure_min = 0.7    # Minimum buy pressure
    sell_pressure_min = 0.7   # Minimum sell pressure
    take_profit = 0.003       # 0.3%
    stop_loss = 0.002         # 0.2%
    absorption_trade = True   # Trade absorption patterns
    
    def init(self):
        self.buy_pressure = self.I(lambda: self.data.Buy_Pressure)
        self.sell_pressure = self.I(lambda: self.data.Sell_Pressure)
        self.net_flow = self.I(lambda: self.data.Net_Flow)
        self.cumulative_flow = self.I(lambda: self.data.Cumulative_Flow)
        self.absorption = self.I(lambda: self.data.Absorption)
        self.divergence = self.I(lambda: self.data.Flow_Price_Divergence)
        
    def next(self):
        if len(self.data) < 30:
            return
            
        current_price = self.data.Close[-1]
        buy_pressure = self.buy_pressure[-1] if self.buy_pressure[-1] else 0.5
        sell_pressure = self.sell_pressure[-1] if self.sell_pressure[-1] else 0.5
        net_flow = self.net_flow[-1] if self.net_flow[-1] else 0
        cum_flow = self.cumulative_flow[-1] if self.cumulative_flow[-1] else 0
        is_absorption = self.absorption[-1] if self.absorption[-1] else False
        
        # Exit on flow reversal
        if self.position:
            if self.position.is_long and net_flow < -self.flow_threshold/2:
                self.position.close()
                return
            elif self.position.is_short and net_flow > self.flow_threshold/2:
                self.position.close()
                return
        
        # Entry logic
        if not self.position:
            
            # Strong buy flow
            if (cum_flow > self.flow_threshold and 
                buy_pressure > self.buy_pressure_min):
                
                tp = current_price * (1 + self.take_profit)
                sl = current_price * (1 - self.stop_loss)
                self.buy(tp=tp, sl=sl)
                return
                
            # Strong sell flow
            elif (cum_flow < -self.flow_threshold and
                  sell_pressure > self.sell_pressure_min):
                
                tp = current_price * (1 - self.take_profit)
                sl = current_price * (1 + self.stop_loss)
                self.sell(tp=tp, sl=sl)
                return
            
            # Absorption patterns
            if self.absorption_trade and is_absorption:
                # Bullish absorption (sellers absorbed)
                if buy_pressure > 0.6:
                    tp = current_price * (1 + self.take_profit)
                    sl = current_price * (1 - self.stop_loss)
                    self.buy(tp=tp, sl=sl)
                    
                # Bearish absorption (buyers absorbed)
                elif sell_pressure > 0.6:
                    tp = current_price * (1 - self.take_profit)
                    sl = current_price * (1 + self.stop_loss)
                    self.sell(tp=tp, sl=sl)


# Run backtest
print("\n" + "="*70)
print("RUNNING ORDER FLOW PROXY BACKTEST")
print("="*70)

bt = Backtest(
    data,
    OrderFlowProxyStrategy,
    cash=1000000,
    commission=0.001,
    exclusive_orders=True
)

baseline_stats = bt.run()

print(f"\n📊 RESULTS:")
print(baseline_stats)

# Optimization
print("\n" + "="*70)
print("OPTIMIZING FOR RETURN ON INVESTMENT")
print("="*70)

try:
    optimization_results = bt.optimize(
        flow_threshold=[3000, 5000, 7000],
        buy_pressure_min=[0.65, 0.7, 0.75],
        take_profit=[0.002, 0.003, 0.004],
        stop_loss=[0.0015, 0.002, 0.0025],
        maximize='Return [%]',
        return_heatmap=False
    )
    
    print(f"\n✨ OPTIMIZED RESULTS:")
    print(optimization_results)
    
except Exception as e:
    print(f"Optimization failed: {str(e)}")

bt.plot()