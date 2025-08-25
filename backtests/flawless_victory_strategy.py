#!/usr/bin/env python3
"""
Flawless Victory Strategy - Three Versions
==========================================

This strategy implements three versions of a Bollinger Band + RSI/MFI system:

Version 1 - No SL/TP:
- Bollinger Bands (20 period, 1.0 mult)
- RSI (14 period)
- Long Entry: Price < Lower BB AND RSI > 42
- Exit: Price > Upper BB AND RSI > 70
- No stop loss or take profit

Version 2 - With SL/TP:
- Bollinger Bands (17 period, 1.0 mult)
- RSI (14 period)
- Long Entry: Price < Lower BB AND RSI > 42
- Exit: Price > Upper BB AND RSI > 76
- Stop Loss: 6.604%
- Take Profit: 2.328%

Version 3 - MFI Version:
- Bollinger Bands (20 period, 1.0 mult)
- RSI (14 period)
- MFI (14 period)
- Long Entry: Price < Lower BB AND MFI < 60
- Exit: Price > Upper BB AND RSI > 65 AND MFI > 64
- Stop Loss: 8.882%
- Take Profit: 2.317%
"""

import pandas as pd
import numpy as np
import pandas_ta as ta
from backtesting import Strategy
import warnings
warnings.filterwarnings('ignore')

print("🚀 Flawless Victory Strategy Loading... 🎮")

class FlawlessVictoryV1(Strategy):
    """Version 1: No SL/TP"""
    
    # BB parameters
    bb_period = 20
    bb_mult = 1.0
    
    # RSI parameters
    rsi_period = 14
    rsi_entry_threshold = 42
    rsi_exit_threshold = 70
    
    def init(self):
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        volume = pd.Series(self.data.Volume)
        
        # Calculate Bollinger Bands
        bb = ta.bbands(close, length=self.bb_period, std=self.bb_mult)
        if bb is not None and not bb.empty:
            self.bb_upper = self.I(lambda: bb[f'BBU_{self.bb_period}_{self.bb_mult}'].values)
            self.bb_lower = self.I(lambda: bb[f'BBL_{self.bb_period}_{self.bb_mult}'].values)
            self.bb_middle = self.I(lambda: bb[f'BBM_{self.bb_period}_{self.bb_mult}'].values)
        else:
            # Fallback to manual calculation
            sma = close.rolling(self.bb_period).mean()
            std = close.rolling(self.bb_period).std()
            self.bb_upper = self.I(lambda: (sma + self.bb_mult * std).values)
            self.bb_lower = self.I(lambda: (sma - self.bb_mult * std).values)
            self.bb_middle = self.I(lambda: sma.values)
        
        # Calculate RSI
        rsi = ta.rsi(close, length=self.rsi_period)
        if rsi is not None and not rsi.empty:
            self.rsi = self.I(lambda: rsi.values)
        else:
            # Fallback calculation
            delta = close.diff()
            gain = delta.where(delta > 0, 0).rolling(self.rsi_period).mean()
            loss = -delta.where(delta < 0, 0).rolling(self.rsi_period).mean()
            rs = gain / loss
            rsi_calc = 100 - (100 / (1 + rs))
            self.rsi = self.I(lambda: rsi_calc.values)
    
    def next(self):
        # Skip if we don't have enough data
        if len(self.data) < max(self.bb_period, self.rsi_period) + 1:
            return
        
        # Current values
        current_price = self.data.Close[-1]
        current_rsi = self.rsi[-1]
        upper_bb = self.bb_upper[-1]
        lower_bb = self.bb_lower[-1]
        
        # Check for NaN values
        if pd.isna(current_rsi) or pd.isna(upper_bb) or pd.isna(lower_bb):
            return
        
        if self.position:
            # Exit conditions
            if current_price > upper_bb and current_rsi > self.rsi_exit_threshold:
                self.position.close()
        else:
            # Entry conditions
            if current_price < lower_bb and current_rsi > self.rsi_entry_threshold:
                self.buy()


class FlawlessVictoryV2(Strategy):
    """Version 2: With SL/TP"""
    
    # BB parameters
    bb_period = 17
    bb_mult = 1.0
    
    # RSI parameters
    rsi_period = 14
    rsi_entry_threshold = 42
    rsi_exit_threshold = 76
    
    # Risk management
    stop_loss = 0.06604    # 6.604%
    take_profit = 0.02328  # 2.328%
    
    def init(self):
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        volume = pd.Series(self.data.Volume)
        
        # Calculate Bollinger Bands
        bb = ta.bbands(close, length=self.bb_period, std=self.bb_mult)
        if bb is not None and not bb.empty:
            self.bb_upper = self.I(lambda: bb[f'BBU_{self.bb_period}_{self.bb_mult}'].values)
            self.bb_lower = self.I(lambda: bb[f'BBL_{self.bb_period}_{self.bb_mult}'].values)
            self.bb_middle = self.I(lambda: bb[f'BBM_{self.bb_period}_{self.bb_mult}'].values)
        else:
            # Fallback to manual calculation
            sma = close.rolling(self.bb_period).mean()
            std = close.rolling(self.bb_period).std()
            self.bb_upper = self.I(lambda: (sma + self.bb_mult * std).values)
            self.bb_lower = self.I(lambda: (sma - self.bb_mult * std).values)
            self.bb_middle = self.I(lambda: sma.values)
        
        # Calculate RSI
        rsi = ta.rsi(close, length=self.rsi_period)
        if rsi is not None and not rsi.empty:
            self.rsi = self.I(lambda: rsi.values)
        else:
            # Fallback calculation
            delta = close.diff()
            gain = delta.where(delta > 0, 0).rolling(self.rsi_period).mean()
            loss = -delta.where(delta < 0, 0).rolling(self.rsi_period).mean()
            rs = gain / loss
            rsi_calc = 100 - (100 / (1 + rs))
            self.rsi = self.I(lambda: rsi_calc.values)
        
        # Track entry price for SL/TP
        self.entry_price = None
    
    def next(self):
        # Skip if we don't have enough data
        if len(self.data) < max(self.bb_period, self.rsi_period) + 1:
            return
        
        # Current values
        current_price = self.data.Close[-1]
        current_rsi = self.rsi[-1]
        upper_bb = self.bb_upper[-1]
        lower_bb = self.bb_lower[-1]
        
        # Check for NaN values
        if pd.isna(current_rsi) or pd.isna(upper_bb) or pd.isna(lower_bb):
            return
        
        if self.position:
            # Check stop loss
            if self.entry_price and current_price <= self.entry_price * (1 - self.stop_loss):
                self.position.close()
                self.entry_price = None
            # Check take profit
            elif self.entry_price and current_price >= self.entry_price * (1 + self.take_profit):
                self.position.close()
                self.entry_price = None
            # Exit conditions
            elif current_price > upper_bb and current_rsi > self.rsi_exit_threshold:
                self.position.close()
                self.entry_price = None
        else:
            # Entry conditions
            if current_price < lower_bb and current_rsi > self.rsi_entry_threshold:
                self.buy()
                self.entry_price = current_price


class FlawlessVictoryV3(Strategy):
    """Version 3: MFI Version"""
    
    # BB parameters
    bb_period = 20
    bb_mult = 1.0
    
    # RSI parameters
    rsi_period = 14
    rsi_exit_threshold = 65
    
    # MFI parameters
    mfi_period = 14
    mfi_entry_threshold = 60
    mfi_exit_threshold = 64
    
    # Risk management
    stop_loss = 0.08882    # 8.882%
    take_profit = 0.02317  # 2.317%
    
    def init(self):
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        volume = pd.Series(self.data.Volume)
        
        # Calculate Bollinger Bands
        bb = ta.bbands(close, length=self.bb_period, std=self.bb_mult)
        if bb is not None and not bb.empty:
            self.bb_upper = self.I(lambda: bb[f'BBU_{self.bb_period}_{self.bb_mult}'].values)
            self.bb_lower = self.I(lambda: bb[f'BBL_{self.bb_period}_{self.bb_mult}'].values)
            self.bb_middle = self.I(lambda: bb[f'BBM_{self.bb_period}_{self.bb_mult}'].values)
        else:
            # Fallback to manual calculation
            sma = close.rolling(self.bb_period).mean()
            std = close.rolling(self.bb_period).std()
            self.bb_upper = self.I(lambda: (sma + self.bb_mult * std).values)
            self.bb_lower = self.I(lambda: (sma - self.bb_mult * std).values)
            self.bb_middle = self.I(lambda: sma.values)
        
        # Calculate RSI
        rsi = ta.rsi(close, length=self.rsi_period)
        if rsi is not None and not rsi.empty:
            self.rsi = self.I(lambda: rsi.values)
        else:
            # Fallback calculation
            delta = close.diff()
            gain = delta.where(delta > 0, 0).rolling(self.rsi_period).mean()
            loss = -delta.where(delta < 0, 0).rolling(self.rsi_period).mean()
            rs = gain / loss
            rsi_calc = 100 - (100 / (1 + rs))
            self.rsi = self.I(lambda: rsi_calc.values)
        
        # Calculate MFI
        mfi = ta.mfi(high, low, close, volume, length=self.mfi_period)
        if mfi is not None and not mfi.empty:
            self.mfi = self.I(lambda: mfi.values)
        else:
            # Fallback calculation
            typical_price = (high + low + close) / 3
            raw_money_flow = typical_price * volume
            
            # Positive and negative money flow
            money_flow_diff = typical_price.diff()
            positive_flow = raw_money_flow.where(money_flow_diff > 0, 0)
            negative_flow = raw_money_flow.where(money_flow_diff < 0, 0)
            
            # Calculate MFI
            positive_mf = positive_flow.rolling(self.mfi_period).sum()
            negative_mf = negative_flow.rolling(self.mfi_period).sum()
            
            mfi_ratio = positive_mf / negative_mf
            mfi_calc = 100 - (100 / (1 + mfi_ratio))
            self.mfi = self.I(lambda: mfi_calc.values)
        
        # Track entry price for SL/TP
        self.entry_price = None
    
    def next(self):
        # Skip if we don't have enough data
        if len(self.data) < max(self.bb_period, self.rsi_period, self.mfi_period) + 1:
            return
        
        # Current values
        current_price = self.data.Close[-1]
        current_rsi = self.rsi[-1]
        current_mfi = self.mfi[-1]
        upper_bb = self.bb_upper[-1]
        lower_bb = self.bb_lower[-1]
        
        # Check for NaN values
        if pd.isna(current_rsi) or pd.isna(current_mfi) or pd.isna(upper_bb) or pd.isna(lower_bb):
            return
        
        if self.position:
            # Check stop loss
            if self.entry_price and current_price <= self.entry_price * (1 - self.stop_loss):
                self.position.close()
                self.entry_price = None
            # Check take profit
            elif self.entry_price and current_price >= self.entry_price * (1 + self.take_profit):
                self.position.close()
                self.entry_price = None
            # Exit conditions
            elif (current_price > upper_bb and 
                  current_rsi > self.rsi_exit_threshold and 
                  current_mfi > self.mfi_exit_threshold):
                self.position.close()
                self.entry_price = None
        else:
            # Entry conditions
            if current_price < lower_bb and current_mfi < self.mfi_entry_threshold:
                self.buy()
                self.entry_price = current_price


# Wrapper class that can switch between versions
class FlawlessVictory(Strategy):
    """Main strategy class that switches between versions"""
    
    # Version selection (1, 2, or 3)
    version = 1
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Select the appropriate version
        if self.version == 1:
            self.strategy = FlawlessVictoryV1(*args, **kwargs)
        elif self.version == 2:
            self.strategy = FlawlessVictoryV2(*args, **kwargs)
        elif self.version == 3:
            self.strategy = FlawlessVictoryV3(*args, **kwargs)
        else:
            raise ValueError(f"Invalid version: {self.version}. Must be 1, 2, or 3.")
    
    def init(self):
        # Delegate to selected version
        self.strategy.data = self.data
        self.strategy.init()
        
        # Copy indicators
        for attr in dir(self.strategy):
            if not attr.startswith('_') and hasattr(getattr(self.strategy, attr), '__call__'):
                continue
            if attr in ['bb_upper', 'bb_lower', 'bb_middle', 'rsi', 'mfi', 'entry_price']:
                setattr(self, attr, getattr(self.strategy, attr, None))
    
    def next(self):
        # Update strategy's position reference
        self.strategy.position = self.position
        self.strategy.data = self.data
        
        # Copy entry price if it exists
        if hasattr(self.strategy, 'entry_price'):
            entry_price = self.strategy.entry_price
        
        # Delegate to selected version
        self.strategy.next()
        
        # Update entry price if changed
        if hasattr(self.strategy, 'entry_price'):
            self.strategy.entry_price = getattr(self, 'entry_price', None)
            if self.position and not self.strategy.entry_price:
                self.strategy.entry_price = self.data.Close[-1]


# TEST SINGLE DATA SOURCE AND MULTI-DATA
if __name__ == "__main__":
    from backtesting import Backtest
    import sys
    import os
    
    # Test each version
    for version in [1, 2, 3]:
        print("\n" + "="*80)
        print(f"TESTING FLAWLESS VICTORY STRATEGY - VERSION {version}")
        print("="*80)
        
        # Version descriptions
        if version == 1:
            print("Version 1: No SL/TP - BB(20,1.0), RSI(14), Entry: Price<LowerBB & RSI>42, Exit: Price>UpperBB & RSI>70")
        elif version == 2:
            print("Version 2: With SL/TP - BB(17,1.0), RSI(14), Entry: Price<LowerBB & RSI>42, Exit: Price>UpperBB & RSI>76")
            print("Stop Loss: 6.604%, Take Profit: 2.328%")
        elif version == 3:
            print("Version 3: MFI Version - BB(20,1.0), RSI(14), MFI(14), Entry: Price<LowerBB & MFI<60")
            print("Exit: Price>UpperBB & RSI>65 & MFI>64, Stop Loss: 8.882%, Take Profit: 2.317%")
        
        # Load sample data for single test
        data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'
        
        if os.path.exists(data_path):
            data = pd.read_csv(data_path, parse_dates=['datetime'], index_col='datetime')
            data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            data = data.sort_index()
            data = data.dropna()
            
            # Select appropriate strategy class
            if version == 1:
                strategy_class = FlawlessVictoryV1
            elif version == 2:
                strategy_class = FlawlessVictoryV2
            else:
                strategy_class = FlawlessVictoryV3
            
            # Run backtest
            bt = Backtest(data, strategy_class, cash=10000000, commission=0.00045)
            stats = bt.run()
            
            print("\n" + "="*50)
            print(f"BACKTEST RESULTS - FLAWLESS VICTORY V{version}")
            print("="*50)
            print(stats)
            
            # Show plot for first version only
            if version == 1:
                bt.plot()
    
    # Test on all data sources using Version 1 as default
    print("\n" + "="*80)
    print("RUNNING MULTI-DATA TEST - VERSION 1 (DEFAULT)")
    print("="*80)
    
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    results = test_on_all_data(FlawlessVictoryV1, 'FlawlessVictoryV1')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/FlawlessVictoryV1.csv")
        print("\nSUMMARY STATISTICS:")
        print(f"Average Return: {results['Return_%'].mean():.2f}%")
        print(f"Best Return: {results['Return_%'].max():.2f}%")
        print(f"Worst Return: {results['Return_%'].min():.2f}%")
        print(f"Profitable on {(results['Return_%'] > 0).sum()}/{len(results)} data sources")
        print(f"Average Win Rate: {results['Win_Rate_%'].mean():.1f}%")
        print(f"Average Sharpe: {results['Sharpe'].mean():.3f}")