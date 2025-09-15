"""
High Probability Order Blocks + MFI Strategy
============================================

Enhanced version of the Order Blocks strategy with MFI (Money Flow Index) filter.
Combines order block z-score signals with MFI to ensure trades align with 
volume-weighted price momentum and avoid false signals during low conviction moves.

MFI Enhancement:
- Bullish signals confirmed when MFI shows oversold conditions (< 30)
- Bearish signals confirmed when MFI shows overbought conditions (> 70)
- MFI divergence detection for additional confluence
- Volume-price relationship validation

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

print("🚀 High Probability Order Blocks + MFI Strategy Loading... 📦💰")

class OrderBlocksMFIStrategy(Strategy):
    # Order Blocks parameters
    lookback_period = 50        # Lookback period for z-score calculation
    zscore_threshold_bull = 4.0  # Z-score threshold for bullish signals
    zscore_threshold_bear = -4.0 # Z-score threshold for bearish signals
    box_expiration = 100        # Number of bars after which order block expires
    min_probability = 0.6      # Minimum survival probability to enter trade
    
    # MFI parameters
    mfi_period = 14            # MFI calculation period
    mfi_oversold = 30          # MFI oversold threshold
    mfi_overbought = 70        # MFI overbought threshold
    mfi_extreme_oversold = 20   # Extreme oversold for stronger signals
    mfi_extreme_overbought = 80 # Extreme overbought for stronger signals
    
    # Risk management
    take_profit = 0.025        # 2.5% take profit
    stop_loss = 0.015         # 1.5% stop loss
    
    def init(self):
        print("🎯 Initializing High Probability Order Blocks + MFI Strategy")
        print(f"📊 Order Blocks: Lookback={self.lookback_period}, ZScore Bull={self.zscore_threshold_bull}, Bear={self.zscore_threshold_bear}")
        print(f"💰 MFI: Period={self.mfi_period}, Oversold={self.mfi_oversold}, Overbought={self.mfi_overbought}")
        
        # Calculate up and down distances
        self.up_distance = self.I(self.calculate_up_distance)
        self.down_distance = self.I(self.calculate_down_distance)
        
        # Calculate z-scores for distances
        self.zscore_up = self.I(self.calculate_zscore, self.up_distance)
        self.zscore_down = self.I(self.calculate_zscore, self.down_distance)
        
        # MFI calculation
        self.mfi = self.I(talib.MFI, 
                          self.data.High, 
                          self.data.Low, 
                          self.data.Close, 
                          self.data.Volume, 
                          timeperiod=self.mfi_period)
        
        # Additional volume indicators for confirmation
        self.volume_sma = self.I(talib.SMA, self.data.Volume, timeperiod=20)
        
        # Order block tracking
        self.order_blocks = []  # List to store order blocks
        self.block_counter = 0
        
        print("✅ Order Blocks + MFI indicators initialized")
    
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
    
    def check_mfi_conditions(self, direction):
        """Check MFI conditions for money flow confirmation"""
        current_mfi = self.mfi[-1]
        previous_mfi = self.mfi[-2] if len(self.mfi) > 1 else current_mfi
        current_volume = self.data.Volume[-1]
        avg_volume = self.volume_sma[-1]
        
        # Skip if invalid MFI
        if np.isnan(current_mfi) or np.isnan(avg_volume):
            return False, 0
        
        # Volume confirmation - prefer above average volume
        volume_confirmation = current_volume > avg_volume
        
        signal_strength = 0
        
        if direction == 'bullish':
            # For bullish trades: MFI should indicate oversold conditions
            # and potentially starting to recover
            if current_mfi <= self.mfi_extreme_oversold:
                signal_strength = 3  # Strong signal
            elif current_mfi <= self.mfi_oversold:
                signal_strength = 2  # Medium signal
            elif current_mfi < 50 and current_mfi > previous_mfi:
                signal_strength = 1  # Weak signal (recovering from oversold)
            
            # Additional confirmation: MFI turning up from oversold
            mfi_turning_up = (current_mfi > previous_mfi and 
                            previous_mfi <= self.mfi_oversold)
            
            if mfi_turning_up:
                signal_strength += 1
                
        else:  # bearish
            # For bearish trades: MFI should indicate overbought conditions
            # and potentially starting to decline
            if current_mfi >= self.mfi_extreme_overbought:
                signal_strength = 3  # Strong signal
            elif current_mfi >= self.mfi_overbought:
                signal_strength = 2  # Medium signal
            elif current_mfi > 50 and current_mfi < previous_mfi:
                signal_strength = 1  # Weak signal (declining from overbought)
            
            # Additional confirmation: MFI turning down from overbought
            mfi_turning_down = (current_mfi < previous_mfi and 
                              previous_mfi >= self.mfi_overbought)
            
            if mfi_turning_down:
                signal_strength += 1
        
        # Require minimum signal strength
        is_confirmed = signal_strength >= 2 and volume_confirmation
        
        return is_confirmed, signal_strength
    
    def next(self):
        current_bar = len(self.data) - 1
        current_price = self.data.Close[-1]
        current_high = self.data.High[-1]
        current_low = self.data.Low[-1]
        
        # Skip if not enough data
        if current_bar < max(self.lookback_period * 2, self.mfi_period + 10):
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
            # Check for bullish trade setup with MFI confirmation
            if bullish_signal:
                mfi_confirmed, mfi_strength = self.check_mfi_conditions('bullish')
                
                if mfi_confirmed:
                    probability = self.calculate_kaplan_meier_probability('bullish')
                    
                    if probability >= self.min_probability:
                        stop_price = current_price * (1 - self.stop_loss)
                        target_price = current_price * (1 + self.take_profit)
                        
                        mfi_val = self.mfi[-1]
                        volume_ratio = self.data.Volume[-1] / self.volume_sma[-1]
                        
                        print(f"🚀 LONG Entry (MFI Confirmed): Price=${current_price:.2f}, Prob={probability:.2f}")
                        print(f"   Stop=${stop_price:.2f}, Target=${target_price:.2f}")
                        print(f"   MFI={mfi_val:.1f}, Strength={mfi_strength}, Vol Ratio={volume_ratio:.1f}x")
                        
                        self.buy(sl=stop_price, tp=target_price)
            
            # Check for bearish trade setup with MFI confirmation
            elif bearish_signal:
                mfi_confirmed, mfi_strength = self.check_mfi_conditions('bearish')
                
                if mfi_confirmed:
                    probability = self.calculate_kaplan_meier_probability('bearish')
                    
                    if probability >= self.min_probability:
                        stop_price = current_price * (1 + self.stop_loss)
                        target_price = current_price * (1 - self.take_profit)
                        
                        mfi_val = self.mfi[-1]
                        volume_ratio = self.data.Volume[-1] / self.volume_sma[-1]
                        
                        print(f"🎯 SHORT Entry (MFI Confirmed): Price=${current_price:.2f}, Prob={probability:.2f}")
                        print(f"   Stop=${stop_price:.2f}, Target=${target_price:.2f}")
                        print(f"   MFI={mfi_val:.1f}, Strength={mfi_strength}, Vol Ratio={volume_ratio:.1f}x")
                        
                        self.sell(sl=stop_price, tp=target_price)
        
        # Exit conditions: Close position if MFI shows extreme reversal signals
        elif self.position and not np.isnan(self.mfi[-1]):
            current_mfi = self.mfi[-1]
            
            if self.position.is_long and current_mfi >= self.mfi_extreme_overbought:
                print(f"❌ Exiting LONG position: MFI extremely overbought ({current_mfi:.1f})")
                self.position.close()
            elif self.position.is_short and current_mfi <= self.mfi_extreme_oversold:
                print(f"❌ Exiting SHORT position: MFI extremely oversold ({current_mfi:.1f})")
                self.position.close()

# Test the strategy using multi-data framework
if __name__ == "__main__":
    print("\n🎯 Testing High Probability Order Blocks + MFI Strategy")
    print("=" * 80)
    
    # Test on all available data sources
    results = test_on_all_data(
        OrderBlocksMFIStrategy, 
        'OrderBlocksMFI',
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
    
    print("\n🌙 High Probability Order Blocks + MFI Strategy Testing Complete! 🚀")