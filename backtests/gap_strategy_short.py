import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy

print("🚀 Moon Dev's Gap Down Strategy (Short Only) Loading... 🌙")

# Data configuration
# Option 1: 1-hour data (500 weeks)
#DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data_gapped.csv'
# Option 2: 5-minute data (70 weeks)
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-5m-70wks-data_gapped.csv'

# Strategy parameters (configurable)
GAP_DOWN_PERCENT = 2.0  # Minimum gap down percentage to trigger entry
TAKE_PROFIT_PERCENT = 3.0  # Take profit percentage (for short)
STOP_LOSS_PERCENT = 1.5  # Stop loss percentage (for short)

print(f"📊 Loading gapped data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
# Ensure data is sorted in ascending order (oldest first)
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows of market hours data 🌙")

class GapDownShortStrategy(Strategy):
    gap_threshold = GAP_DOWN_PERCENT / 100
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100
    
    def init(self):
        # Calculate gaps between candles
        close_values = pd.Series(self.data.Close)
        open_values = pd.Series(self.data.Open)
        
        # Gap is difference between current open and previous close
        self.prev_close = self.I(lambda: close_values.shift(1).values)
        self.gap_percent = self.I(lambda: (open_values.values - close_values.shift(1).values) / close_values.shift(1).values)
        
    def next(self):
        # Skip if not enough data
        if len(self.data) < 2:
            return
            
        # Skip if we have NaN values
        if pd.isna(self.gap_percent[-1]):
            return
            
        # Check for gaps on any candle
        if not self.position:
            current_gap = self.gap_percent[-1]
            
            # Check for gap down (negative gap)
            if current_gap < -self.gap_threshold:
                current_price = self.data.Close[-1]
                
                # Calculate stop loss and take profit for short position
                sl_price = current_price * (1 + self.stop_loss)  # Stop loss above entry
                tp_price = current_price * (1 - self.take_profit)  # Take profit below entry
                
                # Enter short position
                self.sell(sl=sl_price, tp=tp_price)

# Run backtest
bt = Backtest(data, GapDownShortStrategy, cash=100000, commission=0.002)

print("\n🌙 ===== GAP DOWN STRATEGY (SHORT ONLY) - DEFAULT PARAMETERS ===== 🌙")
print(f"Gap Down Threshold: {GAP_DOWN_PERCENT}%")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")
stats_default = bt.run()
print(stats_default)

print("\n🚀 Optimizing Gap Down Strategy...")
optimization_results = bt.optimize(
    gap_threshold=[i / 1000 for i in range(10, 51, 5)],  # 1% to 5%
    take_profit=[i / 1000 for i in range(20, 61, 5)],    # 2% to 6%
    stop_loss=[i / 1000 for i in range(10, 31, 5)],      # 1% to 3%
    maximize='Sortino Ratio',
    constraint=lambda p: p.take_profit > p.stop_loss
)

print("\n🚀 ===== GAP DOWN OPTIMIZATION RESULTS ===== 🚀")
print(optimization_results)

print("\n🏆 BEST PARAMETERS:")
print(f"Gap Down Threshold: {optimization_results._strategy.gap_threshold * 100:.1f}%")
print(f"Take Profit: {optimization_results._strategy.take_profit * 100:.1f}%")
print(f"Stop Loss: {optimization_results._strategy.stop_loss * 100:.1f}%")