"""
MULTI-TIMEFRAME RSI - 2 BAR ENTRY DELAY + 2 BAR EXIT DELAY
============================================================

Based on the successful Multi-Timeframe RSI strategy with 22% return.
Using wider stop loss and take profit targets for realistic execution.
ENTERS 2 BARS LATE AND EXITS 2 BARS LATE (except SL/TP)
Simulates very slow execution for maximum realism.

Original optimal params: TP=0.009 (0.9%), SL=0.004 (0.4%)
New wider ranges: TP=0.015-0.025 (1.5-2.5%), SL=0.008-0.012 (0.8-1.2%)
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

print("🎯 Moon Dev's MULTI-TIMEFRAME RSI - 2 BAR ENTRY/EXIT DELAY Strategy V3 🎯")
print("=" * 70)

# Load data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1m-4wks-data.csv'
print(f"📊 Loading BTC 1-minute data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Calculate RSI for different timeframes
data['RSI_1m'] = ta.rsi(data['Close'], length=14)

# Resample for 5-minute RSI
data_5m = data['Close'].resample('5T').last()
rsi_5m = ta.rsi(data_5m, length=14)
data['RSI_5m'] = rsi_5m.reindex(data.index, method='ffill')

# Resample for 15-minute RSI
data_15m = data['Close'].resample('15T').last()
rsi_15m = ta.rsi(data_15m, length=14)
data['RSI_15m'] = rsi_15m.reindex(data.index, method='ffill')

# Combined RSI score
data['RSI_Combined'] = (data['RSI_1m'] + data['RSI_5m'] + data['RSI_15m']) / 3

# RSI alignment
data['All_Oversold'] = ((data['RSI_1m'] < 35) &
                        (data['RSI_5m'] < 40) &
                        (data['RSI_15m'] < 45)).astype(int)

data['All_Overbought'] = ((data['RSI_1m'] > 65) &
                          (data['RSI_5m'] > 60) &
                          (data['RSI_15m'] > 55)).astype(int)

# Volume confirmation
data['Volume_MA'] = data['Volume'].rolling(20).mean()
data['Volume_Ratio'] = data['Volume'] / data['Volume_MA']

print(f"✅ Loaded {len(data):,} 1-minute bars")


class MultiTimeframeRSI2BarDelay(Strategy):
    """
    Trade when multiple RSI timeframes align with wider SL/TP
    ENTERS 2 BARS LATE (delayed entry)
    EXITS 2 BARS LATE (delayed exit except for SL/TP)
    """

    rsi_1m_oversold = 35  # From optimization
    rsi_1m_overbought = 65  # From optimization
    rsi_5m_oversold = 35
    rsi_5m_overbought = 65
    rsi_15m_oversold = 40
    rsi_15m_overbought = 60
    take_profit = 0.02  # WIDER: 2% (was 0.9%)
    stop_loss = 0.01   # WIDER: 1% (was 0.4%)
    entry_delay = 2  # DELAY ENTRY BY 2 BARS
    exit_delay = 2   # DELAY EXIT BY 2 BARS

    def init(self):
        self.rsi_1m = self.I(lambda: self.data.RSI_1m)
        self.rsi_5m = self.I(lambda: self.data.RSI_5m)
        self.rsi_15m = self.I(lambda: self.data.RSI_15m)
        self.rsi_combined = self.I(lambda: self.data.RSI_Combined)
        self.volume_ratio = self.I(lambda: self.data.Volume_Ratio)

        # Track pending signals with bar counters
        self.pending_buy_bars = 0
        self.pending_sell_bars = 0
        self.pending_exit_bars = 0

    def next(self):
        if len(self.data) < 50:
            return

        price = self.data.Close[-1]
        rsi_1m = self.rsi_1m[-1]
        rsi_5m = self.rsi_5m[-1]
        rsi_15m = self.rsi_15m[-1]

        if pd.isna(rsi_1m) or pd.isna(rsi_5m) or pd.isna(rsi_15m):
            return

        # Handle delayed exits
        if self.position:
            # Check for exit signals (will execute after delay)
            if self.pending_exit_bars == 0:  # No pending exit yet
                if self.position.is_long and (rsi_1m > 60 or rsi_5m > 55):
                    self.pending_exit_bars = self.exit_delay
                elif self.position.is_short and (rsi_1m < 40 or rsi_5m < 45):
                    self.pending_exit_bars = self.exit_delay

            # Process delayed exit
            if self.pending_exit_bars > 0:
                self.pending_exit_bars -= 1
                if self.pending_exit_bars == 0:
                    self.position.close()
            return

        # Process delayed entries
        if not self.position:
            # Execute pending buy signal after delay
            if self.pending_buy_bars > 0:
                self.pending_buy_bars -= 1
                if self.pending_buy_bars == 0:
                    tp = price * (1 + self.take_profit)
                    sl = price * (1 - self.stop_loss)
                    self.buy(tp=tp, sl=sl)
                return

            # Execute pending sell signal after delay
            if self.pending_sell_bars > 0:
                self.pending_sell_bars -= 1
                if self.pending_sell_bars == 0:
                    tp = price * (1 - self.take_profit)
                    sl = price * (1 + self.stop_loss)
                    self.sell(tp=tp, sl=sl)
                return

        # Check for new signals (will execute after 2 bars)
        if not self.position and self.pending_buy_bars == 0 and self.pending_sell_bars == 0:
            # BUY SIGNAL: All timeframes oversold
            if (rsi_1m < self.rsi_1m_oversold and
                rsi_5m < self.rsi_5m_oversold and
                rsi_15m < self.rsi_15m_oversold and
                self.volume_ratio[-1] > 0.8):

                # Set pending buy signal (will execute after 2 bars)
                self.pending_buy_bars = self.entry_delay

            # SELL SIGNAL: All timeframes overbought
            elif (rsi_1m > self.rsi_1m_overbought and
                  rsi_5m > self.rsi_5m_overbought and
                  rsi_15m > self.rsi_15m_overbought and
                  self.volume_ratio[-1] > 0.8):

                # Set pending sell signal (will execute after 2 bars)
                self.pending_sell_bars = self.entry_delay


# Run backtest
print("\n" + "="*70)
print("RUNNING MULTI-TIMEFRAME RSI - 2 BAR ENTRY/EXIT DELAY BACKTEST")
print("="*70)

bt = Backtest(
    data,
    MultiTimeframeRSI2BarDelay,
    cash=1000000,
    commission=0.001,
    exclusive_orders=True
)

baseline_stats = bt.run()
print(f"\n📊 BASELINE RESULTS (2% TP, 1% SL, 2-bar entry delay, 2-bar exit delay):")
print(baseline_stats)

# Optimization with wider ranges
print("\n" + "="*70)
print("OPTIMIZING WITH WIDER STOP LOSS AND TAKE PROFIT")
print("="*70)

try:
    optimization_results = bt.optimize(
        take_profit=[0.015, 0.02, 0.025],  # 1.5%, 2%, 2.5%
        stop_loss=[0.008, 0.01, 0.012],    # 0.8%, 1%, 1.2%
        maximize='Return [%]',
        return_heatmap=False
    )

    print(f"\n✨ OPTIMIZED RESULTS:")
    print(optimization_results)

    print(f"\n🎯 OPTIMAL PARAMETERS (2-BAR ENTRY/EXIT DELAY):")
    print(f"rsi_1m_oversold: {optimization_results._strategy.rsi_1m_oversold}")
    print(f"rsi_1m_overbought: {optimization_results._strategy.rsi_1m_overbought}")
    print(f"take_profit: {optimization_results._strategy.take_profit}")
    print(f"stop_loss: {optimization_results._strategy.stop_loss}")
    print(f"entry_delay: {optimization_results._strategy.entry_delay}")
    print(f"exit_delay: {optimization_results._strategy.exit_delay}")

except Exception as e:
    print(f"Optimization failed: {str(e)}")

bt.plot()