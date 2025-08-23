import pandas as pd
import talib
from backtesting import Backtest, Strategy
print("🚀 Moon Dev's Gap + Bollinger Bands Strategy (Long Only) Loading... 🌙")
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
# Bollinger Bands parameters
BB_PERIOD = 20
BB_STD_DEV = 2.0
print(f"📊 Loading gapped data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
# Ensure data is sorted in ascending order (oldest first)
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows of market hours data 🌙")
class GapBollingerStrategy(Strategy):
    gap_threshold = GAP_UP_PERCENT / 100
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100
    bb_period = BB_PERIOD
    bb_std = BB_STD_DEV
    def init(self):
        # Calculate gaps between candles
        close_values = pd.Series(self.data.Close)
        open_values = pd.Series(self.data.Open)
        self.prev_close = self.I(lambda: close_values.shift(1).values)
        self.gap_percent = self.I(lambda: (open_values.values - close_values.shift(1).values) / close_values.shift(1).values)
        # Bollinger Bands
        self.bb_upper, self.bb_middle, self.bb_lower = self.I(
            talib.BBANDS, 
            self.data.Close, 
            self.bb_period, 
            self.bb_std, 
            self.bb_std, 
            0
        )
        # Bollinger Band Width for volatility
        self.bb_width = self.I(lambda: (self.bb_upper - self.bb_lower) / self.bb_middle)
        # %B indicator (position within bands)
        self.percent_b = self.I(lambda: (self.data.Close - self.bb_lower) / (self.bb_upper - self.bb_lower))
        # ATR for volatility-adjusted stops
        self.atr = self.I(talib.ATR, self.data.High, self.data.Low, self.data.Close, 14)
        # Momentum indicators
        self.rsi = self.I(talib.RSI, self.data.Close, 14)
        self.macd, self.macd_signal, _ = self.I(talib.MACD, self.data.Close, 12, 26, 9)
    def next(self):
        if len(self.data) < max(2, self.bb_period):
            return
        if (pd.isna(self.gap_percent[-1])  or 
            pd.isna(self.bb_upper[-1]) or pd.isna(self.percent_b[-1])):
            return
        # Only trade at market open with gap up
        if not self.position:
            current_gap = self.gap_percent[-1]
            current_price = self.data.Close[-1]
            current_bb_upper = self.bb_upper[-1]
            current_bb_middle = self.bb_middle[-1]
            current_bb_lower = self.bb_lower[-1]
            current_bb_width = self.bb_width[-1]
            current_percent_b = self.percent_b[-1]
            current_rsi = self.rsi[-1] if not pd.isna(self.rsi[-1]) else 50
            current_macd = self.macd[-1] if not pd.isna(self.macd[-1]) else 0
            current_macd_signal = self.macd_signal[-1] if not pd.isna(self.macd_signal[-1]) else 0
            current_atr = self.atr[-1] if not pd.isna(self.atr[-1]) else 0
            # Gap up signal
            gap_signal = current_gap > self.gap_threshold
            # Bollinger Band signals (Jim Simons style - mean reversion with trend)
            # Gap up near lower band = oversold bounce opportunity
            bb_oversold_bounce = current_percent_b < 0.3
            # Gap up with room to upper band = trend continuation
            bb_room_to_run = current_percent_b < 0.7
            # Volatility expanding = bigger moves expected
            volatility_expanding = current_bb_width > 0.04 if not pd.isna(current_bb_width) else False
            # Momentum confirmation
            macd_bullish = current_macd > current_macd_signal
            rsi_not_overbought = current_rsi < 70
            # Jim Simons approach: High probability setups from volatility patterns
            if gap_signal and (bb_oversold_bounce or (bb_room_to_run and volatility_expanding)):
                if macd_bullish or rsi_not_overbought:
                    # Dynamic position sizing based on volatility
                    if volatility_expanding and current_bb_width > 0.06:
                        # High volatility: wider stops, bigger targets
                        sl_multiplier = 1.5
                        tp_multiplier = 1.5
                    elif current_percent_b < 0.2:
                        # Oversold bounce: tighter stops, quick profits
                        sl_multiplier = 0.8
                        tp_multiplier = 1.0
                    else:
                        # Normal conditions
                        sl_multiplier = 1.0
                        tp_multiplier = 1.0
                    # Use Bollinger Bands for dynamic stops
                    bb_stop = current_bb_lower - (current_atr * 0.5) if current_atr > 0 else current_bb_lower
                    percent_stop = current_price * (1 - self.stop_loss * sl_multiplier)
                    sl_price = max(bb_stop, percent_stop)
                    # Target based on band position
                    if current_percent_b < 0.3:
                        # From oversold, target middle band first
                        bb_target = current_bb_middle
                    else:
                        # Otherwise target upper band
                        bb_target = current_bb_upper
                    percent_target = current_price * (1 + self.take_profit * tp_multiplier)
                    tp_price = min(bb_target, percent_target)
                    self.buy(sl=sl_price, tp=tp_price)
# Run backtest
bt = Backtest(data, GapBollingerStrategy, cash=100000, commission=0.00045)
print("\n🌙 ===== GAP + BOLLINGER BANDS STRATEGY - DEFAULT PARAMETERS ===== 🌙")
print(f"Gap Up Threshold: {GAP_UP_PERCENT}%")
print(f"BB Period: {BB_PERIOD}")
print(f"BB Std Dev: {BB_STD_DEV}")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")
stats_default = bt.run()
print(stats_default)
print("\n🚀 Optimizing Gap + Bollinger Bands Strategy...")
optimization_results = bt.optimize(
    gap_threshold=[i / 1000 for i in range(5, 31, 5)],      # 0.5% to 3%
    take_profit=[i / 1000 for i in range(20, 51, 5)],       # 2% to 5%
    stop_loss=[i / 1000 for i in range(10, 31, 5)],         # 1% to 3%
    bb_period=range(15, 31, 5),
    bb_std=[1.5, 2.0, 2.5],
    maximize='Sortino Ratio',
    constraint=lambda p: p.take_profit > p.stop_loss
)
print("\n🚀 ===== GAP + BOLLINGER OPTIMIZATION RESULTS ===== 🚀")
print(optimization_results)
print("\n🏆 BEST PARAMETERS:")
print(f"Gap Up Threshold: {optimization_results._strategy.gap_threshold * 100:.1f}%")
print(f"BB Period: {optimization_results._strategy.bb_period}")
print(f"BB Std Dev: {optimization_results._strategy.bb_std}")
print(f"Take Profit: {optimization_results._strategy.take_profit * 100:.1f}%")
print(f"Stop Loss: {optimization_results._strategy.stop_loss * 100:.1f}%")