"""
2xmareversal_walkforward_compound_sma200.py
─────────────────────────────────────────────────────────────────
Compounded walk-forward WITH a 100-day trend filter:
    • Only trade when Close > SMA(100).
    • Otherwise stay flat (positions closed & no new entries).

Outputs land in /data/walk_forward/ as:
    slice_stats_compound_sma100.csv
    equity_curve_compound_sma100.csv / .png
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

# ─── strategy WITH 100-SMA filter ────────────────────────────
class MAReversalStrategy200(Strategy):
    ma_fast, ma_slow = 9, 36
    take_profit, stop_loss = .02, .02

    def init(self):
        self.sma_fast  = self.I(talib.SMA, self.data.Close, self.ma_fast)
        self.sma_slow  = self.I(talib.SMA, self.data.Close, self.ma_slow)
        self.sma_100   = self.I(talib.SMA, self.data.Close, 100)

    def next(self):
        price = self.data.Close[-1]

        # ── trend gate ──────────────────────
        if price <= self.sma_100[-1]:
            if self.position:
                self.position.close()      # flatten if trend turns down
            return                         # skip any new entries
        # ── original MA-reversal logic ─────
        if price > self.sma_fast[-1] < self.sma_slow[-1] and not self.position:
            self.sell(sl=price*(1+self.stop_loss), tp=price*(1-self.take_profit))
        elif price > self.sma_fast[-1] > self.sma_slow[-1] and not self.position:
            self.buy(sl=price*(1-self.stop_loss), tp=price*(1+self.take_profit))
        elif self.position and self.position.is_short and price > self.sma_slow[-1]:
            self.position.close()

# ─── load BTC daily data ─────────────────────────────────────
df = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
df.columns = ['Open','High','Low','Close','Volume']
df.sort_index(inplace=True)

# ─── simple grid search (no return_history arg) ──────────────
def grid_search(data) -> dict:
    bt = Backtest(data, MAReversalStrategy200, cash=START_CAP, commission=COMMISSION)
    best_val, best_params = -np.inf, None
    for f, s, tp, sl in product(FAST_MAS, SLOW_MAS, TPS_SLs, TPS_SLs):
        if f >= s:
            continue
        st = bt.run(ma_fast=f, ma_slow=s, take_profit=tp, stop_loss=sl)
        if st['Sharpe Ratio'] > best_val:
            best_val = st['Sharpe Ratio']
            best_params = dict(ma_fast=f, ma_slow=s, take_profit=tp, stop_loss=sl)
    return best_params

# ─── compounded walk-forward loop ────────────────────────────
slice_rows, equity_master = [], pd.Series(dtype=float)
bankroll = START_CAP
start, end = df.index.min(), df.index.max()

while True:
    train_end = start + pd.DateOffset(years=TRAIN_YEARS) - timedelta(days=1)
    trade_end = train_end + pd.DateOffset(months=TRADE_MONTHS)
    if trade_end > end:
        break

    train_df = df.loc[start:train_end]
    trade_df = df.loc[train_end+timedelta(days=1):trade_end]

    params = grid_search(train_df)
    bt_trade = Backtest(trade_df, MAReversalStrategy200,
                        cash=bankroll, commission=COMMISSION)
    st = bt_trade.run(**params)

    equity_master = pd.concat([equity_master, st['_equity_curve']['Equity']])

    slice_rows.append({
        'train_start': start.date(), 'train_end': train_end.date(),
        'trade_start': (train_end+timedelta(days=1)).date(),
        'trade_end'  : trade_end.date(),
        **params,
        'Return %'   : st['Return [%]'],
        'Sharpe'     : st['Sharpe Ratio'],
        'Sortino'    : st['Sortino Ratio'],
        'Calmar'     : st['Calmar Ratio'],
        'Max DD %'   : st['Max. Drawdown [%]'],
        '# Trades'   : st['# Trades']
    })

    print(f"✓ {slice_rows[-1]['trade_start']} ➜ {slice_rows[-1]['trade_end']}  "
          f"|  Sharpe {st['Sharpe Ratio']:.2f}  |  Return {st['Return [%]']:.1f}%")

    bankroll = equity_master.iloc[-1]
    start += pd.DateOffset(months=TRADE_MONTHS)

# ─── save outputs ────────────────────────────────────────────
pd.DataFrame(slice_rows).to_csv(os.path.join(SAVE_DIR,
    'slice_stats_compound_sma100.csv'), index=False)
equity_master.to_csv(os.path.join(SAVE_DIR,
    'equity_curve_compound_sma100.csv'), header=['Equity'])

tot_ret = (equity_master.iloc[-1]/equity_master.iloc[0]-1)*100
yrs = (equity_master.index[-1]-equity_master.index[0]).days/365
CAGR = (equity_master.iloc[-1]/equity_master.iloc[0])**(1/yrs)-1
max_dd = ((equity_master/equity_master.cummax())-1).min()*100

print('\n─────────  Aggregated (Compounded + SMA-100)  ─────────')
print(f'Final equity : ${equity_master.iloc[-1]:,.0f}')
print(f'Total return : {tot_ret:,.1f} %')
print(f'CAGR         : {CAGR*100:,.1f} %')
print(f'Max DD       : {max_dd:,.1f} %')
print('Mean Sharpe  :', np.round(pd.DataFrame(slice_rows)['Sharpe'].mean(),2))
print('Mean Calmar  :', np.round(pd.DataFrame(slice_rows)['Calmar'].mean(),2))

plt.figure(figsize=(10,5))
equity_master.plot()
plt.title('Walk-Forward Equity (compounded, SMA-100 filter)')
plt.ylabel('Equity ($)')
plt.grid(alpha=.3)
plt.tight_layout()
plt.savefig(os.path.join(SAVE_DIR,'equity_curve_compound_sma100.png'), dpi=150)
plt.close()

print(f'\n🎉 Done!  Files saved in {SAVE_DIR}')
