#!/usr/bin/env python3
"""
Jim Simons Style Quantitative Analysis: Finding Market Inefficiencies
Focus on: Statistical Significance, Consistency, Sharpe, and Trade Frequency
"""

import pandas as pd
import numpy as np
from scipy import stats

# Load the data
data_file = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/backtests/trending/results/ALL_TRENDING_STRATEGIES.csv'
df = pd.read_csv(data_file)

print("="*80)
print("🧮 JIM SIMONS MEDALLION FUND STYLE ANALYSIS")
print("Finding Statistical Edges in Market Inefficiencies")
print("="*80)

def calculate_simons_score(strategy_df):
    """
    Jim Simons approach focuses on:
    1. High frequency of trades (more data points = statistical significance)
    2. Consistency across timeframes (low variance of returns)
    3. Sharpe ratio (risk-adjusted returns)
    4. Win rate consistency (edge reliability)
    5. Small but consistent edges (many small wins > few big wins)
    """
    scores = []
    
    for strategy in strategy_df['Strategy'].unique():
        strat_data = strategy_df[strategy_df['Strategy'] == strategy]
        
        # Skip if insufficient data
        if len(strat_data) < 3:
            continue
            
        # 1. Trade Frequency Score (25%) - More trades = more statistical significance
        total_trades = strat_data['Trades'].sum()
        freq_score = min(100, (total_trades / 100))  # Cap at 10000 trades
        
        # 2. Return Consistency Score (20%) - Low variance across data sources
        returns = strat_data['Return_%'].values
        if len(returns) > 1 and returns.std() > 0:
            # Coefficient of variation (lower is better)
            cv = abs(returns.std() / (returns.mean() + 0.01))
            consistency_score = max(0, 100 * np.exp(-cv/2))  # Exponential decay
        else:
            consistency_score = 0
            
        # 3. Sharpe Quality Score (20%) - Consistency of Sharpe across sources
        sharpes = strat_data['Sharpe'].values
        positive_sharpes = sharpes[sharpes > 0]
        if len(positive_sharpes) > 0:
            sharpe_score = min(100, positive_sharpes.mean() * 50)
        else:
            sharpe_score = 0
            
        # 4. Win Rate Stability (15%) - Tight distribution around mean
        win_rates = strat_data['Win_Rate_%'].values
        if len(win_rates) > 1:
            wr_std = win_rates.std()
            wr_mean = win_rates.mean()
            if wr_mean > 35 and wr_std < 15:  # Good win rate with low variance
                wr_score = 100 * (wr_mean/50) * np.exp(-wr_std/20)
            else:
                wr_score = wr_mean
        else:
            wr_score = 0
            
        # 5. Edge Persistence (20%) - Positive expectancy consistency
        expectancies = strat_data['Expectancy_%'].values
        positive_exp = (expectancies > 0).sum() / len(expectancies)
        edge_score = positive_exp * 100
        
        # Bonus: Penalize extreme drawdowns (Simons avoids large DDs)
        max_dd = strat_data['Max_DD_%'].mean()
        if max_dd < -50:
            dd_penalty = 0.7  # 30% penalty for excessive risk
        elif max_dd < -40:
            dd_penalty = 0.85
        else:
            dd_penalty = 1.0
            
        # Calculate final Simons score
        simons_score = (
            freq_score * 0.25 +
            consistency_score * 0.20 +
            sharpe_score * 0.20 +
            wr_score * 0.15 +
            edge_score * 0.20
        ) * dd_penalty
        
        # Additional metrics for analysis
        avg_return = strat_data['Return_%'].mean()
        median_return = strat_data['Return_%'].median()
        profit_factor = strat_data['Profit_Factor'].mean()
        
        # Information Ratio proxy (return per unit of tracking error)
        if returns.std() > 0:
            info_ratio = avg_return / returns.std()
        else:
            info_ratio = 0
            
        scores.append({
            'Strategy': strategy,
            'Simons_Score': simons_score,
            'Total_Trades': total_trades,
            'Avg_Return%': avg_return,
            'Median_Return%': median_return,
            'Return_Consistency': consistency_score,
            'Sharpe_Quality': sharpe_score,
            'Win_Rate_Stability': wr_score,
            'Edge_Persistence': edge_score,
            'Avg_Sharpe': strat_data['Sharpe'].mean(),
            'Avg_WinRate%': strat_data['Win_Rate_%'].mean(),
            'Avg_Expectancy%': strat_data['Expectancy_%'].mean(),
            'Avg_MaxDD%': strat_data['Max_DD_%'].mean(),
            'Info_Ratio': info_ratio,
            'Profit_Factor': profit_factor,
            'Data_Sources': len(strat_data)
        })
    
    return pd.DataFrame(scores)

# Calculate Simons scores
simons_df = calculate_simons_score(df)
simons_df = simons_df.sort_values('Simons_Score', ascending=False)

print("\n🎯 JIM SIMONS TOP 10 STRATEGIES")
print("(Based on Statistical Significance & Consistency)")
print("-"*80)

top_10_simons = simons_df.head(10)

for i, idx in enumerate(top_10_simons.index[:10], 1):
    row = top_10_simons.loc[idx]
    print(f"\n#{i} {row['Strategy']}")
    print(f"   🧮 Simons Score: {row['Simons_Score']:.2f}/100")
    print(f"   📊 Total Trades: {int(row['Total_Trades']):,} (Statistical Power)")
    print(f"   📈 Avg Return: {row['Avg_Return%']:.2f}% | Median: {row['Median_Return%']:.2f}%")
    print(f"   🎯 Win Rate: {row['Avg_WinRate%']:.1f}% (Stability: {row['Win_Rate_Stability']:.1f})")
    print(f"   ⚡ Sharpe: {row['Avg_Sharpe']:.3f} (Quality: {row['Sharpe_Quality']:.1f})")
    print(f"   🔄 Edge Persistence: {row['Edge_Persistence']:.1f}% of sources profitable")
    print(f"   📉 Avg Max DD: {row['Avg_MaxDD%']:.2f}%")
    print(f"   📐 Info Ratio: {row['Info_Ratio']:.3f}")

# Detailed comparison table
print("\n" + "="*80)
print("MEDALLION-STYLE METRICS TABLE")
print("="*80)
display_cols = ['Simons_Score', 'Total_Trades', 'Avg_Return%', 'Return_Consistency', 
                'Avg_Sharpe', 'Win_Rate_Stability', 'Edge_Persistence', 'Info_Ratio']
print(top_10_simons[['Strategy'] + display_cols].to_string(index=False))

# Load original top 10 for comparison
original_top_10 = [
    'DonchianLongTrend', 'GoldenCrossTrend', 'MA200LongTrend', 'VolumeMATrend',
    'ADXMATrend', 'BollingerTrend', 'DualMATrend', 'FastMAADXTrend',
    'RSIMATrend', 'FastBBADXTrend'
]

print("\n" + "="*80)
print("COMPARISON: SIMONS VS ORIGINAL APPROACH")
print("="*80)

simons_list = top_10_simons['Strategy'].tolist()

print("\n🆕 New Additions (Simons found, Original missed):")
for strat in simons_list:
    if strat not in original_top_10:
        row = simons_df[simons_df['Strategy'] == strat].iloc[0]
        print(f"  • {strat}")
        print(f"    Why Simons likes it: {int(row['Total_Trades']):,} trades, "
              f"{row['Edge_Persistence']:.0f}% edge persistence, "
              f"Sharpe: {row['Avg_Sharpe']:.3f}")

print("\n❌ Removed from Original (Simons rejected):")
for strat in original_top_10:
    if strat not in simons_list:
        if strat in simons_df['Strategy'].values:
            row = simons_df[simons_df['Strategy'] == strat].iloc[0]
            rank = simons_df[simons_df['Strategy'] == strat].index[0] + 1
            print(f"  • {strat} (Ranked #{rank})")
            print(f"    Why rejected: Score {row['Simons_Score']:.2f}, "
                  f"Trades: {int(row['Total_Trades'])}, "
                  f"Consistency: {row['Return_Consistency']:.1f}")

# Statistical significance analysis
print("\n" + "="*80)
print("STATISTICAL SIGNIFICANCE ANALYSIS")
print("="*80)

for i, idx in enumerate(top_10_simons.head(5).index, 1):
    row = top_10_simons.loc[idx]
    strategy = row['Strategy']
    strat_data = df[df['Strategy'] == strategy]
    returns = strat_data['Return_%'].values
    
    # Calculate t-statistic for returns different from 0
    if len(returns) > 1:
        t_stat, p_value = stats.ttest_1samp(returns, 0)
        confidence = (1 - p_value) * 100
        
        print(f"\n{strategy}:")
        print(f"  Sample Size: {len(returns)} data sources × {int(row['Total_Trades']/len(returns))} avg trades")
        print(f"  T-Statistic: {t_stat:.3f}")
        print(f"  P-Value: {p_value:.4f}")
        print(f"  Statistical Confidence: {confidence:.1f}%")
        if p_value < 0.05:
            print(f"  ✅ STATISTICALLY SIGNIFICANT at 95% confidence")
        else:
            print(f"  ⚠️ Not statistically significant")

# Simons-style insights
print("\n" + "="*80)
print("JIM SIMONS STYLE INSIGHTS")
print("="*80)
print("\n🔬 Key Findings (Medallion Fund Approach):")
print("1. High-frequency strategies provide more statistical significance")
print("2. Consistency across timeframes matters more than peak returns")
print("3. Small edges with high win-rate stability compound effectively")
print("4. Strategies with 10,000+ trades show strongest statistical validity")
print("5. Information Ratio (return/volatility) crucial for position sizing")

print("\n💡 Simons' Top Pick Characteristics:")
top_pick = top_10_simons.iloc[0]
print(f"• {top_pick['Strategy']}: {int(top_pick['Total_Trades']):,} trades")
print(f"• Edge present in {top_pick['Edge_Persistence']:.0f}% of markets")
print(f"• Consistent Sharpe of {top_pick['Avg_Sharpe']:.3f}")
print(f"• Return consistency score: {top_pick['Return_Consistency']:.1f}")

print("\n📊 Portfolio Construction (Simons Style):")
print("• Allocate based on Sharpe × Trade Frequency")
print("• Diversify across uncorrelated strategies")
print("• Scale position size inverse to volatility")
print("• Continuously monitor statistical significance")
print("="*80)