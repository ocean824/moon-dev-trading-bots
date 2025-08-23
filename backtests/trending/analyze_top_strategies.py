#!/usr/bin/env python3
"""
Data Science Analysis: Find Top 10 Trading Strategies
Based on weighted scoring of Return, Drawdown, Sortino, and Expectancy
"""

import pandas as pd
import numpy as np

# Load the data
data_file = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/backtests/trending/results/ALL_TRENDING_STRATEGIES.csv'
df = pd.read_csv(data_file)

print("="*80)
print("🔬 DATA SCIENCE ANALYSIS: TOP 10 TRADING STRATEGIES")
print("="*80)

# Create composite scoring system
def calculate_strategy_score(row):
    """
    Calculate weighted score for each strategy based on:
    - Return% (30% weight) - Higher is better
    - Max Drawdown (25% weight) - Lower is better (inverted)
    - Sortino Ratio (25% weight) - Higher is better  
    - Expectancy% (20% weight) - Higher is better
    
    All metrics normalized to 0-100 scale
    """
    score = 0
    
    # Return component (30%)
    # Cap extreme returns at 500% for normalization
    return_score = min(max(row['Return_%'], -100), 500) / 5  # Scale to 0-100
    if return_score > 0:
        score += return_score * 0.30
    
    # Drawdown component (25%) - Inverted (lower drawdown = higher score)
    # Best case 0% DD = 100 points, worst case -100% DD = 0 points
    dd_score = max(100 + row['Max_DD_%'], 0)  # 0% DD = 100, -100% DD = 0
    score += dd_score * 0.25
    
    # Sortino component (25%)
    # Normalize Sortino 0-3 range to 0-100
    sortino_score = min(max(row['Sortino'], 0), 3) * 33.33
    score += sortino_score * 0.25
    
    # Expectancy component (20%)
    # Cap at 10% expectancy = 100 points
    exp_score = min(max(row['Expectancy_%'], -10), 10) * 10
    if exp_score > 0:
        score += exp_score * 0.20
    
    return score

# Calculate scores for all strategies
df['Composite_Score'] = df.apply(calculate_strategy_score, axis=1)

# Additional risk-adjusted metrics
df['Return_DD_Ratio'] = df['Return_%'] / abs(df['Max_DD_%'])
df['Risk_Adjusted_Return'] = df['Return_%'] * (1 - abs(df['Max_DD_%'])/100)

# Get average scores by strategy across all data sources
strategy_summary = df.groupby('Strategy').agg({
    'Return_%': 'mean',
    'Max_DD_%': 'mean',
    'Sortino': 'mean',
    'Expectancy_%': 'mean',
    'Sharpe': 'mean',
    'Profit_Factor': 'mean',
    'Win_Rate_%': 'mean',
    'Composite_Score': 'mean',
    'Return_DD_Ratio': 'mean',
    'Risk_Adjusted_Return': 'mean',
    'Trades': 'sum',
    'Data_Source': 'count'  # Number of data sources tested
}).round(2)

strategy_summary.columns = ['Avg_Return%', 'Avg_MaxDD%', 'Avg_Sortino', 'Avg_Expectancy%', 
                            'Avg_Sharpe', 'Avg_ProfitFactor', 'Avg_WinRate%', 
                            'Composite_Score', 'Return_DD_Ratio', 'Risk_Adj_Return',
                            'Total_Trades', 'Data_Sources']

# Sort by composite score
strategy_summary = strategy_summary.sort_values('Composite_Score', ascending=False)

# Display top 10 strategies
print("\n🏆 TOP 10 STRATEGIES BY COMPOSITE SCORE")
print("Scoring weights: Return(30%), MaxDD(25%), Sortino(25%), Expectancy(20%)")
print("-"*80)

top_10 = strategy_summary.head(10)

for i, (strategy, row) in enumerate(top_10.iterrows(), 1):
    print(f"\n#{i} {strategy}")
    print(f"   📊 Composite Score: {row['Composite_Score']:.2f}/100")
    print(f"   💰 Avg Return: {row['Avg_Return%']:.2f}%")
    print(f"   📉 Avg Max DD: {row['Avg_MaxDD%']:.2f}%")
    print(f"   📈 Sortino: {row['Avg_Sortino']:.3f}")
    print(f"   🎯 Expectancy: {row['Avg_Expectancy%']:.3f}%")
    print(f"   ⚖️ Return/DD Ratio: {row['Return_DD_Ratio']:.3f}")
    print(f"   🛡️ Risk-Adj Return: {row['Risk_Adj_Return']:.2f}%")
    print(f"   📋 Total Trades: {int(row['Total_Trades'])}")
    print(f"   🎲 Win Rate: {row['Avg_WinRate%']:.1f}%")

# Detailed table view
print("\n" + "="*80)
print("DETAILED METRICS TABLE - TOP 10 STRATEGIES")
print("="*80)
display_cols = ['Composite_Score', 'Avg_Return%', 'Avg_MaxDD%', 'Avg_Sortino', 
                'Avg_Expectancy%', 'Return_DD_Ratio', 'Avg_WinRate%', 'Total_Trades']
print(top_10[display_cols].to_string())

# Best strategy per category analysis
print("\n" + "="*80)
print("CATEGORY WINNERS")
print("="*80)

# Add category to dataframe
df_with_cat = df.merge(
    pd.DataFrame(strategy_summary.index.tolist(), columns=['Strategy']).reset_index(),
    on='Strategy', how='left'
)

categories = df['Category'].unique()
for category in categories:
    cat_data = df[df['Category'] == category].copy()
    cat_data['Composite_Score'] = cat_data.apply(calculate_strategy_score, axis=1)
    cat_summary = cat_data.groupby('Strategy')['Composite_Score'].mean().sort_values(ascending=False)
    
    if len(cat_summary) > 0:
        winner = cat_summary.index[0]
        score = cat_summary.iloc[0]
        winner_stats = strategy_summary.loc[winner]
        
        print(f"\n{category}:")
        print(f"  🥇 Winner: {winner}")
        print(f"  Score: {score:.2f} | Return: {winner_stats['Avg_Return%']:.2f}% | DD: {winner_stats['Avg_MaxDD%']:.2f}%")

# Performance by data source
print("\n" + "="*80)
print("BEST PERFORMERS BY ASSET CLASS")
print("="*80)

# Group by asset type
btc_strategies = df[df['Data_Source'].str.contains('BTC')].groupby('Strategy')['Composite_Score'].mean().sort_values(ascending=False).head(3)
eth_strategies = df[df['Data_Source'].str.contains('ETH')].groupby('Strategy')['Composite_Score'].mean().sort_values(ascending=False).head(3)
sol_strategies = df[df['Data_Source'].str.contains('SOL')].groupby('Strategy')['Composite_Score'].mean().sort_values(ascending=False).head(3)
stock_strategies = df[df['Data_Source'].str.contains('AAPL|TSLA|GOOG|NVDA|ES|NQ')].groupby('Strategy')['Composite_Score'].mean().sort_values(ascending=False).head(3)

print("\n🪙 BTC Top 3:")
for i, (strat, score) in enumerate(btc_strategies.items(), 1):
    print(f"  {i}. {strat}: {score:.2f}")

print("\n💎 ETH Top 3:")
for i, (strat, score) in enumerate(eth_strategies.items(), 1):
    print(f"  {i}. {strat}: {score:.2f}")

print("\n☀️ SOL Top 3:")
for i, (strat, score) in enumerate(sol_strategies.items(), 1):
    print(f"  {i}. {strat}: {score:.2f}")

print("\n📈 Stocks/Futures Top 3:")
for i, (strat, score) in enumerate(stock_strategies.items(), 1):
    print(f"  {i}. {strat}: {score:.2f}")

print("\n" + "="*80)
print("ANALYSIS COMPLETE")
print("="*80)
print("\n💡 Key Insights:")
print("- Composite scoring balances return potential with risk management")
print("- Top strategies show consistent performance across multiple timeframes")
print("- Return/DD ratio indicates efficiency of capital deployment")
print("- Sortino ratio focuses on downside volatility (more relevant for trading)")
print("="*80)