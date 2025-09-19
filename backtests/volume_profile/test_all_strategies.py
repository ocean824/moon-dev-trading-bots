"""
Test all Volume Profile Strategies on multiple data sources
"""

import pandas as pd
import numpy as np
from backtesting import Backtest
import warnings
warnings.filterwarnings('ignore')
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from multi_data_tester import test_on_all_data

# Import simplified strategy (the only one that works currently)
from volume_profile_simple_base import VolumeProfileSimpleBase

# Create results directory
results_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
os.makedirs(results_dir, exist_ok=True)

print("="*80)
print("TESTING ALL VOLUME PROFILE STRATEGIES")
print("="*80)
print(f"Results will be saved to: {results_dir}")
print()

# Test the working strategy on all data sources
print("Testing Volume Profile Simple Base Strategy on all data sources...")
results = test_on_all_data(VolumeProfileSimpleBase, 'VolumeProfileSimpleBase', verbose=False)

if results is not None:
    print("\n" + "="*80)
    print("TESTING COMPLETE")
    print("="*80)

    # Show summary statistics
    print("\nTop 5 Best Performing Data Sources:")
    print(results.nlargest(5, 'Return_%')[['Data_Source', 'Return_%', 'Sharpe', 'Trades', 'Win_Rate_%']])

    print("\nOverall Statistics:")
    print(f"Average Return: {results['Return_%'].mean():.2f}%")
    print(f"Average Sharpe: {results['Sharpe'].mean():.3f}")
    print(f"Average Win Rate: {results['Win_Rate_%'].mean():.2f}%")
    print(f"Total Trades Across All Data: {results['Trades'].sum()}")

    # Save summary to separate file
    summary_path = os.path.join(results_dir, f"volume_profile_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
    with open(summary_path, 'w') as f:
        f.write("VOLUME PROFILE STRATEGY TEST SUMMARY\n")
        f.write("="*50 + "\n\n")
        f.write("Strategy: VolumeProfileSimpleBase\n")
        f.write(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("PERFORMANCE METRICS\n")
        f.write("-"*30 + "\n")
        f.write(f"Average Return: {results['Return_%'].mean():.2f}%\n")
        f.write(f"Best Return: {results['Return_%'].max():.2f}%\n")
        f.write(f"Worst Return: {results['Return_%'].min():.2f}%\n")
        f.write(f"Average Sharpe: {results['Sharpe'].mean():.3f}\n")
        f.write(f"Average Win Rate: {results['Win_Rate_%'].mean():.2f}%\n")
        f.write(f"Total Trades: {results['Trades'].sum()}\n\n")
        f.write("TOP PERFORMING DATA SOURCES\n")
        f.write("-"*30 + "\n")
        f.write(results.nlargest(5, 'Return_%')[['Data_Source', 'Return_%', 'Sharpe']].to_string())

    print(f"\nSummary saved to: {summary_path}")
else:
    print("No results generated!")

print("\nDr. Data Dawg, your Volume Profile strategies have been tested!")