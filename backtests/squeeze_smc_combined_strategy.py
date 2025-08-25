#!/usr/bin/env python3
"""
Combined Squeeze Momentum + Smart Money Concepts Strategy
==========================================================

This strategy combines the best of both worlds:
- Squeeze Momentum for timing (when to enter)
- Smart Money Concepts for location (where to enter)

Strategy Logic:
- Use Squeeze OFF condition for momentum confirmation
- Use SMC order blocks and FVGs for precise entry locations
- Require confluence from both indicators
- Long: Squeeze OFF + bullish momentum + at bullish order block
- Short: Squeeze OFF + bearish momentum + at bearish order block
- Exit when either indicator signals reversal
"""

import pandas as pd
import numpy as np
import pandas_ta as ta
from backtesting import Strategy
import warnings
warnings.filterwarnings('ignore')

print("Initializing Combined Squeeze + SMC Strategy...")

class SqueezeSMCCombined(Strategy):
    # Squeeze parameters
    bb_period = 20
    bb_mult = 2.0
    kc_period = 20
    kc_mult = 1.5
    mom_period = 12
    
    # SMC parameters
    swing_lookback = 50
    order_block_lookback = 10
    fvg_min_gap = 0.001
    
    # Risk management
    take_profit = 0.04  # 4% TP
    stop_loss = 0.02    # 2% SL
    
    def init(self):
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        open_price = pd.Series(self.data.Open)
        
        # ============= SQUEEZE MOMENTUM INDICATORS =============
        
        # Bollinger Bands
        bb = ta.bbands(close, length=self.bb_period, std=self.bb_mult)
        if bb is not None and not bb.empty:
            self.bb_upper = self.I(lambda: bb[f'BBU_{self.bb_period}_{self.bb_mult}'].values)
            self.bb_lower = self.I(lambda: bb[f'BBL_{self.bb_period}_{self.bb_mult}'].values)
        else:
            sma = close.rolling(self.bb_period).mean()
            std = close.rolling(self.bb_period).std()
            self.bb_upper = self.I(lambda: (sma + self.bb_mult * std).values)
            self.bb_lower = self.I(lambda: (sma - self.bb_mult * std).values)
        
        # Keltner Channels
        ema = close.ewm(span=self.kc_period, adjust=False).mean()
        tr = pd.DataFrame({
            'h-l': high - low,
            'h-c': (high - close.shift()).abs(),
            'l-c': (low - close.shift()).abs()
        }).max(axis=1)
        atr = tr.rolling(self.kc_period).mean()
        
        self.kc_upper = self.I(lambda: (ema + self.kc_mult * atr).values)
        self.kc_lower = self.I(lambda: (ema - self.kc_mult * atr).values)
        
        # Squeeze detection
        def detect_squeeze(bb_upper, bb_lower, kc_upper, kc_lower):
            squeeze_on = (bb_lower > kc_lower) & (bb_upper < kc_upper)
            return squeeze_on.astype(float)
        
        self.squeeze = self.I(detect_squeeze, 
                            self.bb_upper, self.bb_lower,
                            self.kc_upper, self.kc_lower)
        
        # Momentum calculation
        def calculate_momentum(close, high, low, period):
            highest = high.rolling(period).max()
            lowest = low.rolling(period).min()
            sma = close.rolling(period).mean()
            source = close - ((highest + lowest) / 2 + sma) / 2
            
            momentum = np.zeros(len(source))
            for i in range(period, len(source)):
                y = source[i-period+1:i+1].values
                x = np.arange(period)
                if len(y) == period and not np.isnan(y).any():
                    x_mean = x.mean()
                    y_mean = y.mean()
                    num = ((x - x_mean) * (y - y_mean)).sum()
                    den = ((x - x_mean) ** 2).sum()
                    if den != 0:
                        momentum[i] = num / den
            return momentum
        
        self.momentum = self.I(calculate_momentum, close, high, low, self.mom_period)
        
        # Momentum direction
        def momentum_direction(momentum):
            direction = np.zeros(len(momentum))
            for i in range(1, len(momentum)):
                if momentum[i] > 0 and momentum[i] > momentum[i-1]:
                    direction[i] = 2  # Strong bullish
                elif momentum[i] > 0:
                    direction[i] = 1  # Weak bullish
                elif momentum[i] < 0 and momentum[i] < momentum[i-1]:
                    direction[i] = -2  # Strong bearish
                elif momentum[i] < 0:
                    direction[i] = -1  # Weak bearish
            return direction
        
        self.mom_direction = self.I(momentum_direction, self.momentum)
        
        # ============= SMART MONEY CONCEPTS =============
        
        # Swing detection
        def detect_swings(high, low, lookback):
            swing_highs = np.zeros(len(high))
            swing_lows = np.zeros(len(low))
            
            for i in range(lookback, len(high) - lookback):
                if high[i] == high[i-lookback:i+lookback+1].max():
                    swing_highs[i] = high[i]
                if low[i] == low[i-lookback:i+lookback+1].min():
                    swing_lows[i] = low[i]
            
            return swing_highs, swing_lows
        
        swing_highs, swing_lows = detect_swings(high.values, low.values, self.swing_lookback // 2)
        self.swing_highs = self.I(lambda: swing_highs)
        self.swing_lows = self.I(lambda: swing_lows)
        
        # Structure breaks
        def detect_structure_breaks(close, swing_highs, swing_lows):
            bos_bull = np.zeros(len(close))
            bos_bear = np.zeros(len(close))
            
            last_high = 0
            last_low = float('inf')
            
            for i in range(1, len(close)):
                if swing_highs[i] > 0:
                    last_high = swing_highs[i]
                if swing_lows[i] > 0:
                    last_low = swing_lows[i]
                
                if close[i] > last_high and last_high > 0:
                    bos_bull[i] = 1
                elif close[i] < last_low and last_low < float('inf'):
                    bos_bear[i] = 1
            
            return bos_bull, bos_bear
        
        bos_bull, bos_bear = detect_structure_breaks(close.values, swing_highs, swing_lows)
        self.bos_bull = self.I(lambda: bos_bull)
        self.bos_bear = self.I(lambda: bos_bear)
        
        # Order blocks
        def detect_order_blocks(open_price, close, high, low, bos_bull, bos_bear, lookback):
            bull_ob_zones = np.zeros(len(close))
            bear_ob_zones = np.zeros(len(close))
            
            for i in range(lookback, len(close)):
                # Track order block zones
                if bos_bull[i] > 0:
                    # Find last down candle
                    for j in range(i-1, max(0, i-lookback), -1):
                        if close[j] < open_price[j]:
                            # Mark zone from this candle's low to high
                            for k in range(i, min(len(close), i+50)):
                                bull_ob_zones[k] = (high[j] + low[j]) / 2
                            break
                
                if bos_bear[i] > 0:
                    # Find last up candle
                    for j in range(i-1, max(0, i-lookback), -1):
                        if close[j] > open_price[j]:
                            # Mark zone from this candle's low to high
                            for k in range(i, min(len(close), i+50)):
                                bear_ob_zones[k] = (high[j] + low[j]) / 2
                            break
            
            return bull_ob_zones, bear_ob_zones
        
        bull_ob_zones, bear_ob_zones = detect_order_blocks(
            open_price.values, close.values, high.values, low.values,
            bos_bull, bos_bear, self.order_block_lookback
        )
        
        self.bull_ob_zones = self.I(lambda: bull_ob_zones)
        self.bear_ob_zones = self.I(lambda: bear_ob_zones)
        
        # Fair Value Gaps
        def detect_fvg(high, low, min_gap):
            bull_fvg = np.zeros(len(high))
            bear_fvg = np.zeros(len(high))
            
            for i in range(2, len(high)):
                # Bullish FVG
                if low[i] > high[i-2]:
                    gap_size = (low[i] - high[i-2]) / high[i-2]
                    if gap_size > min_gap:
                        # Mark FVG zone for next 20 bars
                        for k in range(i, min(len(high), i+20)):
                            bull_fvg[k] = (low[i] + high[i-2]) / 2
                
                # Bearish FVG
                if high[i] < low[i-2]:
                    gap_size = (low[i-2] - high[i]) / low[i-2]
                    if gap_size > min_gap:
                        # Mark FVG zone for next 20 bars
                        for k in range(i, min(len(high), i+20)):
                            bear_fvg[k] = (high[i] + low[i-2]) / 2
            
            return bull_fvg, bear_fvg
        
        bull_fvg, bear_fvg = detect_fvg(high.values, low.values, self.fvg_min_gap)
        self.bull_fvg = self.I(lambda: bull_fvg)
        self.bear_fvg = self.I(lambda: bear_fvg)
        
        # Track entry
        self.entry_price = None
        self.position_type = None
    
    def next(self):
        # Skip if not enough data
        if len(self.data) < max(self.swing_lookback, self.kc_period + self.mom_period):
            return
        
        current_price = self.data.Close[-1]
        current_low = self.data.Low[-1]
        current_high = self.data.High[-1]
        
        # Get indicator values
        squeeze_on = self.squeeze[-1] > 0
        momentum = self.momentum[-1]
        mom_dir = self.mom_direction[-1]
        
        bull_ob_level = self.bull_ob_zones[-1]
        bear_ob_level = self.bear_ob_zones[-1]
        bull_fvg_level = self.bull_fvg[-1]
        bear_fvg_level = self.bear_fvg[-1]
        
        # Check for recent structure breaks
        recent_bull_break = any(self.bos_bull[-10:] > 0) if len(self.bos_bull) >= 10 else False
        recent_bear_break = any(self.bos_bear[-10:] > 0) if len(self.bos_bear) >= 10 else False
        
        # Position management
        if self.position:
            if self.position_type == 'long':
                # Exit conditions
                if current_price >= self.entry_price * (1 + self.take_profit):
                    self.position.close()
                    self.entry_price = None
                    self.position_type = None
                elif current_price <= self.entry_price * (1 - self.stop_loss):
                    self.position.close()
                    self.entry_price = None
                    self.position_type = None
                # Exit on reversal signals
                elif momentum < 0 or mom_dir < 0 or recent_bear_break:
                    self.position.close()
                    self.entry_price = None
                    self.position_type = None
            
            elif self.position_type == 'short':
                # Exit conditions
                if current_price <= self.entry_price * (1 - self.take_profit):
                    self.position.close()
                    self.entry_price = None
                    self.position_type = None
                elif current_price >= self.entry_price * (1 + self.stop_loss):
                    self.position.close()
                    self.entry_price = None
                    self.position_type = None
                # Exit on reversal signals
                elif momentum > 0 or mom_dir > 0 or recent_bull_break:
                    self.position.close()
                    self.entry_price = None
                    self.position_type = None
        
        else:
            # Entry logic - Require confluence from both systems
            
            # Long entry conditions
            long_squeeze = not squeeze_on and momentum > 0 and mom_dir >= 1
            long_smc = (bull_ob_level > 0 and abs(current_low - bull_ob_level) / bull_ob_level < 0.02) or \
                      (bull_fvg_level > 0 and abs(current_low - bull_fvg_level) / bull_fvg_level < 0.02)
            long_structure = recent_bull_break
            
            if long_squeeze and long_smc and long_structure:
                # Strong confluence for long entry
                self.buy()
                self.entry_price = current_price
                self.position_type = 'long'
            
            # Short entry conditions
            short_squeeze = not squeeze_on and momentum < 0 and mom_dir <= -1
            short_smc = (bear_ob_level > 0 and abs(current_high - bear_ob_level) / bear_ob_level < 0.02) or \
                       (bear_fvg_level > 0 and abs(current_high - bear_fvg_level) / bear_fvg_level < 0.02)
            short_structure = recent_bear_break
            
            if short_squeeze and short_smc and short_structure:
                # Strong confluence for short entry
                self.sell()
                self.entry_price = current_price
                self.position_type = 'short'


# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING COMBINED SQUEEZE + SMC STRATEGY ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    
    # Test with single data source first
    from backtesting import Backtest
    
    # Load sample data
    data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'
    
    if os.path.exists(data_path):
        data = pd.read_csv(data_path, parse_dates=['datetime'], index_col='datetime')
        data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        data = data.dropna()
        
        print(f"\nTesting on BTC hourly data...")
        print(f"Data shape: {data.shape}")
        
        # Run backtest
        bt = Backtest(data, SqueezeSMCCombined, cash=10000, commission=0.00045)
        stats = bt.run()
        
        print("\n" + "="*50)
        print("BACKTEST RESULTS - SQUEEZE + SMC COMBINED")
        print("="*50)
        print(stats)
        
        # Show plot
        #bt.plot()
    
    # Test on all data sources
    print("\n" + "="*80)
    print("RUNNING MULTI-DATA TEST")
    print("="*80)
    
    from multi_data_tester import test_on_all_data
    
    results = test_on_all_data(SqueezeSMCCombined, 'SqueezeSMCCombined')
    
    if results is not None:
        print("\nTesting complete! Results saved in: ./results/SqueezeSMCCombined.csv")