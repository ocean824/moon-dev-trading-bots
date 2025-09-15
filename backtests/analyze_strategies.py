import pandas as pd
import os
import numpy as np
from pathlib import Path

# List of strategy CSV files to analyze (excluding summary files)
strategy_files = [
    'AccelerationAO.csv',
    'AccelerationAOKalman.csv',
    'AccelerationBands.csv',
    'AccelerationBandsKalman.csv',
    'AccelerationRSI.csv',
    'BayesianWhaleADXMulti.csv',
    'BayesianWhaleMFIMulti.csv',
    'BayesianWhaleMulti.csv',
    'BollingerBreakoutADX.csv',
    'BollingerBreakoutBase.csv',
    'BollingerBreakoutKalman.csv',
    'BollingerBreakoutMACD.csv',
    'CMMACDUltimate.csv',
    'CamarillaPivot80Percent.csv',
    'CamarillaPivotKalman.csv',
    'CamarillaPivotLongOnly.csv',
    'CamarillaPivotLongShort.csv',
    'CamarillaPivotMFI.csv',
    'DynamicSwingVWAP_ADX.csv',
    'DynamicSwingVWAP_Base.csv',
    'DynamicSwingVWAP_MFI.csv',
    'DynamicSwingVWAP_VWAP.csv',
    'ExhaustionGapBayesian.csv',
    'FalseBreakoutADX.csv',
    'FalseBreakoutKalman.csv',
    'FalseBreakoutMFI.csv',
    'FalseBreakoutReversal.csv',
    'FibonacciPivotADX.csv',
    'FibonacciPivotBoth.csv',
    'FibonacciPivotKalman.csv',
    'FibonacciPivotLong.csv',
    'FibonacciPivotMFI.csv',
    'FlawlessVictoryV1.csv',
    'FlawlessVictoryV2.csv',
    'FlawlessVictoryV3.csv',
    'MomentumCrossImpulseMACD.csv',
    'MomentumCrossImpulseMACDKalman.csv',
    'MomentumCrossStochasticDivKalman.csv',
    'MomentumCrossTripleEMA.csv',
    'MomentumCrossTripleEMAKalman.csv',
    'MutanabbyADX.csv',
    'MutanabbyUltimate.csv',
    'NadarayaWatsonEnvelope.csv',
    'NadarayaWatsonEnvelopeKalman.csv',
    'NadarayaWatsonReversal.csv',
    'NadarayaWatsonReversalLongOnly.csv',
    'ParabolicSARADX.csv',
    'ParabolicSARBoth.csv',
    'ParabolicSARKalman.csv',
    'ParabolicSARLong.csv',
    'ParabolicSARMFI.csv',
    'SmartMoneyConcepts.csv',
    'SqueezeMomentum.csv',
    'SqueezeSMCCombined.csv',
    'SwingVWAPADX.csv',
    'VolatilityBreakoutADX.csv',
    'VolatilityBreakoutATR.csv',
    'VolatilityBreakoutKalman.csv',
    'VolatilityBreakoutMFI.csv',
    'ZeroLagTEMAADXStrategy.csv',
    'ZeroLagTEMAMFIStrategy.csv',
    'ZeroLagTEMAStrategy.csv',
    'ZeroLagTEMA_ADX.csv',
    'ZeroLagTEMA_Base.csv',
    'ZeroLagTEMA_MFI.csv'
]

results_dir = Path('results')
strategy_scores = {}

for file in strategy_files:
    filepath = results_dir / file
    if not filepath.exists():
        print(f"File not found: {file}")
        continue

    try:
        df = pd.read_csv(filepath)

        # Get strategy name
        strategy_name = file.replace('.csv', '')

        # Calculate metrics for scoring
        positive_returns = []
        sharpe_ratios = []
        win_rates = []

        # Check for common column names
        for col in df.columns:
            if 'Return [%]' in col or 'return' in col.lower():
                returns = df[col].dropna()
                positive_returns.extend(returns[returns > 0])
            elif 'sharpe' in col.lower():
                sharpe_ratios.extend(df[col].dropna())
            elif 'win rate' in col.lower() or 'winrate' in col.lower():
                win_rates.extend(df[col].dropna())

        # Calculate overall score
        avg_positive_return = np.mean(positive_returns) if positive_returns else 0
        positive_rate = len(positive_returns) / len(df) if len(df) > 0 else 0
        avg_sharpe = np.mean(sharpe_ratios) if sharpe_ratios else 0
        avg_win_rate = np.mean(win_rates) if win_rates else 0

        # Composite score (weighted average)
        score = (avg_positive_return * 0.4 +
                positive_rate * 100 * 0.3 +
                avg_sharpe * 10 * 0.2 +
                avg_win_rate * 0.1)

        strategy_scores[strategy_name] = {
            'avg_positive_return': avg_positive_return,
            'positive_rate': positive_rate,
            'avg_sharpe': avg_sharpe,
            'avg_win_rate': avg_win_rate,
            'composite_score': score,
            'num_datasets': len(df)
        }

    except Exception as e:
        print(f"Error processing {file}: {e}")

# Sort strategies by composite score
sorted_strategies = sorted(strategy_scores.items(), key=lambda x: x[1]['composite_score'], reverse=True)

print("\n" + "="*80)
print("TOP 5 TRADING STRATEGIES BY OVERALL PERFORMANCE")
print("="*80)

for i, (strategy, metrics) in enumerate(sorted_strategies[:5], 1):
    print(f"\n{i}. {strategy}")
    print(f"   Composite Score: {metrics['composite_score']:.2f}")
    print(f"   Avg Positive Return: {metrics['avg_positive_return']:.2f}%")
    print(f"   Positive Rate: {metrics['positive_rate']*100:.1f}%")
    print(f"   Avg Sharpe Ratio: {metrics['avg_sharpe']:.2f}")
    print(f"   Datasets Tested: {metrics['num_datasets']}")

print("\n" + "="*80)
print("All Strategies Ranked by Performance:")
print("="*80)

for i, (strategy, metrics) in enumerate(sorted_strategies, 1):
    print(f"{i:2d}. {strategy:40s} Score: {metrics['composite_score']:6.2f} | Datasets: {metrics['num_datasets']:3d}")