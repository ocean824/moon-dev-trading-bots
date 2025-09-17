#!/usr/bin/env python3
"""
Test FlowScope strategies on a single dataset for quick verification
"""

import pandas as pd
import sys
import os
from backtesting import Backtest

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import strategies
from flowscope_base import FlowScopeBase
from flowscope_adx import FlowScopeADX
from flowscope_vwap import FlowScopeVWAP
from flowscope_mfi import FlowScopeMFI

# Load a single dataset for testing
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'
data = pd.read_csv(data_path, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Limit data for faster testing
data = data[-5000:]  # Last 5000 candles

print("="*80)
print("TESTING FLOWSCOPE STRATEGIES ON BTC-1h DATA")
print(f"Data points: {len(data)}")
print("="*80)

strategies = [
    (FlowScopeBase, 'FlowScopeBase'),
    (FlowScopeADX, 'FlowScopeADX'),
    (FlowScopeVWAP, 'FlowScopeVWAP'),
    (FlowScopeMFI, 'FlowScopeMFI')
]

for strategy_class, strategy_name in strategies:
    print(f"\nTesting {strategy_name}...")
    print("-"*40)

    try:
        bt = Backtest(data, strategy_class, cash=10000000, commission=0.00045)
        stats = bt.run()

        print(f"\nResults for {strategy_name}:")
        print(f"Return: {stats['Return [%]']:.2f}%")
        print(f"Buy & Hold Return: {stats['Buy & Hold Return [%]']:.2f}%")
        print(f"Max Drawdown: {stats['Max. Drawdown [%]']:.2f}%")
        print(f"# Trades: {stats['# Trades']}")
        print(f"Win Rate: {stats['Win Rate [%]']:.2f}%" if pd.notna(stats['Win Rate [%]']) else "Win Rate: N/A")
        print(f"Sharpe Ratio: {stats['Sharpe Ratio']:.3f}" if pd.notna(stats['Sharpe Ratio']) else "Sharpe Ratio: N/A")
        print(f"Profit Factor: {stats['Profit Factor']:.3f}" if pd.notna(stats['Profit Factor']) else "Profit Factor: N/A")

    except Exception as e:
        print(f"Error testing {strategy_name}: {e}")

print("\n" + "="*80)
print("TESTING COMPLETE")
print("="*80)