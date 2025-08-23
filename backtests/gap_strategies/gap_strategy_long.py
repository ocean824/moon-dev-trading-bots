'''


🌙 1 HOUR DATA ===== GAP UP STRATEGY (LONG ONLY) - DEFAULT PARAMETERS ===== 🌙
Gap Up Threshold: 2.0%
Take Profit: 3.0%
Stop Loss: 1.5%
Start                     2015-09-21 14:00:00
End                       2025-04-18 19:00:00
Duration                   3497 days 05:00:00
Exposure Time [%]                   24.134712
Equity Final [$]                  949860.3743
Equity Peak [$]                 1251726.94422
Return [%]                         849.860374
Buy & Hold Return [%]            36875.660311
Return (Ann.) [%]                   25.472371
Volatility (Ann.) [%]               39.981389
Sharpe Ratio                         0.637106
Sortino Ratio                        1.290124
Calmar Ratio                         0.493781
Max. Drawdown [%]                   -51.58637
Avg. Drawdown [%]                   -4.112942
Max. Drawdown Duration     1555 days 00:00:00
Avg. Drawdown Duration       41 days 06:00:00
# Trades                                  429
Win Rate [%]                        52.214452
Best Trade [%]                      19.777409
Worst Trade [%]                     -15.34597
Avg. Trade [%]                       0.528766
Max. Trade Duration          13 days 23:00:00
Avg. Trade Duration           1 days 16:00:00
Profit Factor                        1.395055
Expectancy [%]                        0.63605
SQN                                  1.418822
_strategy                   GapUpLongStrategy
_equity_curve                             ...
_trades                        Size  Entry...
dtype: object

🚀 Optimizing Gap Up Strategy...
/opt/anaconda3/envs/tflow/lib/python3.10/site-packages/backtesting/backtesting.py:1488: UserWarning: Searching for best of 351 configurations.
  output = _optimize_grid()
/opt/anaconda3/envs/tflow/lib/python3.10/site-packages/backtesting/backtesting.py:1375: UserWarning: For multiprocessing support in `Backtest.optimize()` set multiprocessing start method to 'fork'.
  warnings.warn("For multiprocessing support in `Backtest.optimize()` "
                                                                                                                                         
🚀 ===== GAP UP OPTIMIZATION RESULTS ===== 🚀
Start                     2015-09-21 14:00:00
End                       2025-04-18 19:00:00
Duration                   3497 days 05:00:00
Exposure Time [%]                   39.446482
Equity Final [$]                8894964.00069
Equity Peak [$]                 9636089.84957
Return [%]                        8794.964001
Buy & Hold Return [%]            36875.660311
Return (Ann.) [%]                   57.207671
Volatility (Ann.) [%]               61.213027
Sharpe Ratio                         0.934567
Sortino Ratio                         2.42197
Calmar Ratio                         1.288037
Max. Drawdown [%]                  -44.414633
Avg. Drawdown [%]                   -3.357163
Max. Drawdown Duration      937 days 21:00:00
Avg. Drawdown Duration       17 days 12:00:00
# Trades                                  641
Win Rate [%]                        60.686427
Best Trade [%]                      19.777409
Worst Trade [%]                     -15.34597
Avg. Trade [%]                       0.705142
Max. Trade Duration          16 days 23:00:00
Avg. Trade Duration           1 days 21:00:00
Profit Factor                        1.536985
Expectancy [%]                       0.804968
SQN                                  2.262554
_strategy                 GapUpLongStrateg...
_equity_curve                             ...
_trades                        Size  Entry...
dtype: object

🏆 BEST PARAMETERS:
Gap Up Threshold: 1.0%
Take Profit: 2.5%
Stop Loss: 2.0%
(tflow) md@mds-MacBook-Pro moon-dev-trading-bots % 

'''


import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy

print("🚀 Moon Dev's Gap Up Strategy (Long Only) Loading... 🌙")

# Data configuration
# Option 1: 1-hour data (500 weeks) - Market hours only
#DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data_gapped.csv'
# Option 2: 5-minute data (70 weeks) - Market hours only
#DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-5m-70wks-data_gapped.csv'
# Option 3: 1-hour data (500 weeks) - After-hours only
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data_inverse_gapped.csv'
# Option 4: 5-minute data (70 weeks) - After-hours only
#DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-5m-70wks-data_inverse_gapped.csv'

# Strategy parameters (configurable)
GAP_UP_PERCENT = 0.5  # Minimum gap up percentage to trigger entry (lowered for more signals)
TAKE_PROFIT_PERCENT = 2.0  # Take profit percentage
STOP_LOSS_PERCENT = 1.0  # Stop loss percentage

print(f"📊 Loading gapped data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
# Ensure data is sorted in ascending order (oldest first)
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows of data 🌙")

class GapUpLongStrategy(Strategy):
    gap_threshold = GAP_UP_PERCENT / 100
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100
    
    def init(self):
        # Calculate gaps between candles
        close_values = pd.Series(self.data.Close)
        open_values = pd.Series(self.data.Open)
        
        # Gap is difference between current open and previous close
        self.prev_close = self.I(lambda: close_values.shift(1).values)
        self.gap_percent = self.I(lambda: (open_values.values - close_values.shift(1).values) / close_values.shift(1).values)
        
        # For after-hours data, detect session breaks (gaps in time)
        times = pd.Series(self.data.index)
        time_diff = times.diff()
        # Session break if more than 1 hour gap (for hourly) or 15 min gap (for 5-min data)
        threshold = pd.Timedelta(minutes=15)
        self.session_break = self.I(lambda: (time_diff > threshold).values)
        
    def next(self):
        # Skip if not enough data
        if len(self.data) < 2:
            return
            
        # Skip if we have NaN values
        if pd.isna(self.gap_percent[-1]):
            return
            
        # Check for gaps on any candle (not just session breaks for now)
        # This will catch all significant gaps in the data
        if not self.position:
            current_gap = self.gap_percent[-1]
            
            # Check for gap up
            if current_gap > self.gap_threshold:
                current_price = self.data.Close[-1]
                
                # Calculate stop loss and take profit
                sl_price = current_price * (1 - self.stop_loss)
                tp_price = current_price * (1 + self.take_profit)
                
                # Enter long position
                self.buy(sl=sl_price, tp=tp_price)

# Run backtest
bt = Backtest(data, GapUpLongStrategy, cash=100000, commission=0.00045)

print("\n🌙 ===== GAP UP STRATEGY (LONG ONLY) - DEFAULT PARAMETERS ===== 🌙")
print(f"Gap Up Threshold: {GAP_UP_PERCENT}%")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")
stats_default = bt.run()
print(stats_default)

print("\n🚀 Optimizing Gap Up Strategy...")
optimization_results = bt.optimize(
    gap_threshold=[i / 1000 for i in range(10, 51, 5)],  # 1% to 5%
    take_profit=[i / 1000 for i in range(20, 61, 5)],    # 2% to 6%
    stop_loss=[i / 1000 for i in range(10, 31, 5)],      # 1% to 3%
    maximize='Sortino Ratio',
    constraint=lambda p: p.take_profit > p.stop_loss
)

print("\n🚀 ===== GAP UP OPTIMIZATION RESULTS ===== 🚀")
print(optimization_results)

print("\n🏆 BEST PARAMETERS:")
print(f"Gap Up Threshold: {optimization_results._strategy.gap_threshold * 100:.1f}%")
print(f"Take Profit: {optimization_results._strategy.take_profit * 100:.1f}%")
print(f"Stop Loss: {optimization_results._strategy.stop_loss * 100:.1f}%")