import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
from backtesting.lib import crossover

print("🚀 Moon Dev's Volume Breakout Trading Strategy Loading... 🌙")

# Load the BTCUSD data using Moon Dev's standard approach
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-5m-70wks-data.csv'

# 🌙 MOON DEV Adaptive header detection for different data sources
# First, peek at the headers to determine format
sample_df = pd.read_csv(data_path, nrows=1)
headers = sample_df.columns.tolist()

# Determine which datetime column to use
if 'timestamp' in headers:
    datetime_col = 'timestamp'
elif 'datetime' in headers:
    datetime_col = 'datetime'
else:
    raise ValueError("🌙 MOON DEV Error: No 'timestamp' or 'datetime' column found!")

# Load data with the correct datetime column
data = pd.read_csv(data_path, parse_dates=[datetime_col], index_col=datetime_col)

print(f"✅ Data loaded successfully! Moon Dev's dataset has {len(data)} rows 🌙")

# Volume Breakout Strategy
class VolumeBreakoutStrategy(Strategy):
    # Strategy Parameters - MOON DEV Style! 🌙
    volume_window = 20          # Rolling window for average volume calculation
    volume_threshold = 2.0      # Volume spike threshold (2x average)
    price_window = 10           # Window for recent highs/lows
    volume_decline_threshold = 0.8  # Volume decline exit threshold
    
    # Risk Management Parameters
    stop_loss = 0.02            # 2% stop loss
    take_profit = 0.03          # 3% take profit
    time_exit_bars = 50         # Time-based exit after N bars
    atr_period = 14             # ATR period for volatility-based position sizing
    cooldown_bars = 5           # Cooldown period after losses
    
    def init(self):
        # Volume indicators
        self.avg_volume = self.I(talib.SMA, self.data.Volume, self.volume_window)
        self.volume_roc = self.I(talib.ROC, self.data.Volume, 1)  # Volume rate of change
        
        # Price breakout levels
        self.recent_high = self.I(talib.MAX, self.data.High, self.price_window)
        self.recent_low = self.I(talib.MIN, self.data.Low, self.price_window)
        
        # Volatility for position sizing
        self.atr = self.I(talib.ATR, self.data.High, self.data.Low, self.data.Close, self.atr_period)
        
        # Track position timing and cooldown
        self.position_entry_bar = None
        self.last_loss_bar = None
        
    def next(self):
        # Skip if not enough data
        if len(self.data) < max(self.volume_window, self.price_window, self.atr_period):
            return
            
        current_price = self.data.Close[-1]
        current_volume = self.data.Volume[-1]
        current_avg_volume = self.avg_volume[-1]
        current_atr = self.atr[-1]
        current_bar = len(self.data) - 1
        
        # Skip if we don't have valid indicator values
        if (pd.isna(current_avg_volume) or pd.isna(current_atr) or 
            current_avg_volume == 0 or current_atr == 0):
            return
        
        # Volume spike detection
        volume_spike = current_volume > (self.volume_threshold * current_avg_volume)
        
        # Price breakout detection
        price_breakout_high = current_price > self.recent_high[-2]  # Above yesterday's recent high
        price_breakout_low = current_price < self.recent_low[-2]    # Below yesterday's recent low
        
        # Cooldown check - avoid trading too soon after losses
        in_cooldown = (self.last_loss_bar is not None and 
                      current_bar - self.last_loss_bar < self.cooldown_bars)
        
        # Position management for existing positions
        if self.position:
            # Time-based exit
            if (self.position_entry_bar is not None and 
                current_bar - self.position_entry_bar >= self.time_exit_bars):
                self.position.close()
                return
            
            # Volume decline exit
            if current_volume < (self.volume_decline_threshold * current_avg_volume):
                self.position.close()
                return
        
        # Entry conditions - only if no position and not in cooldown
        if not self.position and not in_cooldown:
            
            # Long Entry: Volume spike + Price breakout above recent high
            if volume_spike and price_breakout_high:
                # Calculate position size based on ATR (volatility-based sizing)
                # Risk 1% of capital per trade, adjust size based on volatility
                risk_per_trade = 0.01  # 1% risk
                stop_distance = current_price * self.stop_loss
                position_size = (risk_per_trade * self.cash) / stop_distance
                
                # Limit position size to reasonable bounds
                max_position_value = self.cash * 0.95  # Max 95% of capital
                position_size = min(position_size, max_position_value / current_price)
                
                self.buy(
                    size=position_size,
                    sl=current_price * (1 - self.stop_loss),
                    tp=current_price * (1 + self.take_profit)
                )
                self.position_entry_bar = current_bar
            
            # Short Entry: Volume spike + Price breakout below recent low
            elif volume_spike and price_breakout_low:
                # Calculate position size based on ATR (volatility-based sizing)
                risk_per_trade = 0.01  # 1% risk
                stop_distance = current_price * self.stop_loss
                position_size = (risk_per_trade * self.cash) / stop_distance
                
                # Limit position size to reasonable bounds
                max_position_value = self.cash * 0.95  # Max 95% of capital
                position_size = min(position_size, max_position_value / current_price)
                
                self.sell(
                    size=position_size,
                    sl=current_price * (1 + self.stop_loss),
                    tp=current_price * (1 - self.take_profit)
                )
                self.position_entry_bar = current_bar
    
    def on_trade_closed(self, trade):
        """Track losses for cooldown period"""
        if trade.pnl < 0:  # If trade was a loss
            self.last_loss_bar = len(self.data) - 1

# Prepare data - convert lowercase columns to uppercase for backtesting.py
data.columns = [col.title() for col in data.columns]

# Remove any invalid data
data = data.dropna()
print(f"✅ Moon Dev's data cleaned! {len(data)} valid rows remaining 🚀")

# Create and configure the backtest
bt = Backtest(data, VolumeBreakoutStrategy, cash=100000, commission=0.002)

# Run the backtest with default parameters
stats_default = bt.run()
print("\n🌙 ===== MOON DEV'S DEFAULT PARAMETERS RESULTS ===== 🌙")
print(stats_default)
print("🌙 ================================================== 🌙\n")

# Comprehensive optimization parameters
optimization_results = bt.optimize(
    volume_window=range(15, 31, 5),                                    # Volume windows: 15, 20, 25, 30
    volume_threshold=[1.5, 1.8, 2.0, 2.2, 2.5, 3.0],                # Volume thresholds: 1.5x to 3.0x
    price_window=range(5, 21, 5),                                     # Price windows: 5, 10, 15, 20
    volume_decline_threshold=[0.6, 0.7, 0.8, 0.9],                   # Volume decline thresholds
    stop_loss=[i / 100 for i in range(1, 4, 1)],                     # Stop loss: 1%, 2%, 3%
    take_profit=[i / 100 for i in range(2, 6, 1)],                   # Take profit: 2%, 3%, 4%, 5%
    time_exit_bars=range(20, 81, 20),                                 # Time exits: 20, 40, 60, 80 bars
    cooldown_bars=range(3, 11, 2),                                    # Cooldown: 3, 5, 7, 9 bars
    maximize='Equity Final [$]',
    constraint=lambda param: (param.volume_window > 0 and 
                             param.volume_threshold > 1 and 
                             param.price_window > 0 and
                             param.volume_decline_threshold > 0 and
                             param.volume_decline_threshold < 1 and
                             param.take_profit > param.stop_loss and
                             param.time_exit_bars > param.price_window and
                             param.cooldown_bars > 0)
)

print("\n🚀 ===== MOON DEV'S OPTIMIZATION RESULTS ===== 🚀")
print(optimization_results)
print("🚀 ========================================== 🚀\n")

# Print the best optimized parameters
print("🏆 Moon Dev's VOLUME BREAKOUT BEST PARAMETERS! 🏆")
print(f"🌙 Volume Window: {optimization_results._strategy.volume_window}")
print(f"🌙 Volume Threshold: {optimization_results._strategy.volume_threshold:.1f}x")
print(f"🌙 Price Window: {optimization_results._strategy.price_window}")
print(f"🌙 Volume Decline Threshold: {optimization_results._strategy.volume_decline_threshold:.1f}x")
print(f"🌙 Stop Loss: {optimization_results._strategy.stop_loss:.3f} ({optimization_results._strategy.stop_loss*100:.1f}%)")
print(f"🌙 Take Profit: {optimization_results._strategy.take_profit:.3f} ({optimization_results._strategy.take_profit*100:.1f}%)")
print(f"🌙 Time Exit Bars: {optimization_results._strategy.time_exit_bars}")
print(f"🌙 Cooldown Bars: {optimization_results._strategy.cooldown_bars}")

print("\n🌙 Moon Dev's Volume Breakout Strategy Analysis Complete! 🚀")
print("💰 Volume spikes + Price breakouts = Moon missions! 🌙")