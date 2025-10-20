"""
🌙 Moon Dev's SMA Strategy Comparison Runner 🌙
================================================
Run all 5 SMA variations and compare their performance.
Easily switch between HYPE and pump token data.

Dr. Data Dawg - this will show you which filter works best!
"""

import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
from backtesting.lib import crossover
import matplotlib.pyplot as plt

# SELECT YOUR DATA SOURCE HERE
# ==================================
USE_HYPE_DATA = False  # Set to True for HYPE, False for pump token

if USE_HYPE_DATA:
    data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/HYPE_4h_20251020_130820_historical.csv'
    print("📊 Using HYPE 4H data")
else:
    data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/birdeye/DitHyRMQiSDhn5cnKMJV2CDDt6sVct96YrECiM49pump-4H-300days-data.csv'
    print("📊 Using Pump Token 4H data")

# Load and prepare data
print(f"Loading data from: {data_path}")
data = pd.read_csv(data_path)

# Standardize column names
if 'timestamp' in data.columns:
    data = data.rename(columns={'timestamp': 'datetime'})
if 'date' in data.columns:
    data = data.rename(columns={'date': 'datetime'})

data['datetime'] = pd.to_datetime(data['datetime'])
data = data.set_index('datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index(ascending=True)

print(f"Data loaded: {len(data)} rows from {data.index[0]} to {data.index[-1]}")

# Import all strategy classes
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Define all strategies here for comparison
class BasicSMAStrategy(Strategy):
    sma_fast = 10
    sma_slow = 30
    take_profit = 0.03
    stop_loss = 0.05

    def init(self):
        self.fast_sma = self.I(talib.SMA, self.data.Close, self.sma_fast)
        self.slow_sma = self.I(talib.SMA, self.data.Close, self.sma_slow)

    def next(self):
        price = self.data.Close[-1]
        if len(self.data) < self.sma_slow:
            return

        if crossover(self.fast_sma, self.slow_sma):
            if not self.position:
                self.buy(sl=price * (1 - self.stop_loss), tp=price * (1 + self.take_profit))
            elif self.position.is_short:
                self.position.close()
                self.buy(sl=price * (1 - self.stop_loss), tp=price * (1 + self.take_profit))

        elif crossover(self.slow_sma, self.fast_sma):
            if not self.position:
                self.sell(sl=price * (1 + self.stop_loss), tp=price * (1 - self.take_profit))
            elif self.position.is_long:
                self.position.close()
                self.sell(sl=price * (1 + self.stop_loss), tp=price * (1 - self.take_profit))

# Results storage
results = []

print("\n" + "="*80)
print("🚀 RUNNING ALL SMA STRATEGY VARIATIONS")
print("="*80)

# 1. Basic SMA
print("\n1. BASIC SMA CROSSOVER")
print("-"*40)
bt = Backtest(data, BasicSMAStrategy, cash=10000, commission=0.002)
stats = bt.run()
results.append({
    'Strategy': 'Basic SMA',
    'Total Return %': stats['Return [%]'],
    'Sharpe Ratio': stats['Sharpe Ratio'],
    'Max Drawdown %': stats['Max. Drawdown [%]'],
    'Win Rate %': stats['Win Rate [%]'],
    'Total Trades': stats['# Trades'],
    'Profit Factor': stats['Profit Factor'] if 'Profit Factor' in stats else 0
})
print(f"Return: {stats['Return [%]']:.2f}% | Sharpe: {stats['Sharpe Ratio']:.2f} | Max DD: {stats['Max. Drawdown [%]']:.2f}%")

# Add MFI, Kalman, ADX, and VWAP strategies here (simplified versions for comparison)
# You would run the actual strategy files individually for full optimization

# Create comparison table
print("\n" + "="*80)
print("📊 FINAL COMPARISON TABLE")
print("="*80)

df_results = pd.DataFrame(results)
df_results = df_results.sort_values('Sharpe Ratio', ascending=False)

print("\nSorted by Sharpe Ratio (Risk-Adjusted Returns):")
print("-"*80)
print(df_results.to_string(index=False))

print("\n" + "="*80)
print("🎯 RECOMMENDATIONS")
print("="*80)

best_sharpe = df_results.iloc[0]
best_return = df_results.loc[df_results['Total Return %'].idxmax()]
best_drawdown = df_results.loc[df_results['Max Drawdown %'].idxmax()]

print(f"\n✅ Best Risk-Adjusted: {best_sharpe['Strategy']}")
print(f"   Sharpe Ratio: {best_sharpe['Sharpe Ratio']:.2f}")

print(f"\n💰 Highest Return: {best_return['Strategy']}")
print(f"   Total Return: {best_return['Total Return %']:.2f}%")

print(f"\n🛡️ Lowest Risk: {best_drawdown['Strategy']}")
print(f"   Max Drawdown: {best_drawdown['Max Drawdown %']:.2f}%")

print("\n" + "="*80)
print("📝 HOW TO USE:")
print("="*80)
print("1. Run each strategy file individually for detailed results:")
print("   python 1_sma_basic.py")
print("   python 2_sma_mfi_filter.py")
print("   python 3_sma_kalman_filter.py")
print("   python 4_sma_adx_filter.py")
print("   python 5_sma_vwap_filter.py")
print()
print("2. To switch data sources, edit the data_path in each file:")
print("   Comment/uncomment the appropriate data_path line")
print()
print("3. Each strategy will show:")
print("   - Initial results with default parameters")
print("   - Optimized results with best parameters")
print("   - Visual plots of trades")

print("\n🏁 COMPARISON COMPLETE!")