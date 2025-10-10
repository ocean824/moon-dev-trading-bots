"""
Ichimoku Theories Strategies - Results Analysis
===============================================
Analyzes and compares the performance of all Ichimoku strategy variations
"""

import pandas as pd
import os

def analyze_strategy_results():
    """Load and analyze all strategy results"""

    results_dir = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/backtests/ichimoku_theories/results'

    # Strategy files to analyze
    strategies = {
        'Base': 'IchimokuBase.csv',
        'MFI': 'IchimokuMFI.csv',
        'ADX': 'IchimokuADX.csv',
        'Kalman': 'IchimokuKalman.csv'
    }

    print("\n" + "="*80)
    print("ICHIMOKU THEORIES STRATEGIES - PERFORMANCE ANALYSIS")
    print("="*80)

    # Load all strategy results
    all_results = {}
    for name, file in strategies.items():
        filepath = os.path.join(results_dir, file)
        if os.path.exists(filepath):
            all_results[name] = pd.read_csv(filepath)
            print(f"\n✅ Loaded {name} strategy: {len(all_results[name])} data sources tested")
        else:
            print(f"\n❌ Could not find {name} strategy results at {filepath}")

    if not all_results:
        print("\n❌ No results files found!")
        return

    # Analyze each strategy
    for strategy_name, df in all_results.items():
        print(f"\n{'='*40}")
        print(f"STRATEGY: {strategy_name}")
        print(f"{'='*40}")

        # Filter out rows with no trades (Return% = 0)
        active_df = df[df['Return_%'] != 0]

        if len(active_df) == 0:
            print("No active trades across any data source")
            continue

        print(f"\nActive on {len(active_df)} out of {len(df)} data sources")
        print(f"\nTop Performing Data Sources:")
        top_5 = active_df.nlargest(5, 'Return_%')[['Data_Source', 'Return_%', 'Sharpe', 'Win_Rate_%', 'Trades']]
        print(top_5.to_string(index=False))

        # Overall statistics (only for active trading)
        print(f"\nOverall Statistics (Active Sources Only):")
        print(f"  Average Return:      {active_df['Return_%'].mean():.2f}%")
        print(f"  Median Return:       {active_df['Return_%'].median():.2f}%")
        print(f"  Best Return:         {active_df['Return_%'].max():.2f}%")
        print(f"  Worst Return:        {active_df['Return_%'].min():.2f}%")
        print(f"  Avg Sharpe Ratio:    {active_df['Sharpe'].mean():.3f}")
        print(f"  Avg Win Rate:        {active_df['Win_Rate_%'].mean():.1f}%")
        print(f"  Total Trades:        {active_df['Trades'].sum():.0f}")
        print(f"  Avg Trades/Source:   {active_df['Trades'].mean():.1f}")

    # Compare strategies side by side
    print(f"\n{'='*80}")
    print("STRATEGY COMPARISON")
    print(f"{'='*80}")

    comparison_data = []
    for strategy_name, df in all_results.items():
        active_df = df[df['Return_%'] != 0]

        if len(active_df) == 0:
            comparison_data.append({
                'Strategy': strategy_name,
                'Active Sources': 0,
                'Avg Return %': 0,
                'Best Return %': 0,
                'Avg Sharpe': 0,
                'Total Trades': 0,
                'Avg Win Rate %': 0
            })
        else:
            comparison_data.append({
                'Strategy': strategy_name,
                'Active Sources': len(active_df),
                'Avg Return %': round(active_df['Return_%'].mean(), 2),
                'Best Return %': round(active_df['Return_%'].max(), 2),
                'Avg Sharpe': round(active_df['Sharpe'].mean(), 3),
                'Total Trades': int(active_df['Trades'].sum()),
                'Avg Win Rate %': round(active_df['Win_Rate_%'].mean(), 1)
            })

    comparison_df = pd.DataFrame(comparison_data)
    print("\n", comparison_df.to_string(index=False))

    # Find best overall performer
    print(f"\n{'='*80}")
    print("RECOMMENDATIONS")
    print(f"{'='*80}")

    # Combine all results to find best data source/strategy combination
    best_performers = []
    for strategy_name, df in all_results.items():
        active_df = df[df['Return_%'] > 0].copy()
        if len(active_df) > 0:
            active_df['Strategy'] = strategy_name
            best_performers.append(active_df)

    if best_performers:
        all_active = pd.concat(best_performers)
        top_10 = all_active.nlargest(10, 'Return_%')[['Strategy', 'Data_Source', 'Return_%', 'Sharpe', 'Win_Rate_%', 'Trades']]

        print("\nTop 10 Strategy/Data Combinations by Return:")
        print(top_10.to_string(index=False))

        # Find most consistent (best Sharpe ratio)
        top_sharpe = all_active[all_active['Sharpe'] > 0].nlargest(5, 'Sharpe')[['Strategy', 'Data_Source', 'Sharpe', 'Return_%', 'Win_Rate_%']]

        if len(top_sharpe) > 0:
            print("\nTop 5 by Sharpe Ratio (Risk-Adjusted Return):")
            print(top_sharpe.to_string(index=False))

    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")

    print("""
The Ichimoku strategies show very conservative trading behavior across most data sources.
Key observations:

1. The strategies generate very few signals, indicating highly selective entry criteria
2. The Kalman filter version shows some extreme returns on BTC-6h timeframes
3. Most data sources show no trading activity (0 trades)
4. The base strategy and enhanced versions need parameter optimization

Recommendations:
- Consider adjusting entry thresholds to be less restrictive
- Test with different Ichimoku period parameters
- The Kalman filter version shows promise but needs refinement
- Focus on timeframes that showed activity (6h, 1h, daily)
""")

if __name__ == "__main__":
    analyze_strategy_results()