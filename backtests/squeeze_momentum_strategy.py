#!/usr/bin/env python3
"""
LazyBear's Squeeze Momentum Indicator Strategy
===============================================

This strategy implements the famous Squeeze Momentum indicator which combines
Bollinger Bands and Keltner Channels to identify squeeze conditions and
momentum breakouts.

Strategy Logic:
- Squeeze ON: When Bollinger Bands are inside Keltner Channels (low volatility)
- Squeeze OFF: When Bollinger Bands break outside Keltner Channels
- Momentum calculated via linear regression of price difference from baseline
- Long Entry: Squeeze OFF + positive and increasing momentum
- Short Entry: Squeeze OFF + negative and decreasing momentum
- Exit: Momentum reversal or opposite signal
"""

import pandas as pd
import numpy as np
import pandas_ta as ta
from backtesting import Strategy
import warnings
warnings.filterwarnings('ignore')

print("Initializing LazyBear's Squeeze Momentum Strategy...")

class SqueezeMomentum(Strategy):
    # Squeeze parameters
    bb_period = 20
    bb_mult = 2.0
    kc_period = 20
    kc_mult = 1.5
    mom_period = 12
    
    # Risk management
    take_profit = 0.04  # 4% TP
    stop_loss = 0.02    # 2% SL
    
    def init(self):
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        
        # Calculate Bollinger Bands
        bb = ta.bbands(close, length=self.bb_period, std=self.bb_mult)
        if bb is not None and not bb.empty:
            self.bb_upper = self.I(lambda: bb[f'BBU_{self.bb_period}_{self.bb_mult}'].values)
            self.bb_lower = self.I(lambda: bb[f'BBL_{self.bb_period}_{self.bb_mult}'].values)
            self.bb_middle = self.I(lambda: bb[f'BBM_{self.bb_period}_{self.bb_mult}'].values)
        else:
            # Fallback calculation
            sma = close.rolling(self.bb_period).mean()
            std = close.rolling(self.bb_period).std()
            self.bb_upper = self.I(lambda: (sma + self.bb_mult * std).values)
            self.bb_lower = self.I(lambda: (sma - self.bb_mult * std).values)
            self.bb_middle = self.I(lambda: sma.values)
        
        # Calculate Keltner Channels
        ema = close.ewm(span=self.kc_period, adjust=False).mean()
        tr = pd.DataFrame({
            'h-l': high - low,
            'h-c': (high - close.shift()).abs(),
            'l-c': (low - close.shift()).abs()
        }).max(axis=1)
        atr = tr.rolling(self.kc_period).mean()
        
        self.kc_upper = self.I(lambda: (ema + self.kc_mult * atr).values)
        self.kc_lower = self.I(lambda: (ema - self.kc_mult * atr).values)
        self.kc_middle = self.I(lambda: ema.values)
        
        # Detect squeeze condition
        def detect_squeeze(bb_upper, bb_lower, kc_upper, kc_lower):
            # Squeeze is ON when BB is inside KC
            squeeze_on = (bb_lower > kc_lower) & (bb_upper < kc_upper)
            return squeeze_on.astype(float)
        
        self.squeeze = self.I(detect_squeeze, 
                            self.bb_upper, self.bb_lower,
                            self.kc_upper, self.kc_lower)
        
        # Calculate momentum using linear regression
        def calculate_momentum(close, high, low, period):
            # LazyBear's momentum calculation
            highest = high.rolling(period).max()
            lowest = low.rolling(period).min()
            sma = close.rolling(period).mean()
            
            # Source for momentum calculation
            source = close - ((highest + lowest) / 2 + sma) / 2
            
            # Linear regression of source
            momentum = np.zeros(len(source))
            for i in range(period, len(source)):
                y = source[i-period+1:i+1].values
                x = np.arange(period)
                if len(y) == period and not np.isnan(y).any():
                    # Calculate linear regression
                    x_mean = x.mean()
                    y_mean = y.mean()
                    num = ((x - x_mean) * (y - y_mean)).sum()
                    den = ((x - x_mean) ** 2).sum()
                    if den != 0:
                        momentum[i] = num / den
            
            return momentum
        
        self.momentum = self.I(calculate_momentum, close, high, low, self.mom_period)
        
        # Track momentum direction
        def momentum_color(momentum):
            colors = np.zeros(len(momentum))
            for i in range(1, len(momentum)):
                if momentum[i] > 0:
                    if momentum[i] > momentum[i-1]:
                        colors[i] = 2  # Lime - increasing bullish
                    else:
                        colors[i] = 1  # Green - decreasing bullish
                else:
                    if momentum[i] < momentum[i-1]:
                        colors[i] = -2  # Maroon - increasing bearish
                    else:
                        colors[i] = -1  # Red - decreasing bearish
            return colors
        
        self.mom_color = self.I(momentum_color, self.momentum)
        
        # Track entry price
        self.entry_price = None
        self.position_type = None  # 'long' or 'short'
    
    def next(self):
        # Skip if not enough data
        if len(self.data) < self.kc_period + self.mom_period:
            return
        
        # Current values
        squeeze_on = self.squeeze[-1] > 0
        momentum = self.momentum[-1]
        momentum_prev = self.momentum[-2] if len(self.momentum) > 1 else 0
        mom_color = self.mom_color[-1]
        
        # Check if we have a position
        if self.position:
            current_price = self.data.Close[-1]
            
            # Exit logic based on position type
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
                # Momentum reversal
                elif momentum < 0 or mom_color < 0:
                    self.position.close()
                    self.entry_price = None
                    self.position_type = None
                    
            elif self.position_type == 'short':
                # Take profit (price went down)
                if current_price <= self.entry_price * (1 - self.take_profit):
                    self.position.close()
                    self.entry_price = None
                    self.position_type = None
                # Stop loss (price went up)
                elif current_price >= self.entry_price * (1 + self.stop_loss):
                    self.position.close()
                    self.entry_price = None
                    self.position_type = None
                # Momentum reversal
                elif momentum > 0 or mom_color > 0:
                    self.position.close()
                    self.entry_price = None
                    self.position_type = None
        
        else:
            # Entry logic - Squeeze must be OFF (breaking out)
            if not squeeze_on:  # Squeeze is OFF
                # Long entry conditions
                if momentum > 0 and momentum > momentum_prev and mom_color == 2:
                    # Additional confirmation: momentum is accelerating
                    if len(self.momentum) > 3:
                        recent_acceleration = self.momentum[-1] - self.momentum[-3]
                        if recent_acceleration > 0:
                            self.buy()
                            self.entry_price = self.data.Close[-1]
                            self.position_type = 'long'
                
                # Short entry conditions (disabled for now to avoid extreme losses)
                # Note: Short selling can lead to unlimited losses in trending markets
                # Uncomment below to enable short positions with caution
                # elif momentum < 0 and momentum < momentum_prev and mom_color == -2:
                #     # Additional confirmation: momentum is accelerating downward
                #     if len(self.momentum) > 3:
                #         recent_acceleration = self.momentum[-1] - self.momentum[-3]
                #         if recent_acceleration < 0:
                #             self.sell()
                #             self.entry_price = self.data.Close[-1]
                #             self.position_type = 'short'


# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING SQUEEZE MOMENTUM STRATEGY ON ALL DATA SOURCES")
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
        bt = Backtest(data, SqueezeMomentum, cash=10000, commission=0.00045)
        stats = bt.run()
        
        print("\n" + "="*50)
        print("BACKTEST RESULTS - SQUEEZE MOMENTUM")
        print("="*50)
        print(stats)
        
        # Show plot
        #bt.plot()
    
    # Test on all data sources
    print("\n" + "="*80)
    print("RUNNING MULTI-DATA TEST")
    print("="*80)
    
    from multi_data_tester import test_on_all_data
    
    results = test_on_all_data(SqueezeMomentum, 'SqueezeMomentum')
    
    if results is not None:
        print("\nTesting complete! Results saved in: ./results/SqueezeMomentum.csv")