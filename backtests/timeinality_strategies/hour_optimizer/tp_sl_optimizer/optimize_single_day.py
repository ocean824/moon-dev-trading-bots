"""
TP/SL Optimizer for Single-Day Hour Strategies (SHORT)
=======================================================
Optimizes Take Profit and Stop Loss for specific day-hour combinations using backtesting.py optimizer.

Configurations to test:
1. SOLUSD - Tuesday at 11:00 UTC
2. SOLUSD - Thursday at 11:00 UTC
3. SUIUSD - Monday at 07:00 UTC

Optimization:
- Take Profit: 1% to 15% in 1% increments (15 values)
- Stop Loss: 1% to 15% in 1% increments (15 values)
- Total: 225 combinations per configuration = 675 backtests
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
from datetime import datetime
import os

# Disable scientific notation
pd.set_option('display.float_format', lambda x: '%.6f' % x)
pd.options.display.float_format = '{:.6f}'.format

print("🎯 Moon Dev's TP/SL Optimizer (Single-Day SHORT Strategies) Loading... 🌙\n")

# ============================================================================
# CONFIGURATION
# ============================================================================
DATA_DIR = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/1_hr_data/'

# Define the specific configurations to test
CONFIGS = [
    {
        'data_file': 'SOLUSD-1h-250wks-data.csv',
        'symbol': 'SOLUSD',
        'day': 1,  # Tuesday (0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun)
        'hour': 11
    },
    {
        'data_file': 'SOLUSD-1h-250wks-data.csv',
        'symbol': 'SOLUSD',
        'day': 3,  # Thursday
        'hour': 11
    },
    {
        'data_file': 'SUIUSD-1h-52wks-data.csv',
        'symbol': 'SUIUSD',
        'day': 0,  # Monday
        'hour': 7
    }
]

DAY_NAMES = {0: 'Monday', 1: 'Tuesday', 2: 'Wednesday', 3: 'Thursday', 4: 'Friday', 5: 'Saturday', 6: 'Sunday'}

print(f"📊 Configurations to optimize:")
for i, config in enumerate(CONFIGS, 1):
    print(f"   {i}. {config['symbol']} - {DAY_NAMES[config['day']]} at {config['hour']:02d}:00 UTC")

print(f"\n🔧 Optimization Range:")
print(f"   Take Profit: 1% to 15% (1% increments)")
print(f"   Stop Loss: 1% to 15% (1% increments)")
print(f"   Total combinations per config: 225")
print(f"   Total backtests: {len(CONFIGS) * 225}\n")

# ============================================================================
# DATA LOADING
# ============================================================================
def load_and_prepare_data(filepath):
    """Load CSV and prepare data for backtesting"""
    df = pd.read_csv(filepath)
    if 'datetime' in df.columns:
        df['datetime'] = pd.to_datetime(df['datetime'])
        df.set_index('datetime', inplace=True)
    df.columns = [col.capitalize() for col in df.columns]
    df = df.sort_index()
    df = df.dropna()
    return df

# ============================================================================
# STRATEGY
# ============================================================================
class HourlyShortOptimizer(Strategy):
    # Parameters to optimize
    take_profit = 3.0  # Will be optimized
    stop_loss = 5.0    # Will be optimized

    # Fixed parameters (set dynamically)
    target_hour = 11
    target_day = 1

    def init(self):
        # Pre-calculate which bars match our target hour and day
        self.is_target_time = self.I(lambda: self.calculate_target_times())

    def calculate_target_times(self):
        """Calculate which bars match target hour and day"""
        target_times = np.zeros(len(self.data), dtype=bool)

        for i in range(len(self.data)):
            timestamp = self.data.index[i]
            # Check if it's the right day AND the right hour
            if timestamp.dayofweek == self.target_day and timestamp.hour == self.target_hour:
                target_times[i] = True

        return target_times

    def next(self):
        # Check if current bar matches our target time
        if self.is_target_time[-1]:
            # Close any existing position before opening new one
            if self.position:
                self.position.close()

            # Open SHORT position with 95% of equity
            current_price = self.data.Close[-1]

            # Calculate stop loss and take profit for SHORT position
            sl_price = current_price * (1 + self.stop_loss / 100)  # Stop loss above entry
            tp_price = current_price * (1 - self.take_profit / 100)  # Take profit below entry

            # Execute SHORT trade with 95% of equity
            self.sell(sl=sl_price, tp=tp_price, size=0.95)

# ============================================================================
# MAIN OPTIMIZATION LOOP
# ============================================================================
if __name__ == "__main__":
    print("="*80)
    print("STARTING TP/SL OPTIMIZATION (SINGLE-DAY SHORT STRATEGIES)")
    print("="*80)

    all_results = []

    for config_idx, config in enumerate(CONFIGS, 1):
        print(f"\n{'='*80}")
        print(f"📊 Configuration {config_idx}/{len(CONFIGS)}: {config['symbol']} - {DAY_NAMES[config['day']]} at {config['hour']:02d}:00 UTC")
        print(f"{'='*80}")

        # Load data
        data_path = os.path.join(DATA_DIR, config['data_file'])
        test_data = load_and_prepare_data(data_path)
        print(f"✅ Loaded {config['data_file']}: {len(test_data)} rows")

        # Create strategy class with specific day and hour
        class OptimizedStrategy(HourlyShortOptimizer):
            target_hour = config['hour']
            target_day = config['day']

        # Run optimization
        print(f"🔧 Running optimization (225 combinations)...")
        bt = Backtest(
            test_data,
            OptimizedStrategy,
            cash=1000000,
            commission=0.00045,
            trade_on_close=False,
            exclusive_orders=True
        )

        # Optimize with backtesting.py optimizer
        stats = bt.optimize(
            take_profit=range(1, 16, 1),  # 1% to 15% in 1% increments
            stop_loss=range(1, 16, 1),    # 1% to 15% in 1% increments
            maximize='Return [%]',
            constraint=lambda p: p.take_profit > 0 and p.stop_loss > 0
        )

        # Extract optimization results
        print(f"\n✅ Optimization complete!")
        print(f"🏆 Best combination:")
        print(f"   Take Profit: {stats._strategy.take_profit}%")
        print(f"   Stop Loss: {stats._strategy.stop_loss}%")
        print(f"   Return: {stats['Return [%]']:.2f}%")
        print(f"   Sharpe Ratio: {stats.get('Sharpe Ratio', 0):.3f}")
        print(f"   Max Drawdown: {stats['Max. Drawdown [%]']:.2f}%")
        print(f"   Total Trades: {int(stats['# Trades'])}")
        print(f"   Win Rate: {stats['Win Rate [%]']:.1f}%")

        # Store best result
        result = {
            'Symbol': config['symbol'],
            'Data_File': config['data_file'],
            'Day': DAY_NAMES[config['day']],
            'Hour_UTC': config['hour'],
            'Best_TP_%': stats._strategy.take_profit,
            'Best_SL_%': stats._strategy.stop_loss,
            'Return_%': stats['Return [%]'],
            'BuyHold_Return_%': stats['Buy & Hold Return [%]'],
            'Sharpe_Ratio': stats.get('Sharpe Ratio', 0),
            'Max_Drawdown_%': stats['Max. Drawdown [%]'],
            'Total_Trades': stats['# Trades'],
            'Win_Rate_%': stats['Win Rate [%]'],
            'Profit_Factor': stats.get('Profit Factor', 0)
        }
        all_results.append(result)

    # Save results
    if all_results:
        results_df = pd.DataFrame(all_results)

        # Save to CSV
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        results_dir = os.path.join(os.path.dirname(__file__), 'results')
        os.makedirs(results_dir, exist_ok=True)
        output_file = os.path.join(results_dir, f'tp_sl_optimized_single_day_{timestamp}.csv')
        results_df.to_csv(output_file, index=False)

        print("\n" + "="*80)
        print("OPTIMIZATION COMPLETE!")
        print("="*80)
        print(f"✅ Optimized {len(all_results)} configurations")
        print(f"✅ Results saved to: {output_file}")

        print("\n" + "="*80)
        print("ALL OPTIMIZED RESULTS:")
        print("="*80)
        print(results_df.to_string(index=False))

    else:
        print("\n❌ No results collected!")

print("\n🌙 Optimization complete!")
