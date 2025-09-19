"""
Test Volume Profile Strategies - Simple test without multi-data
"""

import pandas as pd
import numpy as np
from backtesting import Backtest
import warnings
warnings.filterwarnings('ignore')

# Import our strategies
from volume_profile_base import VolumeProfileBase
from volume_profile_poc import VolumeProfilePOC
from volume_profile_breakout import VolumeProfileBreakout
from volume_profile_pivot import VolumeProfilePivot
from volume_profile_spike import VolumeProfileSpike

# Data configuration
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

print("Testing Volume Profile Strategies")
print("=" * 80)

# Load data once
print(f"Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()

# Use only recent data for faster testing
data = data[-5000:]  # Last 5000 bars only

print(f"Data loaded! Using last {len(data)} rows for testing")
print()

# Define strategies to test
strategies = [
    ('Base', VolumeProfileBase),
    ('POC Mean Reversion', VolumeProfilePOC),
    ('Breakout', VolumeProfileBreakout),
    ('Pivot', VolumeProfilePivot),
    ('Spike', VolumeProfileSpike)
]

# Test each strategy
results = []
for name, strategy_class in strategies:
    print(f"\nTesting {name} Strategy...")
    print("-" * 40)

    try:
        bt = Backtest(data, strategy_class, cash=1000000, commission=0.001)
        stats = bt.run()

        # Extract key metrics
        result = {
            'Strategy': name,
            'Return %': round(stats['Return [%]'], 2),
            'Sharpe': round(stats['Sharpe Ratio'], 3) if not pd.isna(stats['Sharpe Ratio']) else 0,
            'Max DD %': round(stats['Max. Drawdown [%]'], 2),
            'Trades': stats['# Trades'],
            'Win Rate %': round(stats['Win Rate [%]'], 2) if not pd.isna(stats['Win Rate [%]']) else 0,
            'Avg Trade %': round(stats['Avg. Trade [%]'], 3) if not pd.isna(stats['Avg. Trade [%]']) else 0,
        }

        results.append(result)
        print(f"✓ {name}: Return={result['Return %']}%, Sharpe={result['Sharpe']}, Trades={result['Trades']}")

    except Exception as e:
        print(f"✗ {name}: Error - {e}")
        results.append({
            'Strategy': name,
            'Return %': 0,
            'Sharpe': 0,
            'Max DD %': 0,
            'Trades': 0,
            'Win Rate %': 0,
            'Avg Trade %': 0,
        })

# Summary
print("\n" + "=" * 80)
print("SUMMARY OF ALL STRATEGIES")
print("=" * 80)

if results:
    results_df = pd.DataFrame(results)
    print(results_df.to_string(index=False))

print("\nTest complete!")