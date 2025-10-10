"""
Statistical Arbitrage with TIME-OF-DAY OPTIMIZATION
====================================================

STRATEGY GOAL: Increase expectancy by trading only during historically
profitable time periods, avoiding low-probability hours.

Key Improvements:
- Analyze historical performance by hour/minute
- Filter trades based on time-of-day edge
- Adjust parameters for different market sessions
- Avoid known low-liquidity periods

Target: 4000+ trades with >0.05% expectancy

n /Users/md/Dropbox/dev/github/moon-dev-trading-bots/backtests/stat_arb/stat_arb_time_of_day.py
md@mds-MacBook-Pro moon-dev-trading-bots % conda activate tflow
(tflow) md@mds-MacBook-Pro moon-dev-trading-bots % /opt/anaconda3/envs/tflow/bin/python /Users/md/Dropbox/dev/github/moon-dev-trading-bots/backtests/stat_arb/stat_arb_time_of_day.py
🚀 Moon Dev's STAT ARB + TIME-OF-DAY Strategy 🌙
======================================================================
📊 Loading BTC 1-minute data...
✅ Loaded 40,320 1-minute bars

======================================================================
RUNNING TIME-OF-DAY BACKTEST
======================================================================

📊 BASELINE RESULTS:
Take Profit: 0.70%
Stop Loss: 0.20%
--------------------------------------------------
Start                     2025-08-26 15:41:00
End                       2025-09-23 15:40:00
Duration                     27 days 23:59:00
Exposure Time [%]                   35.084325
Equity Final [$]                2137126.07975
Equity Peak [$]                 2138491.55993
Return [%]                         113.712608
Buy & Hold Return [%]                2.958633
Return (Ann.) [%]               925163.208938
Volatility (Ann.) [%]           524213.036321
Sharpe Ratio                         1.764861
Sortino Ratio                   385687.357296
Calmar Ratio                    645662.363319
Max. Drawdown [%]                    -1.43289
Avg. Drawdown [%]                   -0.071957
Max. Drawdown Duration        3 days 22:30:00
Avg. Drawdown Duration        0 days 00:36:00
# Trades                                 1235
Win Rate [%]                        92.793522
Best Trade [%]                       0.777367
Worst Trade [%]                     -0.310139
Avg. Trade [%]                       0.064115
Max. Trade Duration           0 days 03:28:00
Avg. Trade Duration           0 days 00:11:00
Profit Factor                        4.419035
Expectancy [%]                       0.064214
SQN                                 14.959242
_strategy                 StatArbTimeOfDay...
_equity_curve                             ...
_trades                         Size  Entr...
dtype: object

======================================================================
OPTIMIZING FOR RETURN ON INVESTMENT
======================================================================
     ======================================================================
OPTIMIZING FOR RETURN ON INVESTMENT
======================================================================
                                                                                
✨ OPTIMIZED RESULTS:
Start                     2025-08-26 15:41:00
End                       2025-09-23 15:40:00
Duration                     27 days 23:59:00
Exposure Time [%]                    45.46627
Equity Final [$]                2531505.70291
Equity Peak [$]                 2533174.62313
Return [%]                          153.15057
Buy & Hold Return [%]                2.958633
Return (Ann.) [%]              8344691.694676
Volatility (Ann.) [%]          6236565.812308
Sharpe Ratio                         1.338027
Sortino Ratio                  8084027.308192
Calmar Ratio                   5516178.385915
Max. Drawdown [%]                   -1.512767
Avg. Drawdown [%]                   -0.076353
Max. Drawdown Duration        2 days 21:05:00
Avg. Drawdown Duration        0 days 00:32:00
# Trades                                 1637
Win Rate [%]                        91.264508
Best Trade [%]                       0.890203
Worst Trade [%]                     -0.260194
Avg. Trade [%]                         0.0588
Max. Trade Duration           0 days 02:07:00
Avg. Trade Duration           0 days 00:11:00
Profit Factor                        3.869726
Expectancy [%]                       0.058896
SQN                                 15.468598
_strategy                 StatArbTimeOfDay...
_equity_curve                             ...
_trades                         Size  Entr...
dtype: object

🎯 OPTIMIZED PARAMETERS:
Lookback Period: 5 bars
Z-Score Entry: 1.3
Take Profit: 0.80%
Stop Loss: 0.15%
Min Volume Rank: 0.30

"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's STAT ARB + TIME-OF-DAY Strategy 🌙")
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

# Time features
data['Hour'] = data.index.hour
data['Minute'] = data.index.minute
data['DayOfWeek'] = data.index.dayofweek

# Session flags (UTC times)
data['AsianSession'] = ((data['Hour'] >= 0) & (data['Hour'] < 8)).astype(int)
data['EuropeanSession'] = ((data['Hour'] >= 7) & (data['Hour'] < 16)).astype(int)
data['USSession'] = ((data['Hour'] >= 13) & (data['Hour'] < 22)).astype(int)
data['Weekend'] = (data['DayOfWeek'] >= 5).astype(int)

# Volatility by hour (historical)
data['HourlyVolatility'] = data.groupby('Hour')['Close'].transform(
    lambda x: x.pct_change().std()
)

# Volume profile by hour
data['HourlyVolumeRank'] = data.groupby('Hour')['Volume'].transform(
    lambda x: x.rank(pct=True)
)

# Bollinger Bands
data['BB_Middle'] = data['Close'].rolling(20).mean()
data['BB_Std'] = data['Close'].rolling(20).std()

print(f"✅ Loaded {len(data):,} 1-minute bars")


class StatArbTimeOfDayStrategy(Strategy):
    """
    Time-of-Day Optimized Statistical Arbitrage
    
    Only trades during statistically favorable time periods
    """
    
    # Parameters
    lookback_period = 6
    zscore_entry = 1.5
    zscore_exit = 0.3
    
    # Time filters
    trade_asian = True
    trade_european = True
    trade_us = True
    avoid_weekends = True
    avoid_low_volume_hours = True
    min_hourly_volume_rank = 0.3
    
    # Session-specific parameters
    asian_zscore_mult = 1.2  # More conservative in Asian session
    us_zscore_mult = 0.8     # More aggressive in US session
    
    take_profit = 0.007  # Higher TP for better expectancy
    stop_loss = 0.002
    
    def init(self):
        # Zones
        self.support = self.I(lambda: pd.Series(self.data.Close).rolling(
            window=self.lookback_period, min_periods=1).min())
        self.resistance = self.I(lambda: pd.Series(self.data.Close).rolling(
            window=self.lookback_period, min_periods=1).max())
        
        # Indicators
        self.zscore_5 = self.I(lambda: self.data.ZScore_5)
        self.zscore_10 = self.I(lambda: self.data.ZScore_10)
        self.hour = self.I(lambda: self.data.Hour)
        self.day_of_week = self.I(lambda: self.data.DayOfWeek)
        self.asian_session = self.I(lambda: self.data.AsianSession)
        self.european_session = self.I(lambda: self.data.EuropeanSession)
        self.us_session = self.I(lambda: self.data.USSession)
        self.hourly_volume_rank = self.I(lambda: self.data.HourlyVolumeRank)
        self.bb_middle = self.I(lambda: self.data.BB_Middle)
        
        # Define good/bad trading hours based on historical performance
        # These are typically the most liquid hours
        self.good_hours = [14, 15, 16, 17, 18, 19, 20]  # US market hours
        self.bad_hours = [3, 4, 5]  # Low liquidity Asian hours
        
    def should_trade_now(self):
        """Check if current time is favorable for trading"""
        current_hour = self.hour[-1]
        current_dow = self.day_of_week[-1]
        current_vol_rank = self.hourly_volume_rank[-1] if self.hourly_volume_rank[-1] else 0.5
        
        # Weekend filter
        if self.avoid_weekends and current_dow >= 5:
            return False
            
        # Bad hours filter
        if current_hour in self.bad_hours:
            return False
            
        # Low volume filter
        if self.avoid_low_volume_hours and current_vol_rank < self.min_hourly_volume_rank:
            return False
            
        # Session filters
        if not self.trade_asian and self.asian_session[-1] == 1:
            return False
        if not self.trade_european and self.european_session[-1] == 1:
            return False
        if not self.trade_us and self.us_session[-1] == 1:
            return False
            
        return True
    
    def get_session_multiplier(self):
        """Get z-score multiplier based on current session"""
        if self.asian_session[-1] == 1:
            return self.asian_zscore_mult
        elif self.us_session[-1] == 1:
            return self.us_zscore_mult
        return 1.0
    
    def next(self):
        # Skip if insufficient data
        if len(self.data) < 50:
            return
        
        # Check if we should trade at this time
        if not self.should_trade_now():
            # Still check exits even if we don't enter new trades
            if self.position:
                current_price = self.data.Close[-1]
                z5 = self.zscore_5[-1] if self.zscore_5[-1] and not np.isnan(self.zscore_5[-1]) else 0
                
                if self.position.is_long:
                    if z5 > -self.zscore_exit and self.position.pl_pct > 0:
                        self.position.close()
                else:
                    if z5 < self.zscore_exit and self.position.pl_pct > 0:
                        self.position.close()
            return
        
        # Get current values
        current_price = self.data.Close[-1]
        z5 = self.zscore_5[-1] if self.zscore_5[-1] and not np.isnan(self.zscore_5[-1]) else 0
        z10 = self.zscore_10[-1] if self.zscore_10[-1] and not np.isnan(self.zscore_10[-1]) else 0
        current_bb_middle = self.bb_middle[-1] if self.bb_middle[-1] and not np.isnan(self.bb_middle[-1]) else current_price
        
        # Get session multiplier
        session_mult = self.get_session_multiplier()
        adjusted_zscore_entry = self.zscore_entry * session_mult
        
        # Get zones
        demand_zone = self.support[-1]
        supply_zone = self.resistance[-1]
        
        # Exit logic
        if self.position:
            if self.position.is_long:
                if z5 > -self.zscore_exit and self.position.pl_pct > 0:
                    self.position.close()
                    return
            else:
                if z5 < self.zscore_exit and self.position.pl_pct > 0:
                    self.position.close()
                    return
        
        # Entry logic
        if not self.position:
            near_demand = abs(current_price - demand_zone) / demand_zone <= 0.005
            near_supply = abs(current_price - supply_zone) / supply_zone <= 0.005
            
            # Extra boost during good hours
            hour_boost = 0.8 if self.hour[-1] in self.good_hours else 1.0
            
            # BUY signal
            if z5 < -adjusted_zscore_entry * hour_boost and z10 < -adjusted_zscore_entry * hour_boost * 0.8 and near_demand:
                sl_price = current_price * (1 - self.stop_loss)
                tp_price = max(current_bb_middle, current_price * (1 + self.take_profit))
                if tp_price <= current_price * 1.002:
                    tp_price = current_price * (1 + self.take_profit)
                
                self.buy(sl=sl_price, tp=tp_price)
            
            # SELL signal
            elif z5 > adjusted_zscore_entry * hour_boost and z10 > adjusted_zscore_entry * hour_boost * 0.8 and near_supply:
                sl_price = current_price * (1 + self.stop_loss)
                tp_price = min(current_bb_middle, current_price * (1 - self.take_profit))
                if tp_price >= current_price * 0.998:
                    tp_price = current_price * (1 - self.take_profit)
                
                self.sell(sl=sl_price, tp=tp_price)


# Run backtest
print("\n" + "="*70)
print("RUNNING TIME-OF-DAY BACKTEST")
print("="*70)

bt = Backtest(
    data,
    StatArbTimeOfDayStrategy,
    cash=1000000,
    commission=0.001,
    exclusive_orders=True
)

# Run baseline
baseline_stats = bt.run()

print(f"\n📊 BASELINE RESULTS:")
print(f"Take Profit: {StatArbTimeOfDayStrategy.take_profit*100:.2f}%")
print(f"Stop Loss: {StatArbTimeOfDayStrategy.stop_loss*100:.2f}%")
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
        take_profit=[0.006, 0.007, 0.008],
        stop_loss=[0.0015, 0.002, 0.0025],
        min_hourly_volume_rank=[0.2, 0.3, 0.4],
        maximize='Return [%]',
        return_heatmap=False
    )

    print(f"\n✨ OPTIMIZED RESULTS:")
    print(optimization_results)
    print(f"\n🎯 OPTIMIZED PARAMETERS:")
    print(f"Lookback Period: {optimization_results._strategy.lookback_period} bars")
    print(f"Z-Score Entry: {optimization_results._strategy.zscore_entry}")
    print(f"Take Profit: {optimization_results._strategy.take_profit*100:.2f}%")
    print(f"Stop Loss: {optimization_results._strategy.stop_loss*100:.2f}%")
    print(f"Min Volume Rank: {optimization_results._strategy.min_hourly_volume_rank:.2f}")
    
except Exception as e:
    print(f"Optimization failed: {str(e)}")

bt.plot()