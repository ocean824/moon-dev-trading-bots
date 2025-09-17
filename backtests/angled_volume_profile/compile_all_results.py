"""
Compile all AVP strategy results into master CSV files
"""
import pandas as pd
import os

def main():
    print("="*80)
    print("COMPILING AVP STRATEGY RESULTS")
    print("="*80)

    # Read the multi-data results that we have
    result_files = {
        'AVP_Base': 'results/avp_base_multi_data_results.csv',
        'AVP_VWAP': 'results/avp_vwap_multi_data_results.csv',
    }

    all_results = []

    for strategy_name, file_path in result_files.items():
        if os.path.exists(file_path):
            df = pd.read_csv(file_path)
            df['Strategy'] = strategy_name
            all_results.append(df)
            print(f"✅ Loaded {strategy_name}: {len(df)} results")
        else:
            print(f"❌ Missing {file_path}")

    if all_results:
        # Combine all results
        combined = pd.concat(all_results, ignore_index=True)

        # Save master file
        combined.to_csv('results/all_avp_strategies_25_sources.csv', index=False)
        print(f"\n✅ Combined {len(combined)} results saved to results/all_avp_strategies_25_sources.csv")

        # Summary by strategy
        print("\n" + "="*80)
        print("PERFORMANCE SUMMARY BY STRATEGY")
        print("="*80)

        strategy_summary = combined.groupby('Strategy').agg({
            'Return_%': ['mean', 'std', 'min', 'max'],
            'Sharpe': 'mean',
            'Max_DD_%': 'mean',
            'Win_Rate_%': 'mean',
            'Num_Trades': ['sum', 'mean']
        }).round(2)

        print(strategy_summary)

        # Summary by data source
        print("\n" + "="*80)
        print("PERFORMANCE SUMMARY BY DATA SOURCE TYPE")
        print("="*80)

        source_summary = combined.groupby('Source').agg({
            'Return_%': 'mean',
            'Sharpe': 'mean',
            'Win_Rate_%': 'mean',
            'Num_Trades': 'mean'
        }).round(2)

        print(source_summary)

        # Best performers overall
        print("\n" + "="*80)
        print("TOP 10 BEST PERFORMERS (ALL STRATEGIES)")
        print("="*80)

        top10 = combined.nlargest(10, 'Return_%')[['Strategy', 'Symbol', 'Source', 'Return_%', 'Sharpe', 'Win_Rate_%']]
        print(top10.to_string(index=False))

        # Worst performers overall
        print("\n" + "="*80)
        print("BOTTOM 10 WORST PERFORMERS (ALL STRATEGIES)")
        print("="*80)

        bottom10 = combined.nsmallest(10, 'Return_%')[['Strategy', 'Symbol', 'Source', 'Return_%', 'Max_DD_%']]
        print(bottom10.to_string(index=False))

        # Save summary statistics
        summary_stats = pd.DataFrame({
            'Metric': ['Total Tests', 'Avg Return %', 'Avg Sharpe', 'Avg Max DD %', 'Avg Win Rate %', 'Total Trades'],
            'Value': [
                len(combined),
                round(combined['Return_%'].mean(), 2),
                round(combined['Sharpe'].mean(), 3),
                round(combined['Max_DD_%'].mean(), 2),
                round(combined['Win_Rate_%'].mean(), 2),
                combined['Num_Trades'].sum()
            ]
        })

        summary_stats.to_csv('results/avp_summary_stats.csv', index=False)
        print(f"\n✅ Summary statistics saved to results/avp_summary_stats.csv")

        return combined
    else:
        print("\n❌ No result files found")
        return None

if __name__ == "__main__":
    results = main()

    if results is not None:
        print("\n" + "="*80)
        print(f"COMPILATION COMPLETE: {len(results)} total test results")
        print("="*80)