"""
Quick test of FVG strategies on a single dataset
"""

import pandas as pd
import numpy as np
from backtesting import Backtest
from fvg_base import FVGBase
from fvg_mfi import FVGMFI
from fvg_adx import FVGADX
from fvg_kalman import FVGKalman

# Load data
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'
print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows")

# Test each strategy
strategies = {
    'FVG_Base': FVGBase,
    'FVG_MFI': FVGMFI,
    'FVG_ADX': FVGADX,
    'FVG_Kalman': FVGKalman
}

print("\n" + "="*60)
print("Testing FVG Strategies on BTC 1H Data")
print("="*60)

for name, strategy_class in strategies.items():
    print(f"\n🔍 Testing {name}...")
    try:
        bt = Backtest(data, strategy_class, cash=1000000, commission=0.00045)
        stats = bt.run()

        # Print key metrics
        print(f"✅ {name} Results:")
        print(f"   Return: {stats['Return [%]']:.2f}%")
        print(f"   Sharpe Ratio: {stats['Sharpe Ratio']:.2f}")
        print(f"   Max Drawdown: {stats['Max. Drawdown [%]']:.2f}%")
        print(f"   Win Rate: {stats['Win Rate [%]']:.1f}%")
        print(f"   # Trades: {stats['# Trades']}")

    except Exception as e:
        print(f"❌ Error with {name}: {str(e)[:100]}")

print("\n✅ Quick test complete!")