"""
Pure Liquidation Contrarian Strategy (Buy the Dip/Sell the Rip)
================================================================

This strategy uses ONLY liquidation data - no OHLCV data.
It trades contrarian to liquidations:
- When long positions are liquidated → BUY (dip buying)
- When short positions are liquidated → SELL (rip selling)

The theory: Liquidations represent forced selling/buying that creates temporary price extremes.
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
from backtesting.lib import crossover
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Pure Liquidation CONTRARIAN Strategy 🌙")
print("Theory: Buy when longs are liquidated, Sell when shorts are liquidated")
print("=" * 70)

# # Load liquidation data
# LIQUIDATION_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/backtests/liquidations/results/all_liquidations.csv'
# 
# # Try to load all liquidations first, fall back to 90-day data if not available
# try:
#     liq_data = pd.read_csv(LIQUIDATION_PATH)
#     print(f"✅ Loaded ALL liquidation data from: {LIQUIDATION_PATH}")
# except:
#     LIQUIDATION_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/backtests/liquidations/data/liquidations_90days.csv'
#     liq_data = pd.read_csv(LIQUIDATION_PATH)
#     print(f"📊 Loaded 90-day liquidation data from: {LIQUIDATION_PATH}")
# 
# # Process liquidation data
# if len(liq_data.columns) >= 13:
#     column_names = ['symbol', 'side', 'order_type', 'time_in_force', 'quantity',
#                    'price', 'avg_price', 'status', 'filled_qty', 'total_qty',
#                    'timestamp_ms', 'usd_value', 'datetime']
#     liq_data.columns = column_names[:len(liq_data.columns)]
# 
# # Convert to proper types
# liq_data['datetime'] = pd.to_datetime(liq_data['datetime'])
# liq_data['usd_value'] = pd.to_numeric(liq_data['usd_value'], errors='coerce')
# liq_data['price'] = pd.to_numeric(liq_data['price'], errors='coerce')
# 
# # Sort by datetime
# liq_data = liq_data.sort_values('datetime')
# 
# print(f"📊 Total liquidations: {len(liq_data):,}")
# print(f"📅 Date range: {liq_data['datetime'].min()} → {liq_data['datetime'].max()}")
# 
# # Create hourly aggregated data for backtesting
# print("\n🔧 Creating hourly aggregated liquidation data...")
# 
# # Group by hour and aggregate liquidations
# liq_data['hour'] = liq_data['datetime'].dt.floor('H')
# 
# # Aggregate by hour
# hourly_data = []
# 
# for hour in pd.date_range(start=liq_data['hour'].min(), end=liq_data['hour'].max(), freq='H'):
#     hour_liqs = liq_data[liq_data['hour'] == hour]
# 
#     if len(hour_liqs) > 0:
#         # Calculate liquidation metrics
#         long_liqs = hour_liqs[hour_liqs['side'].str.upper() == 'BUY']
#         short_liqs = hour_liqs[hour_liqs['side'].str.upper() == 'SELL']
# 
#         long_volume = long_liqs['usd_value'].sum()
#         short_volume = short_liqs['usd_value'].sum()
#         total_volume = long_volume + short_volume
# 
#         # Use average price from liquidations as proxy for market price
#         avg_price = hour_liqs['price'].mean()
# 
#         # Create OHLCV-like data from liquidations
#         hourly_data.append({
#             'datetime': hour,
#             'Open': avg_price,
#             'High': hour_liqs['price'].max(),
#             'Low': hour_liqs['price'].min(),
#             'Close': avg_price,
#             'Volume': total_volume,
#             'long_liq_volume': long_volume,
#             'short_liq_volume': short_volume,
#             'net_liq_volume': short_volume - long_volume,  # Positive = more shorts liquidated
#             'total_liq_count': len(hour_liqs),
#             'long_liq_count': len(long_liqs),
#             'short_liq_count': len(short_liqs)
#         })
# 
# # Convert to DataFrame
# data = pd.DataFrame(hourly_data)
# data = data.set_index('datetime')
# 
# # Fill missing hours with forward fill
# full_range = pd.date_range(start=data.index.min(), end=data.index.max(), freq='H')
# data = data.reindex(full_range)
# data[['Open', 'High', 'Low', 'Close']] = data[['Open', 'High', 'Low', 'Close']].ffill()
# data[['Volume', 'long_liq_volume', 'short_liq_volume', 'net_liq_volume']] = data[['Volume', 'long_liq_volume', 'short_liq_volume', 'net_liq_volume']].fillna(0)
# data[['total_liq_count', 'long_liq_count', 'short_liq_count']] = data[['total_liq_count', 'long_liq_count', 'short_liq_count']].fillna(0)
# 
# print(f"✅ Created {len(data)} hourly data points")

# Data configuration
# Load preprocessed BTC data - choose between 1-minute and 5-minute
# Just comment/uncomment to switch between timeframes

# Option 1: 1-minute data
# data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/moondev_api/liq_data_BTC_1m_ohlcv.csv'
# timeframe = '1-minute'

# Option 2: 5-minute data (currently active)
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/moondev_api/liq_data_BTC_5m_ohlcv.csv'
timeframe = '5-minute'

print(f"📊 Loading preprocessed {timeframe} BTC liquidation data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)

# Data already has proper columns from preprocessing
print(f"✅ Loaded {len(data):,} {timeframe} bars")
print(f"📊 Data columns: {list(data.columns)}")

# Map liquidation columns to match strategy expectations
if 'long_liquidations' in data.columns and 'short_liquidations' in data.columns:
    data['long_liq_volume'] = data['long_liquidations']
    data['short_liq_volume'] = data['short_liquidations']
    data['net_liq_volume'] = data['short_liquidations'] - data['long_liquidations']
    data['total_liq_count'] = data['liquidation_count'] if 'liquidation_count' in data.columns else 0
    data['long_liq_count'] = (data['long_liquidations'] > 0).astype(int)
    data['short_liq_count'] = (data['short_liquidations'] > 0).astype(int)
else:
    # Create empty liquidation columns if they don't exist
    print("⚠️ Warning: Liquidation columns not found, creating empty columns")
    data['long_liq_volume'] = 0
    data['short_liq_volume'] = 0
    data['net_liq_volume'] = 0
    data['total_liq_count'] = 0
    data['long_liq_count'] = 0
    data['short_liq_count'] = 0

class PureLiquidationContrarianStrategy(Strategy):
    """
    Pure Liquidation CONTRARIAN Strategy

    Entry Logic:
    - BUY when long liquidation volume exceeds threshold (buying the dip)
    - SELL when short liquidation volume exceeds threshold (selling the rip)

    Exit Logic:
    - Take profit at X%
    - Stop loss at Y%
    - Time-based exit after max_hold_hours
    """

    # Optimizable parameters
    liquidation_threshold = 500_000  # Minimum USD liquidation volume to trigger trade
    take_profit = 0.015  # 1.5% take profit
    stop_loss = 0.01     # 1% stop loss
    max_hold_hours = 12  # Maximum holding period

    # Position sizing
    position_size = 0.95  # Use 95% of available capital

    def init(self):
        """Initialize strategy indicators"""
        print("🔧 Initializing Pure Liquidation Contrarian Strategy...")

        # Store liquidation volumes as indicators
        self.long_liq_volume = self.I(lambda: self.data.long_liq_volume)
        self.short_liq_volume = self.I(lambda: self.data.short_liq_volume)
        self.net_liq_volume = self.I(lambda: self.data.net_liq_volume)

        # Calculate rolling averages for context
        self.avg_long_liq = self.I(lambda x: pd.Series(x).rolling(24).mean(), self.long_liq_volume)
        self.avg_short_liq = self.I(lambda x: pd.Series(x).rolling(24).mean(), self.short_liq_volume)

        print("✅ Strategy initialized!")

    def next(self):
        """Main strategy logic - CONTRARIAN approach"""

        # Get current liquidation volumes
        current_long_liq = self.long_liq_volume[-1]
        current_short_liq = self.short_liq_volume[-1]
        current_price = self.data.Close[-1]

        # Skip if no liquidations
        if current_long_liq == 0 and current_short_liq == 0:
            return

        # Entry logic - CONTRARIAN
        if not self.position:

            # BUY when longs are liquidated (buy the dip)
            if current_long_liq >= self.liquidation_threshold:
                sl_price = current_price * (1 - self.stop_loss)
                tp_price = current_price * (1 + self.take_profit)

                self.buy(size=self.position_size, sl=sl_price, tp=tp_price)

            # SELL when shorts are liquidated (sell the rip)
            elif current_short_liq >= self.liquidation_threshold:
                sl_price = current_price * (1 + self.stop_loss)
                tp_price = current_price * (1 - self.take_profit)

                self.sell(size=self.position_size, sl=sl_price, tp=tp_price)

        # Exit logic - time-based exit
        else:
            if len(self.trades) > 0:
                entry_time = self.trades[-1].entry_time
                current_time = self.data.index[-1]
                hours_held = (current_time - entry_time).total_seconds() / 3600

                if hours_held >= self.max_hold_hours:
                    self.position.close()


# Run backtest with baseline parameters
print("\n" + "="*70)
print("RUNNING BASELINE BACKTEST (Non-Optimized)")
print("="*70)

if len(data) > 100:
    bt = Backtest(
        data[['Open', 'High', 'Low', 'Close', 'Volume', 'long_liq_volume', 'short_liq_volume', 'net_liq_volume']],
        PureLiquidationContrarianStrategy,
        cash=1000000,
        commission=0.001
    )

    # Run baseline
    baseline_stats = bt.run()

    print(f"\n📊 BASELINE RESULTS (CONTRARIAN):")
    print(f"Liquidation Threshold: ${PureLiquidationContrarianStrategy.liquidation_threshold:,}")
    print(f"Take Profit: {PureLiquidationContrarianStrategy.take_profit*100:.1f}%")
    print(f"Stop Loss: {PureLiquidationContrarianStrategy.stop_loss*100:.1f}%")
    print(f"Max Hold: {PureLiquidationContrarianStrategy.max_hold_hours} hours")
    print("-" * 50)
    print(f"Total Trades: {baseline_stats['# Trades']}")
    print(f"Win Rate: {baseline_stats['Win Rate [%]']:.2f}%")
    print(f"Return: {baseline_stats['Return [%]']:.2f}%")
    print(f"Sharpe: {baseline_stats['Sharpe Ratio']:.2f}")
    print(f"Max Drawdown: {baseline_stats['Max. Drawdown [%]']:.2f}%")

    print("\n📈 FULL BASELINE STATS:")
    print("="*70)
    print(baseline_stats)

    # Run optimization automatically
    print("\n" + "="*70)
    print("RUNNING OPTIMIZATION")
    print("="*70)
    print("🔄 Optimizing parameters... This may take a few minutes...")

    # Run the optimizer with error handling
    try:
        optimization_results = bt.optimize(
            liquidation_threshold=range(100_000, 2_000_000, 100_000),  # $100k to $2M in $100k steps
            take_profit=[0.01, 0.015, 0.02, 0.025, 0.03],  # 1% to 3%
            stop_loss=[0.005, 0.01, 0.015, 0.02],  # 0.5% to 2%
            max_hold_hours=[6, 12, 24, 48],  # 6 to 48 hours
            maximize='Sharpe Ratio',
            # Remove constraint to allow all parameter combinations
            return_heatmap=False  # Disable heatmap to avoid potential issues
        )

        print("\n✨ OPTIMIZED RESULTS:")
        print("="*70)
        print(optimization_results)

        # Extract and display optimized parameters
        print("\n🎯 OPTIMIZED PARAMETERS:")
        print("-" * 50)
        print(f"Liquidation Threshold: ${optimization_results._strategy.liquidation_threshold:,}")
        print(f"Take Profit: {optimization_results._strategy.take_profit*100:.1f}%")
        print(f"Stop Loss: {optimization_results._strategy.stop_loss*100:.1f}%")
        print(f"Max Hold Hours: {optimization_results._strategy.max_hold_hours}")

        # Compare baseline vs optimized
        print("\n📊 IMPROVEMENT SUMMARY:")
        print("-" * 50)
        baseline_return = baseline_stats['Return [%]']
        optimized_return = optimization_results['Return [%]']
        print(f"Baseline Return: {baseline_return:.2f}%")
        print(f"Optimized Return: {optimized_return:.2f}%")
        print(f"Improvement: {optimized_return - baseline_return:.2f}%")

    except Exception as e:
        print(f"\n⚠️ Optimization failed: {str(e)}")
        print("This may happen if there aren't enough trades with the current parameter ranges.")
        print("Try adjusting the parameter ranges or using more data.")

else:
    print("❌ Insufficient data for backtesting")