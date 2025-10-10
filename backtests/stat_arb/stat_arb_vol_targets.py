"""
Statistical Arbitrage with VOLATILITY-ADJUSTED TARGETS
=======================================================

STRATEGY GOAL: Increase expectancy by scaling profit targets and stops
based on current volatility, capturing larger moves in volatile periods.

Key Improvements:
- ATR-based dynamic targets (larger profits in volatile markets)
- Volatility percentile ranking for context
- Tighter stops in calm markets, wider in volatile
- Volatility regime detection

Target: 4000+ trades with >0.04% expectancy

t/anaconda3/envs/tflow/bin/python /Users/md/Dropbox/dev/github/moon-dev-trading-bots/backtests/stat_arb/stat_arb_vol_targets.py
(tflow) md@mds-MacBook-Pro moon-dev-trading-bots % /opt/anaconda3/envs/tflow/bin/python /Users/md/Dropbox/dev/github/moon-dev-trading-bots/backtests/stat_arb/stat_arb_vol_targets.py
🚀 Moon Dev's STAT ARB + VOLATILITY TARGETS Strategy 🌙
======================================================================
📊 Loading BTC 1-minute data...
✅ Loaded 40,320 1-minute bars

======================================================================
RUNNING VOLATILITY TARGETS BACKTEST
======================================================================

📊 BASELINE RESULTS:
Base TP: 0.50%
Base SL: 0.20%
--------------------------------------------------
Start                     2025-08-26 15:41:00
End                       2025-09-23 15:40:00
Duration                     27 days 23:59:00
Exposure Time [%]                   68.687996
Equity Final [$]               1573024.495396
Equity Peak [$]                1573475.688736
Return [%]                           57.30245
Buy & Hold Return [%]                2.958633
Return (Ann.) [%]                 25589.07683
Volatility (Ann.) [%]             9147.582509
Sharpe Ratio                         2.797359
Sortino Ratio                     4779.799627
Calmar Ratio                     12198.104412
Max. Drawdown [%]                   -2.097791
Avg. Drawdown [%]                   -0.085838
Max. Drawdown Duration        4 days 02:53:00
Avg. Drawdown Duration        0 days 00:51:00
# Trades                                 1509
Win Rate [%]                        91.451292
Best Trade [%]                       0.885294
Worst Trade [%]                      -0.50051
Avg. Trade [%]                       0.031377
Max. Trade Duration           0 days 08:54:00
Avg. Trade Duration           0 days 00:18:00
Profit Factor                        2.310904
Expectancy [%]                       0.031461
SQN                                  8.982137
_strategy                 StatArbVolatilit...
_equity_curve                             ...
_trades                         Size  Entr...
dtype: object

======================================================================
OPTIMIZING FOR RETURN ON INVESTMENT
======================================================================
                                                                                                                                                                                                    
✨ OPTIMIZED RESULTS:
Start                     2025-08-26 15:41:00
End                       2025-09-23 15:40:00
Duration                     27 days 23:59:00
Exposure Time [%]                   79.518849
Equity Final [$]               2503702.358925
Equity Peak [$]                2505371.279145
Return [%]                         150.370236
Buy & Hold Return [%]                2.958633
Return (Ann.) [%]              8616917.444149
Volatility (Ann.) [%]          6029579.307543
Sharpe Ratio                         1.429108
Sortino Ratio                  1320976.517687
Calmar Ratio                   3000717.647369
Max. Drawdown [%]                   -2.871619
Avg. Drawdown [%]                   -0.073467
Max. Drawdown Duration        3 days 07:56:00
Avg. Drawdown Duration        0 days 00:28:00
# Trades                                 2186
Win Rate [%]                        91.765782
Best Trade [%]                       0.899541
Worst Trade [%]                     -0.402151
Avg. Trade [%]                       0.043538
Max. Trade Duration           0 days 07:26:00
Avg. Trade Duration           0 days 00:14:00
Profit Factor                        3.170075
Expectancy [%]                       0.043615
SQN                                 14.937113
_strategy                 StatArbVolatilit...
_equity_curve                             ...
_trades                         Size  Entr...
dtype: object

🎯 OPTIMIZED PARAMETERS:
Lookback Period: 5 bars
Z-Score Entry: 1.3
Base Take Profit: 0.50%
Base Stop Loss: 0.15%
ATR TP Multiplier: 1.5
ATR SL Multiplier: 0.8
(tflow) md@mds-MacBook-Pro moon-dev-trading-bots % 
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's STAT ARB + VOLATILITY TARGETS Strategy 🌙")
print("=" * 70)

# Load data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1m-4wks-data.csv'
print(f"📊 Loading BTC 1-minute data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Calculate indicators
def calculate_zscore(series, period):
    mean = series.rolling(period).mean()
    std = series.rolling(period).std()
    zscore = (series - mean) / std
    return zscore

# Z-scores
data['ZScore_5'] = calculate_zscore(data['Close'], 5)
data['ZScore_10'] = calculate_zscore(data['Close'], 10)

# ATR for volatility
high = data['High']
low = data['Low']
close = data['Close']
tr1 = high - low
tr2 = abs(high - close.shift())
tr3 = abs(low - close.shift())
tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
data['ATR'] = tr.rolling(14).mean()
data['ATR_Pct'] = data['ATR'] / close

# Volatility percentile
data['Vol_Percentile'] = data['ATR'].rolling(100).rank(pct=True) * 100

# Historical volatility
data['HV'] = close.pct_change().rolling(20).std()

# Bollinger Bands
data['BB_Middle'] = close.rolling(20).mean()
data['BB_Std'] = close.rolling(20).std()

print(f"✅ Loaded {len(data):,} 1-minute bars")


class StatArbVolatilityTargetsStrategy(Strategy):
    """
    Volatility-Adjusted Targets for Higher Expectancy

    Scales TP/SL based on current market volatility
    """

    # Parameters
    lookback_period = 6
    zscore_entry = 1.5
    zscore_exit = 0.3
    base_take_profit = 0.005  # Base 0.5%
    base_stop_loss = 0.002   # Base 0.2%
    atr_tp_multiplier = 2.0   # TP = ATR * this
    atr_sl_multiplier = 1.0   # SL = ATR * this
    vol_scale_factor = 1.5    # How much to scale by volatility

    def init(self):
        # Zones
        self.support = self.I(lambda: pd.Series(self.data.Close).rolling(
            window=self.lookback_period, min_periods=1).min())
        self.resistance = self.I(lambda: pd.Series(self.data.Close).rolling(
            window=self.lookback_period, min_periods=1).max())

        # Indicators
        self.zscore_5 = self.I(lambda: self.data.ZScore_5)
        self.zscore_10 = self.I(lambda: self.data.ZScore_10)
        self.atr = self.I(lambda: self.data.ATR)
        self.atr_pct = self.I(lambda: self.data.ATR_Pct)
        self.vol_percentile = self.I(lambda: self.data.Vol_Percentile)
        self.bb_middle = self.I(lambda: self.data.BB_Middle)
        self.bb_std = self.I(lambda: self.data.BB_Std)

    def calculate_dynamic_targets(self, current_price):
        """Calculate volatility-adjusted TP and SL"""
        current_atr = self.atr[-1] if self.atr[-1] else current_price * 0.001
        current_vol_pct = self.vol_percentile[-1] if self.vol_percentile[-1] else 50

        # Scale factor based on volatility percentile
        vol_scale = 0.5 + (current_vol_pct / 100) * self.vol_scale_factor  # 0.5x to 2x

        # ATR-based targets
        atr_tp = current_atr * self.atr_tp_multiplier
        atr_sl = current_atr * self.atr_sl_multiplier

        # Percentage-based targets scaled by volatility
        pct_tp = self.base_take_profit * vol_scale
        pct_sl = self.base_stop_loss * vol_scale

        # Use larger of ATR or percentage
        final_tp = max(atr_tp, current_price * pct_tp)
        final_sl = max(atr_sl, current_price * pct_sl)

        return final_tp, final_sl

    def next(self):
        # Skip if insufficient data
        if len(self.data) < 100:
            return

        # Get current values
        current_price = self.data.Close[-1]
        z5 = self.zscore_5[-1] if self.zscore_5[-1] and not np.isnan(self.zscore_5[-1]) else 0
        z10 = self.zscore_10[-1] if self.zscore_10[-1] and not np.isnan(self.zscore_10[-1]) else 0
        current_bb_middle = self.bb_middle[-1] if self.bb_middle[-1] and not np.isnan(self.bb_middle[-1]) else current_price

        # Get zones
        demand_zone = self.support[-1]
        supply_zone = self.resistance[-1]

        # Exit logic
        if self.position:
            # Adaptive exit based on volatility
            current_vol_pct = self.vol_percentile[-1] if self.vol_percentile[-1] else 50
            exit_threshold = self.zscore_exit * (1 + current_vol_pct / 100)  # Wider exit in high vol

            if self.position.is_long:
                if z5 > -exit_threshold and self.position.pl_pct > 0:
                    self.position.close()
                    return
            else:
                if z5 < exit_threshold and self.position.pl_pct > 0:
                    self.position.close()
                    return

        # Entry logic
        if not self.position:
            near_demand = abs(current_price - demand_zone) / demand_zone <= 0.005
            near_supply = abs(current_price - supply_zone) / supply_zone <= 0.005

            # Calculate dynamic targets
            tp_amount, sl_amount = self.calculate_dynamic_targets(current_price)

            # BUY signal
            if z5 < -self.zscore_entry and z10 < -self.zscore_entry * 0.8 and near_demand:
                sl_price = current_price - sl_amount
                tp_price = current_price + tp_amount

                # Ensure minimum profit
                if tp_price <= current_price * 1.002:
                    tp_price = current_price * 1.005

                self.buy(sl=sl_price, tp=tp_price)

            # SELL signal
            elif z5 > self.zscore_entry and z10 > self.zscore_entry * 0.8 and near_supply:
                sl_price = current_price + sl_amount
                tp_price = current_price - tp_amount

                # Ensure minimum profit
                if tp_price >= current_price * 0.998:
                    tp_price = current_price * 0.995

                self.sell(sl=sl_price, tp=tp_price)


# Run backtest
print("\n" + "="*70)
print("RUNNING VOLATILITY TARGETS BACKTEST")
print("="*70)

bt = Backtest(
    data,
    StatArbVolatilityTargetsStrategy,
    cash=1000000,
    commission=0.001,
    exclusive_orders=True
)

# Run baseline
baseline_stats = bt.run()

print(f"\n📊 BASELINE RESULTS:")
print(f"Base TP: {StatArbVolatilityTargetsStrategy.base_take_profit*100:.2f}%")
print(f"Base SL: {StatArbVolatilityTargetsStrategy.base_stop_loss*100:.2f}%")
print("-" * 50)
print(baseline_stats)

# Optimization
print("\n" + "="*70)
print("OPTIMIZING FOR RETURN ON INVESTMENT")
print("="*70)

try:
    optimization_results = bt.optimize(
        lookback_period=[5, 6, 7],
        zscore_entry=[1.3, 1.5, 1.7],
        base_take_profit=[0.004, 0.005, 0.006],
        base_stop_loss=[0.0015, 0.002, 0.0025],
        atr_tp_multiplier=[1.5, 2.0, 2.5],
        atr_sl_multiplier=[0.8, 1.0, 1.2],
        maximize='Return [%]',
        return_heatmap=False
    )

    print(f"\n✨ OPTIMIZED RESULTS:")
    print(optimization_results)
    print(f"\n🎯 OPTIMIZED PARAMETERS:")
    print(f"Lookback Period: {optimization_results._strategy.lookback_period} bars")
    print(f"Z-Score Entry: {optimization_results._strategy.zscore_entry}")
    print(f"Base Take Profit: {optimization_results._strategy.base_take_profit*100:.2f}%")
    print(f"Base Stop Loss: {optimization_results._strategy.base_stop_loss*100:.2f}%")
    print(f"ATR TP Multiplier: {optimization_results._strategy.atr_tp_multiplier}")
    print(f"ATR SL Multiplier: {optimization_results._strategy.atr_sl_multiplier}")

except Exception as e:
    print(f"Optimization failed: {str(e)}")

bt.plot()