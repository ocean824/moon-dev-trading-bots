"""
ADAPTIVE RSI BANDS - Bollinger-style Bands on RSI
===================================================

Concept: Apply Bollinger Bands to RSI for extreme overbought/oversold levels.
Trade when RSI breaks outside its own bands at supply/demand zones.

Focus: PROFITABILITY with high volume
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

print("🎯 Moon Dev's ADAPTIVE RSI BANDS Strategy V3 🎯")
print("=" * 70)

# Load data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1m-4wks-data.csv'
print(f"📊 Loading BTC 1-minute data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Calculate RSI
data['RSI'] = ta.rsi(data['Close'], length=14)

# Create Bollinger Bands on RSI
rsi_period = 20
rsi_std_mult = 2
data['RSI_MA'] = data['RSI'].rolling(rsi_period).mean()
data['RSI_STD'] = data['RSI'].rolling(rsi_period).std()
data['RSI_Upper'] = data['RSI_MA'] + (data['RSI_STD'] * rsi_std_mult)
data['RSI_Lower'] = data['RSI_MA'] - (data['RSI_STD'] * rsi_std_mult)

# RSI band width (volatility indicator)
data['RSI_Band_Width'] = (data['RSI_Upper'] - data['RSI_Lower']) / data['RSI_MA']

# Supply and demand zones
data['Demand_Zone'] = data['Close'].rolling(15).min()
data['Supply_Zone'] = data['Close'].rolling(15).max()

# Zone proximity
data['Near_Demand'] = (data['Close'] - data['Demand_Zone']) / data['Demand_Zone']
data['Near_Supply'] = (data['Supply_Zone'] - data['Close']) / data['Close']

# Volume analysis
data['Volume_MA'] = data['Volume'].rolling(20).mean()
data['Volume_Ratio'] = data['Volume'] / data['Volume_MA']

# Trend filter
data['SMA_50'] = data['Close'].rolling(50).mean()
data['Trend'] = np.where(data['Close'] > data['SMA_50'], 1, -1)

print(f"✅ Loaded {len(data):,} 1-minute bars")


class AdaptiveRSIBands(Strategy):
    """
    Trade RSI band breakouts at key zones
    """

    band_multiplier = 2.0
    zone_proximity = 0.002
    min_band_width = 10  # Minimum RSI band width
    take_profit = 0.007
    stop_loss = 0.003
    volume_threshold = 1.1

    def init(self):
        self.rsi = self.I(lambda: self.data.RSI)
        self.rsi_upper = self.I(lambda: self.data.RSI_Upper)
        self.rsi_lower = self.I(lambda: self.data.RSI_Lower)
        self.rsi_band_width = self.I(lambda: self.data.RSI_Band_Width)
        self.near_demand = self.I(lambda: self.data.Near_Demand)
        self.near_supply = self.I(lambda: self.data.Near_Supply)
        self.volume_ratio = self.I(lambda: self.data.Volume_Ratio)
        self.trend = self.I(lambda: self.data.Trend)

    def next(self):
        if len(self.data) < 50:
            return

        price = self.data.Close[-1]
        rsi = self.rsi[-1]
        rsi_upper = self.rsi_upper[-1]
        rsi_lower = self.rsi_lower[-1]

        if pd.isna(rsi) or pd.isna(rsi_upper) or pd.isna(rsi_lower):
            return

        # Exit when RSI returns to middle band
        if self.position:
            rsi_middle = (rsi_upper + rsi_lower) / 2
            if self.position.is_long and rsi > rsi_middle:
                self.position.close()
            elif self.position.is_short and rsi < rsi_middle:
                self.position.close()
            return

        # Entry logic
        if not self.position:
            # Check band width (volatility)
            band_width = rsi_upper - rsi_lower
            if band_width < self.min_band_width:
                return

            # BUY: RSI below lower band + near demand zone
            if (rsi < rsi_lower and
                self.near_demand[-1] < self.zone_proximity and
                self.volume_ratio[-1] > self.volume_threshold and
                self.trend[-1] > 0):  # Trend filter

                tp = price * (1 + self.take_profit)
                sl = price * (1 - self.stop_loss)
                self.buy(tp=tp, sl=sl)

            # SELL: RSI above upper band + near supply zone
            elif (rsi > rsi_upper and
                  self.near_supply[-1] < self.zone_proximity and
                  self.volume_ratio[-1] > self.volume_threshold and
                  self.trend[-1] < 0):  # Trend filter

                tp = price * (1 - self.take_profit)
                sl = price * (1 + self.stop_loss)
                self.sell(tp=tp, sl=sl)


# Run backtest
print("\n" + "="*70)
print("RUNNING ADAPTIVE RSI BANDS BACKTEST")
print("="*70)

bt = Backtest(
    data,
    AdaptiveRSIBands,
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
        band_multiplier=[1.5, 2.0, 2.5],
        zone_proximity=[0.0015, 0.002, 0.0025],
        take_profit=[0.006, 0.007, 0.008],
        stop_loss=[0.002, 0.003, 0.004],
        maximize='Return [%]',
        return_heatmap=False
    )

    print(f"\n✨ OPTIMIZED RESULTS:")
    print(optimization_results)

    print(f"\n🎯 OPTIMAL PARAMETERS:")
    print(f"band_multiplier: {optimization_results._strategy.band_multiplier}")
    print(f"zone_proximity: {optimization_results._strategy.zone_proximity}")
    print(f"take_profit: {optimization_results._strategy.take_profit}")
    print(f"stop_loss: {optimization_results._strategy.stop_loss}")

except Exception as e:
    print(f"Optimization failed: {str(e)}")

bt.plot()