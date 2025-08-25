#!/usr/bin/env python3
"""
Smart Money Concepts (SMC) Trading Strategy
============================================

This strategy implements simplified Smart Money Concepts including:
- Swing structure detection (highs/lows)
- Break of Structure (BOS) and Change of Character (CHoCH)
- Order Blocks (last candle before structure break)
- Fair Value Gaps (imbalance zones)

Strategy Logic:
- Detect market structure using swing highs/lows
- Identify BOS/CHoCH for trend confirmation
- Find Order Blocks as potential entry zones
- Use Fair Value Gaps for additional confluence
- Enter at order blocks with structure confirmation
"""

import pandas as pd
import numpy as np
import pandas_ta as ta
from backtesting import Strategy
import warnings
warnings.filterwarnings('ignore')

print("Initializing Smart Money Concepts Strategy...")

class SmartMoneyConcepts(Strategy):
    # SMC parameters
    swing_lookback = 50  # Period to identify swing points
    order_block_lookback = 10  # Candles to look back for order blocks
    fvg_min_gap = 0.001  # Minimum gap size (0.1%)
    
    # Risk management
    take_profit = 0.04  # 4% TP
    stop_loss = 0.02    # 2% SL
    
    def init(self):
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        open_price = pd.Series(self.data.Open)
        
        # Detect swing highs and lows
        def detect_swings(high, low, lookback):
            swing_highs = np.zeros(len(high))
            swing_lows = np.zeros(len(low))
            
            for i in range(lookback, len(high) - lookback):
                # Swing high: highest point in range
                if high[i] == high[i-lookback:i+lookback+1].max():
                    swing_highs[i] = high[i]
                
                # Swing low: lowest point in range
                if low[i] == low[i-lookback:i+lookback+1].min():
                    swing_lows[i] = low[i]
            
            return swing_highs, swing_lows
        
        swing_highs, swing_lows = detect_swings(high.values, low.values, self.swing_lookback // 2)
        self.swing_highs = self.I(lambda: swing_highs)
        self.swing_lows = self.I(lambda: swing_lows)
        
        # Detect Break of Structure (BOS) and Change of Character (CHoCH)
        def detect_structure_breaks(close, swing_highs, swing_lows):
            bos_bull = np.zeros(len(close))
            bos_bear = np.zeros(len(close))
            choch = np.zeros(len(close))
            
            last_high = 0
            last_low = float('inf')
            trend = 0  # 1 for bullish, -1 for bearish, 0 for neutral
            
            for i in range(1, len(close)):
                # Update last swing points
                if swing_highs[i] > 0:
                    last_high = swing_highs[i]
                if swing_lows[i] > 0:
                    last_low = swing_lows[i]
                
                # Bullish BOS: Break above last high in uptrend
                if close[i] > last_high and trend >= 0:
                    bos_bull[i] = 1
                    trend = 1
                
                # Bearish BOS: Break below last low in downtrend
                elif close[i] < last_low and trend <= 0:
                    bos_bear[i] = 1
                    trend = -1
                
                # CHoCH: Break against the trend
                elif close[i] > last_high and trend < 0:
                    choch[i] = 1  # Bullish CHoCH
                    trend = 1
                elif close[i] < last_low and trend > 0:
                    choch[i] = -1  # Bearish CHoCH
                    trend = -1
            
            return bos_bull, bos_bear, choch
        
        bos_bull, bos_bear, choch = detect_structure_breaks(
            close.values, swing_highs, swing_lows
        )
        self.bos_bull = self.I(lambda: bos_bull)
        self.bos_bear = self.I(lambda: bos_bear)
        self.choch = self.I(lambda: choch)
        
        # Detect Order Blocks (last candle before structure break)
        def detect_order_blocks(open_price, close, high, low, bos_bull, bos_bear, lookback):
            bull_ob = np.zeros(len(close))
            bear_ob = np.zeros(len(close))
            bull_ob_high = np.zeros(len(close))
            bull_ob_low = np.zeros(len(close))
            bear_ob_high = np.zeros(len(close))
            bear_ob_low = np.zeros(len(close))
            
            for i in range(lookback, len(close)):
                # Bullish order block: Last down candle before bullish break
                if bos_bull[i] > 0:
                    for j in range(i-1, max(0, i-lookback), -1):
                        if close[j] < open_price[j]:  # Down candle
                            bull_ob[i] = 1
                            bull_ob_high[i] = high[j]
                            bull_ob_low[i] = low[j]
                            break
                
                # Bearish order block: Last up candle before bearish break
                if bos_bear[i] > 0:
                    for j in range(i-1, max(0, i-lookback), -1):
                        if close[j] > open_price[j]:  # Up candle
                            bear_ob[i] = 1
                            bear_ob_high[i] = high[j]
                            bear_ob_low[i] = low[j]
                            break
            
            return bull_ob, bear_ob, bull_ob_high, bull_ob_low, bear_ob_high, bear_ob_low
        
        bull_ob, bear_ob, bull_ob_high, bull_ob_low, bear_ob_high, bear_ob_low = detect_order_blocks(
            open_price.values, close.values, high.values, low.values,
            bos_bull, bos_bear, self.order_block_lookback
        )
        
        self.bull_ob = self.I(lambda: bull_ob)
        self.bear_ob = self.I(lambda: bear_ob)
        self.bull_ob_high = self.I(lambda: bull_ob_high)
        self.bull_ob_low = self.I(lambda: bull_ob_low)
        self.bear_ob_high = self.I(lambda: bear_ob_high)
        self.bear_ob_low = self.I(lambda: bear_ob_low)
        
        # Detect Fair Value Gaps (FVG)
        def detect_fvg(open_price, close, high, low, min_gap):
            bull_fvg = np.zeros(len(close))
            bear_fvg = np.zeros(len(close))
            
            for i in range(2, len(close)):
                # Bullish FVG: Gap between previous high and current low
                if low[i] > high[i-2]:
                    gap_size = (low[i] - high[i-2]) / high[i-2]
                    if gap_size > min_gap:
                        bull_fvg[i] = 1
                
                # Bearish FVG: Gap between previous low and current high
                if high[i] < low[i-2]:
                    gap_size = (low[i-2] - high[i]) / low[i-2]
                    if gap_size > min_gap:
                        bear_fvg[i] = 1
            
            return bull_fvg, bear_fvg
        
        bull_fvg, bear_fvg = detect_fvg(
            open_price.values, close.values, high.values, low.values, self.fvg_min_gap
        )
        self.bull_fvg = self.I(lambda: bull_fvg)
        self.bear_fvg = self.I(lambda: bear_fvg)
        
        # Track recent order block levels
        self.recent_bull_ob_level = self.I(lambda: self._track_ob_levels(bull_ob_high, bull_ob_low, 'bull'))
        self.recent_bear_ob_level = self.I(lambda: self._track_ob_levels(bear_ob_high, bear_ob_low, 'bear'))
        
        # Track entry
        self.entry_price = None
        self.position_type = None
    
    def _track_ob_levels(self, ob_high, ob_low, ob_type):
        """Track the most recent order block levels"""
        levels = np.zeros(len(ob_high))
        last_high = 0
        last_low = 0
        
        for i in range(len(ob_high)):
            if ob_high[i] > 0:
                last_high = ob_high[i]
                last_low = ob_low[i]
            
            if ob_type == 'bull':
                # For bullish OB, we care about the low (support)
                levels[i] = last_low if last_low > 0 else 0
            else:
                # For bearish OB, we care about the high (resistance)
                levels[i] = last_high if last_high > 0 else 0
        
        return levels
    
    def next(self):
        # Skip if not enough data
        if len(self.data) < self.swing_lookback * 2:
            return
        
        current_price = self.data.Close[-1]
        current_low = self.data.Low[-1]
        current_high = self.data.High[-1]
        
        # Check if we have a position
        if self.position:
            # Exit logic
            if self.position_type == 'long':
                # Take profit
                if current_price >= self.entry_price * (1 + self.take_profit):
                    self.position.close()
                    self.entry_price = None
                    self.position_type = None
                # Stop loss
                elif current_price <= self.entry_price * (1 - self.stop_loss):
                    self.position.close()
                    self.entry_price = None
                    self.position_type = None
                # Structure break in opposite direction
                elif self.bos_bear[-1] > 0 or self.choch[-1] < 0:
                    self.position.close()
                    self.entry_price = None
                    self.position_type = None
            
            elif self.position_type == 'short':
                # Take profit
                if current_price <= self.entry_price * (1 - self.take_profit):
                    self.position.close()
                    self.entry_price = None
                    self.position_type = None
                # Stop loss
                elif current_price >= self.entry_price * (1 + self.stop_loss):
                    self.position.close()
                    self.entry_price = None
                    self.position_type = None
                # Structure break in opposite direction
                elif self.bos_bull[-1] > 0 or self.choch[-1] > 0:
                    self.position.close()
                    self.entry_price = None
                    self.position_type = None
        
        else:
            # Entry logic
            
            # Check for recent structure breaks (within last 10 bars)
            recent_bos_bull = any(self.bos_bull[-10:] > 0) if len(self.bos_bull) >= 10 else False
            recent_bos_bear = any(self.bos_bear[-10:] > 0) if len(self.bos_bear) >= 10 else False
            recent_bull_choch = any(self.choch[-10:] > 0) if len(self.choch) >= 10 else False
            recent_bear_choch = any(self.choch[-10:] < 0) if len(self.choch) >= 10 else False
            
            # Get recent order block levels
            bull_ob_level = self.recent_bull_ob_level[-1] if len(self.recent_bull_ob_level) > 0 else 0
            bear_ob_level = self.recent_bear_ob_level[-1] if len(self.recent_bear_ob_level) > 0 else 0
            
            # Check for FVG support/resistance
            has_bull_fvg = any(self.bull_fvg[-5:] > 0) if len(self.bull_fvg) >= 5 else False
            has_bear_fvg = any(self.bear_fvg[-5:] > 0) if len(self.bear_fvg) >= 5 else False
            
            # Long entry conditions
            if (recent_bos_bull or recent_bull_choch) and bull_ob_level > 0:
                # Price at or near bullish order block
                if current_low <= bull_ob_level * 1.01:  # Within 1% of OB level
                    # Additional confluence with FVG
                    if has_bull_fvg or not has_bear_fvg:
                        self.buy()
                        self.entry_price = current_price
                        self.position_type = 'long'
            
            # Short entry conditions
            elif (recent_bos_bear or recent_bear_choch) and bear_ob_level > 0:
                # Price at or near bearish order block
                if current_high >= bear_ob_level * 0.99:  # Within 1% of OB level
                    # Additional confluence with FVG
                    if has_bear_fvg or not has_bull_fvg:
                        self.sell()
                        self.entry_price = current_price
                        self.position_type = 'short'


# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING SMART MONEY CONCEPTS STRATEGY ON ALL DATA SOURCES")
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
        bt = Backtest(data, SmartMoneyConcepts, cash=10000, commission=0.00045)
        stats = bt.run()
        
        print("\n" + "="*50)
        print("BACKTEST RESULTS - SMART MONEY CONCEPTS")
        print("="*50)
        print(stats)
        
        # Show plot
        bt.plot()
    
    # Test on all data sources
    print("\n" + "="*80)
    print("RUNNING MULTI-DATA TEST")
    print("="*80)
    
    from multi_data_tester import test_on_all_data
    
    results = test_on_all_data(SmartMoneyConcepts, 'SmartMoneyConcepts')
    
    if results is not None:
        print("\nTesting complete! Results saved in: ./results/SmartMoneyConcepts.csv")