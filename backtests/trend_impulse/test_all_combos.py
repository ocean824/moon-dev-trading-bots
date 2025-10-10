"""
Quick test script to run all Trend Impulse combination strategies
==================================================================
Tests each strategy on a single dataset for quick comparison.
"""

import pandas as pd
from backtesting import Backtest
import warnings
warnings.filterwarnings('ignore')

# Import all strategies
from trend_impulse_adx_combo import TrendImpulseADXCombo
from trend_impulse_mfi_combo import TrendImpulseMFICombo
from trend_impulse_rsi_macd_combo import TrendImpulseRSIMACDCombo
from trend_impulse_bbands_combo import TrendImpulseBBandsCombo

print("🚀 Testing All Trend Impulse Combination Strategies 🌙")
print("="*80)

# Load data once
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'
print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows\n")

# Test each strategy
strategies = [
    ('ADX Combo', TrendImpulseADXCombo),
    ('MFI Combo', TrendImpulseMFICombo),
    ('RSI/MACD Combo', TrendImpulseRSIMACDCombo),
    ('Bollinger Bands Combo', TrendImpulseBBandsCombo),
]

results = []

for name, strategy in strategies:
    print(f"Testing {name}...")
    try:
        bt = Backtest(data, strategy, cash=10000000, commission=0.00045)
        stats = bt.run()

        results.append({
            'Strategy': name,
            'Return %': round(stats['Return [%]'], 2) if 'Return [%]' in stats else 0,
            'Sharpe': round(stats['Sharpe Ratio'], 3) if 'Sharpe Ratio' in stats and not pd.isna(stats['Sharpe Ratio']) else 0,
            'Max DD %': round(stats['Max. Drawdown [%]'], 2) if 'Max. Drawdown [%]' in stats else 0,
            'Trades': stats['# Trades'] if '# Trades' in stats else 0,
            'Win Rate %': round(stats['Win Rate [%]'], 2) if 'Win Rate [%]' in stats and not pd.isna(stats['Win Rate [%]']) else 0,
            'Profit Factor': round(stats['Profit Factor'], 3) if 'Profit Factor' in stats and not pd.isna(stats['Profit Factor']) else 0,
        })
        print(f"   ✓ Return: {results[-1]['Return %']}%")
        print(f"   ✓ Trades: {results[-1]['Trades']}")
        print(f"   ✓ Win Rate: {results[-1]['Win Rate %']}%\n")

    except Exception as e:
        print(f"   ✗ Error: {e}\n")
        results.append({
            'Strategy': name,
            'Return %': 'Error',
            'Sharpe': 'Error',
            'Max DD %': 'Error',
            'Trades': 'Error',
            'Win Rate %': 'Error',
            'Profit Factor': 'Error',
        })

# Display summary
print("\n" + "="*80)
print("SUMMARY OF ALL TREND IMPULSE COMBINATION STRATEGIES")
print("="*80)

df = pd.DataFrame(results)
print(df.to_string())

print("\n" + "="*80)
print("KEY INSIGHTS:")
print("="*80)

# Find best performing strategy
if len(results) > 0:
    # Filter out error results
    valid_results = [r for r in results if r['Return %'] != 'Error']

    if valid_results:
        best_return = max(valid_results, key=lambda x: x['Return %'])
        most_trades = max(valid_results, key=lambda x: x['Trades'])
        best_win_rate = max(valid_results, key=lambda x: x['Win Rate %'])

        print(f"📈 Best Return: {best_return['Strategy']} with {best_return['Return %']}%")
        print(f"🎯 Best Win Rate: {best_win_rate['Strategy']} with {best_win_rate['Win Rate %']}%")
        print(f"📊 Most Active: {most_trades['Strategy']} with {most_trades['Trades']} trades")

print("\n✅ Testing Complete!")