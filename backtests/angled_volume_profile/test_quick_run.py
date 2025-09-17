"""
Quick test runner for AVP strategies on limited data sources
"""
import subprocess
import pandas as pd
import os
import time

def run_strategy(script_name, timeout=300):
    """Run a single strategy with timeout"""
    print(f"\nRunning {script_name}...")
    try:
        result = subprocess.run(
            ['python', script_name],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        print(f"Completed {script_name}")
        return True
    except subprocess.TimeoutExpired:
        print(f"Timeout on {script_name}")
        return False
    except Exception as e:
        print(f"Error running {script_name}: {e}")
        return False

def main():
    strategies = [
        'avp_base.py',
        'avp_vwap.py',
        'avp_mfi.py',
        'avp_adx.py'
    ]

    print("="*80)
    print("RUNNING ALL AVP STRATEGIES ON 25+ DATA SOURCES")
    print("="*80)

    results = []
    for strategy in strategies:
        success = run_strategy(strategy)
        results.append((strategy, success))

    print("\n" + "="*80)
    print("EXECUTION SUMMARY")
    print("="*80)
    for strategy, success in results:
        status = "✅ Success" if success else "❌ Failed/Timeout"
        print(f"{strategy}: {status}")

    # Check for result files
    print("\n" + "="*80)
    print("RESULT FILES")
    print("="*80)

    result_files = [
        'results/avp_base_multi_data_results.csv',
        'results/avp_vwap_multi_data_results.csv',
        'results/avp_mfi_multi_data_results.csv',
        'results/avp_adx_multi_data_results.csv'
    ]

    all_results = []
    for file in result_files:
        if os.path.exists(file):
            df = pd.read_csv(file)
            strategy_name = file.split('/')[-1].replace('_multi_data_results.csv', '')
            df['Strategy'] = strategy_name
            all_results.append(df)
            print(f"✅ Found {file}: {len(df)} results")
        else:
            print(f"❌ Missing {file}")

    # Combine all results
    if all_results:
        combined = pd.concat(all_results, ignore_index=True)
        combined.to_csv('results/all_strategies_combined.csv', index=False)
        print(f"\n✅ Combined results saved to results/all_strategies_combined.csv")

        # Show summary
        print("\n" + "="*80)
        print("PERFORMANCE SUMMARY BY STRATEGY")
        print("="*80)
        summary = combined.groupby('Strategy').agg({
            'Return_%': ['mean', 'std', 'min', 'max'],
            'Sharpe': 'mean',
            'Win_Rate_%': 'mean',
            'Num_Trades': 'sum'
        }).round(2)
        print(summary)

if __name__ == "__main__":
    main()