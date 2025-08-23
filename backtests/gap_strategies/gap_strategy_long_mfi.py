import pandas as pd
import talib
from backtesting import Backtest, Strategy
print("🚀 Moon Dev's Gap + MFI Strategy (Long Only) Loading... 🌙")
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
# MFI and momentum parameters
MFI_PERIOD = 14
MFI_OVERSOLD = 30
MFI_OVERBOUGHT = 70
print(f"📊 Loading gapped data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
# Ensure data is sorted in ascending order (oldest first)
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows of market hours data 🌙")
class GapMFIStrategy(Strategy):
    gap_threshold = GAP_UP_PERCENT / 100
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100
    mfi_period = MFI_PERIOD
    mfi_oversold = MFI_OVERSOLD
    mfi_overbought = MFI_OVERBOUGHT
    def init(self):
        # Calculate gaps between candles
        close_values = pd.Series(self.data.Close)
        open_values = pd.Series(self.data.Open)
        self.prev_close = self.I(lambda: close_values.shift(1).values)
        self.gap_percent = self.I(lambda: (open_values.values - close_values.shift(1).values) / close_values.shift(1).values)
        # Money Flow Index for volume-weighted momentum
        self.mfi = self.I(talib.MFI, 
                         self.data.High, 
                         self.data.Low, 
                         self.data.Close, 
                         self.data.Volume, 
                         self.mfi_period)
        # Williams %R for additional oversold/overbought
        self.williams = self.I(talib.WILLR,
                               self.data.High,
                               self.data.Low,
                               self.data.Close,
                               14)
        # Ultimate Oscillator for multi-timeframe momentum
        self.uo = self.I(talib.ULTOSC,
                        self.data.High,
                        self.data.Low,
                        self.data.Close,
                        7, 14, 28)
        # CCI for trend strength
        self.cci = self.I(talib.CCI,
                         self.data.High,
                         self.data.Low,
                         self.data.Close,
                         20)
        # Volume analysis
        self.volume_ma = self.I(talib.SMA, self.data.Volume, 20)
        self.volume_ratio = self.I(lambda: self.data.Volume / self.volume_ma)
        # ATR for dynamic stops
        self.atr = self.I(talib.ATR, self.data.High, self.data.Low, self.data.Close, 14)
    def calculate_money_flow_strength(self):
        """Calculate composite money flow score"""
        if pd.isna(self.mfi[-1]):
            return 0
        score = 0
        # MFI position
        current_mfi = self.mfi[-1]
        if current_mfi < self.mfi_oversold:
            score += 2  # Oversold
        elif current_mfi < 50:
            score += 1  # Below neutral
        elif current_mfi > self.mfi_overbought:
            score -= 1  # Overbought warning
        # MFI momentum (compare to recent values)
        if len(self.mfi) >= 5:
            mfi_momentum = current_mfi - self.mfi[-5]
            if mfi_momentum > 10:
                score += 2  # Strong positive momentum
            elif mfi_momentum > 0:
                score += 1  # Positive momentum
        return score
    def next(self):
        if len(self.data) < max(2, self.mfi_period, 28):
            return
        if pd.isna(self.gap_percent[-1])  or pd.isna(self.mfi[-1]):
            return
        # Only trade at market open with gap up
        if not self.position:
            current_gap = self.gap_percent[-1]
            current_price = self.data.Close[-1]
            current_mfi = self.mfi[-1]
            current_williams = self.williams[-1] if not pd.isna(self.williams[-1]) else -50
            current_uo = self.uo[-1] if not pd.isna(self.uo[-1]) else 50
            current_cci = self.cci[-1] if not pd.isna(self.cci[-1]) else 0
            current_volume_ratio = self.volume_ratio[-1] if not pd.isna(self.volume_ratio[-1]) else 1
            current_atr = self.atr[-1] if not pd.isna(self.atr[-1]) else 0
            # Gap up signal
            gap_signal = current_gap > self.gap_threshold
            # Money flow analysis
            mf_score = self.calculate_money_flow_strength()
            mfi_bullish = mf_score > 0
            # Additional confirmations
            williams_oversold = current_williams < -70
            uo_oversold = current_uo < 35
            cci_oversold = current_cci < -100
            volume_surge = current_volume_ratio > 1.3
            # Scoring system for entry (Jim Simons style - multiple weak signals)
            entry_score = sum([
                gap_signal * 3,           # Gap is primary signal
                mfi_bullish * 2,          # Money flow confirmation
                williams_oversold * 1,     # Oversold conditions
                uo_oversold * 1,
                cci_oversold * 1,
                volume_surge * 2          # Volume confirms interest
            ])
            # Need strong composite score for entry
            if entry_score >= 6:
                # Dynamic position sizing based on MFI
                if current_mfi < 25:
                    # Very oversold: aggressive positioning
                    sl_multiplier = 1.2
                    tp_multiplier = 1.5
                elif current_mfi < self.mfi_oversold:
                    # Oversold: normal positioning  
                    sl_multiplier = 1.0
                    tp_multiplier = 1.2
                else:
                    # Normal conditions
                    sl_multiplier = 1.0
                    tp_multiplier = 1.0
                # ATR-based stops
                atr_stop = current_price - (current_atr * 2.0) if current_atr > 0 else current_price * 0.98
                percent_stop = current_price * (1 - self.stop_loss * sl_multiplier)
                sl_price = max(atr_stop, percent_stop)
                tp_price = current_price * (1 + self.take_profit * tp_multiplier)
                self.buy(sl=sl_price, tp=tp_price)
# Run backtest
bt = Backtest(data, GapMFIStrategy, cash=100000, commission=0.00045)
print("\n🌙 ===== GAP + MFI STRATEGY - DEFAULT PARAMETERS ===== 🌙")
print(f"Gap Up Threshold: {GAP_UP_PERCENT}%")
print(f"MFI Period: {MFI_PERIOD}")
print(f"MFI Oversold: {MFI_OVERSOLD}")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")
stats_default = bt.run()
print(stats_default)
print("\n🚀 Optimizing Gap + MFI Strategy...")
optimization_results = bt.optimize(
    gap_threshold=[i / 1000 for i in range(5, 31, 5)],      # 0.5% to 3%
    take_profit=[i / 1000 for i in range(20, 51, 5)],       # 2% to 5%
    stop_loss=[i / 1000 for i in range(10, 31, 5)],         # 1% to 3%
    mfi_period=range(10, 21, 5),
    mfi_oversold=range(20, 41, 10),
    maximize='Sortino Ratio',
    constraint=lambda p: p.take_profit > p.stop_loss
)
print("\n🚀 ===== GAP + MFI OPTIMIZATION RESULTS ===== 🚀")
print(optimization_results)
print("\n🏆 BEST PARAMETERS:")
print(f"Gap Up Threshold: {optimization_results._strategy.gap_threshold * 100:.1f}%")
print(f"MFI Period: {optimization_results._strategy.mfi_period}")
print(f"MFI Oversold: {optimization_results._strategy.mfi_oversold}")
print(f"Take Profit: {optimization_results._strategy.take_profit * 100:.1f}%")
print(f"Stop Loss: {optimization_results._strategy.stop_loss * 100:.1f}%")