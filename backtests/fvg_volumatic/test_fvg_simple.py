#!/usr/bin/env python3
"""
Simple test of FVG strategies without optimization
"""

import pandas as pd
from backtesting import Backtest
from fvg_base import FVGBase
from fvg_mfi import FVGMFI
from fvg_adx import FVGADX
from fvg_kalman import FVGKalman

def test_strategy(strategy_class, data, name):
    """Test a single strategy"""
    print(f"\n{'='*60}")
    print(f"Testing {name}")
    print('='*60)

    bt = Backtest(data, strategy_class, cash=1000000, commission=0.002)
    stats = bt.run()

    # Print key metrics
    print(f"Return: {stats['Return [%]']:.2f}%")
    print(f"Buy & Hold: {stats['Buy & Hold Return [%]']:.2f}%")
    print(f"Sharpe Ratio: {stats['Sharpe Ratio']:.2f}")
    print(f"Max Drawdown: {stats['Max. Drawdown [%]']:.2f}%")
    print(f"Win Rate: {stats['Win Rate [%]']:.1f}%")
    print(f"# Trades: {stats['# Trades']}")
    print(f"Profit Factor: {stats['Profit Factor']:.2f}")

    return stats

if __name__ == "__main__":
    # Load data
    print("📊 Loading BTC hourly data...")
    data = pd.read_csv('/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv')
    data.index = pd.to_datetime(data.index)

    # Use recent data only for faster testing
    data = data.tail(10000)
    print(f"✅ Using recent {len(data)} bars for testing")

    # Test all strategies
    strategies = [
        (FVGBase, "FVG Base"),
        (FVGMFI, "FVG + MFI"),
        (FVGADX, "FVG + ADX"),
        (FVGKalman, "FVG + Kalman Filter")
    ]

    results = {}
    for strategy_class, name in strategies:
        stats = test_strategy(strategy_class, data, name)
        results[name] = stats

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY COMPARISON")
    print('='*60)
    print(f"{'Strategy':<20} {'Return':<12} {'Sharpe':<10} {'Win Rate':<10} {'Trades':<10}")
    print('-'*60)

    for name, stats in results.items():
        print(f"{name:<20} {stats['Return [%]']:>10.2f}% {stats['Sharpe Ratio']:>10.2f} {stats['Win Rate [%]']:>9.1f}% {stats['# Trades']:>10}")

    print("\n✅ All tests complete!")