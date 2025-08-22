import pandas as pd
import talib
from backtesting import Backtest, Strategy

print("🚀 Moon Dev's Gap Fade + Ultimate Indicators Strategy (Short Only) Loading... 🌙")

# Data configuration - Focusing on after-hours for gap fading
# Option 1: 1-hour data (500 weeks) - After-hours only (RECOMMENDED FOR SHORTS)
#DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data_inverse_gapped.csv'
# Option 2: 5-minute data (70 weeks) - After-hours only
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-5m-70wks-data_inverse_gapped.csv'
# Option 3: 1-hour data (500 weeks) - Market hours only
#DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data_gapped.csv'
# Option 4: 5-minute data (70 weeks) - Market hours only
#DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-5m-70wks-data_gapped.csv'

# Strategy parameters (configurable)
GAP_UP_PERCENT = 0.5  # Based on best long params, for shorting gap ups
GAP_DOWN_PERCENT = 1.0  # For potential bounce shorts after gap downs
TAKE_PROFIT_PERCENT = 5.0  # From best optimization
STOP_LOSS_PERCENT = 2.0

# Ultimate indicator parameters
UO_PERIOD1 = 7
UO_PERIOD2 = 14
UO_PERIOD3 = 28
UO_OVERSOLD = 25  # From best optimization
UO_OVERBOUGHT = 70

ADX_PERIOD = 14
ADX_THRESHOLD = 30  # From best optimization
ADX_STRONG = 40

MFI_PERIOD = 14
MFI_OVERSOLD = 35  # From best optimization
MFI_OVERBOUGHT = 70

print(f"📊 Loading gapped data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
# Ensure data is sorted in ascending order (oldest first)
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows of after-hours data 🌙")

class GapFadeUltimateStrategy(Strategy):
    gap_up_threshold = GAP_UP_PERCENT / 100
    gap_down_threshold = GAP_DOWN_PERCENT / 100
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
        
        # Gap is difference between current open and previous close
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
        if self.minus_di[-1] > self.plus_di[-1]:
            trend_score += 1  # Bearish (good for shorts)
        else:
            trend_score -= 1  # Bullish (bad for shorts)
        
        return trend_score
    
    def check_divergence(self):
        """Check for bearish divergence"""
        if len(self.data) < 20:
            return False
            
        # Price vs UO divergence
        price_change = (self.data.Close[-1] - self.data.Close[-10]) / self.data.Close[-10]
        uo_change = self.uo[-1] - self.uo[-10] if not pd.isna(self.uo[-1]) and not pd.isna(self.uo[-10]) else 0
        
        # Bearish divergence: price up, UO down
        return price_change > 0.01 and uo_change < -5
    
    def next(self):
        # Skip if not enough data
        if len(self.data) < max(self.uo_period3, self.adx_period, self.mfi_period):
            return
        
        # Skip if we have NaN values
        if (pd.isna(self.gap_percent[-1]) or 
            pd.isna(self.uo[-1]) or pd.isna(self.adx[-1]) or pd.isna(self.mfi[-1])):
            return
            
        # Check for gaps on any candle
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
            
            # Gap up signal for SHORTING (fade the gap in after-hours)
            gap_up_signal = current_gap > self.gap_up_threshold
            
            # After-hours gap fade scoring (opposite of long logic)
            short_score = sum([
                gap_up_signal * 3,                                   # Gap up to fade
                (current_uo > self.uo_overbought) * 2,              # UO overbought
                (current_mfi > self.mfi_overbought) * 1.5,          # MFI overbought
                (current_williams > -20) * 1,                        # Williams overbought
                (current_adx > self.adx_threshold) * 2,             # Trending (for reversal)
                (current_minus_di > current_plus_di) * 1.5,         # Bearish DI
                (current_price < current_sar) * 1,                  # Below SAR
                (current_cci > 100) * 1,                            # CCI overbought
                (current_volume_ratio < 0.8) * 1.5,                 # Low volume (weak gap)
                has_divergence * 3,                                 # Bearish divergence
                (trend_strength < 0) * 2                            # Weak/bearish trend
            ])
            
            # Need strong composite score for shorting
            if short_score >= 8:
                # Dynamic position sizing based on indicator confluence
                position_multiplier = 1.0
                
                if current_adx > self.adx_strong and trend_strength <= -1:
                    position_multiplier = self.trend_multiplier
                
                # Multi-factor stop loss calculation for shorts
                atr_multiplier = 2.5 if current_adx > self.adx_strong else 2.0
                
                # For short positions, stop loss must be above current price
                atr_stop = current_price + (current_atr * atr_multiplier) if current_atr > 0 else current_price * 1.02
                sar_stop = max(current_sar + (current_atr * 0.5) if current_atr > 0 else current_sar, current_price * 1.02)
                percent_stop = current_price * (1 + self.stop_loss)
                
                # Take the lowest valid stop that's still above current price
                valid_stops = [s for s in [atr_stop, sar_stop, percent_stop] if s > current_price]
                sl_price = min(valid_stops) if valid_stops else current_price * (1 + self.stop_loss)
                
                # Dynamic take profit based on conditions
                if short_score >= 12:
                    # Very strong signal: aim for bigger profits
                    tp_multiplier = 1.5
                elif current_mfi > 75 or current_uo > 75:
                    # Extreme overbought: expect reversal
                    tp_multiplier = 1.2
                else:
                    tp_multiplier = position_multiplier
                
                tp_price = current_price * (1 - self.take_profit * tp_multiplier)
                
                self.sell(sl=sl_price, tp=tp_price)

# Run backtest
bt = Backtest(data, GapFadeUltimateStrategy, cash=100000, commission=0.00045)

print("\n🌙 ===== GAP FADE + ULTIMATE (SHORT ONLY) - DEFAULT PARAMETERS ===== 🌙")
print(f"Gap Up Threshold (to short): {GAP_UP_PERCENT}%")
print(f"UO Periods: {UO_PERIOD1}/{UO_PERIOD2}/{UO_PERIOD3}")
print(f"ADX Period: {ADX_PERIOD}, Threshold: {ADX_THRESHOLD}")
print(f"MFI Period: {MFI_PERIOD}, Oversold: {MFI_OVERSOLD}")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")
stats_default = bt.run()
print(stats_default)

print("\n🚀 Optimizing Gap Fade Strategy...")
optimization_results = bt.optimize(
    gap_up_threshold=[i / 1000 for i in range(3, 21, 3)],      # 0.3% to 2%
    take_profit=[i / 1000 for i in range(30, 71, 10)],         # 3% to 7%
    stop_loss=[i / 1000 for i in range(10, 31, 5)],            # 1% to 3%
    uo_overbought=range(65, 81, 5),
    adx_threshold=range(20, 36, 5),
    mfi_overbought=range(65, 81, 5),
    maximize='Sortino Ratio',
    constraint=lambda p: p.take_profit > p.stop_loss
)

print("\n🚀 ===== GAP FADE OPTIMIZATION RESULTS ===== 🚀")
print(optimization_results)

print("\n🏆 BEST PARAMETERS:")
print(f"Gap Up Threshold (to short): {optimization_results._strategy.gap_up_threshold * 100:.1f}%")
print(f"UO Overbought: {optimization_results._strategy.uo_overbought}")
print(f"ADX Threshold: {optimization_results._strategy.adx_threshold}")
print(f"MFI Overbought: {optimization_results._strategy.mfi_overbought}")
print(f"Take Profit: {optimization_results._strategy.take_profit * 100:.1f}%")
print(f"Stop Loss: {optimization_results._strategy.stop_loss * 100:.1f}%")