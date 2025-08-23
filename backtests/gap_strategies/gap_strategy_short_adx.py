import pandas as pd
import talib
from backtesting import Backtest, Strategy

print("🚀 Moon Dev's Gap Fade + ADX Strategy (Short Only) Loading... 🌙")

# Data configuration - Focusing on after-hours for gap fading
# Option 1: 1-hour data (500 weeks) - After-hours only (RECOMMENDED FOR SHORTS)
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data_inverse_gapped.csv'
# Option 2: 5-minute data (70 weeks) - After-hours only
#DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-5m-70wks-data_inverse_gapped.csv'
# Option 3: 1-hour data (500 weeks) - Market hours only
#DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data_gapped.csv'
# Option 4: 5-minute data (70 weeks) - Market hours only
#DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-5m-70wks-data_gapped.csv'

# Strategy parameters (configurable)
GAP_UP_PERCENT = 1.0  # Gap up threshold for shorting
TAKE_PROFIT_PERCENT = 2.5  # Take profit percentage
STOP_LOSS_PERCENT = 2.0  # Stop loss percentage

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
print(f"✅ Data loaded! {len(data)} rows of after-hours data 🌙")

class GapFadeADXStrategy(Strategy):
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
        
        # Gap is difference between current open and previous close
        self.prev_close = self.I(lambda: close_values.shift(1).values)
        self.gap_percent = self.I(lambda: (open_values.values - close_values.shift(1).values) / close_values.shift(1).values)
        
        # ADX for trend strength (we want weak trends for fading)
        self.adx = self.I(talib.ADX, self.data.High, self.data.Low, self.data.Close, self.adx_period)
        self.plus_di = self.I(talib.PLUS_DI, self.data.High, self.data.Low, self.data.Close, self.adx_period)
        self.minus_di = self.I(talib.MINUS_DI, self.data.High, self.data.Low, self.data.Close, self.adx_period)
        
        # ATR for dynamic stops
        self.atr = self.I(talib.ATR, self.data.High, self.data.Low, self.data.Close, 14)
        
        # RSI for momentum
        self.rsi = self.I(talib.RSI, self.data.Close, 14)
        
        # MACD for trend confirmation
        self.macd, self.macd_signal, _ = self.I(talib.MACD, self.data.Close, 12, 26, 9)
        
        # Volume analysis
        self.volume_ma = self.I(talib.SMA, self.data.Volume, 20)
        self.volume_ratio = self.I(lambda: self.data.Volume / self.volume_ma)
        
    def next(self):
        if len(self.data) < max(2, self.adx_period):
            return
            
        if pd.isna(self.gap_percent[-1]) or pd.isna(self.adx[-1]):
            return
            
        # Check for gaps on any candle
        if not self.position:
            current_gap = self.gap_percent[-1]
            current_adx = self.adx[-1]
            current_plus_di = self.plus_di[-1]
            current_minus_di = self.minus_di[-1]
            current_atr = self.atr[-1]
            current_rsi = self.rsi[-1] if not pd.isna(self.rsi[-1]) else 50
            current_macd = self.macd[-1] if not pd.isna(self.macd[-1]) else 0
            current_macd_signal = self.macd_signal[-1] if not pd.isna(self.macd_signal[-1]) else 0
            current_volume_ratio = self.volume_ratio[-1] if not pd.isna(self.volume_ratio[-1]) else 1
            
            # Gap up signal for shorting
            gap_signal = current_gap > self.gap_threshold
            
            # ADX signals for gap fading
            # We want either weak trend (ADX < threshold) OR overextended trend (ADX > strong)
            weak_trend = current_adx < self.adx_threshold  # Weak trend = gap likely to fade
            overextended = current_adx > self.adx_strong    # Very strong = due for reversal
            bearish_di = current_minus_di > current_plus_di  # Bearish momentum
            
            # Additional signals
            rsi_overbought = current_rsi > 65
            macd_bearish = current_macd < current_macd_signal
            volume_weak = current_volume_ratio < 1.0  # Below average volume
            
            # Jim Simons approach: Fade gaps in after-hours with weak structure
            if gap_signal and (weak_trend or (overextended and bearish_di)):
                # Score system for confirmation
                fade_score = sum([
                    gap_signal * 3,
                    weak_trend * 2,              # Weak trend means gap won't hold
                    overextended * 1.5,          # Overextended can reverse
                    bearish_di * 2,              # Bearish momentum
                    rsi_overbought * 1,
                    macd_bearish * 1,
                    volume_weak * 2              # Weak volume = gap fades
                ])
                
                if fade_score >= 5:
                    current_price = self.data.Close[-1]
                    
                    # Dynamic stops based on ADX and trend strength
                    if overextended:
                        # Wider stops for overextended markets
                        sl_multiplier = 1.5
                        tp_multiplier = 1.5
                    elif weak_trend:
                        # Tighter stops for weak trends
                        sl_multiplier = 0.8
                        tp_multiplier = 1.0
                    else:
                        # Normal stops
                        sl_multiplier = 1.0
                        tp_multiplier = 1.0
                    
                    # ATR-based stops for shorts
                    atr_stop = current_price + (current_atr * 2.0) if current_atr > 0 else current_price * 1.02
                    percent_stop = current_price * (1 + self.stop_loss * sl_multiplier)
                    sl_price = min(atr_stop, percent_stop)
                    
                    tp_price = current_price * (1 - self.take_profit * tp_multiplier)
                    
                    self.sell(sl=sl_price, tp=tp_price)

# Run backtest
bt = Backtest(data, GapFadeADXStrategy, cash=100000, commission=0.00045)

print("\n🌙 ===== GAP FADE + ADX (SHORT ONLY) - DEFAULT PARAMETERS ===== 🌙")
print(f"Gap Up Threshold (to short): {GAP_UP_PERCENT}%")
print(f"ADX Threshold: {ADX_THRESHOLD}")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")
stats_default = bt.run()
print(stats_default)

print("\n🚀 Optimizing Gap Fade + ADX Strategy...")
optimization_results = bt.optimize(
    gap_threshold=[i / 1000 for i in range(5, 31, 5)],      # 0.5% to 3%
    take_profit=[i / 1000 for i in range(20, 51, 5)],       # 2% to 5%
    stop_loss=[i / 1000 for i in range(10, 31, 5)],         # 1% to 3%
    adx_period=range(10, 21, 5),
    adx_threshold=range(20, 36, 5),
    maximize='Sortino Ratio',
    constraint=lambda p: p.take_profit > p.stop_loss
)

print("\n🚀 ===== GAP FADE + ADX OPTIMIZATION RESULTS ===== 🚀")
print(optimization_results)

print("\n🏆 BEST PARAMETERS:")
print(f"Gap Up Threshold (to short): {optimization_results._strategy.gap_threshold * 100:.1f}%")
print(f"ADX Period: {optimization_results._strategy.adx_period}")
print(f"ADX Threshold: {optimization_results._strategy.adx_threshold}")
print(f"Take Profit: {optimization_results._strategy.take_profit * 100:.1f}%")
print(f"Stop Loss: {optimization_results._strategy.stop_loss * 100:.1f}%")