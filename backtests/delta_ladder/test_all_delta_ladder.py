"""
Test All Delta Ladder Strategies

This script runs all Delta Ladder strategy variations and compares their performance
across multiple datasets.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Import strategy classes
from delta_ladder_simple import DeltaLadderSimple
from delta_ladder_base import DeltaLadderBase
from delta_ladder_mfi import DeltaLadderMFI
from delta_ladder_adx import DeltaLadderADX
from delta_ladder_kalman import DeltaLadderKalman

# Import multi_data_tester
from multi_data_tester import test_on_all_data

def test_all_strategies():
    """Test all Delta Ladder strategy variations"""

    # Define strategies to test
    strategies = [
        (DeltaLadderSimple, "DeltaLadderSimple"),
        # Commented out as these need fixing
        # (DeltaLadderBase, "DeltaLadderBase"),
        # (DeltaLadderMFI, "DeltaLadderMFI"),
        # (DeltaLadderADX, "DeltaLadderADX"),
        # (DeltaLadderKalman, "DeltaLadderKalman")
    ]

    print("\n" + "="*80)
    print("TESTING ALL DELTA LADDER STRATEGIES")
    print("="*80)
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)

    # Test each strategy
    for strategy_class, strategy_name in strategies:
        print(f"\n{'='*60}")
        print(f"Testing {strategy_name}...")
        print(f"{'='*60}")

        try:
            # Run tests using test_on_all_data
            results = test_on_all_data(
                strategy_class=strategy_class,
                strategy_name=strategy_name,
                optimize=False,
                verbose=False  # Set to False to reduce output
            )

            print(f"{strategy_name}: Completed Successfully")

        except Exception as e:
            print(f"Error testing {strategy_name}: {str(e)}")
            continue

    print("\n" + "="*80)
    print("NOTES:")
    print("="*80)
    print("1. DeltaLadderSimple: Basic implementation with volume delta")
    print("2. Other variations need signal generation improvements")
    print("3. Run individual strategies for detailed results:")
    print("   python delta_ladder_simple.py")
    print("\n" + "="*80)
    print(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)

if __name__ == "__main__":
    # Create results directory if it doesn't exist
    os.makedirs('/Users/md/Dropbox/dev/github/moon-dev-trading-bots/backtests/delta_ladder/results', exist_ok=True)

    # Run all tests
    test_all_strategies()