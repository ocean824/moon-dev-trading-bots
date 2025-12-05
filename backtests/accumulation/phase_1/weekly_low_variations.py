"""
Moon Dev's Weekly Low Variations - Phase 1
==========================================
Testing variations of the Weekly Low strategy that beat DCA by +35% in Phase 0

Variations:
1. Weekly Low + RSI Filter - Only buy weekly low if RSI < 50
2. Weekly Low + Volume Confirm - Only buy if volume > average
3. Weekly Low + Trend Filter - Only buy if below 50 MA
4. Weekly Low + Double Down - Buy more on consecutive weekly lows
5. Weekly Low + Volatility Scale - Buy more when ATR is high
6. Weekly Low + Monthly Low Bonus - Extra buy at monthly lows
7. Weekly Low + Red Week - Only buy if week closed red
"""

import pandas as pd
import numpy as np
import pandas_ta as ta
from backtesting import Backtest, Strategy
import warnings
warnings.filterwarnings('ignore')

print("=" * 70)
print("Moon Dev's Weekly Low Variations - Phase 1")
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
# BASE WEEKLY LOW (for comparison)
# =============================================================================
class WeeklyLowBase(Strategy):
    """Original Weekly Low from Phase 0"""
    weekly_buy = 0.01

    def init(self):
        close = pd.Series(self.data.Close, index=self.data.index)
        weekly_min = close.resample('W').transform('min')
        self.is_weekly_low = self.I(lambda: (close == weekly_min).values.astype(float))
        self.total_coins = 0
        self.total_spent = 0
        self.buy_count = 0
        self.last_week_bought = -1

    def next(self):
        if len(self.data) < 7:
            return
        remaining = STARTING_CAPITAL - self.total_spent
        if remaining <= 0:
            return
        current_price = self.data.Close[-1]
        is_low = self.is_weekly_low[-1]
        current_idx = len(self.data) - 1
        if is_low > 0 and current_idx > self.last_week_bought + 5:
            buy_amount = min(STARTING_CAPITAL * self.weekly_buy, remaining)
            coins = buy_amount / current_price
            self.total_coins += coins
            self.total_spent += buy_amount
            self.buy_count += 1
            self.last_week_bought = current_idx


# =============================================================================
# VARIATION 1: Weekly Low + RSI Filter
# =============================================================================
class WeeklyLowRSI(Strategy):
    """Only buy weekly low if RSI < 50 (momentum confirmation)"""
    weekly_buy = 0.01
    rsi_threshold = 50

    def init(self):
        close = pd.Series(self.data.Close, index=self.data.index)
        weekly_min = close.resample('W').transform('min')
        self.is_weekly_low = self.I(lambda: (close == weekly_min).values.astype(float))
        self.rsi = self.I(ta.rsi, pd.Series(self.data.Close), length=14)
        self.total_coins = 0
        self.total_spent = 0
        self.buy_count = 0
        self.last_week_bought = -1

    def next(self):
        if len(self.data) < 14:
            return
        remaining = STARTING_CAPITAL - self.total_spent
        if remaining <= 0:
            return
        current_price = self.data.Close[-1]
        is_low = self.is_weekly_low[-1]
        current_rsi = self.rsi[-1]
        current_idx = len(self.data) - 1

        if pd.isna(current_rsi):
            return

        if is_low > 0 and current_idx > self.last_week_bought + 5 and current_rsi < self.rsi_threshold:
            buy_amount = min(STARTING_CAPITAL * self.weekly_buy, remaining)
            coins = buy_amount / current_price
            self.total_coins += coins
            self.total_spent += buy_amount
            self.buy_count += 1
            self.last_week_bought = current_idx


# =============================================================================
# VARIATION 2: Weekly Low + Volume Confirm
# =============================================================================
class WeeklyLowVolume(Strategy):
    """Only buy weekly low if volume > 20-day average (capitulation signal)"""
    weekly_buy = 0.01
    volume_mult = 1.0

    def init(self):
        close = pd.Series(self.data.Close, index=self.data.index)
        weekly_min = close.resample('W').transform('min')
        self.is_weekly_low = self.I(lambda: (close == weekly_min).values.astype(float))
        self.avg_volume = self.I(ta.sma, pd.Series(self.data.Volume), length=20)
        self.total_coins = 0
        self.total_spent = 0
        self.buy_count = 0
        self.last_week_bought = -1

    def next(self):
        if len(self.data) < 20:
            return
        remaining = STARTING_CAPITAL - self.total_spent
        if remaining <= 0:
            return
        current_price = self.data.Close[-1]
        current_volume = self.data.Volume[-1]
        is_low = self.is_weekly_low[-1]
        avg_vol = self.avg_volume[-1]
        current_idx = len(self.data) - 1

        if pd.isna(avg_vol) or avg_vol == 0:
            return

        if is_low > 0 and current_idx > self.last_week_bought + 5 and current_volume >= avg_vol * self.volume_mult:
            buy_amount = min(STARTING_CAPITAL * self.weekly_buy, remaining)
            coins = buy_amount / current_price
            self.total_coins += coins
            self.total_spent += buy_amount
            self.buy_count += 1
            self.last_week_bought = current_idx


# =============================================================================
# VARIATION 3: Weekly Low + Trend Filter (Below MA)
# =============================================================================
class WeeklyLowTrend(Strategy):
    """Only buy weekly low if price is below 50 MA (buy the dip in downtrend)"""
    weekly_buy = 0.01
    ma_period = 50

    def init(self):
        close = pd.Series(self.data.Close, index=self.data.index)
        weekly_min = close.resample('W').transform('min')
        self.is_weekly_low = self.I(lambda: (close == weekly_min).values.astype(float))
        self.ma = self.I(ta.sma, pd.Series(self.data.Close), length=self.ma_period)
        self.total_coins = 0
        self.total_spent = 0
        self.buy_count = 0
        self.last_week_bought = -1

    def next(self):
        if len(self.data) < self.ma_period:
            return
        remaining = STARTING_CAPITAL - self.total_spent
        if remaining <= 0:
            return
        current_price = self.data.Close[-1]
        is_low = self.is_weekly_low[-1]
        ma_value = self.ma[-1]
        current_idx = len(self.data) - 1

        if pd.isna(ma_value):
            return

        if is_low > 0 and current_idx > self.last_week_bought + 5 and current_price < ma_value:
            buy_amount = min(STARTING_CAPITAL * self.weekly_buy, remaining)
            coins = buy_amount / current_price
            self.total_coins += coins
            self.total_spent += buy_amount
            self.buy_count += 1
            self.last_week_bought = current_idx


# =============================================================================
# VARIATION 4: Weekly Low + Double Down
# =============================================================================
class WeeklyLowDoubleDown(Strategy):
    """Buy more on consecutive weekly lows (averaging down aggressively)"""
    weekly_buy = 0.01

    def init(self):
        close = pd.Series(self.data.Close, index=self.data.index)
        weekly_min = close.resample('W').transform('min')
        self.is_weekly_low = self.I(lambda: (close == weekly_min).values.astype(float))
        self.total_coins = 0
        self.total_spent = 0
        self.buy_count = 0
        self.last_week_bought = -1
        self.consecutive_lows = 0

    def next(self):
        if len(self.data) < 7:
            return
        remaining = STARTING_CAPITAL - self.total_spent
        if remaining <= 0:
            return
        current_price = self.data.Close[-1]
        is_low = self.is_weekly_low[-1]
        current_idx = len(self.data) - 1

        if is_low > 0 and current_idx > self.last_week_bought + 5:
            # Check if this is a consecutive low (price lower than last buy)
            if self.buy_count > 0 and current_price < self.total_spent / self.total_coins:
                self.consecutive_lows += 1
            else:
                self.consecutive_lows = 0

            # Scale buy amount: 1x, 1.5x, 2x for consecutive lows
            multiplier = min(1.0 + (self.consecutive_lows * 0.5), 2.0)
            buy_amount = min(STARTING_CAPITAL * self.weekly_buy * multiplier, remaining)
            coins = buy_amount / current_price
            self.total_coins += coins
            self.total_spent += buy_amount
            self.buy_count += 1
            self.last_week_bought = current_idx


# =============================================================================
# VARIATION 5: Weekly Low + Volatility Scale
# =============================================================================
class WeeklyLowVolatility(Strategy):
    """Buy more when volatility (ATR) is elevated (better deals in chaos)"""
    weekly_buy = 0.01
    atr_period = 14
    atr_lookback = 50

    def init(self):
        close = pd.Series(self.data.Close, index=self.data.index)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        weekly_min = close.resample('W').transform('min')
        self.is_weekly_low = self.I(lambda: (close == weekly_min).values.astype(float))
        self.atr = self.I(ta.atr, high, low, close, self.atr_period)
        atr_series = ta.atr(high, low, close, self.atr_period)
        self.atr_avg = self.I(lambda: atr_series.rolling(self.atr_lookback).mean().values)
        self.total_coins = 0
        self.total_spent = 0
        self.buy_count = 0
        self.last_week_bought = -1

    def next(self):
        if len(self.data) < self.atr_lookback:
            return
        remaining = STARTING_CAPITAL - self.total_spent
        if remaining <= 0:
            return
        current_price = self.data.Close[-1]
        is_low = self.is_weekly_low[-1]
        current_atr = self.atr[-1]
        avg_atr = self.atr_avg[-1]
        current_idx = len(self.data) - 1

        if pd.isna(current_atr) or pd.isna(avg_atr) or avg_atr == 0:
            return

        if is_low > 0 and current_idx > self.last_week_bought + 5:
            # Scale buy: more when ATR is above average
            atr_ratio = current_atr / avg_atr
            multiplier = min(max(atr_ratio, 0.5), 2.0)  # 0.5x to 2x
            buy_amount = min(STARTING_CAPITAL * self.weekly_buy * multiplier, remaining)
            coins = buy_amount / current_price
            self.total_coins += coins
            self.total_spent += buy_amount
            self.buy_count += 1
            self.last_week_bought = current_idx


# =============================================================================
# VARIATION 6: Weekly Low + Monthly Low Bonus
# =============================================================================
class WeeklyLowMonthly(Strategy):
    """Normal weekly buy, but 2x at monthly lows"""
    weekly_buy = 0.01

    def init(self):
        close = pd.Series(self.data.Close, index=self.data.index)
        weekly_min = close.resample('W').transform('min')
        monthly_min = close.resample('M').transform('min')
        self.is_weekly_low = self.I(lambda: (close == weekly_min).values.astype(float))
        self.is_monthly_low = self.I(lambda: (close == monthly_min).values.astype(float))
        self.total_coins = 0
        self.total_spent = 0
        self.buy_count = 0
        self.last_week_bought = -1

    def next(self):
        if len(self.data) < 30:
            return
        remaining = STARTING_CAPITAL - self.total_spent
        if remaining <= 0:
            return
        current_price = self.data.Close[-1]
        is_weekly = self.is_weekly_low[-1]
        is_monthly = self.is_monthly_low[-1]
        current_idx = len(self.data) - 1

        if is_weekly > 0 and current_idx > self.last_week_bought + 5:
            # 2x at monthly low, 1x at weekly low
            multiplier = 2.0 if is_monthly > 0 else 1.0
            buy_amount = min(STARTING_CAPITAL * self.weekly_buy * multiplier, remaining)
            coins = buy_amount / current_price
            self.total_coins += coins
            self.total_spent += buy_amount
            self.buy_count += 1
            self.last_week_bought = current_idx


# =============================================================================
# VARIATION 7: Weekly Low + Red Week Filter
# =============================================================================
class WeeklyLowRedWeek(Strategy):
    """Only buy weekly low if the week closed red (confirmed weakness)"""
    weekly_buy = 0.01

    def init(self):
        close = pd.Series(self.data.Close, index=self.data.index)
        weekly_min = close.resample('W').transform('min')
        self.is_weekly_low = self.I(lambda: (close == weekly_min).values.astype(float))

        # Calculate weekly returns
        weekly_close = close.resample('W').last()
        weekly_return = weekly_close.pct_change()
        # Forward fill to daily
        weekly_return_daily = weekly_return.reindex(close.index, method='ffill')
        self.weekly_red = self.I(lambda: (weekly_return_daily < 0).values.astype(float))

        self.total_coins = 0
        self.total_spent = 0
        self.buy_count = 0
        self.last_week_bought = -1

    def next(self):
        if len(self.data) < 14:
            return
        remaining = STARTING_CAPITAL - self.total_spent
        if remaining <= 0:
            return
        current_price = self.data.Close[-1]
        is_low = self.is_weekly_low[-1]
        is_red = self.weekly_red[-1]
        current_idx = len(self.data) - 1

        if is_low > 0 and current_idx > self.last_week_bought + 5 and is_red > 0:
            buy_amount = min(STARTING_CAPITAL * self.weekly_buy, remaining)
            coins = buy_amount / current_price
            self.total_coins += coins
            self.total_spent += buy_amount
            self.buy_count += 1
            self.last_week_bought = current_idx


# =============================================================================
# STRATEGY LIST
# =============================================================================
STRATEGIES = [
    ('Weekly Low (Base)', WeeklyLowBase),
    ('WL + RSI Filter', WeeklyLowRSI),
    ('WL + Volume Confirm', WeeklyLowVolume),
    ('WL + Trend Filter', WeeklyLowTrend),
    ('WL + Double Down', WeeklyLowDoubleDown),
    ('WL + Volatility Scale', WeeklyLowVolatility),
    ('WL + Monthly Bonus', WeeklyLowMonthly),
    ('WL + Red Week', WeeklyLowRedWeek),
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
output_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/backtests/accumulation/phase_1/weekly_low_results.csv'
df.to_csv(output_path, index=False)

print(f"\n{'='*70}")
print(f"RESULTS SAVED TO: {output_path}")
print(f"{'='*70}")

# =============================================================================
# SUMMARY
# =============================================================================
print(f"\n{'='*70}")
print("MOON DEV'S WEEKLY LOW VARIATIONS - PHASE 1 RESULTS")
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
print("Moon Dev's Phase 1 Weekly Low Analysis Complete!")
print(f"{'='*70}")
