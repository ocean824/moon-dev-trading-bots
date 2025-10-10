"""
ASTER DCA STRATEGY #5: Time-based DCA With SMA Filter
======================================================

Logic: Every X minutes, check if price is below SMA by Y%. If yes, place 1/N of total allocation.
Layering: Over, say, 30–60 minutes you get a full averaged position.
Exit: Single TP for the basket at +10%, wide SL at -20–30%.

Smooths entries over time, avoids loading all bids into one candle.
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

print("🎯 ASTER DCA STRATEGY #5: Time-based DCA With SMA Filter 🎯")
print("=" * 70)

# Data source selection (comment/uncomment as needed)
#data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/ASTER_1m_20250926_125314_historical.csv'
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/ASTER_5m_20250926_125300_historical.csv'

print(f"📊 Loading ASTER data from: {data_path.split('/')[-1]}")
data = pd.read_csv(data_path, index_col='timestamp', parse_dates=True)
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Calculate indicators
data['SMA_20'] = data['Close'].rolling(20).mean()
data['Below_SMA_Pct'] = (data['SMA_20'] - data['Close']) / data['SMA_20'] * 100
data['Bar_Number'] = range(len(data))

print(f"✅ Loaded {len(data):,} bars")
print(f"📈 Price range: ${data['Close'].min():.4f} - ${data['Close'].max():.4f}")


class TimeBasedSMAFilterDCA(Strategy):
    """
    Time-based DCA with SMA filter
    """

    # Time parameters
    dca_interval_bars = 10    # DCA every 10 bars (10 mins for 1m data)
    total_dca_bars = 60       # Complete DCA over 60 bars

    # SMA filter
    sma_threshold = 1.5       # Must be 1.5% below SMA to DCA

    # Position parameters
    n_chunks = 6              # Split position into 6 chunks
    max_position_pct = 0.10   # Max 10% of capital

    # Exit parameters
    basket_take_profit = 0.10  # 10% TP on basket
    basket_stop_loss = 0.25    # 25% SL on basket

    def init(self):
        self.sma = self.I(lambda: self.data.SMA_20)
        self.below_sma_pct = self.I(lambda: self.data.Below_SMA_Pct)
        self.bar_number = self.I(lambda: self.data.Bar_Number)

        # DCA tracking
        self.dca_start_bar = None
        self.dca_entries = []
        self.dca_sizes = []
        self.chunks_filled = 0
        self.avg_entry = None
        self.last_dca_bar = None

    def next(self):
        if len(self.data) < 30:
            return

        price = self.data.Close[-1]
        sma = self.sma[-1]
        below_pct = self.below_sma_pct[-1]
        current_bar = self.bar_number[-1]

        if pd.isna(sma) or pd.isna(below_pct):
            return

        # Exit logic for basket
        if self.position:
            if self.avg_entry is not None:
                basket_pnl = (price - self.avg_entry) / self.avg_entry

                if basket_pnl >= self.basket_take_profit:
                    self.position.close()
                    self.reset_dca()
                elif basket_pnl <= -self.basket_stop_loss:
                    self.position.close()
                    self.reset_dca()
            return

        # DCA logic
        if not self.position:
            # Check if we should start or continue DCA
            if below_pct >= self.sma_threshold:
                # Start DCA if not started
                if self.dca_start_bar is None:
                    self.dca_start_bar = current_bar
                    self.execute_dca_chunk(price, current_bar)

                # Continue DCA if started and interval passed
                elif self.chunks_filled < self.n_chunks:
                    # Check if enough bars passed since last DCA
                    if self.last_dca_bar is None or (current_bar - self.last_dca_bar) >= self.dca_interval_bars:
                        # Check if we're still within DCA window
                        if (current_bar - self.dca_start_bar) <= self.total_dca_bars:
                            self.execute_dca_chunk(price, current_bar)
                        else:
                            # DCA window expired, reset if not enough chunks filled
                            if self.chunks_filled < self.n_chunks / 2:
                                self.reset_dca()

    def execute_dca_chunk(self, price, current_bar):
        """Execute one chunk of the DCA"""
        chunk_size = self.max_position_pct / self.n_chunks

        self.buy(size=chunk_size)
        self.dca_entries.append(price)
        self.dca_sizes.append(chunk_size)
        self.chunks_filled += 1
        self.last_dca_bar = current_bar

        # Update average entry
        self.update_avg_entry()

    def update_avg_entry(self):
        """Calculate weighted average entry"""
        if self.dca_entries and self.dca_sizes:
            total_value = sum(e * s for e, s in zip(self.dca_entries, self.dca_sizes))
            total_size = sum(self.dca_sizes)
            self.avg_entry = total_value / total_size if total_size > 0 else None

    def reset_dca(self):
        """Reset DCA state"""
        self.dca_start_bar = None
        self.dca_entries = []
        self.dca_sizes = []
        self.chunks_filled = 0
        self.avg_entry = None
        self.last_dca_bar = None


# Run backtest
print("\n" + "="*70)
print("RUNNING TIME-BASED DCA WITH SMA FILTER BACKTEST")
print("="*70)

bt = Backtest(
    data,
    TimeBasedSMAFilterDCA,
    cash=10000,
    commission=0.001,
    exclusive_orders=True
)

baseline_stats = bt.run()
print(f"\n📊 BASELINE RESULTS:")
print(baseline_stats)

# Optimization
print("\n" + "="*70)
print("OPTIMIZING TIME-BASED PARAMETERS")
print("="*70)

try:
    optimization_results = bt.optimize(
        dca_interval_bars=[5, 10, 15],
        sma_threshold=[1.0, 1.5, 2.0, 2.5],
        n_chunks=[4, 6, 8],
        basket_take_profit=[0.08, 0.10, 0.12],
        basket_stop_loss=[0.20, 0.25, 0.30],
        maximize='Return [%]',
        return_heatmap=False
    )

    print(f"\n✨ OPTIMIZED RESULTS:")
    print(optimization_results)

    print(f"\n🎯 OPTIMAL PARAMETERS:")
    print(f"DCA Interval: {optimization_results._strategy.dca_interval_bars} bars")
    print(f"SMA Threshold: {optimization_results._strategy.sma_threshold}%")
    print(f"Number of Chunks: {optimization_results._strategy.n_chunks}")
    print(f"Basket Take Profit: {optimization_results._strategy.basket_take_profit*100}%")
    print(f"Basket Stop Loss: {optimization_results._strategy.basket_stop_loss*100}%")

except Exception as e:
    print(f"Optimization failed: {str(e)}")

bt.plot()