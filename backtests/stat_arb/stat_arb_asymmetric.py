"""
Statistical Arbitrage with ASYMMETRIC RISK-REWARD
==================================================

STRATEGY GOAL: Increase expectancy by using asymmetric risk-reward ratios,
taking many small losses for fewer large wins.

Key Improvements:
- 3:1 or 4:1 reward-to-risk ratios
- Tighter entry criteria for high-probability setups
- Trail stops to capture larger moves
- Cut losses quickly, let winners run

Target: 4000+ trades with >0.06% expectancy
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's STAT ARB + ASYMMETRIC R:R Strategy 🌙")
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
data['ZScore_20'] = calculate_zscore(data['Close'], 20)

# RSI for confirmation
data['RSI'] = ta.rsi(data['Close'], length=14)

# ATR for dynamic stops
high = data['High']
low = data['Low']
close = data['Close']
tr1 = high - low
tr2 = abs(high - close.shift())
tr3 = abs(low - close.shift())
tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
data['ATR'] = tr.rolling(14).mean()

# Momentum
data['Momentum'] = data['Close'].pct_change(5)

# Bollinger Bands
data['BB_Middle'] = data['Close'].rolling(20).mean()
data['BB_Std'] = data['Close'].rolling(20).std()
data['BB_Upper'] = data['BB_Middle'] + (data['BB_Std'] * 2)
data['BB_Lower'] = data['BB_Middle'] - (data['BB_Std'] * 2)

# Quality score for entries
data['Entry_Quality'] = 0
# Oversold with momentum turning
data.loc[(data['ZScore_10'] < -1.5) & (data['Momentum'] > data['Momentum'].shift(1)), 'Entry_Quality'] += 1
# RSI oversold
data.loc[data['RSI'] < 30, 'Entry_Quality'] += 1
# Near BB lower
data.loc[data['Close'] < data['BB_Lower'], 'Entry_Quality'] += 1
# Volume spike
data['Volume_MA'] = data['Volume'].rolling(20).mean()
data.loc[data['Volume'] > data['Volume_MA'] * 1.5, 'Entry_Quality'] += 1

print(f"✅ Loaded {len(data):,} 1-minute bars")


class StatArbAsymmetricStrategy(Strategy):
    """
    Asymmetric Risk-Reward Statistical Arbitrage
    
    Takes many small losses for fewer large wins
    """
    
    # Parameters
    lookback_period = 6
    zscore_entry = 1.8  # Stricter entry for quality
    zscore_exit = 0.0   # Let winners run
    risk_reward_ratio = 3.5  # Target 3.5:1 reward
    min_entry_quality = 2  # Need at least 2 quality factors
    
    # Risk management
    base_stop_loss = 0.0015  # Tight stop: 0.15%
    take_profit_multiplier = 3.5  # TP = SL * this
    use_atr_stops = True
    atr_stop_multiplier = 1.0
    
    # Trailing logic
    trail_after_profit = 0.003  # Start trailing after 0.3%
    trail_percentage = 0.5  # Trail at 50% of max profit
    
    def init(self):
        # Zones
        self.support = self.I(lambda: pd.Series(self.data.Close).rolling(
            window=self.lookback_period, min_periods=1).min())
        self.resistance = self.I(lambda: pd.Series(self.data.Close).rolling(
            window=self.lookback_period, min_periods=1).max())
        
        # Indicators
        self.zscore_5 = self.I(lambda: self.data.ZScore_5)
        self.zscore_10 = self.I(lambda: self.data.ZScore_10)
        self.zscore_20 = self.I(lambda: self.data.ZScore_20)
        self.rsi = self.I(lambda: self.data.RSI)
        self.atr = self.I(lambda: self.data.ATR)
        self.momentum = self.I(lambda: self.data.Momentum)
        self.bb_upper = self.I(lambda: self.data.BB_Upper)
        self.bb_lower = self.I(lambda: self.data.BB_Lower)
        self.bb_middle = self.I(lambda: self.data.BB_Middle)
        self.entry_quality = self.I(lambda: self.data.Entry_Quality)
        
        # Track max profit for trailing
        self.max_profit = 0
        self.entry_price = 0
        
    def calculate_dynamic_stops(self, current_price, is_long):
        """Calculate stops with asymmetric R:R"""
        current_atr = self.atr[-1] if self.atr[-1] else current_price * 0.001

        if self.use_atr_stops:
            stop_distance = current_atr * self.atr_stop_multiplier
        else:
            stop_distance = current_price * self.base_stop_loss

        # Ensure minimum stop distance
        stop_distance = max(stop_distance, current_price * 0.001)

        # Asymmetric targets
        tp_distance = stop_distance * self.take_profit_multiplier

        # Ensure minimum TP distance
        tp_distance = max(tp_distance, current_price * 0.003)

        if is_long:
            sl_price = current_price - stop_distance
            tp_price = current_price + tp_distance
        else:
            sl_price = current_price + stop_distance
            tp_price = current_price - tp_distance

        return sl_price, tp_price
    
    def next(self):
        # Skip if insufficient data
        if len(self.data) < 50:
            return
        
        # Get current values
        current_price = self.data.Close[-1]
        z5 = self.zscore_5[-1] if self.zscore_5[-1] and not np.isnan(self.zscore_5[-1]) else 0
        z10 = self.zscore_10[-1] if self.zscore_10[-1] and not np.isnan(self.zscore_10[-1]) else 0
        z20 = self.zscore_20[-1] if self.zscore_20[-1] and not np.isnan(self.zscore_20[-1]) else 0
        current_rsi = self.rsi[-1] if self.rsi[-1] else 50
        current_quality = self.entry_quality[-1] if self.entry_quality[-1] else 0
        current_momentum = self.momentum[-1] if self.momentum[-1] else 0
        
        # Get zones
        demand_zone = self.support[-1]
        supply_zone = self.resistance[-1]
        
        # Exit logic with trailing
        if self.position:
            current_profit = self.position.pl_pct
            
            # Update max profit
            if current_profit > self.max_profit:
                self.max_profit = current_profit
            
            # Trailing stop logic
            if self.max_profit > self.trail_after_profit:
                trail_threshold = self.max_profit * self.trail_percentage
                if current_profit < trail_threshold:
                    self.position.close()
                    self.max_profit = 0
                    return
            
            # Normal exit - let winners run
            if self.position.is_long:
                # Exit if strongly overbought or momentum reverses
                if z5 > 2 or current_momentum < -0.002:
                    self.position.close()
                    self.max_profit = 0
                    return
            else:
                # Exit if strongly oversold or momentum reverses
                if z5 < -2 or current_momentum > 0.002:
                    self.position.close()
                    self.max_profit = 0
                    return
        
        # Entry logic - high quality only
        if not self.position:
            near_demand = abs(current_price - demand_zone) / demand_zone <= 0.005
            near_supply = abs(current_price - supply_zone) / supply_zone <= 0.005
            
            # Only enter on high-quality setups
            if current_quality < self.min_entry_quality:
                return
            
            # BUY signal - strict criteria
            if (z10 < -self.zscore_entry and 
                z5 < -self.zscore_entry * 0.8 and
                current_rsi < 35 and
                near_demand and
                current_price < self.bb_lower[-1]):
                
                sl_price, tp_price = self.calculate_dynamic_stops(current_price, True)

                # Ensure minimum R:R ratio
                risk_amount = current_price - sl_price
                min_reward = risk_amount * self.risk_reward_ratio
                tp_price = current_price + max(min_reward, tp_price - current_price)

                # Final safety check
                if tp_price <= current_price * 1.001:
                    tp_price = current_price * 1.005

                self.buy(sl=sl_price, tp=tp_price)
                self.entry_price = current_price
                self.max_profit = 0
            
            # SELL signal - strict criteria
            elif (z10 > self.zscore_entry and
                  z5 > self.zscore_entry * 0.8 and
                  current_rsi > 65 and
                  near_supply and
                  current_price > self.bb_upper[-1]):
                
                sl_price, tp_price = self.calculate_dynamic_stops(current_price, False)

                # Ensure minimum R:R ratio
                risk_amount = sl_price - current_price
                min_reward = risk_amount * self.risk_reward_ratio
                tp_price = current_price - max(min_reward, current_price - tp_price)

                # Final safety check
                if tp_price >= current_price * 0.999:
                    tp_price = current_price * 0.995

                self.sell(sl=sl_price, tp=tp_price)
                self.entry_price = current_price
                self.max_profit = 0


# Run backtest
print("\n" + "="*70)
print("RUNNING ASYMMETRIC R:R BACKTEST")
print("="*70)

bt = Backtest(
    data,
    StatArbAsymmetricStrategy,
    cash=1000000,
    commission=0.001,
    exclusive_orders=True
)

# Run baseline
baseline_stats = bt.run()

print(f"\n📊 BASELINE RESULTS:")
print(f"Risk:Reward Ratio: 1:{StatArbAsymmetricStrategy.risk_reward_ratio}")
print(f"Base Stop Loss: {StatArbAsymmetricStrategy.base_stop_loss*100:.2f}%")
print(f"Min Entry Quality: {StatArbAsymmetricStrategy.min_entry_quality}")
print("-" * 50)
print(baseline_stats)

# Optimization
print("\n" + "="*70)
print("OPTIMIZING FOR RETURN ON INVESTMENT")
print("="*70)

try:
    optimization_results = bt.optimize(
        lookback_period=[5, 6, 7],
        zscore_entry=[1.5, 1.8, 2.0],
        risk_reward_ratio=[3.0, 3.5, 4.0],
        base_stop_loss=[0.001, 0.0015, 0.002],
        min_entry_quality=[1, 2, 3],
        maximize='Return [%]',
        return_heatmap=False
    )

    print(f"\n✨ OPTIMIZED RESULTS:")
    print(optimization_results)
    print(f"\n🎯 OPTIMIZED PARAMETERS:")
    print(f"Lookback Period: {optimization_results._strategy.lookback_period} bars")
    print(f"Z-Score Entry: {optimization_results._strategy.zscore_entry}")
    print(f"Risk:Reward Ratio: 1:{optimization_results._strategy.risk_reward_ratio}")
    print(f"Base Stop Loss: {optimization_results._strategy.base_stop_loss*100:.2f}%")
    print(f"Min Entry Quality: {optimization_results._strategy.min_entry_quality}")
    
except Exception as e:
    print(f"Optimization failed: {str(e)}")

bt.plot()