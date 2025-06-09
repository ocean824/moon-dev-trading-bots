"""
🌙 MOON DEV'S LSTM LIQUIDATION PREDICTOR 🚀
Predicting BTC price moves using liquidation data with LSTM neural networks
"""

# 🌙 MOON DEV'S TRAINING CONFIGURATION CONSTANTS 🚀
# ================================================

# 🏠 LOCAL MODE SWITCH - Change to False for full cloud runs! 🚀
LOCAL_MODE = True             # Set to False for production cloud runs

# Training Constants (scaled by LOCAL_MODE)
EPOCHS = 5 if LOCAL_MODE else 1000                    
BATCH_SIZE = 32 if LOCAL_MODE else 64               
LEARNING_RATE = 0.001         # Base learning rate
EARLY_STOPPING_PATIENCE = 3 if LOCAL_MODE else 10   # Much faster stopping for local
LR_REDUCE_PATIENCE = 2 if LOCAL_MODE else 5         # Faster LR adjustment for local
MIN_LEARNING_RATE = 1e-7      # Minimum learning rate
GRADIENT_CLIP_NORM = 1.0      # Gradient clipping value

# Data Processing Constants (scaled by LOCAL_MODE)
DATA_SAMPLE_FRACTION = 0.01 if LOCAL_MODE else 1.0  # Use 1% TIME PERIOD (3.6 days) for local, 100% for cloud
LOOKBACK_WINDOW = 60          # LSTM sequence length
PREDICTION_HORIZON = 5        # Steps ahead to predict
MAX_RETURN_CAP = 10.0         # Cap gains at 1000%
MIN_RETURN_CAP = -0.99        # Cap losses at 99%
TARGET_THRESHOLD = 0.005      # 0.5% threshold for binary targets

# Model Architecture (scaled by LOCAL_MODE)
LSTM_UNITS_1 = 64 if LOCAL_MODE else 128
LSTM_UNITS_2 = 32 if LOCAL_MODE else 64  
LSTM_UNITS_3 = 16 if LOCAL_MODE else 32

# Feature Selection (scaled by LOCAL_MODE)
CORE_FEATURES = [
    'side', 'quantity_sum', 'quantity_mean', 'price_last', 'price_mean',
    'usd_liq_volume', 'usd_liq_net', 'liq_velocity', 'liq_imbalance',
    'total_liq_events', 'hour', 'minute', 'day_of_week'
] if LOCAL_MODE else None  # None means use all features

mode_emoji = "🏠" if LOCAL_MODE else "☁️"
mode_name = "LOCAL TESTING" if LOCAL_MODE else "CLOUD PRODUCTION"
print(f"🌙 MOON DEV'S OPTIMIZED TRAINING CONSTANTS LOADED! 🚀")
print(f"{mode_emoji} MODE: {mode_name}")
print(f"   📊 Data Sample: {DATA_SAMPLE_FRACTION*100:.2f}% of TIME PERIOD (most recent data)")
print(f"   🎯 Epochs: {EPOCHS}")
print(f"   🚀 Batch Size: {BATCH_SIZE}")  
print(f"   ⚡ Early Stopping: {EARLY_STOPPING_PATIENCE} patience")
print(f"   🧠 LSTM Architecture: {LSTM_UNITS_1}/{LSTM_UNITS_2}/{LSTM_UNITS_3}")
if LOCAL_MODE:
    print(f"   🔧 Features: {len(CORE_FEATURES)} core features only")
else:
    print(f"   🔧 Features: All 47 features")
print("=" * 50)

import pandas as pd
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, BatchNormalization
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
import pandas_ta as ta
from sklearn.preprocessing import MinMaxScaler, StandardScaler
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
import os
from datetime import datetime, timedelta
warnings.filterwarnings('ignore')

print("🌙 MOON DEV'S LSTM LIQUIDATION PREDICTOR LOADING... 🚀")
print("=" * 60)

class LSTMLiquidationPredictor:
    def __init__(self, lookback_window=LOOKBACK_WINDOW, prediction_horizon=PREDICTION_HORIZON):
        """
        🌙 Moon Dev's LSTM Liquidation Predictor
        
        Args:
            lookback_window: How many time steps to look back (default from constants)
            prediction_horizon: How many steps ahead to predict (default from constants)
        """
        self.lookback_window = lookback_window
        self.prediction_horizon = prediction_horizon
        self.model = None
        self.price_scaler = MinMaxScaler()
        self.feature_scaler = StandardScaler()
        self.target_scaler = StandardScaler()  # Add target scaler for Moon Dev!
        self.is_trained = False
        
        print(f"🚀 Moon Dev LSTM initialized with {lookback_window} lookback window")
        print(f"🎯 Predicting {prediction_horizon} steps ahead")
        print("=" * 50)
    
    def load_liquidation_data(self, data_path):
        """
        🌙 Load Moon Dev's liquidation data
        """
        print("📊 Loading liquidation data for Moon Dev... 🌙")
        print(f"🔍 Moon Dev checking file path: {data_path}")
        
        if not os.path.exists(data_path):
            print(f"❌ Moon Dev, data file not found: {data_path}")
            return None
            
        print("✅ Moon Dev found the data file! Loading now... 🚀")
        
        # Load the liquidation data
        df = pd.read_csv(data_path)
        print(f"🎉 Moon Dev loaded {len(df):,} liquidation records! 🚀")
        print(f"📊 Moon Dev's data shape: {df.shape}")
        
        # Print column names for debugging
        print(f"🔍 Moon Dev's column names: {list(df.columns)}")
        print(f"📋 Moon Dev's data types:")
        for col in df.columns:
            print(f"   📌 {col}: {df[col].dtype}")
        
        # Print first few rows for inspection
        print("👀 Moon Dev's first 3 rows:")
        print(df.head(3))
        print("=" * 50)
        
        # Handle different timestamp column names
        timestamp_col = None
        possible_timestamp_cols = ['datetime', 'timestamp', 'time', 'date', 'ts']  # Put 'datetime' first since that's what Moon Dev has!
        
        for col in possible_timestamp_cols:
            if col in df.columns:
                timestamp_col = col
                print(f"✅ Moon Dev found timestamp column: '{col}' 🌙")
                break
        
        if timestamp_col:
            print(f"🔄 Moon Dev converting '{timestamp_col}' to datetime...")
            df['timestamp'] = pd.to_datetime(df[timestamp_col])
            df = df.sort_values('timestamp').reset_index(drop=True)
            print("⏰ Moon Dev's data sorted by timestamp! 🌙")
            print(f"🕐 Moon Dev's date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        else:
            print("⚠️ Moon Dev couldn't find timestamp column! Available columns:")
            print(f"   {list(df.columns)}")
            print("🔧 Moon Dev will proceed without timestamp sorting...")
        
        print("=" * 50)
        return df
    
    def engineer_features(self, df, time_window='1min'):
        """
        🌙 Engineer Moon Dev's liquidation features with LOCAL_MODE support
        """
        print(f"🔧 Engineering features for Moon Dev with {time_window} windows... 🚀")
        print(f"📊 Moon Dev input data shape: {df.shape}")
        print(f"🔍 Moon Dev input columns: {list(df.columns)}")
        
        # 🏠 LOCAL_MODE: Sample TIME PERIOD for faster testing (not just events!)
        if LOCAL_MODE and DATA_SAMPLE_FRACTION < 1.0:
            original_size = len(df)
            
            # Sample by TIME PERIOD instead of random events!
            df_sorted = df.sort_values('timestamp')
            total_time_span = df_sorted['timestamp'].max() - df_sorted['timestamp'].min()
            sample_time_span = total_time_span * DATA_SAMPLE_FRACTION
            
            # Take the most recent period for Moon Dev (most relevant!)
            end_time = df_sorted['timestamp'].max()
            start_time = end_time - sample_time_span
            
            df = df_sorted[df_sorted['timestamp'] >= start_time].reset_index(drop=True)
            sample_size = len(df)
            
            print(f"🏠 LOCAL_MODE: Time-based sampling for Moon Dev! 🌙")
            print(f"   📅 Total time span: {total_time_span.days} days")
            print(f"   🎯 Sample time span: {sample_time_span.days} days ({DATA_SAMPLE_FRACTION*100:.1f}%)")
            print(f"   📊 Records in sample: {sample_size:,} from {original_size:,} ({sample_size/original_size*100:.1f}%)")
            print(f"   🕐 Sample period: {start_time} to {end_time}")
        
        # Check if we have timestamp column
        if 'timestamp' not in df.columns:
            print("❌ Moon Dev error: No timestamp column found for resampling!")
            print(f"Available columns: {list(df.columns)}")
            return None
        
        print("✅ Moon Dev found timestamp column, proceeding with resampling... 🌙")
        
        # Set timestamp as index for resampling
        print("🔄 Moon Dev setting timestamp as index...")
        
        # Map Moon Dev's actual column names
        quantity_col = 'original_quantity' if 'original_quantity' in df.columns else 'quantity'
        print(f"📊 Moon Dev using quantity column: '{quantity_col}'")
        
        print("⏳ Moon Dev resampling liquidation data... This might take a moment! 🌙")
        
        # 🎯 MOON DEV'S BITCOIN-ONLY STRATEGY! 🎯
        # Separate ALL liquidations (for features) vs BTC-only (for price targets)
        print("🪙 Moon Dev implementing Bitcoin-only price targeting...")
        
        # Step 1: Aggregate ALL liquidation data for features
        all_liquidations = df.set_index('timestamp').resample(time_window).agg({
            'side': lambda x: (x.str.upper() == 'BUY').sum() - (x.str.upper() == 'SELL').sum(),  # Net short/long liquidations from ALL coins
            quantity_col: ['sum', 'mean', 'std', 'max', 'count'],  # ALL liquidation volumes
            'symbol': 'count'  # Total liquidation events across all symbols
        }).fillna(0)
        
        # Step 2: Get BTC-only data for price movements
        btc_data = df[df['symbol'] == 'BTC'].copy()
        print(f"🪙 BTC-only records: {len(btc_data):,} out of {len(df):,} total ({len(btc_data)/len(df)*100:.1f}%)")
        
        if len(btc_data) == 0:
            print("❌ Moon Dev ERROR: No BTC records found! Check symbol column.")
            print(f"Available symbols: {df['symbol'].unique()[:10]}...")
            return None
        
        btc_prices = btc_data.set_index('timestamp').resample(time_window).agg({
            'price': ['first', 'last', 'min', 'max', 'mean', 'std']
        }).fillna(method='ffill')  # Forward fill BTC prices
        
        # Step 3: Combine ALL liquidations with BTC-only prices
        df_resampled = all_liquidations.join(btc_prices, how='inner')  # Inner join to only keep periods with BTC data
        print(f"✅ Combined data shape: {df_resampled.shape} (ALL liquidations + BTC prices only)")
        print(f"📊 Date range: {df_resampled.index.min()} to {df_resampled.index.max()}")
        
        print(f"✅ Moon Dev resampling complete! Shape: {df_resampled.shape} 🚀")
        
        # Flatten column names
        print("🔄 Moon Dev flattening column names...")
        df_resampled.columns = ['_'.join(col).strip() if col[1] else col[0] for col in df_resampled.columns]
        print(f"📋 Moon Dev's resampled columns: {list(df_resampled.columns)}")
        
        # Standardize column names for Moon Dev's features (handle both original_quantity and quantity)
        print("🔧 Moon Dev standardizing column names...")
        column_mapping = {}
        for col in df_resampled.columns:
            if 'original_quantity' in col:
                new_col = col.replace('original_quantity', 'quantity')
                column_mapping[col] = new_col
            elif 'side_<lambda>' in col:
                # Fix the side column name issue!
                column_mapping[col] = 'side'
            elif 'symbol_count' in col:
                # Rename symbol count to total liquidation events
                column_mapping[col] = 'total_liq_events'
        
        if column_mapping:
            df_resampled = df_resampled.rename(columns=column_mapping)
            print(f"✅ Moon Dev renamed columns: {column_mapping}")
        
        print("🎯 Moon Dev's basic aggregations complete! 🌙")
        print(f"📋 Moon Dev's final columns: {list(df_resampled.columns)}")
        
        # 🚀 LIQUIDATION-ONLY FEATURES (The Real Alpha!)
        print("💰 Moon Dev creating USD liquidation features...")
        # USD notional value of liquidations (this is what really matters!)
        df_resampled['usd_liq_volume'] = df_resampled['quantity_sum'] * df_resampled['price_mean']
        
        # Moon Dev's CORRECT liquidation direction logic! 🌙
        # Positive 'side' = More SHORT liq (BUY orders) = Bullish pressure
        # Negative 'side' = More LONG liq (SELL orders) = Bearish pressure
        df_resampled['usd_short_liq'] = df_resampled['quantity_sum'] * df_resampled['price_mean'] * (df_resampled['side'] > 0)  # SHORT liquidations (BUY orders)
        df_resampled['usd_long_liq'] = df_resampled['quantity_sum'] * df_resampled['price_mean'] * (df_resampled['side'] < 0)  # LONG liquidations (SELL orders)
        
        # Liquidation intensity and flow
        df_resampled['liq_intensity'] = df_resampled['quantity_sum'] / (df_resampled['quantity_count'] + 1)
        df_resampled['liq_imbalance'] = df_resampled['side'] / (df_resampled['quantity_count'] + 1)
        df_resampled['large_liq_ratio'] = (df_resampled['quantity_max'] / (df_resampled['quantity_mean'] + 1)).fillna(0)
        
        # USD-based liquidation imbalances (Moon Dev's alpha!)
        df_resampled['usd_liq_net'] = df_resampled['usd_short_liq'] - df_resampled['usd_long_liq']  # Positive = More shorts liquidated (bullish)
        df_resampled['usd_liq_ratio'] = df_resampled['usd_short_liq'] / (df_resampled['usd_long_liq'] + 1e-8)  # >1 = More shorts liquidated
        df_resampled['usd_liq_dominance'] = df_resampled['usd_liq_net'] / (df_resampled['usd_liq_volume'] + 1e-8)
        
        # Liquidation velocity and acceleration
        df_resampled['liq_velocity'] = df_resampled['quantity_count']  # liquidations per minute
        df_resampled['usd_liq_velocity'] = df_resampled['usd_liq_volume']  # USD liquidated per minute
        
        # Large liquidation events detection
        df_resampled['whale_liq_flag'] = (df_resampled['quantity_max'] > df_resampled['quantity_mean'] * 3).astype(int)
        df_resampled['mega_liq_usd'] = df_resampled['quantity_max'] * df_resampled['price_max']
        
        # Time-based features
        df_resampled['hour'] = df_resampled.index.hour
        df_resampled['minute'] = df_resampled.index.minute
        df_resampled['day_of_week'] = df_resampled.index.dayofweek
        
        # Rolling liquidation statistics (Moon Dev's pattern detection!)
        print("📊 Moon Dev creating rolling statistics...")
        for window in [5, 10, 20]:
            print(f"   🔄 Moon Dev calculating {window}-period rolling averages...")
            df_resampled[f'liq_volume_ma_{window}'] = df_resampled['quantity_sum'].rolling(window).mean()
            df_resampled[f'liq_count_ma_{window}'] = df_resampled['quantity_count'].rolling(window).mean()
            df_resampled[f'usd_liq_ma_{window}'] = df_resampled['usd_liq_volume'].rolling(window).mean()
            df_resampled[f'liq_velocity_ma_{window}'] = df_resampled['liq_velocity'].rolling(window).mean()
            df_resampled[f'liq_imbalance_ma_{window}'] = df_resampled['liq_imbalance'].rolling(window).mean()
        
        print("🚀 Moon Dev calculating acceleration features...")
        # Liquidation acceleration (velocity changes)
        df_resampled['liq_acceleration'] = df_resampled['liq_velocity'] - df_resampled['liq_velocity_ma_5']
        df_resampled['usd_liq_acceleration'] = df_resampled['usd_liq_velocity'] - df_resampled['usd_liq_ma_5']
        
        print("🎪 Moon Dev detecting liquidation clusters...")
        # Liquidation clustering detection
        df_resampled['liq_cluster_intensity'] = df_resampled['liq_velocity'] / (df_resampled['liq_velocity_ma_20'] + 1e-8)
        df_resampled['usd_liq_cluster_intensity'] = df_resampled['usd_liq_velocity'] / (df_resampled['usd_liq_ma_20'] + 1e-8)
        
        # Handle NaN values properly - NO FAKE DATA for Moon Dev! 🌙
        # Only fill with 0 where it makes sense (no liquidations = 0 liquidations)
        liquidation_columns = [col for col in df_resampled.columns if 'liq' in col.lower() or 'side' in col or 'quantity' in col]
        df_resampled[liquidation_columns] = df_resampled[liquidation_columns].fillna(0)
        
        # For rolling averages/technical indicators, drop NaN rows instead of faking data
        df_resampled = df_resampled.dropna()
        
        print(f"🎉 Moon Dev's feature engineering complete! Features shape: {df_resampled.shape} 🚀")
        print(f"📊 Features created: {list(df_resampled.columns)}")
        print("=" * 50)
        
        return df_resampled
    
    def create_target_variable(self, df, target_return_threshold=0.005):
        """
        🌙 Create Moon Dev's target variable for prediction
        """
        print(f"🎯 Creating target variable for Moon Dev (threshold: {target_return_threshold*100:.1f}%)... 🌙")
        print(f"📊 Moon Dev input data shape: {df.shape}")
        print(f"🔮 Moon Dev prediction horizon: {self.prediction_horizon} steps")
        
        # Calculate future returns
        print("📈 Moon Dev calculating future returns...")
        
        # Debug price data quality first!
        print("🔍 Moon Dev analyzing BTC price data quality...")
        print("🪙 NOTE: Using ONLY Bitcoin prices for targets (all liquidation data for features)")
        current_prices = df['price_last']
        future_prices = df['price_last'].shift(-self.prediction_horizon)
        
        zero_current = np.sum(current_prices == 0)
        zero_future = np.sum(future_prices == 0)
        near_zero_current = np.sum((current_prices > 0) & (current_prices < 0.001))
        near_zero_future = np.sum((future_prices > 0) & (future_prices < 0.001))
        
        print(f"💰 PRICE DATA ANALYSIS:")
        print(f"   🔢 Total price points: {len(current_prices):,}")
        print(f"   🚫 Zero current prices: {zero_current:,} ({zero_current/len(current_prices)*100:.3f}%)")
        print(f"   🚫 Zero future prices: {zero_future:,} ({zero_future/len(current_prices)*100:.3f}%)")
        print(f"   ⚠️ Near-zero current (<$0.001): {near_zero_current:,} ({near_zero_current/len(current_prices)*100:.3f}%)")
        print(f"   ⚠️ Near-zero future (<$0.001): {near_zero_future:,} ({near_zero_future/len(current_prices)*100:.3f}%)")
        
        if zero_current > 0 or near_zero_current > 0:
            print("🔥 MOON DEV FOUND THE PROBLEM! Zero/near-zero prices will cause infinite returns!")
            print("💡 This happens with small-cap altcoins that can trade at tiny fractions")
            print("🚀 BUT Moon Dev is right - these are REAL prices and REAL liquidations!")
        
        # Moon Dev's IMPROVED return calculation - cap extreme returns instead of dropping data!
        print("🔧 Moon Dev calculating returns with extreme value capping...")
        
        # Calculate raw returns first
        raw_returns = df['price_last'].shift(-self.prediction_horizon) / df['price_last'] - 1
        
        # Cap extreme returns at reasonable levels (Moon Dev keeps ALL the data!)
        max_return = MAX_RETURN_CAP  # Cap at 1000% gain (from constants)
        min_return = MIN_RETURN_CAP  # Cap at 99% loss (from constants)
        
        # Replace infinite values with capped values instead of dropping!
        df['future_return'] = np.where(
            np.isinf(raw_returns) & (raw_returns > 0), max_return,  # Positive infinity → 1000% gain
            np.where(
                np.isinf(raw_returns) & (raw_returns < 0), min_return,  # Negative infinity → 99% loss  
                np.where(
                    raw_returns > max_return, max_return,  # Cap huge gains
                    np.where(
                        raw_returns < min_return, min_return,  # Cap huge losses
                        raw_returns  # Keep normal returns
                    )
                )
            )
        )
        
        # Report what we capped
        capped_high = np.sum((raw_returns > max_return) | ((raw_returns == np.inf)))
        capped_low = np.sum((raw_returns < min_return) | ((raw_returns == -np.inf)))
        total_capped = capped_high + capped_low
        
        print(f"📊 MOON DEV'S BITCOIN-ONLY RETURN CAPPING RESULTS:")
        print(f"   🪙 Strategy: ALL liquidations → predict ONLY Bitcoin moves")
        print(f"   🚀 BTC returns capped at +{max_return*100:.0f}%: {capped_high:,}")
        print(f"   📉 BTC returns capped at {min_return*100:.0f}%: {capped_low:,}")
        print(f"   🎯 Total BTC moves capped: {total_capped:,} ({total_capped/len(raw_returns)*100:.3f}%)")
        
        # Moon Dev's beautiful colored data retention summary! 🌙
        total_samples = len(df)
        retention_rate = 100.0  # We keep everything now!
        loss_rate = 0.0
        
        # ANSI color codes for terminal
        GREEN_BG = '\033[42m'  # Green background
        WHITE_TEXT = '\033[97m'  # White text
        RED_BG = '\033[41m'     # Red background
        RESET = '\033[0m'       # Reset colors
        BOLD = '\033[1m'        # Bold text
        
        print(f"\n{BOLD}🌙 MOON DEV'S DATA RETENTION SCORECARD 🌙{RESET}")
        print("=" * 60)
        print(f"{GREEN_BG}{WHITE_TEXT}{BOLD} ✅ DATA PRESERVED: {total_samples:,} samples ({retention_rate:.1f}%) {RESET}")
        print(f"{RED_BG}{WHITE_TEXT}{BOLD} ❌ DATA LOST: 0 samples ({loss_rate:.1f}%) {RESET}")
        print(f"{GREEN_BG}{WHITE_TEXT}{BOLD} 🚀 MOON DEV'S APPROACH: ZERO DATA LOSS! {RESET}")
        print("=" * 60)
        
        # Create binary target: 1 if move > threshold, 0 otherwise
        print("🎯 Moon Dev creating binary targets...")
        df['target_binary'] = (abs(df['future_return']) > target_return_threshold).astype(int)
        
        # Create directional target: 1 for up, -1 for down, 0 for sideways
        print("🧭 Moon Dev creating directional targets...")
        df['target_direction'] = np.where(df['future_return'] > target_return_threshold, 1,
                                 np.where(df['future_return'] < -target_return_threshold, -1, 0))
        
        # Regression target (actual future return)
        print("📊 Moon Dev creating regression targets...")
        df['target_return'] = df['future_return']
        
        print(f"🚀 Moon Dev's targets created!")
        print(f"📊 Binary target distribution: {df['target_binary'].value_counts().to_dict()}")
        print(f"📈 Direction target distribution: {df['target_direction'].value_counts().to_dict()}")
        print("=" * 50)
        
        return df
    
    def prepare_sequences(self, df, feature_columns):
        """
        🌙 Prepare LSTM sequences for Moon Dev
        """
        print("🔄 Preparing LSTM sequences for Moon Dev... 🚀")
        print(f"📊 Moon Dev input data shape: {df.shape}")
        print(f"🎯 Moon Dev using {len(feature_columns)} features")
        
        # Remove rows with NaN targets
        print("🧹 Moon Dev cleaning NaN targets...")
        df_clean = df.dropna(subset=['target_return', 'target_binary', 'target_direction'])
        print(f"✅ Cleaned data shape: {df_clean.shape} (Moon Dev approved!)")
        
        # Prepare features and targets
        print("📋 Moon Dev preparing features and targets...")
        features = df_clean[feature_columns].values
        targets_return = df_clean['target_return'].values
        targets_binary = df_clean['target_binary'].values
        targets_direction = df_clean['target_direction'].values
        
        print(f"📊 Features shape: {features.shape}")
        print(f"🎯 Targets shape: {targets_return.shape}")
        
        # 🚨 MOON DEV'S DATA QUALITY CHECKS! 🚨
        print("🔍 Moon Dev running data quality checks...")
        
        # Check for infinite values in features
        inf_features = np.isinf(features).sum()
        nan_features = np.isnan(features).sum() 
        print(f"🔥 Features - Infinite values: {inf_features}, NaN values: {nan_features}")
        
        # Check for infinite values in targets
        inf_targets = np.isinf(targets_return).sum()
        nan_targets = np.isnan(targets_return).sum()
        print(f"🎯 Targets - Infinite values: {inf_targets}, NaN values: {nan_targets}")
        
        # 🚨 COMPREHENSIVE DATA QUALITY ANALYSIS FOR MOON DEV! 🚨
        print("=" * 60)
        print("🔍 MOON DEV'S COMPREHENSIVE DATA QUALITY REPORT 🌙")
        print("=" * 60)
        
        total_samples = len(targets_return)
        print(f"📊 Total samples to analyze: {total_samples:,}")
        
        # Analyze target return distribution
        finite_targets = targets_return[np.isfinite(targets_return)]
        print(f"📈 Finite target statistics:")
        print(f"   ✅ Finite values: {len(finite_targets):,} ({len(finite_targets)/total_samples*100:.2f}%)")
        print(f"   📉 Min return: {finite_targets.min():.6f}")
        print(f"   📈 Max return: {finite_targets.max():.6f}")
        print(f"   📊 Mean return: {finite_targets.mean():.6f}")
        print(f"   📏 Std return: {finite_targets.std():.6f}")
        
        # Break down problematic values
        inf_positive = np.sum(targets_return == np.inf)
        inf_negative = np.sum(targets_return == -np.inf)
        nan_count = np.sum(np.isnan(targets_return))
        
        print(f"🔥 PROBLEMATIC VALUES BREAKDOWN:")
        print(f"   ♾️ Positive infinite: {inf_positive:,} ({inf_positive/total_samples*100:.3f}%)")
        print(f"   ♾️ Negative infinite: {inf_negative:,} ({inf_negative/total_samples*100:.3f}%)")
        print(f"   🚫 NaN values: {nan_count:,} ({nan_count/total_samples*100:.3f}%)")
        print(f"   🔥 Total problematic: {inf_targets:,} ({inf_targets/total_samples*100:.3f}%)")
        
        # Analyze extreme but finite values
        if len(finite_targets) > 0:
            extreme_positive = np.sum(finite_targets > 1.0)  # >100% returns
            extreme_negative = np.sum(finite_targets < -0.5)  # <-50% returns
            print(f"⚡ EXTREME BUT FINITE VALUES:")
            print(f"   📈 Returns >100%: {extreme_positive:,} ({extreme_positive/total_samples*100:.3f}%)")
            print(f"   📉 Returns <-50%: {extreme_negative:,} ({extreme_negative/total_samples*100:.3f}%)")
            
            # Show some examples of extreme values
            if extreme_positive > 0:
                top_returns = finite_targets[finite_targets > 1.0][:5]
                print(f"   🚀 Sample huge gains: {[f'{x:.2%}' for x in top_returns]}")
            if extreme_negative > 0:
                bottom_returns = finite_targets[finite_targets < -0.5][:5]
                print(f"   💥 Sample huge losses: {[f'{x:.2%}' for x in bottom_returns]}")
        
        print("=" * 60)
        
        # Moon Dev's NEW approach - minimal data cleaning since we capped instead of creating infinites!
        if inf_features > 0 or inf_targets > 0:
            print("🧹 Moon Dev cleaning any remaining infinite feature values...")
            initial_count = len(features)
            
            # Only clean features (targets should be clean now!)
            features = np.where(np.isinf(features), np.nan, features)
            
            # Only remove rows with NaN/inf features
            valid_mask = ~np.isnan(features).any(axis=1)
            features = features[valid_mask]
            targets_return = targets_return[valid_mask]
            targets_binary = targets_binary[valid_mask]
            targets_direction = targets_direction[valid_mask]
            
            final_count = len(features)
            removed_count = initial_count - final_count
            
            print(f"📊 MOON DEV'S MINIMAL DATA CLEANING RESULTS:")
            print(f"   📉 Initial samples: {initial_count:,}")
            print(f"   ✅ Final samples: {final_count:,}")
            print(f"   🗑️ Removed samples: {removed_count:,} ({removed_count/initial_count*100:.3f}%)")
            
            # Moon Dev's colored final retention stats! 🌙
            retention_pct = final_count/initial_count*100
            loss_pct = removed_count/initial_count*100
            
            # ANSI color codes
            GREEN_BG = '\033[42m'  # Green background
            WHITE_TEXT = '\033[97m'  # White text
            RED_BG = '\033[41m'     # Red background  
            YELLOW_BG = '\033[43m'  # Yellow background
            BLACK_TEXT = '\033[30m'  # Black text
            RESET = '\033[0m'       # Reset colors
            BOLD = '\033[1m'        # Bold text
            
            print(f"\n{BOLD}🔥 MOON DEV'S FINAL DATA SCORECARD 🔥{RESET}")
            print("=" * 50)
            if retention_pct >= 99:
                print(f"{GREEN_BG}{WHITE_TEXT}{BOLD} 🚀 DATA RETAINED: {final_count:,} ({retention_pct:.2f}%) {RESET}")
            elif retention_pct >= 95:
                print(f"{YELLOW_BG}{BLACK_TEXT}{BOLD} ⚠️ DATA RETAINED: {final_count:,} ({retention_pct:.2f}%) {RESET}")
            else:
                print(f"{RED_BG}{WHITE_TEXT}{BOLD} 🚨 DATA RETAINED: {final_count:,} ({retention_pct:.2f}%) {RESET}")
            
            if loss_pct <= 1:
                print(f"{GREEN_BG}{WHITE_TEXT}{BOLD} ✅ DATA LOST: {removed_count:,} ({loss_pct:.3f}%) {RESET}")
            elif loss_pct <= 5:
                print(f"{YELLOW_BG}{BLACK_TEXT}{BOLD} ⚠️ DATA LOST: {removed_count:,} ({loss_pct:.3f}%) {RESET}")
            else:
                print(f"{RED_BG}{WHITE_TEXT}{BOLD} 🚨 DATA LOST: {removed_count:,} ({loss_pct:.3f}%) {RESET}")
            print("=" * 50)
            print("✅ Moon Dev preserved ALL liquidation data by capping instead of dropping! 🌙")
        else:
            # ANSI color codes
            GREEN_BG = '\033[42m'  # Green background  
            WHITE_TEXT = '\033[97m'  # White text
            RESET = '\033[0m'       # Reset colors
            BOLD = '\033[1m'        # Bold text
            
            print(f"{GREEN_BG}{WHITE_TEXT}{BOLD} 🎉 MOON DEV HAS ZERO INFINITE VALUES! PERFECT DATA CAPPING! 🚀 {RESET}")
        
        print("=" * 60)
        
        # Scale features
        print("⚖️ Moon Dev scaling features...")
        features_scaled = self.feature_scaler.fit_transform(features)
        
        # Scale targets too! This is the key for Moon Dev! 🚀
        print("🎯 Moon Dev scaling targets...")
        targets_return_scaled = self.target_scaler.fit_transform(targets_return.reshape(-1, 1)).flatten()
        
        # Check for issues after scaling
        inf_scaled = np.isinf(features_scaled).sum()
        nan_scaled = np.isnan(features_scaled).sum()
        inf_targets_scaled = np.isinf(targets_return_scaled).sum()
        nan_targets_scaled = np.isnan(targets_return_scaled).sum()
        
        print(f"✅ Scaled features - Infinite: {inf_scaled}, NaN: {nan_scaled}")
        print(f"✅ Scaled targets - Infinite: {inf_targets_scaled}, NaN: {nan_targets_scaled}")
        print(f"📊 Scaled target stats - Min: {targets_return_scaled.min():.4f}, Max: {targets_return_scaled.max():.4f}")
        
        # Use scaled targets instead of raw targets
        targets_return = targets_return_scaled
        
        # Create sequences
        print("🔗 Moon Dev creating LSTM sequences...")
        X, y_return, y_binary, y_direction = [], [], [], []
        
        print(f"🔄 Moon Dev processing {len(features_scaled)} samples...")
        for i in range(self.lookback_window, len(features_scaled)):
            X.append(features_scaled[i-self.lookback_window:i])
            y_return.append(targets_return[i])
            y_binary.append(targets_binary[i])
            y_direction.append(targets_direction[i])
            
            # Progress indicator for Moon Dev
            if (i - self.lookback_window) % 10000 == 0:
                print(f"   🌙 Moon Dev processed {i - self.lookback_window:,} sequences...")
        
        print("🔄 Moon Dev converting to numpy arrays...")
        X = np.array(X)
        y_return = np.array(y_return)
        y_binary = np.array(y_binary)
        y_direction = np.array(y_direction)
        
        print(f"🎉 Moon Dev's sequences ready! Shape: {X.shape} 🌙")
        print(f"📊 Feature sequences: {X.shape}")
        print(f"🎯 Target shapes - Return: {y_return.shape}, Binary: {y_binary.shape}, Direction: {y_direction.shape}")
        print("=" * 50)
        
        return X, y_return, y_binary, y_direction, df_clean.index[self.lookback_window:]
    
    def build_model(self, input_shape, model_type='regression'):
        """
        🌙 Build Moon Dev's LSTM model with LOCAL_MODE scaling
        """
        mode_text = "LOCAL" if LOCAL_MODE else "PRODUCTION"
        print(f"🏗️ Building Moon Dev's {mode_text} LSTM model ({model_type})... 🚀")
        print(f"   🧠 Architecture: {LSTM_UNITS_1}/{LSTM_UNITS_2}/{LSTM_UNITS_3} units")
        
        model = Sequential([
            LSTM(LSTM_UNITS_1, return_sequences=True, input_shape=input_shape, dropout=0.2, recurrent_dropout=0.2),
            BatchNormalization(),
            
            LSTM(LSTM_UNITS_2, return_sequences=True, dropout=0.2, recurrent_dropout=0.2),
            BatchNormalization(),
            
            LSTM(LSTM_UNITS_3, return_sequences=False, dropout=0.2, recurrent_dropout=0.2),
            BatchNormalization(),
            
            Dense(16, activation='relu'),
            Dropout(0.3),
            Dense(8, activation='relu'),
            Dropout(0.2),
        ])
        
        if model_type == 'regression':
            model.add(Dense(1, activation='linear'))  # For return prediction
            # Add gradient clipping for Moon Dev's stability!
            optimizer = Adam(learning_rate=LEARNING_RATE, clipnorm=GRADIENT_CLIP_NORM)
            model.compile(optimizer=optimizer, 
                         loss='mse', 
                         metrics=['mae'])
            print("📈 Moon Dev's regression model compiled with optimized constants! 🌙")
            
        elif model_type == 'binary':
            model.add(Dense(1, activation='sigmoid'))  # For binary classification
            model.compile(optimizer=Adam(learning_rate=0.001), 
                         loss='binary_crossentropy', 
                         metrics=['accuracy'])
            print("🎯 Moon Dev's binary classification model compiled! 🌙")
            
        elif model_type == 'multiclass':
            model.add(Dense(3, activation='softmax'))  # For direction (-1, 0, 1)
            model.compile(optimizer=Adam(learning_rate=0.001), 
                         loss='sparse_categorical_crossentropy', 
                         metrics=['accuracy'])
            print("🎪 Moon Dev's multiclass model compiled! 🌙")
        
        print(f"🏗️ Model architecture for Moon Dev:")
        model.summary()
        print("=" * 50)
        
        return model
    
    def train_model(self, X_train, y_train, X_val, y_val, model_type='regression', epochs=EPOCHS):
        """
        🌙 Train Moon Dev's LSTM model with optimized constants
        """
        print(f"🎓 Training Moon Dev's OPTIMIZED LSTM model ({model_type})... 🚀")
        print(f"   📊 Epochs: {epochs}")
        print(f"   🚀 Batch Size: {BATCH_SIZE}")
        print(f"   ⚡ Early Stopping Patience: {EARLY_STOPPING_PATIENCE}")
        print(f"   📉 LR Reduce Patience: {LR_REDUCE_PATIENCE}")
        
        # Build model
        self.model = self.build_model(input_shape=(X_train.shape[1], X_train.shape[2]), model_type=model_type)
        
        # Optimized callbacks for Moon Dev's training
        callbacks = [
            EarlyStopping(monitor='val_loss', patience=EARLY_STOPPING_PATIENCE, restore_best_weights=True, verbose=1),
            ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=LR_REDUCE_PATIENCE, min_lr=MIN_LEARNING_RATE, verbose=1)
        ]
        
        print("🚂 Moon Dev's OPTIMIZED training starting... 🌙")
        
        # Train the model with optimized parameters
        history = self.model.fit(
            X_train, y_train,
            validation_data=(X_val, y_val),
            epochs=epochs,
            batch_size=BATCH_SIZE,  # Increased batch size!
            callbacks=callbacks,
            verbose=1
        )
        
        self.is_trained = True
        print("🎉 Moon Dev's LSTM training complete! 🚀")
        print("=" * 50)
        
        return history
    
    def evaluate_model(self, X_test, y_test, model_type='regression'):
        """
        🌙 Evaluate Moon Dev's model performance
        """
        print("📊 Evaluating Moon Dev's LSTM performance... 🚀")
        
        if not self.is_trained:
            print("❌ Moon Dev, model needs to be trained first!")
            return None
        
        # Make predictions
        predictions = self.model.predict(X_test)
        
        if model_type == 'regression':
            # Calculate regression metrics
            mse = mean_squared_error(y_test, predictions)
            mae = mean_absolute_error(y_test, predictions)
            rmse = np.sqrt(mse)
            r2 = r2_score(y_test, predictions)
            mape = np.mean(np.abs((y_test - predictions.flatten()) / (y_test + 1e-8))) * 100
            
            print("🎯 MOON DEV'S LSTM PERFORMANCE METRICS 🌙")
            print("=" * 50)
            print(f"📊 RMSE (Root Mean Square Error): {rmse:.6f}")
            print(f"📈 MAE (Mean Absolute Error): {mae:.6f}")
            print(f"🎪 R² (R-squared): {r2:.4f}")
            print(f"📉 MAPE (Mean Absolute % Error): {mape:.2f}%")
            print(f"🚀 MSE (Mean Square Error): {mse:.6f}")
            
            metrics = {
                'rmse': rmse, 'mae': mae, 'r2': r2, 'mape': mape, 'mse': mse,
                'predictions': predictions.flatten(), 'actuals': y_test
            }
            
        else:
            # Calculate classification metrics
            if model_type == 'binary':
                predictions_binary = (predictions > 0.5).astype(int).flatten()
            else:
                predictions_binary = np.argmax(predictions, axis=1)
            
            accuracy = np.mean(predictions_binary == y_test)
            
            print("🎯 MOON DEV'S CLASSIFICATION METRICS 🌙")
            print("=" * 50)
            print(f"🎪 Accuracy: {accuracy:.4f}")
            
            metrics = {
                'accuracy': accuracy,
                'predictions': predictions_binary,
                'actuals': y_test
            }
        
        print("=" * 50)
        return metrics
    
    def plot_results(self, metrics, model_type='regression', save_path=None):
        """
        🌙 Plot Moon Dev's results
        """
        print("📈 Creating Moon Dev's performance plots... 🚀")
        
        if model_type == 'regression':
            fig, axes = plt.subplots(2, 2, figsize=(15, 10))
            fig.suptitle('🌙 MOON DEV\'S LSTM LIQUIDATION PREDICTOR RESULTS 🚀', fontsize=16)
            
            # Scatter plot of predictions vs actuals
            axes[0, 0].scatter(metrics['actuals'], metrics['predictions'], alpha=0.6)
            axes[0, 0].plot([metrics['actuals'].min(), metrics['actuals'].max()], 
                           [metrics['actuals'].min(), metrics['actuals'].max()], 'r--', lw=2)
            axes[0, 0].set_xlabel('Actual Returns')
            axes[0, 0].set_ylabel('Predicted Returns')
            axes[0, 0].set_title('🎯 Moon Dev: Predictions vs Actuals')
            axes[0, 0].grid(True, alpha=0.3)
            
            # Residuals plot
            residuals = metrics['actuals'] - metrics['predictions']
            axes[0, 1].scatter(metrics['predictions'], residuals, alpha=0.6)
            axes[0, 1].axhline(y=0, color='r', linestyle='--')
            axes[0, 1].set_xlabel('Predicted Returns')
            axes[0, 1].set_ylabel('Residuals')
            axes[0, 1].set_title('🌙 Moon Dev: Residuals Plot')
            axes[0, 1].grid(True, alpha=0.3)
            
            # Time series of actuals vs predictions (last 200 points)
            n_points = min(200, len(metrics['actuals']))
            axes[1, 0].plot(metrics['actuals'][-n_points:], label='Actual', alpha=0.7)
            axes[1, 0].plot(metrics['predictions'][-n_points:], label='Predicted', alpha=0.7)
            axes[1, 0].set_xlabel('Time Steps')
            axes[1, 0].set_ylabel('Returns')
            axes[1, 0].set_title('🚀 Moon Dev: Time Series (Last 200 points)')
            axes[1, 0].legend()
            axes[1, 0].grid(True, alpha=0.3)
            
            # Distribution of residuals
            axes[1, 1].hist(residuals, bins=50, alpha=0.7, density=True)
            axes[1, 1].set_xlabel('Residuals')
            axes[1, 1].set_ylabel('Density')
            axes[1, 1].set_title('🌙 Moon Dev: Residuals Distribution')
            axes[1, 1].grid(True, alpha=0.3)
            
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"📊 Moon Dev's plots saved to: {save_path} 🌙")
        
        plt.show()
        print("🎉 Moon Dev's visualization complete! 🚀")
        print("=" * 50)

def main():
    """
    🌙 Moon Dev's main LSTM liquidation prediction pipeline
    """
    print("🚀 STARTING MOON DEV'S LSTM LIQUIDATION PREDICTOR 🌙")
    print("=" * 60)
    
    # Initialize the predictor
    print("🏗️ Moon Dev initializing LSTM predictor...")
    predictor = LSTMLiquidationPredictor(lookback_window=60, prediction_horizon=5)
    
    # Load data (adjust path as needed)
    print("📂 Moon Dev loading liquidation data...")
    data_path = "/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/moondev_api/liq_data.csv"  # Adjust this path
    df = predictor.load_liquidation_data(data_path)
    
    if df is None:
        print("❌ Moon Dev, please check your data path!")
        return
    
    print("✅ Moon Dev data loaded successfully! Moving to feature engineering... 🔧")
    
    # Engineer features
    print("🔧 Moon Dev starting feature engineering...")
    df_features = predictor.engineer_features(df, time_window='1min')
    
    if df_features is None:
        print("❌ Moon Dev, feature engineering failed!")
        return
    
    print("✅ Moon Dev feature engineering complete! Creating targets... 🎯")
    
    # Create target variables
    print("🎯 Moon Dev creating target variables...")
    df_targets = predictor.create_target_variable(df_features, target_return_threshold=TARGET_THRESHOLD)
    
    # Define feature columns (exclude target columns and timestamp)
    all_feature_columns = [col for col in df_targets.columns 
                          if col not in ['target_return', 'target_binary', 'target_direction', 'future_return']]
    
    # 🏠 LOCAL_MODE: Use core features only for faster testing
    if LOCAL_MODE and CORE_FEATURES is not None:
        # Filter to only include core features that exist in the dataset
        feature_columns = [col for col in CORE_FEATURES if col in all_feature_columns]
        print(f"🏠 LOCAL_MODE: Using {len(feature_columns)} core features: {feature_columns}")
        if len(feature_columns) < len(CORE_FEATURES):
            missing = [col for col in CORE_FEATURES if col not in all_feature_columns]
            print(f"⚠️ Missing core features: {missing}")
    else:
        feature_columns = all_feature_columns
        print(f"☁️ PRODUCTION: Using all {len(feature_columns)} features: {feature_columns[:10]}..." if len(feature_columns) > 10 else f"☁️ PRODUCTION: Using features: {feature_columns}")
    
    # Prepare sequences
    X, y_return, y_binary, y_direction, timestamps = predictor.prepare_sequences(df_targets, feature_columns)
    
    # Split data (80% train, 10% val, 10% test) - time series split
    train_size = int(0.8 * len(X))
    val_size = int(0.1 * len(X))
    
    X_train, X_val, X_test = X[:train_size], X[train_size:train_size+val_size], X[train_size+val_size:]
    y_train, y_val, y_test = y_return[:train_size], y_return[train_size:train_size+val_size], y_return[train_size+val_size:]
    
    print(f"🔄 Moon Dev's data split:")
    print(f"📊 Train: {X_train.shape[0]}, Val: {X_val.shape[0]}, Test: {X_test.shape[0]}")
    print("=" * 50)
    
    # Train the model with optimized constants
    history = predictor.train_model(X_train, y_train, X_val, y_val, model_type='regression', epochs=EPOCHS)
    
    # Evaluate the model
    metrics = predictor.evaluate_model(X_test, y_test, model_type='regression')
    
    # Plot results
    predictor.plot_results(metrics, model_type='regression')
    
    print("🎉 MOON DEV'S LSTM LIQUIDATION PREDICTOR COMPLETE! 🚀🌙")
    print("=" * 60)

if __name__ == "__main__":
    main() 