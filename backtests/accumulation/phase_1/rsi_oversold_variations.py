"""
Moon Dev's RSI Oversold Variations - Phase 1
=============================================
Testing variations of the RSI Oversold strategy that beat DCA by +26% in Phase 0

Variations:
1. RSI Extreme (< 25) - More extreme oversold only
2. RSI + Volume Spike - Oversold with high volume (capitulation)
3. RSI + Trend Filter - Oversold and below 50 MA
4. RSI + Consecutive Days - Buy after 2+ days oversold
5. RSI Gradient Buy - Scale buy size based on how oversold
6. RSI + Weekly Low Combo - RSI oversold at weekly low
7. RSI + Drawdown Scale - Buy more at deeper drawdowns from ATH
"""

import pandas as pd
import numpy as np
import pandas_ta as ta
from backtesting import Backtest, Strategy
import warnings
warnings.filterwarnings('ignore')

print("=" * 70)
print("Moon Dev's RSI Oversold Variations - Phase 1")
print("=" * 70)

# =============================================================================
# CONFIGURATION
# =============================================================================
STARTING_CAPITAL = 1_000_000

DATA_PATHS = {
    'BTC': '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1d-260wks-data.csv',
    'ETH': '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/ETHUSD-1d-260wks-data.csv',
    'SOL': '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/SOLUSD-1d-260wks-data.csv',
}

results = []

# =============================================================================
# BASE RSI OVERSOLD (for comparison)
# =============================================================================
class RSIOversoldBase(Strategy):
    """Original RSI Oversold from Phase 0"""
    buy_percent = 0.05
    rsi_period = 14
    rsi_oversold = 30
    min_days_between = 1

    def init(self):
        self.rsi = self.I(ta.rsi, pd.Series(self.data.Close), length=self.rsi_period)
        self.total_coins = 0
        self.total_spent = 0
        self.buy_count = 0
        self.last_buy_bar = -999

    def next(self):
        if len(self.data) < self.rsi_period + 1:
            return
        remaining = STARTING_CAPITAL - self.total_spent
        if remaining <= 0:
            return
        current_rsi = self.rsi[-1]
        current_price = self.data.Close[-1]
        current_bar = len(self.data)
        if pd.isna(current_rsi):
            return
        if current_bar - self.last_buy_bar < self.min_days_between:
            return
        if current_rsi < self.rsi_oversold:
            buy_amount = remaining * self.buy_percent
            coins = buy_amount / current_price
            self.total_coins += coins
            self.total_spent += buy_amount
            self.buy_count += 1
            self.last_buy_bar = current_bar


# =============================================================================
# VARIATION 1: RSI Extreme (< 25)
# =============================================================================
class RSIExtreme(Strategy):
    """Only buy at more extreme oversold levels (RSI < 25)"""
    buy_percent = 0.07  # Larger buys since fewer signals
    rsi_period = 14
    rsi_oversold = 25

    def init(self):
        self.rsi = self.I(ta.rsi, pd.Series(self.data.Close), length=self.rsi_period)
        self.total_coins = 0
        self.total_spent = 0
        self.buy_count = 0
        self.last_buy_bar = -999

    def next(self):
        if len(self.data) < self.rsi_period + 1:
            return
        remaining = STARTING_CAPITAL - self.total_spent
        if remaining <= 0:
            return
        current_rsi = self.rsi[-1]
        current_price = self.data.Close[-1]
        current_bar = len(self.data)
        if pd.isna(current_rsi):
            return
        if current_bar - self.last_buy_bar < 1:
            return
        if current_rsi < self.rsi_oversold:
            buy_amount = remaining * self.buy_percent
            coins = buy_amount / current_price
            self.total_coins += coins
            self.total_spent += buy_amount
            self.buy_count += 1
            self.last_buy_bar = current_bar


# =============================================================================
# VARIATION 2: RSI + Volume Spike (Capitulation)
# =============================================================================
class RSIVolumeSpike(Strategy):
    """RSI oversold + volume spike = capitulation buying"""
    buy_percent = 0.05
    rsi_period = 14
    rsi_oversold = 30
    volume_mult = 1.5

    def init(self):
        self.rsi = self.I(ta.rsi, pd.Series(self.data.Close), length=self.rsi_period)
        self.avg_volume = self.I(ta.sma, pd.Series(self.data.Volume), length=20)
        self.total_coins = 0
        self.total_spent = 0
        self.buy_count = 0
        self.last_buy_bar = -999

    def next(self):
        if len(self.data) < 20:
            return
        remaining = STARTING_CAPITAL - self.total_spent
        if remaining <= 0:
            return
        current_rsi = self.rsi[-1]
        current_volume = self.data.Volume[-1]
        avg_vol = self.avg_volume[-1]
        current_price = self.data.Close[-1]
        current_bar = len(self.data)

        if pd.isna(current_rsi) or pd.isna(avg_vol) or avg_vol == 0:
            return
        if current_bar - self.last_buy_bar < 1:
            return

        if current_rsi < self.rsi_oversold and current_volume >= avg_vol * self.volume_mult:
            buy_amount = remaining * self.buy_percent
            coins = buy_amount / current_price
            self.total_coins += coins
            self.total_spent += buy_amount
            self.buy_count += 1
            self.last_buy_bar = current_bar


# =============================================================================
# VARIATION 3: RSI + Trend Filter (Below MA)
# =============================================================================
class RSITrendFilter(Strategy):
    """RSI oversold + below 50 MA (buying dips in downtrend)"""
    buy_percent = 0.05
    rsi_period = 14
    rsi_oversold = 30
    ma_period = 50

    def init(self):
        self.rsi = self.I(ta.rsi, pd.Series(self.data.Close), length=self.rsi_period)
        self.ma = self.I(ta.sma, pd.Series(self.data.Close), length=self.ma_period)
        self.total_coins = 0
        self.total_spent = 0
        self.buy_count = 0
        self.last_buy_bar = -999

    def next(self):
        if len(self.data) < self.ma_period:
            return
        remaining = STARTING_CAPITAL - self.total_spent
        if remaining <= 0:
            return
        current_rsi = self.rsi[-1]
        ma_value = self.ma[-1]
        current_price = self.data.Close[-1]
        current_bar = len(self.data)

        if pd.isna(current_rsi) or pd.isna(ma_value):
            return
        if current_bar - self.last_buy_bar < 1:
            return

        if current_rsi < self.rsi_oversold and current_price < ma_value:
            buy_amount = remaining * self.buy_percent
            coins = buy_amount / current_price
            self.total_coins += coins
            self.total_spent += buy_amount
            self.buy_count += 1
            self.last_buy_bar = current_bar


# =============================================================================
# VARIATION 4: RSI Consecutive Days
# =============================================================================
class RSIConsecutive(Strategy):
    """Buy after 2+ consecutive days of RSI < 30"""
    buy_percent = 0.05
    rsi_period = 14
    rsi_oversold = 30
    min_consecutive = 2

    def init(self):
        self.rsi = self.I(ta.rsi, pd.Series(self.data.Close), length=self.rsi_period)
        self.total_coins = 0
        self.total_spent = 0
        self.buy_count = 0
        self.last_buy_bar = -999
        self.consecutive_oversold = 0

    def next(self):
        if len(self.data) < self.rsi_period + 1:
            return
        remaining = STARTING_CAPITAL - self.total_spent
        if remaining <= 0:
            return
        current_rsi = self.rsi[-1]
        current_price = self.data.Close[-1]
        current_bar = len(self.data)

        if pd.isna(current_rsi):
            return

        # Track consecutive oversold days
        if current_rsi < self.rsi_oversold:
            self.consecutive_oversold += 1
        else:
            self.consecutive_oversold = 0

        if current_bar - self.last_buy_bar < 1:
            return

        if self.consecutive_oversold >= self.min_consecutive:
            buy_amount = remaining * self.buy_percent
            coins = buy_amount / current_price
            self.total_coins += coins
            self.total_spent += buy_amount
            self.buy_count += 1
            self.last_buy_bar = current_bar


# =============================================================================
# VARIATION 5: RSI Gradient Buy
# =============================================================================
class RSIGradient(Strategy):
    """Scale buy size based on how oversold: RSI 30 = 1x, RSI 20 = 2x, RSI 10 = 3x"""
    buy_percent = 0.03  # Base amount, scaled up
    rsi_period = 14
    rsi_oversold = 30

    def init(self):
        self.rsi = self.I(ta.rsi, pd.Series(self.data.Close), length=self.rsi_period)
        self.total_coins = 0
        self.total_spent = 0
        self.buy_count = 0
        self.last_buy_bar = -999

    def next(self):
        if len(self.data) < self.rsi_period + 1:
            return
        remaining = STARTING_CAPITAL - self.total_spent
        if remaining <= 0:
            return
        current_rsi = self.rsi[-1]
        current_price = self.data.Close[-1]
        current_bar = len(self.data)

        if pd.isna(current_rsi):
            return
        if current_bar - self.last_buy_bar < 1:
            return

        if current_rsi < self.rsi_oversold:
            # Scale: RSI 30 = 1x, RSI 20 = 2x, RSI 10 = 3x
            oversold_depth = (self.rsi_oversold - current_rsi) / 10
            multiplier = 1.0 + min(oversold_depth, 2.0)  # Max 3x
            buy_amount = remaining * self.buy_percent * multiplier
            coins = buy_amount / current_price
            self.total_coins += coins
            self.total_spent += buy_amount
            self.buy_count += 1
            self.last_buy_bar = current_bar


# =============================================================================
# VARIATION 6: RSI + Weekly Low Combo
# =============================================================================
class RSIWeeklyLow(Strategy):
    """RSI oversold at weekly low = maximum discount"""
    buy_percent = 0.05
    rsi_period = 14
    rsi_oversold = 35  # Slightly relaxed since combo is rare

    def init(self):
        self.rsi = self.I(ta.rsi, pd.Series(self.data.Close), length=self.rsi_period)
        close = pd.Series(self.data.Close, index=self.data.index)
        weekly_min = close.resample('W').transform('min')
        self.is_weekly_low = self.I(lambda: (close == weekly_min).values.astype(float))
        self.total_coins = 0
        self.total_spent = 0
        self.buy_count = 0
        self.last_buy_bar = -999

    def next(self):
        if len(self.data) < self.rsi_period + 7:
            return
        remaining = STARTING_CAPITAL - self.total_spent
        if remaining <= 0:
            return
        current_rsi = self.rsi[-1]
        is_low = self.is_weekly_low[-1]
        current_price = self.data.Close[-1]
        current_bar = len(self.data)

        if pd.isna(current_rsi):
            return
        if current_bar - self.last_buy_bar < 5:  # Once per week max
            return

        if current_rsi < self.rsi_oversold and is_low > 0:
            buy_amount = remaining * self.buy_percent
            coins = buy_amount / current_price
            self.total_coins += coins
            self.total_spent += buy_amount
            self.buy_count += 1
            self.last_buy_bar = current_bar


# =============================================================================
# VARIATION 7: RSI + Drawdown Scale
# =============================================================================
class RSIDrawdownScale(Strategy):
    """RSI oversold + scale buy based on drawdown from ATH"""
    buy_percent = 0.03
    rsi_period = 14
    rsi_oversold = 30

    def init(self):
        self.rsi = self.I(ta.rsi, pd.Series(self.data.Close), length=self.rsi_period)
        close = pd.Series(self.data.Close)
        ath = close.cummax()
        self.drawdown = self.I(lambda: ((ath - close) / ath).values)
        self.total_coins = 0
        self.total_spent = 0
        self.buy_count = 0
        self.last_buy_bar = -999

    def next(self):
        if len(self.data) < self.rsi_period + 1:
            return
        remaining = STARTING_CAPITAL - self.total_spent
        if remaining <= 0:
            return
        current_rsi = self.rsi[-1]
        current_dd = self.drawdown[-1]
        current_price = self.data.Close[-1]
        current_bar = len(self.data)

        if pd.isna(current_rsi) or pd.isna(current_dd):
            return
        if current_bar - self.last_buy_bar < 1:
            return

        if current_rsi < self.rsi_oversold:
            # Scale: 20% dd = 1.5x, 40% dd = 2x, 60% dd = 3x
            dd_mult = 1.0 + min(current_dd * 3, 2.0)  # Max 3x
            buy_amount = remaining * self.buy_percent * dd_mult
            coins = buy_amount / current_price
            self.total_coins += coins
            self.total_spent += buy_amount
            self.buy_count += 1
            self.last_buy_bar = current_bar


# =============================================================================
# STRATEGY LIST
# =============================================================================
STRATEGIES = [
    ('RSI Oversold (Base)', RSIOversoldBase),
    ('RSI Extreme (<25)', RSIExtreme),
    ('RSI + Volume Spike', RSIVolumeSpike),
    ('RSI + Trend Filter', RSITrendFilter),
    ('RSI Consecutive', RSIConsecutive),
    ('RSI Gradient', RSIGradient),
    ('RSI + Weekly Low', RSIWeeklyLow),
    ('RSI + Drawdown Scale', RSIDrawdownScale),
]

# =============================================================================
# RUN ALL STRATEGIES
# =============================================================================
for asset, data_path in DATA_PATHS.items():
    print(f"\n{'='*70}")
    print(f"Loading {asset} data...")
    print(f"{'='*70}")

    data = pd.read_csv(data_path, parse_dates=['datetime'], index_col='datetime')
    data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
    data = data.sort_index()
    data = data.dropna()

    first_day_price = data['Close'].iloc[0]
    final_price = data['Close'].iloc[-1]
    first_date = data.index[0].strftime('%Y-%m-%d')
    last_date = data.index[-1].strftime('%Y-%m-%d')
    total_days = len(data)

    print(f"{first_date} to {last_date} ({total_days} days)")
    print(f"${first_day_price:,.2f} -> ${final_price:,.2f}")

    # Daily DCA baseline
    dca_daily_amount = STARTING_CAPITAL / total_days
    dca_coins = (dca_daily_amount / data['Close']).sum()
    dca_avg_price = STARTING_CAPITAL / dca_coins
    dca_final_value = dca_coins * final_price

    results.append({
        'Asset': asset,
        'Strategy': 'Daily DCA',
        'Coins': dca_coins,
        'Avg_Price': dca_avg_price,
        'Capital_Used_Pct': 100.0,
        'Buy_Signals': total_days,
        'Final_Value': dca_final_value,
        'vs_DCA_Pct': 0.0,
    })

    # Run each strategy
    for strat_name, strat_class in STRATEGIES:
        print(f"  Running {strat_name}...", end=" ")

        bt = Backtest(data, strat_class, cash=STARTING_CAPITAL, commission=0.001)
        stats = bt.run()
        strategy = stats._strategy

        if strategy.total_coins > 0:
            avg_price = strategy.total_spent / strategy.total_coins
            final_value = strategy.total_coins * final_price
            capital_pct = (strategy.total_spent / STARTING_CAPITAL) * 100
            vs_dca = ((strategy.total_coins - dca_coins) / dca_coins) * 100

            results.append({
                'Asset': asset,
                'Strategy': strat_name,
                'Coins': strategy.total_coins,
                'Avg_Price': avg_price,
                'Capital_Used_Pct': capital_pct,
                'Buy_Signals': strategy.buy_count,
                'Final_Value': final_value,
                'vs_DCA_Pct': vs_dca,
            })
            print(f"{strategy.total_coins:,.4f} coins ({vs_dca:+.1f}% vs DCA)")
        else:
            results.append({
                'Asset': asset,
                'Strategy': strat_name,
                'Coins': 0,
                'Avg_Price': 0,
                'Capital_Used_Pct': 0,
                'Buy_Signals': 0,
                'Final_Value': 0,
                'vs_DCA_Pct': -100,
            })
            print(f"No signals")

# =============================================================================
# SAVE RESULTS
# =============================================================================
df = pd.DataFrame(results)
output_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/backtests/accumulation/phase_1/rsi_oversold_results.csv'
df.to_csv(output_path, index=False)

print(f"\n{'='*70}")
print(f"RESULTS SAVED TO: {output_path}")
print(f"{'='*70}")

# =============================================================================
# SUMMARY
# =============================================================================
print(f"\n{'='*70}")
print("MOON DEV'S RSI OVERSOLD VARIATIONS - PHASE 1 RESULTS")
print(f"{'='*70}")

# Average vs DCA for each strategy
print(f"\nAverage performance vs Daily DCA:")
print("-" * 50)
for strat in df['Strategy'].unique():
    if strat == 'Daily DCA':
        continue
    avg_vs_dca = df[df['Strategy'] == strat]['vs_DCA_Pct'].mean()
    emoji = "+" if avg_vs_dca > 0 else ""
    winner = " <-- WINNER" if avg_vs_dca >= 20 else ""
    print(f"   {strat:25s}: {emoji}{avg_vs_dca:>6.1f}%{winner}")

# Per-asset breakdown
for asset in DATA_PATHS.keys():
    print(f"\n{asset} Rankings (by vs DCA %):")
    print("-" * 50)
    asset_df = df[df['Asset'] == asset].copy()
    asset_df = asset_df.sort_values('vs_DCA_Pct', ascending=False)

    for i, (_, row) in enumerate(asset_df.iterrows()):
        emoji = "1." if i == 0 else "2." if i == 1 else "3." if i == 2 else f"{i+1}."
        print(f"   {emoji} {row['Strategy']:25s} | {row['vs_DCA_Pct']:>+7.1f}% | {row['Coins']:>12,.2f} coins")

print(f"\n{'='*70}")
print("Moon Dev's Phase 1 RSI Oversold Analysis Complete!")
print(f"{'='*70}")
