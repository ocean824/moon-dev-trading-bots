import pandas as pd
import talib
from backtesting import Backtest, Strategy
print("🚀 Moon Dev's Gap + VWAP Strategy (Long Only) Loading... 🌙")
# Data configuration
# Option 1: 1-hour data (500 weeks) - Market hours only
#DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data_gapped.csv'
# Option 2: 5-minute data (70 weeks) - Market hours only
#DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-5m-70wks-data_gapped.csv'
# Option 3: 1-hour data (500 weeks) - After-hours only
#DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data_inverse_gapped.csv'
# Option 4: 5-minute data (70 weeks) - After-hours only
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-5m-70wks-data_inverse_gapped.csv'
# Strategy parameters (configurable)
GAP_UP_PERCENT = 1.0  # Based on best params from original
TAKE_PROFIT_PERCENT = 2.5
STOP_LOSS_PERCENT = 2.0
# VWAP parameters
VWAP_PERIOD = 20
VWAP_DEVIATION = 0.02  # 2% deviation bands
print(f"📊 Loading gapped data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
# Ensure data is sorted in ascending order (oldest first)
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows of market hours data 🌙")
class GapVWAPStrategy(Strategy):
    gap_threshold = GAP_UP_PERCENT / 100
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100
    vwap_period = VWAP_PERIOD
    vwap_deviation = VWAP_DEVIATION
    def init(self):
        # Calculate gaps between candles
        close_values = pd.Series(self.data.Close)
        open_values = pd.Series(self.data.Open)
        self.prev_close = self.I(lambda: close_values.shift(1).values)
        self.gap_percent = self.I(lambda: (open_values.values - close_values.shift(1).values) / close_values.shift(1).values)
        # VWAP calculation
        typical_price = (self.data.High + self.data.Low + self.data.Close) / 3
        pv = typical_price * self.data.Volume
        # Rolling VWAP
        self.vwap = self.I(lambda: pd.Series(pv).rolling(self.vwap_period).sum().values / 
                          pd.Series(self.data.Volume).rolling(self.vwap_period).sum().values)
        # VWAP bands for mean reversion signals
        self.vwap_upper = self.I(lambda: self.vwap * (1 + self.vwap_deviation))
        self.vwap_lower = self.I(lambda: self.vwap * (1 - self.vwap_deviation))
        # Volume analysis
        self.volume_ma = self.I(talib.SMA, self.data.Volume, 20)
        self.volume_ratio = self.I(lambda: self.data.Volume / self.volume_ma)
        # RSI for momentum confirmation
        self.rsi = self.I(talib.RSI, self.data.Close, 14)
    def next(self):
        if len(self.data) < max(2, self.vwap_period):
            return
        if pd.isna(self.gap_percent[-1])  or pd.isna(self.vwap[-1]):
            return
        # Only trade at market open with gap up
        if not self.position:
            current_gap = self.gap_percent[-1]
            current_price = self.data.Close[-1]
            current_vwap = self.vwap[-1]
            current_volume_ratio = self.volume_ratio[-1]
            current_rsi = self.rsi[-1] if not pd.isna(self.rsi[-1]) else 50
            # Gap up signal
            gap_signal = current_gap > self.gap_threshold
            # VWAP confirmation: Price above VWAP shows institutional buying
            vwap_bullish = current_price > current_vwap
            # Volume confirmation: Higher volume on gap = real interest
            volume_surge = current_volume_ratio > 1.2 if not pd.isna(current_volume_ratio) else False
            # RSI not overbought
            rsi_room = current_rsi < 70
            # Jim Simons approach: Statistical edge from multiple factors
            if gap_signal and vwap_bullish and (volume_surge or rsi_room):
                # Dynamic stops based on VWAP distance
                vwap_distance = abs(current_price - current_vwap) / current_price
                if vwap_distance > 0.03:  # Far from VWAP
                    # Tighter stops when extended
                    sl_multiplier = 0.8
                    tp_multiplier = 0.8
                else:
                    # Normal stops when near VWAP
                    sl_multiplier = 1.0
                    tp_multiplier = 1.2
                # Use VWAP as dynamic support
                vwap_stop = self.vwap_lower[-1] if not pd.isna(self.vwap_lower[-1]) else current_price * 0.98
                percent_stop = current_price * (1 - self.stop_loss * sl_multiplier)
                sl_price = max(vwap_stop, percent_stop)
                tp_price = current_price * (1 + self.take_profit * tp_multiplier)
                self.buy(sl=sl_price, tp=tp_price)
# Run backtest
bt = Backtest(data, GapVWAPStrategy, cash=100000, commission=0.00045)
print("\n🌙 ===== GAP + VWAP STRATEGY - DEFAULT PARAMETERS ===== 🌙")
print(f"Gap Up Threshold: {GAP_UP_PERCENT}%")
print(f"VWAP Period: {VWAP_PERIOD}")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")
stats_default = bt.run()
print(stats_default)
print("\n🚀 Optimizing Gap + VWAP Strategy...")
optimization_results = bt.optimize(
    gap_threshold=[i / 1000 for i in range(5, 31, 5)],      # 0.5% to 3%
    take_profit=[i / 1000 for i in range(20, 51, 5)],       # 2% to 5%
    stop_loss=[i / 1000 for i in range(10, 31, 5)],         # 1% to 3%
    vwap_period=range(10, 31, 10),
    vwap_deviation=[i / 1000 for i in range(10, 31, 10)],   # 1% to 3%
    maximize='Sortino Ratio',
    constraint=lambda p: p.take_profit > p.stop_loss
)
print("\n🚀 ===== GAP + VWAP OPTIMIZATION RESULTS ===== 🚀")
print(optimization_results)
print("\n🏆 BEST PARAMETERS:")
print(f"Gap Up Threshold: {optimization_results._strategy.gap_threshold * 100:.1f}%")
print(f"VWAP Period: {optimization_results._strategy.vwap_period}")
print(f"VWAP Deviation: {optimization_results._strategy.vwap_deviation * 100:.1f}%")
print(f"Take Profit: {optimization_results._strategy.take_profit * 100:.1f}%")
print(f"Stop Loss: {optimization_results._strategy.stop_loss * 100:.1f}%")