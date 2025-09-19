"""
Quick test script for Volume Profile strategies
Tests each strategy on a small data sample for validation
"""

import pandas as pd
import numpy as np
from backtesting import Backtest
import warnings
warnings.filterwarnings('ignore')

# Import strategies
from volume_profile_simple_base import VolumeProfileSimpleBase

# Load small data sample for quick testing
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

print("="*80)
print("QUICK VALIDATION TEST - Volume Profile Strategies")
print("="*80)

# Load data (last 1000 rows for quick test)
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index().dropna().tail(1000)  # Last 1000 bars only

print(f"\nTest data: {len(data)} rows")
print(f"Date range: {data.index[0]} to {data.index[-1]}")

strategies = [
    (VolumeProfileSimpleBase, "Volume Profile Simple Base"),
]

for strategy_class, name in strategies:
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"{'='*60}")

    try:
        bt = Backtest(data, strategy_class, cash=10000, commission=0.001)
        stats = bt.run()

        print(f"Final Return: {stats['Return [%]']:.2f}%")
        print(f"Win Rate: {stats['Win Rate [%]']:.2f}%")
        print(f"Number of Trades: {stats['# Trades']}")
        print(f"Sharpe Ratio: {stats['Sharpe Ratio']:.3f}")
        print(f"Max Drawdown: {stats['Max. Drawdown [%]']:.2f}%")

        if stats['# Trades'] > 0:
            print(f"✅ Strategy executed successfully with {stats['# Trades']} trades")
        else:
            print("⚠️ No trades executed - check strategy logic")

    except Exception as e:
        print(f"❌ Error: {str(e)}")

print(f"\n{'='*80}")
print("Quick validation complete!")
print(f"{'='*80}")