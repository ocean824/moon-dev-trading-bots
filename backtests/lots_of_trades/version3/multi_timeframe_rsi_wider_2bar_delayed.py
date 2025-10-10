"""
MULTI-TIMEFRAME RSI WIDER - 2 BAR HOLD + 1 BAR DELAYED ENTRY
==============================================================

Based on the successful Multi-Timeframe RSI strategy with 22% return.
Using wider stop loss and take profit targets for realistic execution.
MUST HOLD FOR AT LEAST 2 FULL BARS BEFORE CLOSING (except SL/TP)
ENTERS 1 BAR LATE TO SIMULATE REALISTIC EXECUTION DELAYS

Original optimal params: TP=0.009 (0.9%), SL=0.004 (0.4%)
New wider ranges: TP=0.015-0.025 (1.5-2.5%), SL=0.008-0.012 (0.8-1.2%)
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

print("🎯 Moon Dev's MULTI-TIMEFRAME RSI - 2 BAR HOLD + DELAYED ENTRY Strategy V3 🎯")
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


class MultiTimeframeRSIWiderDelayed(Strategy):
    """
    Trade when multiple RSI timeframes align with wider SL/TP
    MUST HOLD FOR MINIMUM 2 BARS
    ENTERS 1 BAR LATE (delayed entry for realistic execution)
    """

    rsi_1m_oversold = 35  # From optimization
    rsi_1m_overbought = 65  # From optimization
    rsi_5m_oversold = 35
    rsi_5m_overbought = 65
    rsi_15m_oversold = 40
    rsi_15m_overbought = 60
    take_profit = 0.02  # WIDER: 2% (was 0.9%)
    stop_loss = 0.01   # WIDER: 1% (was 0.4%)
    min_hold_bars = 2  # MUST HOLD FOR AT LEAST 2 BARS
    entry_delay = 1  # DELAY ENTRY BY 1 BAR

    def init(self):
        self.rsi_1m = self.I(lambda: self.data.RSI_1m)
        self.rsi_5m = self.I(lambda: self.data.RSI_5m)
        self.rsi_15m = self.I(lambda: self.data.RSI_15m)
        self.rsi_combined = self.I(lambda: self.data.RSI_Combined)
        self.volume_ratio = self.I(lambda: self.data.Volume_Ratio)

        # Track entry bar and pending signals
        self.entry_bar = None
        self.pending_buy_signal = False
        self.pending_sell_signal = False

    def next(self):
        if len(self.data) < 50:
            return

        price = self.data.Close[-1]
        rsi_1m = self.rsi_1m[-1]
        rsi_5m = self.rsi_5m[-1]
        rsi_15m = self.rsi_15m[-1]
        current_bar = len(self.data) - 1

        if pd.isna(rsi_1m) or pd.isna(rsi_5m) or pd.isna(rsi_15m):
            return

        # Exit logic with minimum hold period
        if self.position:
            bars_held = current_bar - self.entry_bar

            # Only allow exit after minimum hold period (SL/TP still work immediately)
            if bars_held >= self.min_hold_bars:
                if self.position.is_long and (rsi_1m > 60 or rsi_5m > 55):
                    self.position.close()
                elif self.position.is_short and (rsi_1m < 40 or rsi_5m < 45):
                    self.position.close()
            return

        # Process delayed entries
        if not self.position:
            # Execute pending buy signal (1 bar late)
            if self.pending_buy_signal:
                tp = price * (1 + self.take_profit)
                sl = price * (1 - self.stop_loss)
                self.buy(tp=tp, sl=sl)
                self.entry_bar = current_bar
                self.pending_buy_signal = False
                return

            # Execute pending sell signal (1 bar late)
            if self.pending_sell_signal:
                tp = price * (1 - self.take_profit)
                sl = price * (1 + self.stop_loss)
                self.sell(tp=tp, sl=sl)
                self.entry_bar = current_bar
                self.pending_sell_signal = False
                return

        # Check for new signals (will execute next bar)
        if not self.position and not self.pending_buy_signal and not self.pending_sell_signal:
            # BUY SIGNAL: All timeframes oversold
            if (rsi_1m < self.rsi_1m_oversold and
                rsi_5m < self.rsi_5m_oversold and
                rsi_15m < self.rsi_15m_oversold and
                self.volume_ratio[-1] > 0.8):

                # Set pending buy signal (will execute next bar)
                self.pending_buy_signal = True

            # SELL SIGNAL: All timeframes overbought
            elif (rsi_1m > self.rsi_1m_overbought and
                  rsi_5m > self.rsi_5m_overbought and
                  rsi_15m > self.rsi_15m_overbought and
                  self.volume_ratio[-1] > 0.8):

                # Set pending sell signal (will execute next bar)
                self.pending_sell_signal = True


# Run backtest
print("\n" + "="*70)
print("RUNNING MULTI-TIMEFRAME RSI - 2 BAR HOLD + DELAYED ENTRY BACKTEST")
print("="*70)

bt = Backtest(
    data,
    MultiTimeframeRSIWiderDelayed,
    cash=1000000,
    commission=0.001,
    exclusive_orders=True
)

baseline_stats = bt.run()
print(f"\n📊 BASELINE RESULTS (2% TP, 1% SL, 2-bar hold, 1-bar delay):")
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

    print(f"\n🎯 OPTIMAL PARAMETERS (WIDER + 2-BAR HOLD + 1-BAR DELAY):")
    print(f"rsi_1m_oversold: {optimization_results._strategy.rsi_1m_oversold}")
    print(f"rsi_1m_overbought: {optimization_results._strategy.rsi_1m_overbought}")
    print(f"take_profit: {optimization_results._strategy.take_profit}")
    print(f"stop_loss: {optimization_results._strategy.stop_loss}")
    print(f"min_hold_bars: {optimization_results._strategy.min_hold_bars}")
    print(f"entry_delay: {optimization_results._strategy.entry_delay}")

except Exception as e:
    print(f"Optimization failed: {str(e)}")

bt.plot()