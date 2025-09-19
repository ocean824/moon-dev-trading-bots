"""
Test All Markov Chain Strategies
=================================
Runs all Markov Chain strategy variations across all configured data sources
and saves comprehensive results for comparison.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from multi_data_tester import test_on_all_data
import pandas as pd
from datetime import datetime

# Import all strategy classes
from markov_chain_base import MarkovChainBase
from markov_chain_atr import MarkovChainATR
from markov_chain_volume import MarkovChainVolume
from markov_chain_momentum import MarkovChainMomentum
from markov_chain_ensemble import MarkovChainEnsemble

def test_all_strategies():
    """Test all Markov Chain strategies and save results"""

    print("\n" + "="*80)
    print("🚀 TESTING ALL MARKOV CHAIN STRATEGIES 🚀")
    print("="*80)

    strategies = {
        'MarkovChainBase': MarkovChainBase,
        'MarkovChainATR': MarkovChainATR,
        'MarkovChainVolume': MarkovChainVolume,
        'MarkovChainMomentum': MarkovChainMomentum,
        'MarkovChainEnsemble': MarkovChainEnsemble
    }

    all_results = []

    for name, strategy_class in strategies.items():
        print(f"\n{'='*60}")
        print(f"Testing {name}")
        print(f"{'='*60}")

        # Test on all data sources with large position size
        results = test_on_all_data(
            strategy_class,
            name,
            cash=1000000,  # Position size as requested
            commission=0.00045,
            verbose=True
        )

        if results is not None:
            # Add strategy name column
            results['Strategy'] = name
            all_results.append(results)
            print(f"\n✅ {name} testing complete!")
        else:
            print(f"\n❌ {name} testing failed!")

    # Combine all results
    if all_results:
        combined_results = pd.concat(all_results, ignore_index=True)

        # Save combined results
        results_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
        os.makedirs(results_dir, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        combined_path = os.path.join(results_dir, f'markov_chain_all_results_{timestamp}.csv')
        combined_results.to_csv(combined_path, index=False)

        print("\n" + "="*80)
        print("📊 SUMMARY OF ALL STRATEGIES")
        print("="*80)

        # Group by strategy and calculate average metrics
        summary = combined_results.groupby('Strategy').agg({
            'Return_%': 'mean',
            'Sharpe': 'mean',
            'Sortino': 'mean',
            'Max_DD_%': 'mean',
            'Win_Rate_%': 'mean',
            'Trades': 'sum',
            'Profit_Factor': 'mean',
            'Expectancy_%': 'mean'
        }).round(2)

        print("\nAverage Performance Across All Data Sources:")
        print(summary.to_string())

        # Find best performing strategy for each data source
        print("\n" + "="*80)
        print("🏆 BEST STRATEGY PER DATA SOURCE")
        print("="*80)

        best_per_source = combined_results.loc[
            combined_results.groupby('Data_Source')['Return_%'].idxmax()
        ][['Data_Source', 'Strategy', 'Return_%', 'Sharpe', 'Max_DD_%']]

        print(best_per_source.to_string(index=False))

        # Overall best single result
        best_overall = combined_results.loc[combined_results['Return_%'].idxmax()]
        print("\n" + "="*80)
        print("🌟 BEST SINGLE RESULT")
        print("="*80)
        print(f"Strategy: {best_overall['Strategy']}")
        print(f"Data Source: {best_overall['Data_Source']}")
        print(f"Return: {best_overall['Return_%']:.2f}%")
        print(f"Sharpe: {best_overall['Sharpe']:.3f}")
        print(f"Max DD: {best_overall['Max_DD_%']:.2f}%")
        print(f"Win Rate: {best_overall['Win_Rate_%']:.2f}%")

        print(f"\n✅ All results saved to: {combined_path}")

        return combined_results

    return None

if __name__ == "__main__":
    results = test_all_strategies()

    if results is not None:
        print("\n" + "="*80)
        print("✅ ALL MARKOV CHAIN STRATEGIES TESTED SUCCESSFULLY!")
        print("="*80)
    else:
        print("\n❌ Testing failed - no results generated")