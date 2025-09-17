"""
Run all FVG strategies on multiple data sources using multi_data_tester
"""

import sys
import os
import pandas as pd
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import multi-data tester
from multi_data_tester import test_on_all_data

# Import strategy classes directly
from fvg_base import FVGBase
from fvg_mfi import FVGMFI
from fvg_adx import FVGADX
from fvg_kalman import FVGKalman

def main():
    print("\n" + "="*80)
    print(" "*20 + "🌙 FVG STRATEGIES MULTI-DATA TEST 🌙")
    print("="*80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)

    # Change to strategy directory for results
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # Define strategies
    strategies = [
        ('FVG_Base', FVGBase),
        ('FVG_MFI', FVGMFI),
        ('FVG_ADX', FVGADX),
        ('FVG_Kalman', FVGKalman)
    ]

    # Test each strategy
    for strategy_name, strategy_class in strategies:
        print(f"\n{'='*60}")
        print(f"Testing {strategy_name} on all data sources...")
        print(f"{'='*60}")

        try:
            results = test_on_all_data(strategy_class, strategy_name)

            if results is not None and not results.empty:
                print(f"\n✅ {strategy_name} completed successfully!")
                print(f"   Tested on {len(results)} data sources")
                print(f"   Average Return: {results['Return_%'].mean():.2f}%")
                print(f"   Average Sharpe: {results['Sharpe'].mean():.2f}")
                print(f"   Best Sharpe: {results['Sharpe'].max():.2f}")
                print(f"   Average Win Rate: {results['Win_Rate_%'].mean():.1f}%")
            else:
                print(f"❌ {strategy_name} - No results generated")

        except Exception as e:
            print(f"❌ Error testing {strategy_name}: {str(e)[:200]}")

    print("\n" + "="*80)
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    print("\n✅ Check the ./results/ folder for detailed CSV files!")

if __name__ == "__main__":
    main()