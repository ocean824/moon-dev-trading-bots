"""
Results Combiner
Change the RESULTS_FOLDER path at the top to combine different strategy results
"""

import pandas as pd
import os

# ============================================================================
# CHANGE THIS PATH TO YOUR RESULTS FOLDER
# ============================================================================
RESULTS_FOLDER = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/backtests/consecutive_down/results'

# ============================================================================
# MAIN COMBINING FUNCTION
# ============================================================================

def combine_results():
    """
    Combine all CSV files from the specified results folder
    """
    
    if not os.path.exists(RESULTS_FOLDER):
        print(f"❌ Error: Folder not found: {RESULTS_FOLDER}")
        return None
    
    # Get all CSV files (excluding already combined ones)
    csv_files = [f for f in os.listdir(RESULTS_FOLDER) 
                 if f.endswith('.csv') and not f.startswith('combined')]
    
    if not csv_files:
        print(f"❌ No CSV files found in: {RESULTS_FOLDER}")
        return None
    
    print(f"\n{'='*80}")
    print(f"📊 Combining results from: {RESULTS_FOLDER}")
    print(f"Found {len(csv_files)} strategy files")
    print(f"{'='*80}\n")
    
    all_dataframes = []
    
    for csv_file in csv_files:
        csv_path = os.path.join(RESULTS_FOLDER, csv_file)
        try:
            # Read CSV
            df = pd.read_csv(csv_path)
            
            # Add strategy name (filename without .csv)
            strategy_name = os.path.splitext(csv_file)[0]
            df.insert(0, 'Strategy', strategy_name)
            
            all_dataframes.append(df)
            print(f"✅ {csv_file}: {len(df)} rows")
            
        except Exception as e:
            print(f"❌ Error reading {csv_file}: {e}")
    
    if not all_dataframes:
        print("❌ No data could be loaded")
        return None
    
    # Combine all dataframes
    combined_df = pd.concat(all_dataframes, ignore_index=True)
    
    # Save combined results
    output_path = os.path.join(RESULTS_FOLDER, 'combined_all_strategies.csv')
    combined_df.to_csv(output_path, index=False)
    
    print(f"\n✅ Combined CSV saved to: {output_path}")
    print(f"Total rows: {len(combined_df)}")
    print(f"Strategies: {combined_df['Strategy'].nunique()}")
    
    # Print performance summary
    print("\n" + "="*100)
    print("STRATEGY PERFORMANCE SUMMARY (Average across all data sources):")
    print("="*100)
    
    summary = combined_df.groupby('Strategy').agg({
        'Return_%': 'mean',
        'Buy_Hold_%': 'mean',
        'Sortino': 'mean',
        'Sharpe': 'mean',
        'Max_DD_%': 'mean',
        'Profit_Factor': 'mean',
        'Expectancy_%': 'mean',
        'Win_Rate_%': 'mean',
        'Trades': 'sum'
    }).round(2)
    
    # Sort by average return
    summary = summary.sort_values('Return_%', ascending=False)
    print(summary.to_string())
    
    # Top 10 best individual results
    print("\n" + "="*100)
    print("TOP 10 BEST INDIVIDUAL RESULTS (by Return %):")
    print("="*100)
    
    top10 = combined_df.nlargest(10, 'Return_%')[
        ['Strategy', 'Data_Source', 'Return_%', 'Sortino', 'Sharpe', 'Max_DD_%', 'Trades']
    ]
    print(top10.to_string(index=False))
    
    # Best risk-adjusted returns
    print("\n" + "="*100)
    print("TOP 10 BEST RISK-ADJUSTED (by Sortino Ratio):")
    print("="*100)
    
    best_sortino = combined_df.nlargest(10, 'Sortino')[
        ['Strategy', 'Data_Source', 'Sortino', 'Return_%', 'Max_DD_%', 'Win_Rate_%']
    ]
    print(best_sortino.to_string(index=False))
    
    # Strategy ranking
    print("\n" + "="*100)
    print("OVERALL STRATEGY RANKING (by average Return %):")
    print("="*100)
    
    ranking = summary[['Return_%', 'Sortino', 'Sharpe', 'Max_DD_%', 'Win_Rate_%']].reset_index()
    for i, row in ranking.iterrows():
        print(f"{i+1}. {row['Strategy']}: {row['Return_%']:.2f}% return, "
              f"{row['Sortino']:.3f} Sortino, {row['Max_DD_%']:.2f}% max DD")
    
    return combined_df

# ============================================================================
# RUN THE COMBINER
# ============================================================================

if __name__ == "__main__":
    print("🚀 Moon Dev's Results Combiner")
    print(f"Current folder: {RESULTS_FOLDER}")
    print("Change RESULTS_FOLDER at the top of this file to analyze different strategies\n")
    
    df = combine_results()
    
    if df is not None:
        print("\n" + "="*100)
        print("✅ COMPLETE! Check 'combined_all_strategies.csv' in the results folder")
        print("="*100)