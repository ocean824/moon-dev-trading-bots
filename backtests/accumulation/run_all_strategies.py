"""
Moon Dev's Accumulation Strategy Runner
=======================================
Runs all 9 accumulation strategies across BTC, ETH, and SOL
Outputs results to CSV for analysis
"""

import pandas as pd
import numpy as np
import pandas_ta as ta
from backtesting import Backtest, Strategy
import warnings
warnings.filterwarnings('ignore')

print("=" * 70)
print("🌙 Moon Dev's Accumulation Strategy Runner")
print("=" * 70)

# =============================================================================
# CONFIGURATION
# =============================================================================
STARTING_CAPITAL = 1_000_000

# =============================================================================
# 5-YEAR DATA (260 weeks) - More realistic for Saylor-style accumulation
# =============================================================================
DATA_PATHS = {
    'BTC': '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1d-260wks-data.csv',
    'ETH': '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/ETHUSD-1d-260wks-data.csv',
    'SOL': '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/SOLUSD-1d-260wks-data.csv',
}

# =============================================================================
# 10-YEAR DATA (1000 weeks) - Full history, but starts at generational lows
# =============================================================================
# DATA_PATHS = {
#     'BTC': '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1d-1000wks-data.csv',
#     'ETH': '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/ETHUSD-1d-1000wks-data.csv',
#     'SOL': '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/SOLUSD-1d-1000wks-data.csv',
# }

# Results storage
results = []

# =============================================================================
# STRATEGY DEFINITIONS
# =============================================================================

class RSIOversoldAccumulator(Strategy):
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


class ConsecutiveRedAccumulator(Strategy):
    buy_percent = 0.05
    min_red_days = 3
    scale_with_days = True

    def init(self):
        close = pd.Series(self.data.Close)
        daily_change = close.pct_change()
        def count_consecutive_red(changes):
            result = np.zeros(len(changes))
            count = 0
            for i in range(len(changes)):
                if pd.isna(changes.iloc[i]):
                    count = 0
                elif changes.iloc[i] < 0:
                    count += 1
                else:
                    count = 0
                result[i] = count
            return result
        self.red_days = self.I(lambda: count_consecutive_red(daily_change))
        self.total_coins = 0
        self.total_spent = 0
        self.buy_count = 0

    def next(self):
        if len(self.data) < 5:
            return
        remaining = STARTING_CAPITAL - self.total_spent
        if remaining <= 0:
            return
        current_red = self.red_days[-1]
        current_price = self.data.Close[-1]
        if current_red >= self.min_red_days:
            if self.scale_with_days:
                multiplier = min(current_red / self.min_red_days, 3.0)
            else:
                multiplier = 1.0
            buy_pct = self.buy_percent * multiplier
            buy_amount = min(remaining * buy_pct, remaining)
            coins = buy_amount / current_price
            self.total_coins += coins
            self.total_spent += buy_amount
            self.buy_count += 1


class WeeklyLowAccumulator(Strategy):
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


class VolatilityCrushAccumulator(Strategy):
    buy_percent = 0.02
    atr_period = 14
    atr_lookback = 50
    vol_threshold = 0.7

    def init(self):
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        close = pd.Series(self.data.Close)
        self.atr = self.I(ta.atr, high, low, close, self.atr_period)
        atr_series = ta.atr(high, low, close, self.atr_period)
        self.atr_avg = self.I(lambda: atr_series.rolling(self.atr_lookback).mean().values)
        self.total_coins = 0
        self.total_spent = 0
        self.buy_count = 0
        self.last_buy_bar = -10

    def next(self):
        if len(self.data) < self.atr_lookback + self.atr_period:
            return
        remaining = STARTING_CAPITAL - self.total_spent
        if remaining <= 0:
            return
        if len(self.data) - self.last_buy_bar < 3:
            return
        current_atr = self.atr[-1]
        avg_atr = self.atr_avg[-1]
        current_price = self.data.Close[-1]
        if pd.isna(current_atr) or pd.isna(avg_atr) or avg_atr == 0:
            return
        atr_ratio = current_atr / avg_atr
        if atr_ratio < self.vol_threshold:
            buy_amount = min(remaining * self.buy_percent, remaining)
            coins = buy_amount / current_price
            self.total_coins += coins
            self.total_spent += buy_amount
            self.buy_count += 1
            self.last_buy_bar = len(self.data)


class MADiscountAccumulator(Strategy):
    buy_percent = 0.05
    ma_period = 50
    discount_threshold = 0.10
    scale_discount = True

    def init(self):
        close = pd.Series(self.data.Close)
        self.ma = self.I(ta.sma, close, self.ma_period)
        self.total_coins = 0
        self.total_spent = 0
        self.buy_count = 0
        self.last_buy_bar = -5

    def next(self):
        if len(self.data) < self.ma_period + 1:
            return
        remaining = STARTING_CAPITAL - self.total_spent
        if remaining <= 0:
            return
        if len(self.data) - self.last_buy_bar < 3:
            return
        current_price = self.data.Close[-1]
        ma_value = self.ma[-1]
        if pd.isna(ma_value) or ma_value == 0:
            return
        discount = (ma_value - current_price) / ma_value
        if discount >= self.discount_threshold:
            if self.scale_discount:
                multiplier = min(discount / self.discount_threshold, 3.0)
            else:
                multiplier = 1.0
            buy_pct = self.buy_percent * multiplier
            buy_amount = min(remaining * buy_pct, remaining)
            coins = buy_amount / current_price
            self.total_coins += coins
            self.total_spent += buy_amount
            self.buy_count += 1
            self.last_buy_bar = len(self.data)


class BollingerBounceAccumulator(Strategy):
    buy_percent = 0.05
    bb_period = 20
    bb_std = 2.0

    def init(self):
        close = pd.Series(self.data.Close)
        bb = ta.bbands(close, length=self.bb_period, std=self.bb_std)
        lower_col = f'BBL_{self.bb_period}_{self.bb_std}'
        middle_col = f'BBM_{self.bb_period}_{self.bb_std}'
        self.bb_lower = self.I(lambda: bb[lower_col].values)
        self.bb_middle = self.I(lambda: bb[middle_col].values)
        self.total_coins = 0
        self.total_spent = 0
        self.buy_count = 0
        self.last_buy_bar = -3

    def next(self):
        if len(self.data) < self.bb_period + 1:
            return
        remaining = STARTING_CAPITAL - self.total_spent
        if remaining <= 0:
            return
        if len(self.data) - self.last_buy_bar < 2:
            return
        current_price = self.data.Close[-1]
        current_low = self.data.Low[-1]
        bb_lower = self.bb_lower[-1]
        bb_middle = self.bb_middle[-1]
        if pd.isna(bb_lower):
            return
        if current_low <= bb_lower or current_price <= bb_lower:
            distance_pct = (bb_lower - current_price) / bb_middle if bb_middle > 0 else 0
            multiplier = 1.0 + max(0, distance_pct * 10)
            multiplier = min(multiplier, 2.0)
            buy_pct = self.buy_percent * multiplier
            buy_amount = min(remaining * buy_pct, remaining)
            coins = buy_amount / current_price
            self.total_coins += coins
            self.total_spent += buy_amount
            self.buy_count += 1
            self.last_buy_bar = len(self.data)


class DCAPlusDipAccumulator(Strategy):
    monthly_dca = 0.005
    dip_threshold = 0.05
    dip_buy_pct = 0.02
    dip_reserve = 0.30

    def init(self):
        close = pd.Series(self.data.Close)
        self.daily_return = self.I(lambda x: x.pct_change().values, close)
        months = pd.Series(self.data.index).dt.month.values
        month_change = np.zeros(len(months))
        for i in range(1, len(months)):
            if months[i] != months[i-1]:
                month_change[i] = 1
        self.new_month = self.I(lambda: month_change)
        self.total_coins = 0
        self.total_spent = 0
        self.buy_count = 0
        self.dca_budget = STARTING_CAPITAL * (1 - self.dip_reserve)
        self.dip_budget = STARTING_CAPITAL * self.dip_reserve
        self.dca_spent = 0
        self.dip_spent = 0

    def next(self):
        if len(self.data) < 5:
            return
        current_price = self.data.Close[-1]
        daily_ret = self.daily_return[-1]
        is_new_month = self.new_month[-1]
        if is_new_month > 0 and self.dca_spent < self.dca_budget:
            buy_amount = min(STARTING_CAPITAL * self.monthly_dca, self.dca_budget - self.dca_spent)
            if buy_amount > 0:
                coins = buy_amount / current_price
                self.total_coins += coins
                self.total_spent += buy_amount
                self.dca_spent += buy_amount
                self.buy_count += 1
        if not pd.isna(daily_ret) and daily_ret < -self.dip_threshold:
            if self.dip_spent < self.dip_budget:
                dip_magnitude = abs(daily_ret)
                multiplier = min(dip_magnitude / self.dip_threshold, 3.0)
                buy_amount = min(STARTING_CAPITAL * self.dip_buy_pct * multiplier, self.dip_budget - self.dip_spent)
                if buy_amount > 0:
                    coins = buy_amount / current_price
                    self.total_coins += coins
                    self.total_spent += buy_amount
                    self.dip_spent += buy_amount
                    self.buy_count += 1


class ATHDrawdownAccumulator(Strategy):
    drawdown_levels = {0.20: 0.02, 0.30: 0.04, 0.40: 0.06, 0.50: 0.08, 0.60: 0.10, 0.70: 0.15}

    def init(self):
        close = pd.Series(self.data.Close)
        self.ath = self.I(lambda: close.cummax().values)
        def calc_drawdown(close, ath):
            dd = np.zeros(len(close))
            for i in range(len(close)):
                if ath[i] > 0:
                    dd[i] = (ath[i] - close[i]) / ath[i]
            return dd
        close_arr = close.values
        ath_arr = close.cummax().values
        self.drawdown = self.I(lambda: calc_drawdown(close_arr, ath_arr))
        self.levels_bought = set()
        self.last_ath = 0
        self.total_coins = 0
        self.total_spent = 0
        self.buy_count = 0

    def next(self):
        if len(self.data) < 10:
            return
        remaining = STARTING_CAPITAL - self.total_spent
        if remaining <= 0:
            return
        current_price = self.data.Close[-1]
        current_ath = self.ath[-1]
        current_dd = self.drawdown[-1]
        if current_ath > self.last_ath * 1.05:
            self.levels_bought = set()
            self.last_ath = current_ath
        for dd_level, buy_pct in sorted(self.drawdown_levels.items()):
            if current_dd >= dd_level and dd_level not in self.levels_bought:
                buy_amount = min(remaining * buy_pct, remaining)
                coins = buy_amount / current_price
                self.total_coins += coins
                self.total_spent += buy_amount
                self.buy_count += 1
                self.levels_bought.add(dd_level)
                remaining = STARTING_CAPITAL - self.total_spent
                break


class VolumeSpikeAccumulator(Strategy):
    buy_percent = 0.05
    volume_mult = 2.0
    volume_lookback = 20
    price_drop_pct = -0.02

    def init(self):
        self.avg_volume = self.I(ta.sma, pd.Series(self.data.Volume), length=self.volume_lookback)
        close_series = pd.Series(self.data.Close)
        self.daily_return = self.I(lambda x: x.pct_change().values, close_series)
        self.total_coins = 0
        self.total_spent = 0
        self.buy_count = 0

    def next(self):
        if len(self.data) < self.volume_lookback + 1:
            return
        remaining = STARTING_CAPITAL - self.total_spent
        if remaining <= 0:
            return
        current_volume = self.data.Volume[-1]
        avg_vol = self.avg_volume[-1]
        daily_ret = self.daily_return[-1]
        current_price = self.data.Close[-1]
        if pd.isna(avg_vol) or pd.isna(daily_ret) or avg_vol == 0:
            return
        volume_spike = current_volume >= (avg_vol * self.volume_mult)
        price_dropping = daily_ret < self.price_drop_pct
        if volume_spike and price_dropping:
            buy_amount = remaining * self.buy_percent
            coins = buy_amount / current_price
            self.total_coins += coins
            self.total_spent += buy_amount
            self.buy_count += 1


# =============================================================================
# STRATEGY LIST
# =============================================================================
STRATEGIES = [
    ('RSI Oversold', RSIOversoldAccumulator),
    ('Consecutive Red', ConsecutiveRedAccumulator),
    ('Weekly Low', WeeklyLowAccumulator),
    ('Volatility Crush', VolatilityCrushAccumulator),
    ('MA Discount', MADiscountAccumulator),
    ('Bollinger Bounce', BollingerBounceAccumulator),
    ('DCA + Dip', DCAPlusDipAccumulator),
    ('ATH Drawdown', ATHDrawdownAccumulator),
    ('Volume Spike', VolumeSpikeAccumulator),
]

# =============================================================================
# RUN ALL STRATEGIES
# =============================================================================
for asset, data_path in DATA_PATHS.items():
    print(f"\n{'='*70}")
    print(f"📊 Loading {asset} data...")
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

    print(f"📅 {first_date} to {last_date} ({total_days} days)")
    print(f"💰 ${first_day_price:,.2f} → ${final_price:,.2f}")

    # Day 1 Lump Sum baseline
    day1_coins = STARTING_CAPITAL / first_day_price
    day1_final_value = day1_coins * final_price

    results.append({
        'Asset': asset,
        'Strategy': 'Day 1 Lump Sum',
        'Coins': day1_coins,
        'Avg_Price': first_day_price,
        'Capital_Used_Pct': 100.0,
        'Buy_Signals': 1,
        'Final_Value': day1_final_value,
        'vs_Day1_Pct': 0.0,
        'vs_DCA_Pct': 0.0,
        'First_Date': first_date,
        'Last_Date': last_date,
        'Start_Price': first_day_price,
        'End_Price': final_price,
    })

    # Daily DCA baseline
    dca_daily_amount = STARTING_CAPITAL / total_days
    dca_coins = (dca_daily_amount / data['Close']).sum()
    dca_avg_price = STARTING_CAPITAL / dca_coins
    dca_final_value = dca_coins * final_price

    vs_day1_dca = ((dca_coins - day1_coins) / day1_coins) * 100

    results.append({
        'Asset': asset,
        'Strategy': 'Daily DCA',
        'Coins': dca_coins,
        'Avg_Price': dca_avg_price,
        'Capital_Used_Pct': 100.0,
        'Buy_Signals': total_days,
        'Final_Value': dca_final_value,
        'vs_Day1_Pct': vs_day1_dca,
        'vs_DCA_Pct': 0.0,
        'First_Date': first_date,
        'Last_Date': last_date,
        'Start_Price': first_day_price,
        'End_Price': final_price,
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
            vs_day1 = ((strategy.total_coins - day1_coins) / day1_coins) * 100
            vs_dca = ((strategy.total_coins - dca_coins) / dca_coins) * 100

            results.append({
                'Asset': asset,
                'Strategy': strat_name,
                'Coins': strategy.total_coins,
                'Avg_Price': avg_price,
                'Capital_Used_Pct': capital_pct,
                'Buy_Signals': strategy.buy_count,
                'Final_Value': final_value,
                'vs_Day1_Pct': vs_day1,
                'vs_DCA_Pct': vs_dca,
                'First_Date': first_date,
                'Last_Date': last_date,
                'Start_Price': first_day_price,
                'End_Price': final_price,
            })
            print(f"✅ {strategy.total_coins:,.4f} coins ({vs_day1:+.1f}% vs Day1)")
        else:
            results.append({
                'Asset': asset,
                'Strategy': strat_name,
                'Coins': 0,
                'Avg_Price': 0,
                'Capital_Used_Pct': 0,
                'Buy_Signals': 0,
                'Final_Value': 0,
                'vs_Day1_Pct': -100,
                'vs_DCA_Pct': -100,
                'First_Date': first_date,
                'Last_Date': last_date,
                'Start_Price': first_day_price,
                'End_Price': final_price,
            })
            print(f"⚠️ No signals")

# =============================================================================
# SAVE RESULTS
# =============================================================================
df = pd.DataFrame(results)
output_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/backtests/accumulation/strategy_comparison_results.csv'
df.to_csv(output_path, index=False)

print(f"\n{'='*70}")
print(f"📊 RESULTS SAVED TO: {output_path}")
print(f"{'='*70}")

# =============================================================================
# SUMMARY ANALYSIS
# =============================================================================
print(f"\n{'='*70}")
print("🏆 MOON DEV'S ACCUMULATION STRATEGY ANALYSIS")
print(f"{'='*70}")

for asset in DATA_PATHS.keys():
    asset_df = df[df['Asset'] == asset].copy()
    asset_df = asset_df.sort_values('Coins', ascending=False)

    print(f"\n📊 {asset} RANKINGS (by coins accumulated):")
    print("-" * 60)

    day1_coins = asset_df[asset_df['Strategy'] == 'Day 1 Lump Sum']['Coins'].values[0]

    for i, row in asset_df.iterrows():
        rank = list(asset_df.index).index(i) + 1
        emoji = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else "  "
        print(f"{emoji} {rank}. {row['Strategy']:20s} | {row['Coins']:>12,.4f} {asset} | {row['vs_Day1_Pct']:>+7.1f}% vs Day1 | Capital: {row['Capital_Used_Pct']:>5.1f}%")

# Overall winner analysis
print(f"\n{'='*70}")
print("📈 OVERALL ANALYSIS")
print(f"{'='*70}")

# Count how many times each strategy beats Day 1
strategy_wins = {}
for strat in df['Strategy'].unique():
    if strat == 'Day 1 Lump Sum':
        continue
    beats_day1 = 0
    for asset in DATA_PATHS.keys():
        asset_df = df[df['Asset'] == asset]
        strat_coins = asset_df[asset_df['Strategy'] == strat]['Coins'].values
        day1_coins = asset_df[asset_df['Strategy'] == 'Day 1 Lump Sum']['Coins'].values
        if len(strat_coins) > 0 and len(day1_coins) > 0:
            if strat_coins[0] > day1_coins[0]:
                beats_day1 += 1
    strategy_wins[strat] = beats_day1

print(f"\n🎯 How often each strategy BEATS Day 1 Lump Sum (out of {len(DATA_PATHS)} assets):")
for strat, wins in sorted(strategy_wins.items(), key=lambda x: x[1], reverse=True):
    print(f"   {strat:20s}: {wins}/{len(DATA_PATHS)} times")

# Average performance vs Day 1
print(f"\n📊 Average performance vs Day 1 Lump Sum:")
for strat in df['Strategy'].unique():
    if strat == 'Day 1 Lump Sum':
        continue
    avg_vs_day1 = df[df['Strategy'] == strat]['vs_Day1_Pct'].mean()
    print(f"   {strat:20s}: {avg_vs_day1:>+7.1f}%")

print(f"\n{'='*70}")
print("🌙 Moon Dev's Analysis Complete!")
print(f"{'='*70}")
