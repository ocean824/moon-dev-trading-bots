import pandas as pd
import talib
from backtesting import Backtest, Strategy
print("🚀 Moon Dev's Gap + ADX Strategy (Long Only) Loading... 🌙")
# Data configuration
# Option 1: 1-hour data (500 weeks) - Market hours only
#DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data_gapped.csv'
# Option 2: 5-minute data (70 weeks) - Market hours only
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-5m-70wks-data_gapped.csv'
# Option 3: 1-hour data (500 weeks) - After-hours only
#DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data_inverse_gapped.csv'
# Option 4: 5-minute data (70 weeks) - After-hours only
#DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-5m-70wks-data_inverse_gapped.csv'
# Strategy parameters (configurable)
GAP_UP_PERCENT = 1.0  # Based on best params from original
TAKE_PROFIT_PERCENT = 2.5
STOP_LOSS_PERCENT = 2.0
# ADX parameters
ADX_PERIOD = 14
ADX_THRESHOLD = 25
ADX_STRONG = 40
print(f"📊 Loading gapped data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
# Ensure data is sorted in ascending order (oldest first)
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows of market hours data 🌙")
class GapADXStrategy(Strategy):
    gap_threshold = GAP_UP_PERCENT / 100
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100
    adx_period = ADX_PERIOD
    adx_threshold = ADX_THRESHOLD
    adx_strong = ADX_STRONG
    def init(self):
        # Calculate gaps between candles
        close_values = pd.Series(self.data.Close)
        open_values = pd.Series(self.data.Open)
        self.prev_close = self.I(lambda: close_values.shift(1).values)
        self.gap_percent = self.I(lambda: (open_values.values - close_values.shift(1).values) / close_values.shift(1).values)
        # ADX for trend strength
        self.adx = self.I(talib.ADX, self.data.High, self.data.Low, self.data.Close, self.adx_period)
        self.plus_di = self.I(talib.PLUS_DI, self.data.High, self.data.Low, self.data.Close, self.adx_period)
        self.minus_di = self.I(talib.MINUS_DI, self.data.High, self.data.Low, self.data.Close, self.adx_period)
        # ATR for dynamic stops
        self.atr = self.I(talib.ATR, self.data.High, self.data.Low, self.data.Close, 14)
    def next(self):
        if len(self.data) < max(2, self.adx_period):
            return
        if pd.isna(self.gap_percent[-1])  or pd.isna(self.adx[-1]):
            return
        # Only trade at market open with gap up
        if not self.position:
            current_gap = self.gap_percent[-1]
            current_adx = self.adx[-1]
            current_plus_di = self.plus_di[-1]
            current_minus_di = self.minus_di[-1]
            current_atr = self.atr[-1]
            # Gap up with ADX confirmation
            gap_signal = current_gap > self.gap_threshold
            trend_strong = current_adx > self.adx_threshold
            bullish_di = current_plus_di > current_minus_di
            # Jim Simons approach: Multiple confirmations reduce false signals
            if gap_signal and trend_strong and bullish_di:
                current_price = self.data.Close[-1]
                # Dynamic stops based on ADX strength and ATR
                if current_adx > self.adx_strong:
                    # Strong trend: wider stops, bigger targets
                    sl_multiplier = 1.5
                    tp_multiplier = 1.5
                else:
                    # Normal trend: standard stops
                    sl_multiplier = 1.0
                    tp_multiplier = 1.0
                # ATR-based stops for volatility adjustment
                atr_stop = current_price - (current_atr * 2.0)
                percent_stop = current_price * (1 - self.stop_loss)
                sl_price = max(atr_stop, percent_stop)
                # Take profit with trend strength multiplier
                tp_price = current_price * (1 + self.take_profit * tp_multiplier)
                self.buy(sl=sl_price, tp=tp_price)
# Run backtest
bt = Backtest(data, GapADXStrategy, cash=100000, commission=0.00045)
print("\n🌙 ===== GAP + ADX STRATEGY - DEFAULT PARAMETERS ===== 🌙")
print(f"Gap Up Threshold: {GAP_UP_PERCENT}%")
print(f"ADX Threshold: {ADX_THRESHOLD}")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")
stats_default = bt.run()
print(stats_default)
print("\n🚀 Optimizing Gap + ADX Strategy...")
optimization_results = bt.optimize(
    gap_threshold=[i / 1000 for i in range(5, 31, 5)],      # 0.5% to 3%
    take_profit=[i / 1000 for i in range(20, 51, 5)],       # 2% to 5%
    stop_loss=[i / 1000 for i in range(10, 31, 5)],         # 1% to 3%
    adx_period=range(10, 21, 5),
    adx_threshold=range(20, 36, 5),
    maximize='Sortino Ratio',
    constraint=lambda p: p.take_profit > p.stop_loss
)
print("\n🚀 ===== GAP + ADX OPTIMIZATION RESULTS ===== 🚀")
print(optimization_results)
print("\n🏆 BEST PARAMETERS:")
print(f"Gap Up Threshold: {optimization_results._strategy.gap_threshold * 100:.1f}%")
print(f"ADX Period: {optimization_results._strategy.adx_period}")
print(f"ADX Threshold: {optimization_results._strategy.adx_threshold}")
print(f"Take Profit: {optimization_results._strategy.take_profit * 100:.1f}%")
print(f"Stop Loss: {optimization_results._strategy.stop_loss * 100:.1f}%")