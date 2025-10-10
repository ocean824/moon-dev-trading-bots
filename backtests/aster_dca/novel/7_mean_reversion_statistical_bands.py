"""
NOVEL DCA #7: Mean Reversion Statistical Bands DCA
===================================================

Uses Z-score deviations from mean to identify extreme oversold conditions.
Combines Bollinger Bands, standard deviations, and mean reversion probability.
Superior because it's mathematically based on statistical extremes.

Key Innovation: Multi-timeframe Z-score confluence for high probability reversions.
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

print("🚀 NOVEL DCA #7: Mean Reversion Statistical Bands DCA 🚀")
print("=" * 70)

# Data source selection
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/ASTER_1m_20250926_125314_historical.csv'
#data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/ASTER_5m_20250926_125300_historical.csv'

print(f"📊 Loading ASTER data from: {data_path.split('/')[-1]}")
data = pd.read_csv(data_path, index_col='timestamp', parse_dates=True)
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Statistical calculations
# Z-score calculations for different periods
for period in [10, 20, 50]:
    data[f'MA_{period}'] = data['Close'].rolling(period).mean()
    data[f'STD_{period}'] = data['Close'].rolling(period).std()
    data[f'Z_Score_{period}'] = (data['Close'] - data[f'MA_{period}']) / data[f'STD_{period}']

# Bollinger Bands
bb = ta.bbands(data['Close'], length=20, std=2)
data['BB_Lower'] = bb['BBL_20_2.0']
data['BB_Upper'] = bb['BBU_20_2.0']
data['BB_Width'] = (data['BB_Upper'] - data['BB_Lower']) / data['Close']
data['BB_Position'] = (data['Close'] - data['BB_Lower']) / (data['BB_Upper'] - data['BB_Lower'])

# Mean reversion probability
data['Below_BB'] = data['Close'] < data['BB_Lower']
data['Z_Extreme'] = (data['Z_Score_10'] < -2) | (data['Z_Score_20'] < -2)

# Consecutive bars below mean
data['Below_MA'] = data['Close'] < data['MA_20']
data['Consecutive_Below'] = data['Below_MA'].rolling(5).sum()

# Volatility-adjusted bands
data['ATR'] = ta.atr(data['High'], data['Low'], data['Close'], length=14)
data['Keltner_Lower'] = data['MA_20'] - (2 * data['ATR'])
data['Below_Keltner'] = data['Close'] < data['Keltner_Lower']

# Composite statistical score
data['Statistical_Oversold'] = (
    (data['Z_Score_20'] < -1.5).astype(int) +
    data['Below_BB'].astype(int) +
    data['Below_Keltner'].astype(int) +
    (data['Consecutive_Below'] >= 4).astype(int)
)

print(f"✅ Loaded {len(data):,} bars")
print(f"📊 Z-score extremes (<-2): {data['Z_Extreme'].sum()}")
print(f"📉 Statistical oversold (score >= 3): {(data['Statistical_Oversold'] >= 3).sum()}")


class MeanReversionStatisticalBands(Strategy):
    """
    DCA based on statistical extremes and mean reversion
    """

    # Statistical parameters
    z_score_entry = -1.5      # Z-score threshold for entry
    z_score_extreme = -2.5    # Extreme Z-score for larger size
    min_stat_score = 2        # Minimum statistical oversold score

    # DCA parameters
    n_layers = 6
    layer_spacing = 0.004

    # Adaptive sizing
    base_size = 0.015
    extreme_mult = 2.0        # Double size at extreme Z-scores

    # Exit parameters
    take_profit = 0.08        # 8% TP (mean reversion)
    stop_loss = 0.18          # 18% SL

    max_position_pct = 0.15

    def init(self):
        self.z_score_10 = self.I(lambda: self.data.Z_Score_10)
        self.z_score_20 = self.I(lambda: self.data.Z_Score_20)
        self.z_score_50 = self.I(lambda: self.data.Z_Score_50)
        self.stat_score = self.I(lambda: self.data.Statistical_Oversold)
        self.bb_position = self.I(lambda: self.data.BB_Position)

        # DCA state
        self.stat_entries = []
        self.stat_sizes = []
        self.avg_entry = None
        self.reversion_mode = False
        self.layers_filled = 0
        self.extreme_count = 0

    def next(self):
        if len(self.data) < 100:
            return

        price = self.data.Close[-1]
        z10 = self.z_score_10[-1]
        z20 = self.z_score_20[-1]
        z50 = self.z_score_50[-1]
        stat_score = self.stat_score[-1]
        bb_pos = self.bb_position[-1]

        if pd.isna(z20) or pd.isna(stat_score):
            return

        # Exit logic
        if self.position:
            if self.avg_entry:
                pnl = (price - self.avg_entry) / self.avg_entry

                # Dynamic exit based on Z-score recovery
                if z20 > 0:  # Back above mean
                    if pnl > 0:
                        self.position.close()
                        self.reset_reversion()

                if pnl >= self.take_profit:
                    self.position.close()
                    self.reset_reversion()
                elif pnl <= -self.stop_loss:
                    self.position.close()
                    self.reset_reversion()
            return

        # Entry logic - statistical extremes
        if not self.position:
            # Check for statistical oversold
            is_oversold = (
                z20 <= self.z_score_entry and
                stat_score >= self.min_stat_score
            )

            # Extreme oversold - aggressive entry
            is_extreme = z20 <= self.z_score_extreme or z10 <= self.z_score_extreme

            if (is_oversold or is_extreme) and not self.reversion_mode:
                self.reversion_mode = True
                self.execute_statistical_entry(price, is_extreme)

            # Continue layering
            elif self.reversion_mode and self.layers_filled < self.n_layers:
                # Add layers on continued statistical extremes
                if z20 <= self.z_score_entry or bb_pos < 0:
                    if not self.stat_entries or price <= self.stat_entries[-1] * (1 - self.layer_spacing):
                        self.execute_statistical_entry(price, z20 <= self.z_score_extreme)

    def execute_statistical_entry(self, price, is_extreme):
        """Execute statistically-based entry"""
        # Size based on extremity
        if is_extreme:
            size = self.base_size * self.extreme_mult
            self.extreme_count += 1
        else:
            size = self.base_size

        # Cap at max position
        size = min(size, self.max_position_pct / self.n_layers)

        self.buy(size=size)
        self.stat_entries.append(price)
        self.stat_sizes.append(size)
        self.layers_filled += 1
        self.update_avg_entry()

    def update_avg_entry(self):
        if self.stat_entries:
            total_val = sum(e * s for e, s in zip(self.stat_entries, self.stat_sizes))
            total_size = sum(self.stat_sizes)
            self.avg_entry = total_val / total_size if total_size > 0 else None

    def reset_reversion(self):
        self.stat_entries = []
        self.stat_sizes = []
        self.avg_entry = None
        self.reversion_mode = False
        self.layers_filled = 0
        self.extreme_count = 0


# Run backtest
print("\n" + "="*70)
print("RUNNING MEAN REVERSION STATISTICAL BANDS BACKTEST")
print("="*70)

bt = Backtest(
    data,
    MeanReversionStatisticalBands,
    cash=10000,
    commission=0.001,
    exclusive_orders=True
)

stats = bt.run()
print(f"\n📊 RESULTS:")
print(stats)

# Optimization
print("\n" + "="*70)
print("OPTIMIZING PARAMETERS")
print("="*70)

try:
    opt = bt.optimize(
        z_score_entry=[-1.0, -1.5, -2.0],
        n_layers=[4, 6, 8],
        take_profit=[0.06, 0.08, 0.10],
        stop_loss=[0.15, 0.18, 0.20],
        maximize='Return [%]',
        return_heatmap=False
    )

    print(f"\n✨ OPTIMIZED RESULTS:")
    print(opt)

except Exception as e:
    print(f"Optimization failed: {str(e)}")

bt.plot()