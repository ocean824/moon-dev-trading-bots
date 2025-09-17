"""
Test Bull Bear Sessions Simple on all data sources
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from multi_data_tester import test_on_all_data
from test_single_dataset import BullBearSessionsSimple

print('Testing Bull Bear Sessions Simple on all data sources...')
results = test_on_all_data(BullBearSessionsSimple, 'BullBearSessionsSimple', verbose=True)

if results is not None:
    print('\n' + '='*60)
    print('FINAL RESULTS SUMMARY:')
    print('='*60)
    print(f'Average Return: {results["Return_%"].mean():.2f}%')
    print(f'Average Sharpe: {results["Sharpe"].mean():.3f}')
    print(f'Average Sortino: {results["Sortino"].mean():.3f}')
    print(f'Average Win Rate: {results["Win_Rate_%"].mean():.2f}%')
    print(f'Positive Markets: {(results["Return_%"] > 0).sum()}/{len(results)}')
    print('\n✅ Multi-data test completed successfully!')
else:
    print('❌ Test failed')