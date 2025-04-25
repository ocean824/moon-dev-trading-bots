"""
2xmareversal_walkforward_compound.py
─────────────────────────────────────────────────────────────────
Walk-forward (3-year optimise → next 6-month trade) **with compounding**.

Grid:
    fast  : [7, 9, 11, 13]
    slow  : [30, 33, 36, 39, 42, 45]  (fast < slow enforced)
    TP/SL : [1 %, 2 %, 3 %]

Outputs → /data/walk_forward/
    slice_stats_compound.csv
    equity_curve_compound.csv + .png
"""

import os, pandas as pd, numpy as np, talib, matplotlib.pyplot as plt
from datetime import timedelta
from itertools import product
from backtesting import Backtest, Strategy

# ─── paths & folders ─────────────────────────────────────────
ROOT = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots'
DATA_PATH = f'{ROOT}/data/coinbase/BTCUSD-1d-1000wks-data.csv'
SAVE_DIR  = f'{ROOT}/data/walk_forward/'
os.makedirs(SAVE_DIR, exist_ok=True)

# ─── walk-forward settings ───────────────────────────────────
TRAIN_YEARS, TRADE_MONTHS = 3, 6
FAST_MAS  = [7, 9, 11, 13]
SLOW_MAS  = [30, 33, 36, 39, 42, 45]
TPS_SLs   = [0.01, 0.02, 0.03]            # 1 % – 3 %
START_CAP = 1_000_000                     # bankroll for very first slice
COMMISSION = .002

# ─── strategy definition ─────────────────────────────────────
class MAReversalStrategy(Strategy):
    ma_fast, ma_slow = 9, 36
    take_profit, stop_loss = .02, .02

    def init(self):
        self.sma_fast = self.I(talib.SMA, self.data.Close, self.ma_fast)
        self.sma_slow = self.I(talib.SMA, self.data.Close, self.ma_slow)

    def next(self):
        p = self.data.Close[-1]
        if p > self.sma_fast[-1] < self.sma_slow[-1] and not self.position:
            self.sell(sl=p*(1+self.stop_loss), tp=p*(1-self.take_profit))
        elif p > self.sma_fast[-1] > self.sma_slow[-1] and not self.position:
            self.buy(sl=p*(1-self.stop_loss), tp=p*(1+self.take_profit))
        elif self.position and self.position.is_short and p > self.sma_slow[-1]:
            self.position.close()

# ─── load BTC daily data ─────────────────────────────────────
df = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
df.columns = ['Open','High','Low','Close','Volume']
df.sort_index(inplace=True)

# ─── manual grid search (avoids return_history kwarg) ────────
def grid_search(data) -> dict:
    bt = Backtest(data, MAReversalStrategy, cash=START_CAP, commission=COMMISSION)
    best_val, best_params = -np.inf, None
    for f, s, tp, sl in product(FAST_MAS, SLOW_MAS, TPS_SLs, TPS_SLs):
        if f >= s:   # maintain fast < slow
            continue
        stats = bt.run(ma_fast=f, ma_slow=s, take_profit=tp, stop_loss=sl)
        if stats['Sharpe Ratio'] > best_val:
            best_val = stats['Sharpe Ratio']
            best_params = dict(ma_fast=f, ma_slow=s, take_profit=tp, stop_loss=sl)
    return best_params

# ─── walk-forward loop with compounding ──────────────────────
slice_rows, equity_master = [], pd.Series(dtype=float)
bankroll = START_CAP

start = df.index.min();  end = df.index.max()

while True:
    train_end = start + pd.DateOffset(years=TRAIN_YEARS) - timedelta(days=1)
    trade_end = train_end + pd.DateOffset(months=TRADE_MONTHS)
    if trade_end > end: break

    train_df  = df.loc[start:train_end]
    trade_df  = df.loc[train_end+timedelta(days=1):trade_end]

    params = grid_search(train_df)

    bt_trade = Backtest(trade_df, MAReversalStrategy,
                        cash=bankroll, commission=COMMISSION)
    stats    = bt_trade.run(**params)

    # append equity (already denominated in $) to master series
    equity_slice = stats['_equity_curve']['Equity']
    equity_master = pd.concat([equity_master, equity_slice])

    slice_rows.append({
        'train_start': start.date(), 'train_end': train_end.date(),
        'trade_start': (train_end+timedelta(days=1)).date(),
        'trade_end'  : trade_end.date(),
        **params,
        'Return %'   : stats['Return [%]'],
        'Sharpe'     : stats['Sharpe Ratio'],
        'Sortino'    : stats['Sortino Ratio'],
        'Calmar'     : stats['Calmar Ratio'],
        'Max DD %'   : stats['Max. Drawdown [%]'],
        '# Trades'   : stats['# Trades']
    })

    print(f"✓ {slice_rows[-1]['trade_start']} ➜ {slice_rows[-1]['trade_end']}  "
          f"|  Sharpe {stats['Sharpe Ratio']:.2f}  |  Return {stats['Return [%]']:.1f}%")

    # bankroll for the next slice = last equity value of current slice
    bankroll = equity_slice.iloc[-1]
    start    = start + pd.DateOffset(months=TRADE_MONTHS)

# ─── save artefacts ──────────────────────────────────────────
pd.DataFrame(slice_rows).to_csv(os.path.join(SAVE_DIR,'slice_stats_compound.csv'), index=False)
equity_master.to_csv(os.path.join(SAVE_DIR,'equity_curve_compound.csv'), header=['Equity'])

# overall figures on compounded curve
tot_ret = (equity_master.iloc[-1]/equity_master.iloc[0]-1)*100
yrs = (equity_master.index[-1] - equity_master.index[0]).days / 365
CAGR = (equity_master.iloc[-1]/equity_master.iloc[0])**(1/yrs) - 1
max_dd = ((equity_master / equity_master.cummax()) - 1).min() * 100

print('\n─────────  Aggregated (Compounded)  ─────────')
print(f'Final equity : ${equity_master.iloc[-1]:,.0f}')
print(f'Total return : {tot_ret:,.1f} %')
print(f'CAGR         : {CAGR*100:,.1f} %')
print(f'Max DD       : {max_dd:,.1f} %')
print('Mean Sharpe  :', np.round(pd.DataFrame(slice_rows)['Sharpe'].mean(),2))
print('Mean Calmar  :', np.round(pd.DataFrame(slice_rows)['Calmar'].mean(),2))

# ─── equity plot ─────────────────────────────────────────────
plt.figure(figsize=(10,5))
equity_master.plot()
plt.title('Walk-Forward Equity (compounded)')
plt.ylabel('Equity ($)')
plt.grid(alpha=.3)
plt.tight_layout()
plt.savefig(os.path.join(SAVE_DIR,'equity_curve_compound.png'), dpi=150)
plt.close()

print(f'\n🎉 Compounded walk-forward complete! Files in {SAVE_DIR}')
