from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
from backtesting.lib import crossover
from backtesting.test import GOOG

class ADXMAStrategy(Strategy):
    """
    Strategy that combines ADX for trend strength with Moving Average for trend direction
    Created with 🌙 by Moon Dev
    """
    
    # Define parameters with optimization ranges
    adx_length = 14  # ADX period
    ma_length = 20   # Moving average period
    adx_threshold = 25  # ADX threshold for strong trend

    def init(self):
        print("🚀 Moon Dev's ADX + MA Strategy Initializing...")
        print(f"🔧 Testing with ADX Length: {self.adx_length}, MA Length: {self.ma_length}, ADX Threshold: {self.adx_threshold}")
        
        # Calculate ADX
        df = pd.DataFrame(self.data.Close)
        df['High'] = self.data.High
        df['Low'] = self.data.Low
        
        # Calculate ADX using pandas_ta
        adx = ta.adx(df['High'], df['Low'], df['Close'], length=self.adx_length)
        # Use dynamic column name based on ADX length
        adx_col = f'ADX_{self.adx_length}'
        self.adx = self.I(lambda x: adx[adx_col], 'ADX')
        
        # Calculate Moving Average
        self.ma = self.I(ta.sma, pd.Series(self.data.Close), length=self.ma_length)
        
        print("🎯 Strategy Ready! May the Moon Dev be with you!")

    def next(self):
        # Print current analysis for debugging (only if not optimizing)
        if not hasattr(self, '_optimization_in_progress'):
            print(f"🔍 Moon Dev Analysis - Price: {self.data.Close[-1]:.2f}, ADX: {self.adx[-1]:.2f}, MA: {self.ma[-1]:.2f}")
        
        # Only trade if ADX indicates strong trend
        if self.adx[-1] > self.adx_threshold:
            
            # Long signal: Price above MA and strong trend
            if self.data.Close[-1] > self.ma[-1]:
                if not self.position:
                    if not hasattr(self, '_optimization_in_progress'):
                        print("🌕 Moon Dev Says: Strong Uptrend Detected! Going LONG!")
                    self.buy()
                    
            # Short signal: Price below MA and strong trend
            elif self.data.Close[-1] < self.ma[-1]:
                if not self.position:
                    if not hasattr(self, '_optimization_in_progress'):
                        print("🌑 Moon Dev Says: Strong Downtrend Detected! Going SHORT!")
                    self.sell()
        
        # Exit positions if trend weakens
        elif self.position and self.adx[-1] < self.adx_threshold:
            if not hasattr(self, '_optimization_in_progress'):
                print("💫 Moon Dev Says: Trend Weakening - Closing Position!")
            self.position.close()

# Load the data
print("📊 Loading Moon Dev's Trading Data...")
data = pd.read_csv('/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/ge_data/ES_F_future_1d.csv', 
                   parse_dates=['datetime'], 
                   index_col='datetime')

# Capitalize column names for backtesting.py compatibility
data.columns = [col.capitalize() for col in data.columns]

# Run optimization
print("🎲 Running Moon Dev's Strategy Optimizer...")
bt = Backtest(data, ADXMAStrategy, 
              cash=1000000, 
              commission=.002,
              exclusive_orders=True)

# Define optimization ranges
optimization_params = {
    'adx_length': range(10, 30, 2),      # Test ADX lengths from 10 to 30
    'ma_length': range(10, 50, 5),       # Test MA lengths from 10 to 50
    'adx_threshold': range(15, 35, 2)    # Test ADX thresholds from 15 to 35
}

# Run optimization
print("🔍 Moon Dev is searching for optimal parameters...")
optimization_results = bt.optimize(**optimization_params,
                                 maximize='Equity Final [$]',
                                 constraint=lambda p: p.adx_length < p.ma_length)

# Print optimization results
print("\n🏆 Moon Dev's Optimal Strategy Parameters:")
print(optimization_results._strategy)
print("\n📊 Performance with Optimal Parameters:")
print(optimization_results)

# # Run backtest with optimal parameters
# print("\n🚀 Running Final Backtest with Optimal Parameters...")
# stats = bt.run()
# print("\n🎭 Moon Dev's Strategy Stats (Original Parameters):")
# print(stats)

# Show the plot but don't save
#bt.plot(show_plot=True, save_plot=False)
