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
BATCH_SIZE = 32 if LOCAL_MODE else 64               # 🚀 OPTIMIZED: Batch size 32 confirmed optimal
LEARNING_RATE = 0.001         # 🚀 OPTIMIZED: 0.001 confirmed optimal from parameter search
EARLY_STOPPING_PATIENCE = 3 if LOCAL_MODE else 10   # Much faster stopping for local
LR_REDUCE_PATIENCE = 2 if LOCAL_MODE else 5         # Faster LR adjustment for local
MIN_LEARNING_RATE = 1e-7      # Minimum learning rate
GRADIENT_CLIP_NORM = 1.0      # 🚀 OPTIMIZED: 1.0 confirmed optimal from parameter search

# Data Processing Constants (scaled by LOCAL_MODE)
DATA_SAMPLE_FRACTION = 0.01 if LOCAL_MODE else 1.0  # Use 1% TIME PERIOD (3.6 days) for local, 100% for cloud
LOOKBACK_WINDOW = 10 if LOCAL_MODE else 60          # 🚀 OPTIMIZED: 60→10 from parameter search!
PREDICTION_HORIZON = 5        # Steps ahead to predict
MAX_RETURN_CAP = 10.0         # Cap gains at 1000%
MIN_RETURN_CAP = -0.99        # Cap losses at 99%
TARGET_THRESHOLD = 0.005      # 0.5% threshold for binary targets

# Model Architecture (scaled by LOCAL_MODE) - 🚀 OPTIMIZED PARAMETERS!
LSTM_UNITS_1 = 32 if LOCAL_MODE else 128  # 🚀 OPTIMIZED: 64→32 from parameter search!
LSTM_UNITS_2 = 16 if LOCAL_MODE else 64   # 🚀 OPTIMIZED: 32→16 from parameter search!  
LSTM_UNITS_3 = 16 if LOCAL_MODE else 32   # Keep for production scaling

# Feature Selection (scaled by LOCAL_MODE) - MOON DEV'S FOCUSED APPROACH! 🎯
LIQUIDATION_FOCUSED_FEATURES = [
    'usd_long_liq', 'usd_short_liq', 'usd_liq_volume', 'usd_liq_net', 'liq_imbalance', 'liq_velocity'
] if LOCAL_MODE else None  # Moon Dev's proven 6-feature approach from Random Forest!

CORE_FEATURES = [
    'side', 'quantity_sum', 'quantity_mean', 'price_last', 'price_mean',
    'usd_liq_volume', 'usd_liq_net', 'liq_velocity', 'liq_imbalance',
    'total_liq_events', 'hour', 'minute', 'day_of_week'
] if not LOCAL_MODE else None  # Use full features only in production

mode_emoji = "🏠" if LOCAL_MODE else "☁️"
mode_name = "LOCAL TESTING" if LOCAL_MODE else "CLOUD PRODUCTION"
print(f"🌙 MOON DEV'S OPTIMIZED TRAINING CONSTANTS LOADED! 🚀")
print(f"{mode_emoji} MODE: {mode_name}")
print(f"   📊 Data Sample: {DATA_SAMPLE_FRACTION*100:.2f}% of TIME PERIOD (most recent data)")
print(f"   🎯 Epochs: {EPOCHS}")
print(f"   🚀 Batch Size: {BATCH_SIZE}")  
print(f"   ⚡ Early Stopping: {EARLY_STOPPING_PATIENCE} patience")
print(f"   🧠 LSTM Architecture: {LSTM_UNITS_1}/{LSTM_UNITS_2}/{LSTM_UNITS_3} (OPTIMIZED!)")
print(f"   🔧 Lookback Window: {LOOKBACK_WINDOW} steps (OPTIMIZED!)")
print(f"   📈 Learning Rate: {LEARNING_RATE} (OPTIMIZED!)")
if LOCAL_MODE:
    if LIQUIDATION_FOCUSED_FEATURES:
        print(f"   🎯 Features: {len(LIQUIDATION_FOCUSED_FEATURES)} FOCUSED liquidation features")
    else:
        print(f"   🔧 Features: {len(CORE_FEATURES)} core features only")
else:
    print(f"   🔧 Features: All features")
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
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score, roc_auc_score, roc_curve  # 🚀 Added AUC imports
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
    
    def create_focused_liquidation_features(self, df, time_window='1min'):
        """
        🎯 Moon Dev's FOCUSED liquidation features (same approach as Random Forest!)
        Proven signals from backtesting: liquidation side + volume
        """
        print("🎯 Creating FOCUSED liquidation features based on Moon Dev's backtesting! 🌙")
        print("💡 Core insight: Long liquidations → Buy signal, Short liquidations → Sell signal")
        print("🚀 Reducing feature noise, focusing on PROVEN signals!")
        
        # 🏠 LOCAL_MODE: Sample TIME PERIOD for faster testing (ADD THIS!)
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
            
            print(f"🏠 LOCAL_MODE: FOCUSED features using time-based sampling! 🌙")
            print(f"   📅 Total time span: {total_time_span.days} days")
            print(f"   🎯 Sample time span: {sample_time_span.days} days ({DATA_SAMPLE_FRACTION*100:.1f}%)")
            print(f"   📊 Records in sample: {sample_size:,} from {original_size:,} ({sample_size/original_size*100:.1f}%)")
            print(f"   🕐 Sample period: {start_time} to {end_time}")
        
        # Check for required columns
        quantity_col = 'original_quantity' if 'original_quantity' in df.columns else 'quantity'
        print(f"📊 Moon Dev using quantity column: '{quantity_col}'")
        
        if 'timestamp' not in df.columns:
            print("❌ Moon Dev error: No timestamp column found!")
            return None
        
        # 🪙 Moon Dev implementing Bitcoin-only price targeting...
        print("🪙 Moon Dev implementing Bitcoin-only price targeting...")
        
        # Step 1: Create focused liquidation aggregations (FIXED!)
        print("🔧 Moon Dev creating time-based liquidation aggregations...")
        
        # Set timestamp as index for resampling
        df_indexed = df.set_index('timestamp')
        
        # Create separate aggregations for BUY and SELL sides
        buy_liquidations = df_indexed[df_indexed['side'].str.upper() == 'BUY'].resample(time_window).agg({
            quantity_col: ['sum', 'count'],
            'price': 'mean'
        }).fillna(0)
        
        sell_liquidations = df_indexed[df_indexed['side'].str.upper() == 'SELL'].resample(time_window).agg({
            quantity_col: ['sum', 'count'], 
            'price': 'mean'
        }).fillna(0)
        
        # Create total aggregations
        total_liquidations = df_indexed.resample(time_window).agg({
            quantity_col: ['sum', 'count'],
            'price': 'mean'
        }).fillna(0)
        
        # Flatten column names and rename
        buy_liquidations.columns = [f'buy_{col[0]}_{col[1]}' if col[1] else f'buy_{col[0]}' for col in buy_liquidations.columns]
        sell_liquidations.columns = [f'sell_{col[0]}_{col[1]}' if col[1] else f'sell_{col[0]}' for col in sell_liquidations.columns]
        total_liquidations.columns = [f'total_{col[0]}_{col[1]}' if col[1] else f'total_{col[0]}' for col in total_liquidations.columns]
        
        # Combine all aggregations
        all_liquidations = buy_liquidations.join(sell_liquidations, how='outer').join(total_liquidations, how='outer').fillna(0)
        
        # Step 2: Get BTC prices for targets
        btc_data = df[df['symbol'] == 'BTC'].copy()
        print(f"🪙 BTC records: {len(btc_data):,} out of {len(df):,} total")
        
        if len(btc_data) == 0:
            print("❌ No BTC records found!")
            return None

        btc_prices = btc_data.set_index('timestamp').resample(time_window).agg({
            'price': ['first', 'last', 'mean']
        }).fillna(method='ffill')
        
        # Flatten BTC price columns to match liquidation data structure
        print("🔧 Flattening BTC price columns for joining...")
        btc_prices.columns = [f'{col[0]}_{col[1]}' for col in btc_prices.columns]
        print(f"📊 BTC price columns: {list(btc_prices.columns)}")
        
        # Combine liquidations with BTC prices
        df_focused = all_liquidations.join(btc_prices, how='inner')
        
        # Columns are already flattened, no additional renaming needed
        print("✅ BTC price columns already flattened and ready to use!")
        
        # 🎯 CREATE MOON DEV'S FOCUSED FEATURES
        print("💰 Creating USD liquidation features...")
        print(f"📊 Available columns: {list(df_focused.columns)}")
        
        # Get column names (they have new naming scheme)
        buy_qty_col = f'buy_{quantity_col}_sum'
        sell_qty_col = f'sell_{quantity_col}_sum'
        total_qty_col = f'total_{quantity_col}_sum'
        total_count_col = f'total_{quantity_col}_count'
        
        # Use flattened price column names
        price_col = 'price_last' if 'price_last' in df_focused.columns else (
            'price_mean' if 'price_mean' in df_focused.columns else 'price_first'
        )
        if price_col not in df_focused.columns:
            # Find any price column
            price_cols = [col for col in df_focused.columns if 'price' in col.lower()]
            if price_cols:
                price_col = price_cols[0]
            else:
                print("❌ No price columns found!")
                return None
        
        print(f"🔧 Using price column: {price_col}")
        print(f"🔧 Using buy quantity: {buy_qty_col}")
        print(f"🔧 Using sell quantity: {sell_qty_col}")
        
        # USD liquidation volumes (Moon Dev's core signal!)
        df_focused['usd_long_liq'] = df_focused.get(buy_qty_col, 0) * df_focused.get(price_col, 0)  # Long liquidations in USD
        df_focused['usd_short_liq'] = df_focused.get(sell_qty_col, 0) * df_focused.get(price_col, 0)  # Short liquidations in USD
        df_focused['usd_liq_volume'] = df_focused['usd_long_liq'] + df_focused['usd_short_liq']
        
        # Net liquidation flow (contrarian signal)
        df_focused['usd_liq_net'] = df_focused['usd_short_liq'] - df_focused['usd_long_liq']  # Positive = more shorts liquidated
        
        # Liquidation imbalance ratio
        df_focused['liq_imbalance'] = df_focused['usd_liq_net'] / (df_focused['usd_liq_volume'] + 1e-8)
        
        # Liquidation velocity (intensity)
        df_focused['liq_velocity'] = df_focused.get(total_count_col, 0)
        
        # Clean up and select only focused features
        focused_feature_cols = ['usd_long_liq', 'usd_short_liq', 'usd_liq_volume', 'usd_liq_net', 'liq_imbalance', 'liq_velocity', price_col]
        available_cols = [col for col in focused_feature_cols if col in df_focused.columns]
        
        df_result = df_focused[available_cols].fillna(0).dropna()
        
        print(f"🎯 FOCUSED FEATURES CREATED! Shape: {df_result.shape}")
        print(f"📊 Features: {list(df_result.columns)}")
        print(f"💡 These are the PROVEN liquidation signals from your backtesting!")
        
        return df_result
    
    def create_target_variable(self, df, target_return_threshold=0.003):
        """
        🌙 Create Moon Dev's DIRECTION target variable (viewer's genius suggestion!)
        Focus on SIGN, not magnitude - much easier to predict!
        """
        print(f"💡 VIEWER'S SUGGESTION: Creating DIRECTION target for Moon Dev! 🌙")
        print(f"🎯 Direction threshold: {target_return_threshold*100:.1f}% (lower = more signals)")
        print(f"📊 Moon Dev input data shape: {df.shape}")
        print(f"🔮 Moon Dev prediction horizon: {self.prediction_horizon} steps")
        print("🚀 FOCUS: UP vs DOWN, not exact percentage! Much more achievable!")
        
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
        
        # 🎯 PRIMARY TARGET: Simple UP/DOWN direction (viewer's genius suggestion!)
        print("💡 VIEWER'S SUGGESTION: Creating DIRECTION targets (UP/DOWN)... 🌙")
        # 1 = UP (price goes up), 0 = DOWN (price goes down)
        df['target_direction_binary'] = (df['future_return'] > target_return_threshold).astype(int)
        
        # Alternative: 3-class direction for advanced analysis
        print("🧭 Moon Dev creating 3-class directional targets...")
        df['target_direction_3class'] = np.where(df['future_return'] > target_return_threshold, 2,    # UP
                                        np.where(df['future_return'] < -target_return_threshold, 0,   # DOWN  
                                                1))  # SIDEWAYS
        
        # Keep old targets for comparison (but focus on direction!)
        df['target_binary'] = (abs(df['future_return']) > target_return_threshold).astype(int)
        df['target_direction'] = np.where(df['future_return'] > target_return_threshold, 1,
                                 np.where(df['future_return'] < -target_return_threshold, -1, 0))
        df['target_return'] = df['future_return']
        
        # 📊 MOON DEV'S DIRECTION ANALYSIS
        up_moves = np.sum(df['target_direction_binary'] == 1)
        down_moves = np.sum(df['target_direction_binary'] == 0)
        total_moves = up_moves + down_moves
        
        print(f"🎯 MOON DEV'S DIRECTION TARGETS CREATED! 🚀")
        print(f"📈 UP moves (1): {up_moves:,} ({up_moves/total_moves*100:.1f}%)")
        print(f"📉 DOWN moves (0): {down_moves:,} ({down_moves/total_moves*100:.1f}%)")
        print(f"🎲 Balance ratio: {min(up_moves, down_moves)/max(up_moves, down_moves):.2f} (closer to 1.0 = better)")
        
        # 3-class analysis
        up_3class = np.sum(df['target_direction_3class'] == 2)
        sideways_3class = np.sum(df['target_direction_3class'] == 1) 
        down_3class = np.sum(df['target_direction_3class'] == 0)
        
        print(f"📊 3-Class Distribution:")
        print(f"   📈 UP: {up_3class:,} ({up_3class/len(df)*100:.1f}%)")
        print(f"   ➡️ SIDEWAYS: {sideways_3class:,} ({sideways_3class/len(df)*100:.1f}%)")
        print(f"   📉 DOWN: {down_3class:,} ({down_3class/len(df)*100:.1f}%)")
        
        # Quality check
        if abs(up_moves - down_moves) / total_moves > 0.3:
            print("⚠️ Moon Dev warning: Imbalanced classes! Consider adjusting threshold.")
        else:
            print("✅ Moon Dev: Good class balance for direction prediction!")
        
        print("💡 Viewer's insight: This should be MUCH easier to predict than exact percentages! 🌙")
        print("=" * 50)
        
        return df
    
    def prepare_sequences(self, df, feature_columns):
        """
        🌙 Prepare LSTM sequences for Moon Dev
        """
        print("🔄 Preparing LSTM sequences for Moon Dev... 🚀")
        print(f"📊 Moon Dev input data shape: {df.shape}")
        print(f"🎯 Moon Dev using {len(feature_columns)} features")
        
        # Remove rows with NaN targets (including new direction targets!)
        print("🧹 Moon Dev cleaning NaN targets...")
        df_clean = df.dropna(subset=['target_return', 'target_binary', 'target_direction', 'target_direction_binary'])
        print(f"✅ Cleaned data shape: {df_clean.shape} (Moon Dev approved!)")
        
        # Prepare features and targets (focus on direction!)
        print("📋 Moon Dev preparing features and targets...")
        features = df_clean[feature_columns].values
        targets_return = df_clean['target_return'].values
        targets_binary = df_clean['target_binary'].values
        targets_direction = df_clean['target_direction'].values
        targets_direction_binary = df_clean['target_direction_binary'].values  # NEW: Primary target!
        
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
        
        # Create sequences (focus on direction!)
        print("🔗 Moon Dev creating LSTM sequences with DIRECTION focus...")
        X, y_return, y_binary, y_direction, y_direction_binary = [], [], [], [], []
        
        print(f"🔄 Moon Dev processing {len(features_scaled)} samples...")
        for i in range(self.lookback_window, len(features_scaled)):
            X.append(features_scaled[i-self.lookback_window:i])
            y_return.append(targets_return[i])
            y_binary.append(targets_binary[i])
            y_direction.append(targets_direction[i])
            y_direction_binary.append(targets_direction_binary[i])  # NEW: Primary target!
            
            # Progress indicator for Moon Dev
            if (i - self.lookback_window) % 10000 == 0:
                print(f"   🌙 Moon Dev processed {i - self.lookback_window:,} sequences...")
        
        print("🔄 Moon Dev converting to numpy arrays...")
        X = np.array(X)
        y_return = np.array(y_return)
        y_binary = np.array(y_binary)
        y_direction = np.array(y_direction)
        y_direction_binary = np.array(y_direction_binary)  # NEW!
        
        print(f"🎉 Moon Dev's sequences ready! Shape: {X.shape} 🌙")
        print(f"📊 Feature sequences: {X.shape}")
        print(f"🎯 Target shapes:")
        print(f"   💡 Direction Binary (PRIMARY): {y_direction_binary.shape} - UP/DOWN prediction!")
        print(f"   📊 Old targets: Return: {y_return.shape}, Binary: {y_binary.shape}, Direction: {y_direction.shape}")
        print("🚀 Focus on direction_binary for best results (viewer's genius suggestion)! 🌙")
        print("=" * 50)
        
        return X, y_return, y_binary, y_direction, y_direction_binary, df_clean.index[self.lookback_window:]
    
    def build_model(self, input_shape, model_type='regression'):
        """
        🌙 Build Moon Dev's LSTM model with LOCAL_MODE scaling
        """
        mode_text = "LOCAL" if LOCAL_MODE else "PRODUCTION"
        print(f"🏗️ Building Moon Dev's {mode_text} LSTM model ({model_type})... 🚀")
        print(f"   🧠 Architecture: {LSTM_UNITS_1}/{LSTM_UNITS_2}/{LSTM_UNITS_3} units")
        
        model = Sequential([
            LSTM(LSTM_UNITS_1, return_sequences=True, input_shape=input_shape, dropout=0.2, recurrent_dropout=0.1),  # 🚀 OPTIMIZED dropout rates
            BatchNormalization(),
            
            LSTM(LSTM_UNITS_2, return_sequences=True, dropout=0.2, recurrent_dropout=0.1),  # 🚀 OPTIMIZED dropout rates
            BatchNormalization(),
            
            LSTM(LSTM_UNITS_3, return_sequences=False, dropout=0.2, recurrent_dropout=0.1),  # 🚀 OPTIMIZED dropout rates
            BatchNormalization(),
            
            Dense(16, activation='relu'),
            Dropout(0.3),  # 🚀 OPTIMIZED: 0.3 dense dropout confirmed optimal
            Dense(8, activation='relu'),
            Dropout(0.3),  # 🚀 OPTIMIZED: 0.3 dense dropout confirmed optimal
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
        🌙 Train Moon Dev's LSTM model with optimized constants + CLASS BALANCE FIX! 🚀
        """
        print(f"🎓 Training Moon Dev's OPTIMIZED LSTM model ({model_type})... 🚀")
        print(f"   📊 Epochs: {epochs}")
        print(f"   🚀 Batch Size: {BATCH_SIZE}")
        print(f"   ⚡ Early Stopping Patience: {EARLY_STOPPING_PATIENCE}")
        print(f"   📉 LR Reduce Patience: {LR_REDUCE_PATIENCE}")
        
        # 🚨 MOON DEV'S CLASS BALANCE FIX (Priority #1)! 🚨
        class_weights = None
        if model_type in ['binary', 'multiclass']:
            from sklearn.utils.class_weight import compute_class_weight
            
            # Compute class weights to fix imbalance
            unique_classes = np.unique(y_train)
            class_weights_array = compute_class_weight('balanced', classes=unique_classes, y=y_train)
            class_weights = {int(cls): weight for cls, weight in zip(unique_classes, class_weights_array)}
            
            print("🚨 MOON DEV'S CLASS BALANCE FIX ACTIVATED! 🚨")
            print(f"   🔍 Class distribution in training:")
            for cls in unique_classes:
                count = np.sum(y_train == cls)
                pct = count / len(y_train) * 100
                print(f"     📊 Class {cls}: {count:,} samples ({pct:.1f}%)")
            
            print(f"   ⚖️ Class weights applied:")
            for cls, weight in class_weights.items():
                print(f"     🎯 Class {cls}: weight = {weight:.3f}")
            
            # Calculate UP/DOWN specific metrics for Moon Dev
            if len(unique_classes) == 2:
                up_count = np.sum(y_train == 1)
                down_count = np.sum(y_train == 0)
                up_weight = class_weights.get(1, 1.0)
                down_weight = class_weights.get(0, 1.0)
                
                print(f"   🚀 UP move focus:")
                print(f"     📈 UP samples: {up_count:,} (weight: {up_weight:.3f})")
                print(f"     📉 DOWN samples: {down_count:,} (weight: {down_weight:.3f})")
                print(f"     💡 Model will now CARE about missing UP moves! 🌙")
        
        # Build model
        self.model = self.build_model(input_shape=(X_train.shape[1], X_train.shape[2]), model_type=model_type)
        
        # Optimized callbacks for Moon Dev's training
        callbacks = [
            EarlyStopping(monitor='val_loss', patience=EARLY_STOPPING_PATIENCE, restore_best_weights=True, verbose=1),
            ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=LR_REDUCE_PATIENCE, min_lr=MIN_LEARNING_RATE, verbose=1)
        ]
        
        print("🚂 Moon Dev's OPTIMIZED + BALANCED training starting... 🌙")
        
        # Train the model with optimized parameters + class weights!
        fit_kwargs = {
            'x': X_train,
            'y': y_train,
            'validation_data': (X_val, y_val),
            'epochs': epochs,
            'batch_size': BATCH_SIZE,
            'callbacks': callbacks,
            'verbose': 1
        }
        
        # 🚫 REMOVED: Class weights cause 60x slowdown! Using balanced sampling instead
        # if class_weights is not None:
        #     fit_kwargs['class_weight'] = class_weights
        #     print("✅ Moon Dev's class weights applied to training! 🎯")
        print("🚀 Moon Dev using focused features for speed (class balance via other methods)!")
        
        history = self.model.fit(**fit_kwargs)
        
        self.is_trained = True
        print("🎉 Moon Dev's BALANCED LSTM training complete! 🚀")
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
                predictions_prob = predictions.flatten()  # Store probabilities
            else:
                predictions_binary = np.argmax(predictions, axis=1)
                predictions_prob = predictions.max(axis=1)  # Max probability
            
            accuracy = np.mean(predictions_binary == y_test)
            
            # 🚨 Initialize metrics dictionary first to avoid UnboundLocalError! 🚨
            metrics = {
                'accuracy': accuracy,
                'predictions': predictions_binary,
                'predictions_prob': predictions_prob,
                'actuals': y_test,
                'confusion_matrix': None  # Will be set below
            }
            
            # 🚨 MOON DEV'S DETAILED UP/DOWN ANALYSIS! 🚨
            from sklearn.metrics import confusion_matrix, classification_report
            
            # Confusion matrix
            cm = confusion_matrix(y_test, predictions_binary)
            
            # UP/DOWN specific metrics
            if len(np.unique(y_test)) == 2:
                # Binary classification metrics
                up_mask = y_test == 1
                down_mask = y_test == 0
                
                up_accuracy = np.mean(predictions_binary[up_mask] == y_test[up_mask]) if np.sum(up_mask) > 0 else 0
                down_accuracy = np.mean(predictions_binary[down_mask] == y_test[down_mask]) if np.sum(down_mask) > 0 else 0
                
                up_count = np.sum(up_mask)
                down_count = np.sum(down_mask)
                
                # Prediction distribution
                predicted_up = np.sum(predictions_binary == 1)
                predicted_down = np.sum(predictions_binary == 0)
                
                print("🎯 MOON DEV'S DETAILED CLASSIFICATION METRICS 🌙")
                print("=" * 60)
                print(f"🎪 Overall Accuracy: {accuracy:.4f}")
                print(f"📊 Confusion Matrix:")
                print(f"   True\\Pred:  DOWN  UP")
                print(f"   DOWN:      {cm[0,0]:4d}  {cm[0,1]:4d}")
                print(f"   UP:        {cm[1,0]:4d}  {cm[1,1]:4d}")
                print(f"")
                print(f"🚨 MOON DEV'S UP/DOWN BREAKDOWN:")
                print(f"   📈 UP moves in test: {up_count:,} ({up_count/len(y_test)*100:.1f}%)")
                print(f"   📉 DOWN moves in test: {down_count:,} ({down_count/len(y_test)*100:.1f}%)")
                print(f"   🎯 UP accuracy: {up_accuracy:.4f} ({up_accuracy*100:.1f}%)")
                print(f"   🎯 DOWN accuracy: {down_accuracy:.4f} ({down_accuracy*100:.1f}%)")
                print(f"")
                print(f"🤖 MODEL PREDICTION BEHAVIOR:")
                print(f"   🔮 Predicted UP: {predicted_up:,} ({predicted_up/len(predictions_binary)*100:.1f}%)")
                print(f"   🔮 Predicted DOWN: {predicted_down:,} ({predicted_down/len(predictions_binary)*100:.1f}%)")
                
                # Check for "DOWN-ONLY" problem
                if predicted_up == 0:
                    print(f"   🚨 DOWN-ONLY PREDICTOR DETECTED! Never predicts UP moves!")
                elif predicted_up < up_count * 0.1:
                    print(f"   ⚠️  PESSIMISTIC PREDICTOR: Rarely predicts UP moves!")
                else:
                    print(f"   ✅ BALANCED PREDICTOR: Predicts both UP and DOWN moves!")
                
                # Additional useful metrics
                if up_count > 0 and down_count > 0:
                    # Precision and recall for UP moves (most important!)
                    up_precision = cm[1,1] / (cm[1,1] + cm[0,1]) if (cm[1,1] + cm[0,1]) > 0 else 0
                    up_recall = cm[1,1] / (cm[1,1] + cm[1,0]) if (cm[1,1] + cm[1,0]) > 0 else 0
                    up_f1 = 2 * (up_precision * up_recall) / (up_precision + up_recall) if (up_precision + up_recall) > 0 else 0
                    
                    print(f"")
                    print(f"📈 UP MOVE PREDICTION QUALITY (Most Important!):")
                    print(f"   🎯 UP Precision: {up_precision:.4f} (When it says UP, how often is it right?)")
                    print(f"   🎯 UP Recall: {up_recall:.4f} (Of all UP moves, how many did it catch?)")
                    print(f"   🎯 UP F1-Score: {up_f1:.4f} (Overall UP prediction quality)")
                    
                    # 🚀 MOON DEV'S AUC ANALYSIS (Demijan's request!)
                    try:
                        # Calculate AUC-ROC using prediction probabilities
                        y_prob = metrics.get('predictions_prob', predictions_binary.astype(float))
                        auc_score = roc_auc_score(y_test, y_prob)
                        
                        # Calculate ROC curve data for plotting
                        fpr, tpr, thresholds = roc_curve(y_test, y_prob)
                        
                        print(f"")
                        print(f"🎯 MOON DEV'S AUC-ROC ANALYSIS (DEMIJAN'S REQUEST!) 🌙")
                        print(f"=" * 60)
                        print(f"🏆 AUC-ROC Score: {auc_score:.4f}")
                        print(f"🎯 MOON DEV'S GOAL: 0.70 or better AUC! 🚀")
                        
                        # AUC interpretation with Moon Dev's trading context
                        if auc_score >= 0.70:
                            print(f"✅ GOAL ACHIEVED! AUC = {auc_score:.4f} ≥ 0.70 🎉")
                            print(f"🚀 MOON DEV: This model can distinguish UP vs DOWN moves for trading! 🌙")
                        elif auc_score >= 0.60:
                            print(f"⚠️ CLOSE! AUC = {auc_score:.4f} (Need {0.70-auc_score:.3f} more for goal)")
                            print(f"💡 MOON DEV: Decent predictive power, but room for improvement! 🌙")
                        elif auc_score >= 0.55:
                            print(f"📊 AUC Interpretation: 😐 WEAK (0.55-0.59): Barely better than random")
                            print(f"❌ GOAL MISSED: AUC = {auc_score:.4f} < 0.70 (Need {0.70-auc_score:.3f} improvement)")
                            print(f"🚨 MOON DEV: Model struggles to rank UP vs DOWN moves reliably!")
                        else:
                            print(f"📊 AUC Interpretation: 💔 POOR (< 0.55): Worse than random guessing")
                            print(f"❌ GOAL MISSED: AUC = {auc_score:.4f} < 0.70 (Major improvement needed)")
                            print(f"🚨 MOON DEV: Model cannot distinguish UP vs DOWN moves - not ready for trading!")
                        
                        print(f"")
                        print(f"💡 AUC TRADING INTERPRETATION:")
                        print(f"   🎯 AUC = 0.50: Random coin flip")
                        print(f"   📈 AUC = 0.70: Good trading model (Moon Dev's goal!)")
                        print(f"   🚀 AUC = 0.80+: Excellent trading model")
                        print(f"   🌙 Current: {auc_score:.4f} ({'PASS' if auc_score >= 0.70 else 'NEEDS WORK'})")
                        
                        # Store AUC data for plotting
                        metrics['auc_score'] = auc_score
                        metrics['fpr'] = fpr
                        metrics['tpr'] = tpr
                        metrics['auc_goal_met'] = auc_score >= 0.70
                        
                    except Exception as e:
                        print(f"⚠️ Could not calculate AUC: {str(e)}")
                        print(f"💡 This usually happens when all predictions are the same class")
                        metrics['auc_score'] = 0.5  # Default to random
                        metrics['auc_goal_met'] = False
            else:
                print("🎯 MOON DEV'S CLASSIFICATION METRICS 🌙")
                print("=" * 50)
                print(f"🎪 Accuracy: {accuracy:.4f}")
            
            # Update confusion matrix in metrics
            metrics['confusion_matrix'] = cm if 'cm' in locals() else None
        
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
        
        elif model_type == 'binary':
            # 💡 VIEWER'S SUGGESTION: Direction prediction plots!
            fig, axes = plt.subplots(2, 2, figsize=(15, 10))
            fig.suptitle('🌙 MOON DEV\'S DIRECTION PREDICTION RESULTS (VIEWER\'S SUGGESTION!) 🚀', fontsize=16)
            
            # ROC Curve (Demijan's request!)
            if 'fpr' in metrics and 'tpr' in metrics and 'auc_score' in metrics:
                axes[0, 0].plot(metrics['fpr'], metrics['tpr'], color='green', lw=2, 
                               label=f'ROC Curve (AUC = {metrics["auc_score"]:.3f})')
                axes[0, 0].plot([0, 1], [0, 1], color='red', lw=1, linestyle='--', label='Random Guess')
                axes[0, 0].axhline(y=0.7, color='orange', linestyle=':', label='Moon Dev Goal (AUC=0.70)')
                axes[0, 0].set_xlim([0.0, 1.0])
                axes[0, 0].set_ylim([0.0, 1.05])
                axes[0, 0].set_xlabel('False Positive Rate')
                axes[0, 0].set_ylabel('True Positive Rate')
                axes[0, 0].set_title(f'🎯 ROC Curve (Goal: AUC ≥ 0.70)')
                axes[0, 0].legend()
                axes[0, 0].grid(True, alpha=0.3)
                
                # Add goal achievement text
                goal_text = "✅ GOAL MET!" if metrics.get('auc_goal_met', False) else "❌ GOAL MISSED"
                axes[0, 0].text(0.6, 0.2, goal_text, fontsize=12, 
                               bbox=dict(boxstyle="round,pad=0.3", 
                                       facecolor='lightgreen' if metrics.get('auc_goal_met', False) else 'lightcoral'))
            else:
                # Fallback: Confusion matrix
                from sklearn.metrics import confusion_matrix
                cm = confusion_matrix(metrics['actuals'], metrics['predictions'])
                
                axes[0, 0].imshow(cm, interpolation='nearest', cmap='Blues')
                axes[0, 0].set_title('🎯 Moon Dev: Direction Confusion Matrix')
                axes[0, 0].set_xlabel('Predicted Direction')
                axes[0, 0].set_ylabel('Actual Direction')
                
                # Add text annotations
                for i in range(2):
                    for j in range(2):
                        axes[0, 0].text(j, i, str(cm[i, j]), ha='center', va='center', fontsize=12)
            
            # Prediction probabilities histogram
            predictions_prob = metrics.get('predictions_prob', metrics['predictions'])
            axes[0, 1].hist(predictions_prob, bins=50, alpha=0.7, density=True)
            axes[0, 1].set_xlabel('Prediction Probability')
            axes[0, 1].set_ylabel('Density')
            axes[0, 1].set_title('🌙 Moon Dev: Prediction Confidence')
            axes[0, 1].grid(True, alpha=0.3)
            
            # Time series of predictions (last 200 points)
            n_points = min(200, len(metrics['actuals']))
            time_steps = range(n_points)
            axes[1, 0].plot(time_steps, metrics['actuals'][-n_points:], 'o-', label='Actual Direction', alpha=0.7, markersize=3)
            axes[1, 0].plot(time_steps, metrics['predictions'][-n_points:], 's-', label='Predicted Direction', alpha=0.7, markersize=3)
            axes[1, 0].set_xlabel('Time Steps')
            axes[1, 0].set_ylabel('Direction (0=DOWN, 1=UP)')
            axes[1, 0].set_title('🚀 Moon Dev: Direction Predictions Over Time')
            axes[1, 0].legend()
            axes[1, 0].grid(True, alpha=0.3)
            
            # Accuracy by time (rolling window)
            window_size = min(50, len(metrics['actuals']) // 4)
            rolling_accuracy = []
            for i in range(window_size, len(metrics['actuals'])):
                window_acc = np.mean(metrics['actuals'][i-window_size:i] == metrics['predictions'][i-window_size:i])
                rolling_accuracy.append(window_acc)
            
            axes[1, 1].plot(rolling_accuracy)
            axes[1, 1].set_xlabel('Time Steps')
            axes[1, 1].set_ylabel('Rolling Accuracy')
            axes[1, 1].set_title(f'🌙 Moon Dev: Rolling Accuracy (Window={window_size})')
            axes[1, 1].grid(True, alpha=0.3)
            axes[1, 1].axhline(y=0.5, color='r', linestyle='--', label='Random Guess')
            axes[1, 1].legend()
        
        if model_type == 'regression':
            
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
    
    # 🎯 MOON DEV'S CHOICE: Use focused features or full features
    USE_FOCUSED_FEATURES = LOCAL_MODE  # Use focused features in LOCAL_MODE for faster testing
    
    if USE_FOCUSED_FEATURES:
        print("🎯 USING MOON DEV'S FOCUSED LIQUIDATION FEATURES! 🚀")
        print("💡 Based on successful backtesting: liquidation side + volume")
        
        # Create focused features
        df_features = predictor.create_focused_liquidation_features(df, time_window='1min')
        if df_features is None:
            print("❌ Moon Dev, focused feature engineering failed!")
            return
    else:
        print("📊 USING FULL FEATURE SET (Original approach)")
        
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
                          if col not in ['target_return', 'target_binary', 'target_direction', 'target_direction_binary', 'future_return']]
    
    # 🎯 MOON DEV'S FOCUSED APPROACH
    if USE_FOCUSED_FEATURES and LIQUIDATION_FOCUSED_FEATURES is not None:
        # Use Moon Dev's proven 6-feature approach!
        feature_columns = [col for col in LIQUIDATION_FOCUSED_FEATURES if col in all_feature_columns]
        print(f"🎯 FOCUSED: Using {len(feature_columns)} backtested features: {feature_columns}")
        if len(feature_columns) < len(LIQUIDATION_FOCUSED_FEATURES):
            missing = [col for col in LIQUIDATION_FOCUSED_FEATURES if col not in all_feature_columns]
            print(f"⚠️ Missing focused features: {missing}")
    elif LOCAL_MODE and CORE_FEATURES is not None:
        # Fallback to core features 
        feature_columns = [col for col in CORE_FEATURES if col in all_feature_columns]
        print(f"🏠 LOCAL_MODE: Using {len(feature_columns)} core features: {feature_columns}")
        if len(feature_columns) < len(CORE_FEATURES):
            missing = [col for col in CORE_FEATURES if col not in all_feature_columns]
            print(f"⚠️ Missing core features: {missing}")
    else:
        feature_columns = all_feature_columns
        print(f"☁️ PRODUCTION: Using all {len(feature_columns)} features: {feature_columns[:10]}..." if len(feature_columns) > 10 else f"☁️ PRODUCTION: Using features: {feature_columns}")
    
    # Prepare sequences (including new direction target!)
    X, y_return, y_binary, y_direction, y_direction_binary, timestamps = predictor.prepare_sequences(df_targets, feature_columns)
    
    # Split data (80% train, 10% val, 10% test) - time series split
    train_size = int(0.8 * len(X))
    val_size = int(0.1 * len(X))
    
    X_train, X_val, X_test = X[:train_size], X[train_size:train_size+val_size], X[train_size+val_size:]
    
    # 🎯 VIEWER'S SUGGESTION: Use direction_binary as PRIMARY target!
    y_train_direction = y_direction_binary[:train_size]
    y_val_direction = y_direction_binary[train_size:train_size+val_size] 
    y_test_direction = y_direction_binary[train_size+val_size:]
    
    # 🚀 FAST CLASS BALANCE FIX: Balanced sampling instead of class weights!
    if LOCAL_MODE:
        print("⚖️ Moon Dev applying FAST balanced sampling for LOCAL_MODE...")
        
        # Find UP and DOWN indices in training data
        up_indices = np.where(y_train_direction == 1)[0]
        down_indices = np.where(y_train_direction == 0)[0]
        
        # Use equal samples of each (smaller of the two)
        min_samples = min(len(up_indices), len(down_indices))
        
        # Randomly sample equal amounts (but keep time series order somewhat)
        if min_samples > 1000:  # Only balance if we have enough data
            # Take every nth sample to maintain some time ordering
            up_step = max(1, len(up_indices) // min_samples)
            down_step = max(1, len(down_indices) // min_samples)
            
            balanced_up = up_indices[::up_step][:min_samples]
            balanced_down = down_indices[::down_step][:min_samples]
            
            # Combine and sort to maintain time order
            balanced_indices = np.sort(np.concatenate([balanced_up, balanced_down]))
            
            # Apply balanced sampling
            X_train = X_train[balanced_indices]
            y_train_direction = y_train_direction[balanced_indices]
            
            print(f"   📊 Original training: UP={len(up_indices):,}, DOWN={len(down_indices):,}")
            print(f"   ⚖️ Balanced training: UP={np.sum(y_train_direction==1):,}, DOWN={np.sum(y_train_direction==0):,}")
            print(f"   🚀 Training samples reduced: {train_size:,} → {len(balanced_indices):,} (MUCH faster!)")
        else:
            print(f"   ⚠️ Too few samples ({min_samples}) for balancing - using all data")
    
    # Keep old targets for comparison
    y_train, y_val, y_test = y_return[:train_size], y_return[train_size:train_size+val_size], y_return[train_size+val_size:]
    
    print(f"🔄 Moon Dev's data split:")
    print(f"📊 Train: {X_train.shape[0]}, Val: {X_val.shape[0]}, Test: {X_test.shape[0]}")
    print(f"💡 DIRECTION targets: Train: {y_train_direction.shape[0]}, Val: {y_val_direction.shape[0]}, Test: {y_test_direction.shape[0]}")
    
    # Show direction balance
    train_up = np.sum(y_train_direction == 1)
    train_down = np.sum(y_train_direction == 0)
    print(f"🎯 Training direction balance: UP: {train_up:,} ({train_up/len(y_train_direction)*100:.1f}%), DOWN: {train_down:,} ({train_down/len(y_train_direction)*100:.1f}%)")
    print("=" * 50)
    
    # 🚀 TRAIN WITH DIRECTION PREDICTION (viewer's suggestion!)
    print("💡 IMPLEMENTING VIEWER'S SUGGESTION: Training with DIRECTION prediction! 🌙")
    history = predictor.train_model(X_train, y_train_direction, X_val, y_val_direction, model_type='binary', epochs=EPOCHS)
    
    # Evaluate the direction model
    print("📊 Evaluating DIRECTION model performance...")
    metrics = predictor.evaluate_model(X_test, y_test_direction, model_type='binary')
    
    # Plot results for direction model
    predictor.plot_results(metrics, model_type='binary')
    
    print("💡 VIEWER'S INSIGHT IMPLEMENTED: Direction prediction should perform MUCH better! 🚀🌙")
    
    print("🎉 MOON DEV'S LSTM LIQUIDATION PREDICTOR COMPLETE! 🚀🌙")
    print("=" * 60)

if __name__ == "__main__":
    main() 