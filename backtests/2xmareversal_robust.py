"""
robust_sma_plateau_v2.py
— dense grid + Sharpe / Sortino / Calmar heat-maps
"""

import os, pandas as pd, talib, matplotlib.pyplot as plt
from itertools import product
from backtesting import Backtest, Strategy

# ─── config ──────────────────────────────────────────────────
SAVE_DIR = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/robust_tests/'
os.makedirs(SAVE_DIR, exist_ok=True)

PATH_IS  = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/IS_BTCUSD-1d-1000wks-data.csv'
PATH_OOS = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/OS_BTCUSD-1d-1000wks-data.csv'

# ─── load ────────────────────────────────────────────────────
is_df  = pd.read_csv(PATH_IS,  parse_dates=['datetime'], index_col='datetime')
oos_df = pd.read_csv(PATH_OOS, parse_dates=['datetime'], index_col='datetime')
for df in (is_df, oos_df):
    df.columns = ['Open','High','Low','Close','Volume']
    df.sort_index(inplace=True)

# ─── strategy ────────────────────────────────────────────────
class MAReversalStrategy(Strategy):
    ma_fast, ma_slow = 20, 40
    take_profit, stop_loss = .10, .10
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

# ─── baseline opt for centre point ───────────────────────────
bt_is = Backtest(is_df, MAReversalStrategy, cash=1_000_000, commission=.002)
best   = bt_is.optimize(
            ma_fast = range(10,30,3),
            ma_slow = range(30,60,3),
            take_profit=[i/100 for i in range(2,16,2)],
            stop_loss  =[i/100 for i in range(2,16,2)],
            maximize='Sharpe Ratio',
            constraint=lambda p: p.ma_fast < p.ma_slow)

bf, bs = best._strategy.ma_fast, best._strategy.ma_slow
btp, bsl = best._strategy.take_profit, best._strategy.stop_loss
print(f'🏆 IS champion {bf}/{bs}  TP {btp}  SL {bsl}')

# ─── dense grid ──────────────────────────────────────────────
ma_fast_vals = range(max(2,bf-10), bf+11, 2)
ma_slow_vals = range(max(3,bs-10), bs+11, 2)
tp_vals = [round(btp+i/100,4) for i in (-.01,0,.01)]
sl_vals = [round(bsl+i/100,4) for i in (-.01,0,.01)]

bt_oos = Backtest(oos_df, MAReversalStrategy, cash=1_000_000, commission=.002)
rows = []

for f,s,tp,sl in product(ma_fast_vals, ma_slow_vals, tp_vals, sl_vals):
    if f >= s: continue
    stats_is  = bt_is.run(ma_fast=f,ma_slow=s,take_profit=tp,stop_loss=sl)
    stats_oos = bt_oos.run(ma_fast=f,ma_slow=s,take_profit=tp,stop_loss=sl)
    rows.append((f,s,tp,sl,
                 stats_is['Sharpe Ratio'],  stats_oos['Sharpe Ratio'],
                 stats_is['Sortino Ratio'], stats_oos['Sortino Ratio'],
                 stats_is['Calmar Ratio'],  stats_oos['Calmar Ratio']))

cols = ['fast','slow','tp','sl','sharpe_IS','sharpe_OOS',
        'sortino_IS','sortino_OOS','calmar_IS','calmar_OOS']
res = pd.DataFrame(rows, columns=cols)
csv_path = os.path.join(SAVE_DIR,'sma_plateau_metrics.csv')
res.to_csv(csv_path, index=False)
print(f'✅ metrics → {csv_path}')

# ─── heat-map helper ─────────────────────────────────────────
def plot_heat(metric, slice_, title_suffix):
    pivot = (res.groupby(['fast','slow'])[f'{metric}_{slice_}']
               .mean()
               .unstack())
    plt.figure(figsize=(10,7))
    im = plt.imshow(pivot, origin='lower', aspect='auto',
                    extent=[pivot.columns.min(),pivot.columns.max(),
                            pivot.index.min(), pivot.index.max()])
    plt.colorbar(im, label=metric)
    plt.xlabel('Slow MA'); plt.ylabel('Fast MA')
    plt.title(f'{metric} – {title_suffix}')
    path = os.path.join(SAVE_DIR, f'heat_{metric.lower()}_{slice_.lower()}.png')
    plt.tight_layout(); plt.savefig(path, dpi=150); plt.close()
    print(f'📊 {path} saved')

for m in ('sharpe','sortino','calmar'):
    for sl in ('IS','OOS'):
        plot_heat(m, sl, sl)

print('🎉 All heat-maps done → check your data/robust_tests folder')
