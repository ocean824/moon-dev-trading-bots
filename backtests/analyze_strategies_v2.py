import pandas as pd
import numpy as np
from pathlib import Path

# List of strategy CSV files to analyze
strategy_files = [
    'AccelerationAO.csv', 'AccelerationAOKalman.csv', 'AccelerationBands.csv',
    'AccelerationBandsKalman.csv', 'AccelerationRSI.csv',
    'BayesianWhaleADXMulti.csv', 'BayesianWhaleMFIMulti.csv', 'BayesianWhaleMulti.csv',
    'BollingerBreakoutADX.csv', 'BollingerBreakoutBase.csv', 'BollingerBreakoutKalman.csv',
    'BollingerBreakoutMACD.csv', 'CMMACDUltimate.csv',
    'CamarillaPivot80Percent.csv', 'CamarillaPivotKalman.csv', 'CamarillaPivotLongOnly.csv',
    'CamarillaPivotLongShort.csv', 'CamarillaPivotMFI.csv',
    'DynamicSwingVWAP_ADX.csv', 'DynamicSwingVWAP_Base.csv', 'DynamicSwingVWAP_MFI.csv',
    'DynamicSwingVWAP_VWAP.csv', 'ExhaustionGapBayesian.csv',
    'FalseBreakoutADX.csv', 'FalseBreakoutKalman.csv', 'FalseBreakoutMFI.csv',
    'FalseBreakoutReversal.csv', 'FibonacciPivotADX.csv', 'FibonacciPivotBoth.csv',
    'FibonacciPivotKalman.csv', 'FibonacciPivotLong.csv', 'FibonacciPivotMFI.csv',
    'FlawlessVictoryV1.csv', 'FlawlessVictoryV2.csv', 'FlawlessVictoryV3.csv',
    'MomentumCrossImpulseMACD.csv', 'MomentumCrossImpulseMACDKalman.csv',
    'MomentumCrossStochasticDivKalman.csv', 'MomentumCrossTripleEMA.csv',
    'MomentumCrossTripleEMAKalman.csv', 'MutanabbyADX.csv', 'MutanabbyUltimate.csv',
    'NadarayaWatsonEnvelope.csv', 'NadarayaWatsonEnvelopeKalman.csv',
    'NadarayaWatsonReversal.csv', 'NadarayaWatsonReversalLongOnly.csv',
    'ParabolicSARADX.csv', 'ParabolicSARBoth.csv', 'ParabolicSARKalman.csv',
    'ParabolicSARLong.csv', 'ParabolicSARMFI.csv',
    'SmartMoneyConcepts.csv', 'SqueezeMomentum.csv', 'SqueezeSMCCombined.csv',
    'SwingVWAPADX.csv', 'VolatilityBreakoutADX.csv', 'VolatilityBreakoutATR.csv',
    'VolatilityBreakoutKalman.csv', 'VolatilityBreakoutMFI.csv',
    'ZeroLagTEMAADXStrategy.csv', 'ZeroLagTEMAMFIStrategy.csv', 'ZeroLagTEMAStrategy.csv',
    'ZeroLagTEMA_ADX.csv', 'ZeroLagTEMA_Base.csv', 'ZeroLagTEMA_MFI.csv'
]

results_dir = Path('results')
strategy_metrics = {}

print("Analyzing strategy performance across datasets...")
print("-" * 80)

for file in strategy_files:
    filepath = results_dir / file
    if not filepath.exists():
        continue

    try:
        df = pd.read_csv(filepath)
        strategy_name = file.replace('.csv', '')

        # Extract key metrics
        returns = []
        sharpe_ratios = []
        win_rates = []
        profit_factors = []
        max_drawdowns = []

        # Handle different column names
        return_col = 'Return_%' if 'Return_%' in df.columns else 'Return_[%]' if 'Return_[%]' in df.columns else None
        sharpe_col = 'Sharpe' if 'Sharpe' in df.columns else None
        win_rate_col = 'Win_Rate_%' if 'Win_Rate_%' in df.columns else 'Win_Rate_[%]' if 'Win_Rate_[%]' in df.columns else None
        pf_col = 'Profit_Factor' if 'Profit_Factor' in df.columns else None
        dd_col = 'Max_DD_%' if 'Max_DD_%' in df.columns else 'Max_DD_[%]' if 'Max_DD_[%]' in df.columns else None

        if return_col:
            # Filter out extreme outliers (returns > 10000%)
            raw_returns = df[return_col].replace([np.inf, -np.inf], np.nan).dropna()
            reasonable_returns = raw_returns[raw_returns < 10000]
            returns = reasonable_returns.tolist()

        if sharpe_col:
            raw_sharpe = df[sharpe_col].replace([np.inf, -np.inf], np.nan).dropna()
            reasonable_sharpe = raw_sharpe[(raw_sharpe > -10) & (raw_sharpe < 10)]
            sharpe_ratios = reasonable_sharpe.tolist()

        if win_rate_col:
            win_rates = df[win_rate_col].dropna().tolist()

        if pf_col:
            raw_pf = df[pf_col].replace([np.inf, -np.inf], np.nan).dropna()
            reasonable_pf = raw_pf[(raw_pf > 0) & (raw_pf < 100)]
            profit_factors = reasonable_pf.tolist()

        if dd_col:
            max_drawdowns = df[dd_col].dropna().abs().tolist()

        # Calculate statistics
        if len(returns) > 0:
            avg_return = np.mean(returns)
            median_return = np.median(returns)
            positive_count = sum(1 for r in returns if r > 0)
            positive_rate = positive_count / len(returns) * 100
        else:
            avg_return = median_return = positive_rate = 0

        avg_sharpe = np.mean(sharpe_ratios) if sharpe_ratios else 0
        avg_win_rate = np.mean(win_rates) if win_rates else 0
        avg_profit_factor = np.mean(profit_factors) if profit_factors else 0
        avg_max_dd = np.mean(max_drawdowns) if max_drawdowns else 0

        # Calculate composite score with reasonable weights
        score = (
            min(avg_return, 1000) * 0.25 +  # Cap return contribution
            positive_rate * 0.20 +           # How often strategy is profitable
            avg_sharpe * 20 * 0.20 +         # Risk-adjusted returns
            avg_win_rate * 0.15 +            # Win rate
            min(avg_profit_factor, 10) * 10 * 0.10 +  # Profit factor
            max(0, 100 - avg_max_dd) * 0.10  # Drawdown penalty
        )

        strategy_metrics[strategy_name] = {
            'avg_return': avg_return,
            'median_return': median_return,
            'positive_rate': positive_rate,
            'avg_sharpe': avg_sharpe,
            'avg_win_rate': avg_win_rate,
            'avg_profit_factor': avg_profit_factor,
            'avg_max_dd': avg_max_dd,
            'composite_score': score,
            'num_datasets': len(df),
            'num_profitable': positive_count
        }

    except Exception as e:
        print(f"Error processing {file}: {e}")

# Sort strategies by composite score
sorted_strategies = sorted(strategy_metrics.items(), key=lambda x: x[1]['composite_score'], reverse=True)

print("\n" + "="*100)
print("TOP 5 TRADING STRATEGIES BY OVERALL PERFORMANCE")
print("="*100)

for i, (strategy, metrics) in enumerate(sorted_strategies[:5], 1):
    print(f"\n{i}. {strategy}")
    print(f"   Composite Score:     {metrics['composite_score']:.2f}")
    print(f"   Average Return:      {metrics['avg_return']:.2f}%")
    print(f"   Median Return:       {metrics['median_return']:.2f}%")
    print(f"   Profitable Rate:     {metrics['positive_rate']:.1f}% ({metrics['num_profitable']}/{metrics['num_datasets']} datasets)")
    print(f"   Avg Sharpe Ratio:    {metrics['avg_sharpe']:.2f}")
    print(f"   Avg Win Rate:        {metrics['avg_win_rate']:.1f}%")
    print(f"   Avg Profit Factor:   {metrics['avg_profit_factor']:.2f}")
    print(f"   Avg Max Drawdown:    {metrics['avg_max_dd']:.1f}%")

print("\n" + "="*100)
print("COMPLETE RANKING OF ALL STRATEGIES")
print("="*100)
print(f"{'Rank':<5} {'Strategy':<40} {'Score':<10} {'Avg Return':<12} {'Win Rate':<10} {'Datasets':<10}")
print("-"*100)

for i, (strategy, metrics) in enumerate(sorted_strategies, 1):
    print(f"{i:<5} {strategy:<40} {metrics['composite_score']:<10.2f} "
          f"{metrics['avg_return']:<12.2f} {metrics['avg_win_rate']:<10.1f} "
          f"{metrics['num_datasets']:<10}")

print("\n" + "="*100)
print("KEY INSIGHTS")
print("="*100)

# Find strategies with highest consistency
consistent_strategies = [(s, m) for s, m in sorted_strategies if m['positive_rate'] >= 80][:3]
print("\nMost Consistent Strategies (≥80% profitable across datasets):")
for s, m in consistent_strategies:
    print(f"  • {s}: {m['positive_rate']:.1f}% profitable rate")

# Find strategies with best risk-adjusted returns
best_sharpe = sorted(sorted_strategies, key=lambda x: x[1]['avg_sharpe'], reverse=True)[:3]
print("\nBest Risk-Adjusted Returns (Sharpe Ratio):")
for s, m in best_sharpe:
    print(f"  • {s}: {m['avg_sharpe']:.2f} Sharpe")

# Find strategies with lowest drawdowns
best_dd = sorted(sorted_strategies, key=lambda x: x[1]['avg_max_dd'])[:3]
print("\nLowest Average Drawdowns:")
for s, m in best_dd:
    print(f"  • {s}: {m['avg_max_dd']:.1f}% max drawdown")