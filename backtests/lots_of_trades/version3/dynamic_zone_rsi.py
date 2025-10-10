"""
DYNAMIC ZONE RSI - Adaptive RSI with Dynamic Boundaries
========================================================

Concept: RSI with dynamically adjusting oversold/overbought levels based on volatility.
Zones expand in volatile markets, contract in calm markets.

Focus: PROFITABILITY with high volume
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

print("🎯 Moon Dev's DYNAMIC ZONE RSI Strategy V3 🎯")
print("=" * 70)

# Load data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1m-4wks-data.csv'
print(f"📊 Loading BTC 1-minute data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Calculate RSI
data['RSI'] = ta.rsi(data['Close'], length=14)

# Calculate ATR for volatility
data['ATR'] = ta.atr(data['High'], data['Low'], data['Close'], length=14)
data['ATR_Ratio'] = data['ATR'] / data['Close']

# Dynamic RSI zones based on volatility
data['RSI_MA'] = data['RSI'].rolling(50).mean()
data['RSI_STD'] = data['RSI'].rolling(50).std()

# Adaptive boundaries
data['Dynamic_Oversold'] = data['RSI_MA'] - (1.5 * data['RSI_STD'])
data['Dynamic_Overbought'] = data['RSI_MA'] + (1.5 * data['RSI_STD'])

# Ensure reasonable bounds
data['Dynamic_Oversold'] = data['Dynamic_Oversold'].clip(15, 35)
data['Dynamic_Overbought'] = data['Dynamic_Overbought'].clip(65, 85)

# Price momentum
data['Momentum'] = data['Close'].pct_change(5)

print(f"✅ Loaded {len(data):,} 1-minute bars")


class DynamicZoneRSI(Strategy):
    """
    RSI with adaptive oversold/overbought levels
    """

    base_oversold = 30
    base_overbought = 70
    volatility_multiplier = 1.5
    take_profit = 0.007
    stop_loss = 0.003
    momentum_filter = 0.001

    def init(self):
        self.rsi = self.I(lambda: self.data.RSI)
        self.dynamic_oversold = self.I(lambda: self.data.Dynamic_Oversold)
        self.dynamic_overbought = self.I(lambda: self.data.Dynamic_Overbought)
        self.atr_ratio = self.I(lambda: self.data.ATR_Ratio)
        self.momentum = self.I(lambda: self.data.Momentum)

    def next(self):
        if len(self.data) < 50:
            return

        price = self.data.Close[-1]
        rsi = self.rsi[-1]
        oversold = self.dynamic_oversold[-1]
        overbought = self.dynamic_overbought[-1]

        if pd.isna(rsi) or pd.isna(oversold) or pd.isna(overbought):
            return

        # Exit on mean reversion
        if self.position:
            rsi_neutral = 45 < rsi < 55
            if rsi_neutral:
                self.position.close()
                return

        # Entry logic with dynamic zones
        if not self.position:
            # BUY: RSI below dynamic oversold + positive momentum building
            if (rsi < oversold and
                self.momentum[-1] > -self.momentum_filter):

                # Wider TP in volatile markets
                vol_adjustment = 1 + (self.atr_ratio[-1] * 10)
                tp = price * (1 + self.take_profit * vol_adjustment)
                sl = price * (1 - self.stop_loss)
                self.buy(tp=tp, sl=sl)

            # SELL: RSI above dynamic overbought + negative momentum building
            elif (rsi > overbought and
                  self.momentum[-1] < self.momentum_filter):

                # Wider TP in volatile markets
                vol_adjustment = 1 + (self.atr_ratio[-1] * 10)
                tp = price * (1 - self.take_profit * vol_adjustment)
                sl = price * (1 + self.stop_loss)
                self.sell(tp=tp, sl=sl)


# Run backtest
print("\n" + "="*70)
print("RUNNING DYNAMIC ZONE RSI BACKTEST")
print("="*70)

bt = Backtest(
    data,
    DynamicZoneRSI,
    cash=1000000,
    commission=0.001,
    exclusive_orders=True
)

baseline_stats = bt.run()
print(f"\n📊 BASELINE RESULTS:")
print(baseline_stats)

# Optimization
print("\n" + "="*70)
print("OPTIMIZING FOR MAXIMUM RETURN")
print("="*70)

try:
    optimization_results = bt.optimize(
        volatility_multiplier=[1.2, 1.5, 1.8],
        take_profit=[0.006, 0.007, 0.008],
        stop_loss=[0.002, 0.003, 0.004],
        momentum_filter=[0.0005, 0.001, 0.0015],
        maximize='Return [%]',
        return_heatmap=False
    )

    print(f"\n✨ OPTIMIZED RESULTS:")
    print(optimization_results)

    print(f"\n🎯 OPTIMAL PARAMETERS:")
    print(f"volatility_multiplier: {optimization_results._strategy.volatility_multiplier}")
    print(f"take_profit: {optimization_results._strategy.take_profit}")
    print(f"stop_loss: {optimization_results._strategy.stop_loss}")
    print(f"momentum_filter: {optimization_results._strategy.momentum_filter}")

except Exception as e:
    print(f"Optimization failed: {str(e)}")

bt.plot()