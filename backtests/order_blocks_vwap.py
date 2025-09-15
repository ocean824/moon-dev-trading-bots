"""
High Probability Order Blocks + VWAP Strategy
=============================================

Enhanced version of the Order Blocks strategy with VWAP price level filter.
Combines order block z-score signals with VWAP to improve entry timing and 
ensure trades align with institutional price levels.

VWAP Enhancement:
- Bullish signals only when price is above VWAP (uptrend bias)
- Bearish signals only when price is below VWAP (downtrend bias)
- Uses distance from VWAP as additional confluence factor
- Volume-weighted pricing provides institutional perspective

Moon Dev Trading Bot Framework
"""

import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
from backtesting.lib import crossover
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

# Import the multi-data tester framework
from multi_data_tester import test_on_all_data

print("🚀 High Probability Order Blocks + VWAP Strategy Loading... 📦📊")

class OrderBlocksVWAPStrategy(Strategy):
    # Order Blocks parameters
    lookback_period = 50        # Lookback period for z-score calculation
    zscore_threshold_bull = 4.0  # Z-score threshold for bullish signals
    zscore_threshold_bear = -4.0 # Z-score threshold for bearish signals
    box_expiration = 100        # Number of bars after which order block expires
    min_probability = 0.6      # Minimum survival probability to enter trade
    
    # VWAP parameters
    vwap_period = 20           # VWAP calculation period
    vwap_deviation_threshold = 0.005  # Minimum 0.5% deviation from VWAP for signal
    
    # Risk management
    take_profit = 0.025        # 2.5% take profit
    stop_loss = 0.015         # 1.5% stop loss
    
    def init(self):
        print("🎯 Initializing High Probability Order Blocks + VWAP Strategy")
        print(f"📊 Order Blocks: Lookback={self.lookback_period}, ZScore Bull={self.zscore_threshold_bull}, Bear={self.zscore_threshold_bear}")
        print(f"📈 VWAP: Period={self.vwap_period}, Deviation Threshold={self.vwap_deviation_threshold*100:.1f}%")
        
        # Calculate up and down distances
        self.up_distance = self.I(self.calculate_up_distance)
        self.down_distance = self.I(self.calculate_down_distance)
        
        # Calculate z-scores for distances
        self.zscore_up = self.I(self.calculate_zscore, self.up_distance)
        self.zscore_down = self.I(self.calculate_zscore, self.down_distance)
        
        # VWAP calculation
        self.vwap = self.I(self.calculate_vwap)
        
        # Order block tracking
        self.order_blocks = []  # List to store order blocks
        self.block_counter = 0
        
        print("✅ Order Blocks + VWAP indicators initialized")
    
    def calculate_up_distance(self):
        """Calculate the distance from current high to previous significant highs"""
        up_distances = []
        
        for i in range(len(self.data.High)):
            if i < self.lookback_period:
                up_distances.append(np.nan)
            else:
                current_high = self.data.High[i]
                # Find the highest high in the lookback period before current bar
                lookback_highs = self.data.High[max(0, i - self.lookback_period):i]
                if len(lookback_highs) > 0:
                    max_high = np.max(lookback_highs)
                    up_distance = current_high - max_high
                    up_distances.append(up_distance)
                else:
                    up_distances.append(np.nan)
        
        return np.array(up_distances)
    
    def calculate_down_distance(self):
        """Calculate the distance from current low to previous significant lows"""
        down_distances = []
        
        for i in range(len(self.data.Low)):
            if i < self.lookback_period:
                down_distances.append(np.nan)
            else:
                current_low = self.data.Low[i]
                # Find the lowest low in the lookback period before current bar
                lookback_lows = self.data.Low[max(0, i - self.lookback_period):i]
                if len(lookback_lows) > 0:
                    min_low = np.min(lookback_lows)
                    down_distance = min_low - current_low
                    down_distances.append(down_distance)
                else:
                    down_distances.append(np.nan)
        
        return np.array(down_distances)
    
    def calculate_zscore(self, distance_series):
        """Calculate rolling z-score for distance series"""
        zscores = []
        
        for i in range(len(distance_series)):
            if i < self.lookback_period:
                zscores.append(np.nan)
            else:
                # Get the data window for z-score calculation
                window_data = distance_series[max(0, i - self.lookback_period):i + 1]
                # Remove NaN values
                window_data = window_data[~np.isnan(window_data)]
                
                if len(window_data) > 10:  # Need sufficient data for z-score
                    current_value = distance_series[i]
                    if not np.isnan(current_value):
                        mean_val = np.mean(window_data[:-1])  # Exclude current value from mean
                        std_val = np.std(window_data[:-1])    # Exclude current value from std
                        
                        if std_val > 0:
                            zscore = (current_value - mean_val) / std_val
                            zscores.append(zscore)
                        else:
                            zscores.append(0)
                    else:
                        zscores.append(np.nan)
                else:
                    zscores.append(np.nan)
        
        return np.array(zscores)
    
    def calculate_vwap(self):
        """Calculate VWAP using rolling window approach"""
        # Get the typical price (HLC/3)
        typical_price = (self.data.High + self.data.Low + self.data.Close) / 3
        
        # Calculate volume-weighted typical price
        volume_price = typical_price * self.data.Volume
        
        # Calculate rolling VWAP
        vwap_values = []
        for i in range(len(self.data)):
            if i < self.vwap_period - 1:
                vwap_values.append(np.nan)
            else:
                start_idx = max(0, i - self.vwap_period + 1)
                end_idx = i + 1
                
                volume_sum = np.sum(self.data.Volume[start_idx:end_idx])
                volume_price_sum = np.sum(volume_price[start_idx:end_idx])
                
                if volume_sum > 0:
                    vwap_values.append(volume_price_sum / volume_sum)
                else:
                    vwap_values.append(np.nan)
        
        return np.array(vwap_values)
    
    def create_order_block(self, block_type, price_level, current_bar):
        """Create a new order block"""
        block = {
            'id': self.block_counter,
            'type': block_type,  # 'bullish' or 'bearish'
            'price': price_level,
            'creation_bar': current_bar,
            'expiration_bar': current_bar + self.box_expiration,
            'mitigated': False,
            'mitigation_bar': None,
            'success': None  # Will be set based on price movement after mitigation
        }
        
        self.order_blocks.append(block)
        self.block_counter += 1
        return block
    
    def update_order_blocks(self, current_bar, current_price_high, current_price_low):
        """Update order blocks for mitigation and expiration"""
        for block in self.order_blocks:
            if not block['mitigated'] and current_bar <= block['expiration_bar']:
                # Check for mitigation
                if block['type'] == 'bullish':
                    # Bullish block mitigated when price goes back below the level
                    if current_price_low <= block['price']:
                        block['mitigated'] = True
                        block['mitigation_bar'] = current_bar
                elif block['type'] == 'bearish':
                    # Bearish block mitigated when price goes back above the level
                    if current_price_high >= block['price']:
                        block['mitigated'] = True
                        block['mitigation_bar'] = current_bar
    
    def calculate_kaplan_meier_probability(self, block_type):
        """Calculate Kaplan-Meier survival probability for given block type"""
        # Get all historical blocks of the same type
        blocks = [b for b in self.order_blocks if b['type'] == block_type and b['mitigated']]
        
        if len(blocks) < 5:  # Need minimum data for meaningful probability
            return 0.5  # Default probability
        
        # Calculate survival times (bars until mitigation)
        survival_times = []
        
        for block in blocks:
            if block['mitigated']:
                survival_time = block['mitigation_bar'] - block['creation_bar']
                survival_times.append(survival_time)
            else:
                # Block expired without mitigation
                survival_time = block['expiration_bar'] - block['creation_bar']
                survival_times.append(survival_time)
        
        if len(survival_times) == 0:
            return 0.5
        
        # Simple survival probability calculation
        median_time = np.median(survival_times)
        successful_blocks = sum(1 for t in survival_times if t >= median_time)
        probability = successful_blocks / len(survival_times)
        
        return max(0.1, min(0.9, probability))  # Bound between 0.1 and 0.9
    
    def check_vwap_conditions(self, direction, current_price):
        """Check VWAP conditions for price level confirmation"""
        current_vwap = self.vwap[-1]
        
        # Skip if invalid VWAP
        if np.isnan(current_vwap):
            return False
        
        # Calculate price deviation from VWAP
        price_deviation = abs(current_price - current_vwap) / current_vwap
        
        # Must have meaningful deviation from VWAP
        if price_deviation < self.vwap_deviation_threshold:
            return False
        
        if direction == 'bullish':
            # For bullish trades: price should be above VWAP
            return current_price > current_vwap
        else:  # bearish
            # For bearish trades: price should be below VWAP
            return current_price < current_vwap
    
    def next(self):
        current_bar = len(self.data) - 1
        current_price = self.data.Close[-1]
        current_high = self.data.High[-1]
        current_low = self.data.Low[-1]
        
        # Skip if not enough data
        if current_bar < max(self.lookback_period * 2, self.vwap_period + 10):
            return
        
        # Get current z-scores
        current_zscore_up = self.zscore_up[-1]
        current_zscore_down = self.zscore_down[-1]
        previous_zscore_up = self.zscore_up[-2] if len(self.zscore_up) > 1 else 0
        previous_zscore_down = self.zscore_down[-2] if len(self.zscore_down) > 1 else 0
        
        # Skip if invalid z-scores
        if np.isnan(current_zscore_up) or np.isnan(current_zscore_down):
            return
        
        # Update existing order blocks
        self.update_order_blocks(current_bar, current_high, current_low)
        
        # Check for new order block signals
        bullish_signal = (previous_zscore_up <= self.zscore_threshold_bull and 
                         current_zscore_up > self.zscore_threshold_bull)
        bearish_signal = (previous_zscore_down >= self.zscore_threshold_bear and 
                         current_zscore_down < self.zscore_threshold_bear)
        
        # Create new order blocks
        if bullish_signal:
            block = self.create_order_block('bullish', current_low, current_bar)
            print(f"📈 Bullish Order Block created at {current_price:.2f} (Z-score: {current_zscore_up:.2f})")
        
        if bearish_signal:
            block = self.create_order_block('bearish', current_high, current_bar)
            print(f"📉 Bearish Order Block created at {current_price:.2f} (Z-score: {current_zscore_down:.2f})")
        
        # Trading logic - only trade if not already in position
        if not self.position:
            # Check for bullish trade setup with VWAP confirmation
            if bullish_signal and self.check_vwap_conditions('bullish', current_price):
                probability = self.calculate_kaplan_meier_probability('bullish')
                
                if probability >= self.min_probability:
                    stop_price = current_price * (1 - self.stop_loss)
                    target_price = current_price * (1 + self.take_profit)
                    
                    vwap_val = self.vwap[-1]
                    vwap_deviation = (current_price - vwap_val) / vwap_val * 100
                    
                    print(f"🚀 LONG Entry (VWAP Confirmed): Price=${current_price:.2f}, Prob={probability:.2f}")
                    print(f"   Stop=${stop_price:.2f}, Target=${target_price:.2f}")
                    print(f"   VWAP=${vwap_val:.2f}, Deviation=+{vwap_deviation:.2f}%")
                    
                    self.buy(sl=stop_price, tp=target_price)
            
            # Check for bearish trade setup with VWAP confirmation
            elif bearish_signal and self.check_vwap_conditions('bearish', current_price):
                probability = self.calculate_kaplan_meier_probability('bearish')
                
                if probability >= self.min_probability:
                    stop_price = current_price * (1 + self.stop_loss)
                    target_price = current_price * (1 - self.take_profit)
                    
                    vwap_val = self.vwap[-1]
                    vwap_deviation = (current_price - vwap_val) / vwap_val * 100
                    
                    print(f"🎯 SHORT Entry (VWAP Confirmed): Price=${current_price:.2f}, Prob={probability:.2f}")
                    print(f"   Stop=${stop_price:.2f}, Target=${target_price:.2f}")
                    print(f"   VWAP=${vwap_val:.2f}, Deviation={vwap_deviation:.2f}%")
                    
                    self.sell(sl=stop_price, tp=target_price)
        
        # Exit conditions: Close position if price crosses back to other side of VWAP
        elif self.position and not np.isnan(self.vwap[-1]):
            vwap_val = self.vwap[-1]
            
            if self.position.is_long and current_price < vwap_val:
                print(f"❌ Exiting LONG position: Price crossed below VWAP (${current_price:.2f} < ${vwap_val:.2f})")
                self.position.close()
            elif self.position.is_short and current_price > vwap_val:
                print(f"❌ Exiting SHORT position: Price crossed above VWAP (${current_price:.2f} > ${vwap_val:.2f})")
                self.position.close()

# Test the strategy using multi-data framework
if __name__ == "__main__":
    print("\n🎯 Testing High Probability Order Blocks + VWAP Strategy")
    print("=" * 80)
    
    # Test on all available data sources
    results = test_on_all_data(
        OrderBlocksVWAPStrategy, 
        'OrderBlocksVWAP',
        cash=100000,
        commission=0.002,
        verbose=True
    )
    
    if results is not None:
        print("\n📊 Strategy Summary:")
        print(f"✅ Tested on {len(results)} data sources")
        print(f"📈 Average Return: {results['Return_%'].mean():.2f}%")
        print(f"📊 Average Sharpe Ratio: {results['Sharpe'].mean():.3f}")
        print(f"📉 Average Max Drawdown: {results['Max_DD_%'].mean():.2f}%")
        print(f"🎯 Average Win Rate: {results['Win_Rate_%'].mean():.2f}%")
    
    print("\n🌙 High Probability Order Blocks + VWAP Strategy Testing Complete! 🚀")