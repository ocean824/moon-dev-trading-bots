'''
 ===== 1 HOURRRRR GAP + ULTIMATE INDICATORS - DEFAULT PARAMETERS ===== 🌙
Gap Up Threshold: 1.0%
UO Periods: 7/14/28
ADX Period: 14, Threshold: 25
MFI Period: 14, Oversold: 30
Take Profit: 2.5%
Stop Loss: 2.0%
Start                     2015-09-21 14:00:00
End                       2025-04-18 19:00:00
Duration                   3497 days 05:00:00
Exposure Time [%]                   44.874958
Equity Final [$]              58209164.581832
Equity Peak [$]                67552004.99024
Return [%]                       58109.164582
Buy & Hold Return [%]            36875.660311
Return (Ann.) [%]                    89.98142
Volatility (Ann.) [%]               86.924619
Sharpe Ratio                         1.035166
Sortino Ratio                        3.327941
Calmar Ratio                         1.859139
Max. Drawdown [%]                  -48.399513
Avg. Drawdown [%]                   -3.577805
Max. Drawdown Duration      507 days 22:00:00
Avg. Drawdown Duration       14 days 22:00:00
# Trades                                  746
Win Rate [%]                        56.836461
Best Trade [%]                      22.784747
Worst Trade [%]                    -24.495565
Avg. Trade [%]                          0.859
Max. Trade Duration          17 days 04:00:00
Avg. Trade Duration           1 days 20:00:00
Profit Factor                        1.627961
Expectancy [%]                       0.976755
SQN                                   2.96824
_strategy                 GapUltimateStrategy
_equity_curve                             ...
_trades                        Size  Entry...
dtype: object
🚀 Optimizing Gap + Ultimate Strategy...
/opt/anaconda3/envs/tflow/lib/python3.10/site-packages/backtesting/backtesting.py:1488: UserWarning: Searching for best of 4698 configurations.
  output = _optimize_grid()
/opt/anaconda3/envs/tflow/lib/python3.10/site-packages/backtesting/backtesting.py:1375: UserWarning: For multiprocessing support in `Backtest.optimize()` set multiprocessing start method to 'fork'.
  warnings.warn("For multiprocessing support in `Backtest.optimize()` "
🚀 ===== GAP + ULTIMATE OPTIMIZATION RESULTS ===== 🚀
Start                     2015-09-21 14:00:00
End                       2025-04-18 19:00:00
Duration                   3497 days 05:00:00
Exposure Time [%]                   57.225742
Equity Final [$]              323344527.32049
Equity Peak [$]               396614400.15203
Return [%]                       323244.52732
Buy & Hold Return [%]            36875.660311
Return (Ann.) [%]                  125.826178
Volatility (Ann.) [%]              117.258595
Sharpe Ratio                         1.073066
Sortino Ratio                        4.391558
Calmar Ratio                         2.392126
Max. Drawdown [%]                  -52.600155
Avg. Drawdown [%]                   -3.582057
Max. Drawdown Duration      732 days 23:00:00
Avg. Drawdown Duration       12 days 09:00:00
# Trades                                  576
Win Rate [%]                        46.527778
Best Trade [%]                      28.958835
Worst Trade [%]                    -20.261612
Avg. Trade [%]                       1.414585
Max. Trade Duration          43 days 22:00:00
Avg. Trade Duration           3 days 04:00:00
Profit Factor                        1.844214
Expectancy [%]                       1.615949
SQN                                  2.569512
_strategy                 GapUltimateStrat...
_equity_curve                             ...
_trades                        Size  Entry...
dtype: object
🏆 BEST PARAMETERS:
Gap Up Threshold: 0.5%
UO Oversold: 25
ADX Threshold: 30
MFI Oversold: 35
Take Profit: 5.0%
Stop Loss: 2.0%
'''
import pandas as pd
import talib
from backtesting import Backtest, Strategy
print("🚀 Moon Dev's Gap + Ultimate Indicators Strategy (Long Only) Loading... 🌙")
# Data configuration
# Option 1: 1-hour data (500 weeks) - Market hours only
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data_gapped.csv'
# Option 2: 5-minute data (70 weeks) - Market hours only
#DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-5m-70wks-data_gapped.csv'
# Option 3: 1-hour data (500 weeks) - After-hours only
#DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data_inverse_gapped.csv'
# Option 4: 5-minute data (70 weeks) - After-hours only
#DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-5m-70wks-data_inverse_gapped.csv'
# Strategy parameters (configurable)
GAP_UP_PERCENT = 1.0  # Based on best params from original
TAKE_PROFIT_PERCENT = 2.5
STOP_LOSS_PERCENT = 2.0
# Ultimate indicator parameters
UO_PERIOD1 = 7
UO_PERIOD2 = 14
UO_PERIOD3 = 28
UO_OVERSOLD = 30
UO_OVERBOUGHT = 70
ADX_PERIOD = 14
ADX_THRESHOLD = 25
ADX_STRONG = 40
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
class GapUltimateStrategy(Strategy):
    gap_threshold = GAP_UP_PERCENT / 100
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100
    # Ultimate Oscillator
    uo_period1 = UO_PERIOD1
    uo_period2 = UO_PERIOD2
    uo_period3 = UO_PERIOD3
    uo_oversold = UO_OVERSOLD
    uo_overbought = UO_OVERBOUGHT
    # ADX
    adx_period = ADX_PERIOD
    adx_threshold = ADX_THRESHOLD
    adx_strong = ADX_STRONG
    # MFI
    mfi_period = MFI_PERIOD
    mfi_oversold = MFI_OVERSOLD
    mfi_overbought = MFI_OVERBOUGHT
    # Risk multiplier
    trend_multiplier = 1.5
    def init(self):
        # Calculate gaps between candles
        close_values = pd.Series(self.data.Close)
        open_values = pd.Series(self.data.Open)
        self.prev_close = self.I(lambda: close_values.shift(1).values)
        self.gap_percent = self.I(lambda: (open_values.values - close_values.shift(1).values) / close_values.shift(1).values)
        # Ultimate Oscillator
        self.uo = self.I(talib.ULTOSC,
                        self.data.High,
                        self.data.Low,
                        self.data.Close,
                        self.uo_period1,
                        self.uo_period2,
                        self.uo_period3)
        # ADX and DI
        self.adx = self.I(talib.ADX,
                          self.data.High,
                          self.data.Low,
                          self.data.Close,
                          self.adx_period)
        self.plus_di = self.I(talib.PLUS_DI,
                              self.data.High,
                              self.data.Low,
                              self.data.Close,
                              self.adx_period)
        self.minus_di = self.I(talib.MINUS_DI,
                               self.data.High,
                               self.data.Low,
                               self.data.Close,
                               self.adx_period)
        # MFI
        self.mfi = self.I(talib.MFI,
                          self.data.High,
                          self.data.Low,
                          self.data.Close,
                          self.data.Volume,
                          self.mfi_period)
        # Williams %R
        self.williams = self.I(talib.WILLR,
                               self.data.High,
                               self.data.Low,
                               self.data.Close,
                               14)
        # SAR for trend
        self.sar = self.I(talib.SAR,
                          self.data.High,
                          self.data.Low,
                          acceleration=0.02,
                          maximum=0.2)
        # ATR for volatility
        self.atr = self.I(talib.ATR,
                          self.data.High,
                          self.data.Low,
                          self.data.Close,
                          14)
        # CCI for momentum
        self.cci = self.I(talib.CCI,
                          self.data.High,
                          self.data.Low,
                          self.data.Close,
                          20)
        # Volume analysis
        self.volume_ma = self.I(talib.SMA, self.data.Volume, 20)
        self.volume_ratio = self.I(lambda: self.data.Volume / self.volume_ma)
    def calculate_trend_strength(self):
        """Calculate overall trend strength score"""
        if pd.isna(self.adx[-1]) or pd.isna(self.plus_di[-1]) or pd.isna(self.minus_di[-1]):
            return 0
        trend_score = 0
        # ADX strength
        if self.adx[-1] > self.adx_strong:
            trend_score += 2
        elif self.adx[-1] > self.adx_threshold:
            trend_score += 1
        # DI direction
        if self.plus_di[-1] > self.minus_di[-1]:
            trend_score += 1  # Bullish
        else:
            trend_score -= 1  # Bearish
        return trend_score
    def check_divergence(self):
        """Check for bullish divergence"""
        if len(self.data) < 20:
            return False
        # Price vs UO divergence
        price_change = (self.data.Close[-1] - self.data.Close[-10]) / self.data.Close[-10]
        uo_change = self.uo[-1] - self.uo[-10] if not pd.isna(self.uo[-1]) and not pd.isna(self.uo[-10]) else 0
        # Bullish divergence: price down, UO up
        return price_change < -0.01 and uo_change > 5
    def next(self):
        # Skip if not enough data
        if len(self.data) < max(self.uo_period3, self.adx_period, self.mfi_period):
            return
        # Skip if we have NaN values
        if (pd.isna(self.gap_percent[-1])  or 
            pd.isna(self.uo[-1]) or pd.isna(self.adx[-1]) or pd.isna(self.mfi[-1])):
            return
        # Only trade at market open with gap up
        if not self.position:
            current_gap = self.gap_percent[-1]
            current_price = self.data.Close[-1]
            current_uo = self.uo[-1]
            current_adx = self.adx[-1]
            current_plus_di = self.plus_di[-1]
            current_minus_di = self.minus_di[-1]
            current_mfi = self.mfi[-1]
            current_williams = self.williams[-1] if not pd.isna(self.williams[-1]) else -50
            current_sar = self.sar[-1] if not pd.isna(self.sar[-1]) else current_price
            current_atr = self.atr[-1] if not pd.isna(self.atr[-1]) else 0
            current_cci = self.cci[-1] if not pd.isna(self.cci[-1]) else 0
            current_volume_ratio = self.volume_ratio[-1] if not pd.isna(self.volume_ratio[-1]) else 1
            # Calculate composite scores
            trend_strength = self.calculate_trend_strength()
            has_divergence = self.check_divergence()
            # Gap signal is primary
            gap_signal = current_gap > self.gap_threshold
            # Ultimate scoring system (Jim Simons approach)
            long_score = sum([
                gap_signal * 3,                                    # Gap is key
                (current_uo < self.uo_oversold) * 2,              # UO oversold
                (current_mfi < self.mfi_oversold) * 1.5,          # MFI oversold
                (current_williams < -80) * 1,                      # Williams oversold
                (current_adx > self.adx_threshold) * 2,           # Trending market
                (current_plus_di > current_minus_di) * 1.5,       # Bullish DI
                (current_price > current_sar) * 1,                # Above SAR
                (current_cci < -100) * 1,                         # CCI oversold
                (current_volume_ratio > 1.5) * 1.5,               # Volume surge
                has_divergence * 3,                               # Divergence bonus
                (trend_strength > 0) * 2                          # Trend strength
            ])
            # Need strong composite score (multiple confirmations)
            if long_score >= 8:
                # Dynamic position sizing based on indicator confluence
                position_multiplier = 1.0
                if current_adx > self.adx_strong and trend_strength >= 2:
                    position_multiplier = self.trend_multiplier
                # Multi-factor stop loss calculation
                atr_multiplier = 2.5 if current_adx > self.adx_strong else 2.0
                # Use multiple stop methods and take the lowest valid stop for long positions
                atr_stop = current_price - (current_atr * atr_multiplier) if current_atr > 0 else current_price * 0.98
                sar_stop = min(current_sar - (current_atr * 0.5) if current_atr > 0 else current_sar, current_price * 0.98)
                percent_stop = current_price * (1 - self.stop_loss)
                # For long positions, stop loss must be below current price
                # Take the highest valid stop that's still below current price
                valid_stops = [s for s in [atr_stop, sar_stop, percent_stop] if s < current_price and s > 0]
                sl_price = max(valid_stops) if valid_stops else current_price * (1 - self.stop_loss)
                # Dynamic take profit based on conditions
                if long_score >= 12:
                    # Very strong signal: aim higher
                    tp_multiplier = 1.5
                elif current_mfi < 25 or current_uo < 25:
                    # Extreme oversold: expect bounce
                    tp_multiplier = 1.2
                else:
                    tp_multiplier = position_multiplier
                tp_price = current_price * (1 + self.take_profit * tp_multiplier)
                self.buy(sl=sl_price, tp=tp_price)
# Run backtest
bt = Backtest(data, GapUltimateStrategy, cash=100000, commission=0.00045)
print("\n🌙 ===== GAP + ULTIMATE INDICATORS - DEFAULT PARAMETERS ===== 🌙")
print(f"Gap Up Threshold: {GAP_UP_PERCENT}%")
print(f"UO Periods: {UO_PERIOD1}/{UO_PERIOD2}/{UO_PERIOD3}")
print(f"ADX Period: {ADX_PERIOD}, Threshold: {ADX_THRESHOLD}")
print(f"MFI Period: {MFI_PERIOD}, Oversold: {MFI_OVERSOLD}")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")
stats_default = bt.run()
print(stats_default)
print("\n🚀 Optimizing Gap + Ultimate Strategy...")
optimization_results = bt.optimize(
    gap_threshold=[i / 1000 for i in range(5, 31, 5)],      # 0.5% to 3%
    take_profit=[i / 1000 for i in range(20, 51, 5)],       # 2% to 5%
    stop_loss=[i / 1000 for i in range(10, 31, 5)],         # 1% to 3%
    uo_oversold=range(25, 36, 5),
    adx_threshold=range(20, 31, 5),
    mfi_oversold=range(25, 36, 5),
    maximize='Sortino Ratio',
    constraint=lambda p: p.take_profit > p.stop_loss
)
print("\n🚀 ===== GAP + ULTIMATE OPTIMIZATION RESULTS ===== 🚀")
print(optimization_results)
print("\n🏆 BEST PARAMETERS:")
print(f"Gap Up Threshold: {optimization_results._strategy.gap_threshold * 100:.1f}%")
print(f"UO Oversold: {optimization_results._strategy.uo_oversold}")
print(f"ADX Threshold: {optimization_results._strategy.adx_threshold}")
print(f"MFI Oversold: {optimization_results._strategy.mfi_oversold}")
print(f"Take Profit: {optimization_results._strategy.take_profit * 100:.1f}%")
print(f"Stop Loss: {optimization_results._strategy.stop_loss * 100:.1f}%")