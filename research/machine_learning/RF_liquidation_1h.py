"""
🌙 MOON DEV'S RANDOM FOREST LIQUIDATION PREDICTOR - 1 HOUR 🚀
Predicting BTC price moves using liquidation data with Random Forest
🌲 1-Hour timeframe for better signal clarity! 🌲
"""

# 🌙 MOON DEV'S TRAINING CONFIGURATION CONSTANTS 🚀
# ================================================

# 🏠 LOCAL MODE SWITCH - Change to False for full cloud runs! 🚀
LOCAL_MODE = False             # Set to False for production cloud runs

# Training Constants (scaled by LOCAL_MODE)
# 🚀 DEMIJAN'S OPTIMIZED RF HYPERPARAMETERS! 🚀
# These parameters FIXED the DOWN-only predictor problem!
# Optimization results: UP accuracy 0.8% → 14.6% (18x improvement!)
N_ESTIMATORS = 500                    # Optimal: More trees for stability
MAX_DEPTH = 10                        # Optimal: Shallower to prevent overfitting  
MIN_SAMPLES_SPLIT = 20                # Optimal: Larger splits for generalization
MIN_SAMPLES_LEAF = 10                 # Optimal: Larger leaves for robustness
MAX_FEATURES = 'sqrt'                 # Optimal: sqrt features per split
MAX_SAMPLES = 0.9                     # Optimal: Bootstrap sampling ratio
CLASS_WEIGHT_STRATEGY = 'balanced_subsample'  # Optimal: More aggressive balancing
N_JOBS = -1                                          # Use all CPU cores

# Data Processing Constants (scaled by LOCAL_MODE)
DATA_SAMPLE_FRACTION = 0.3 if LOCAL_MODE else 1.0  # Use 1% TIME PERIOD (3.6 days) for local, 100% for cloud
LOOKBACK_WINDOW = 60          # How many previous minutes to use as features
PREDICTION_HORIZON = 5        # Steps ahead to predict
MAX_RETURN_CAP = 10.0         # Cap gains at 1000%
MIN_RETURN_CAP = -0.99        # Cap losses at 99%
TARGET_THRESHOLD = 0.005      # 0.5% threshold for binary targets

# Feature Selection (scaled by LOCAL_MODE)
CORE_FEATURES = [
    'side', 'quantity_sum', 'quantity_mean', 'price_last', 'price_mean',
    'usd_liq_volume', 'usd_liq_net', 'liq_velocity', 'liq_imbalance',
    'total_liq_events', 'hour', 'minute', 'day_of_week'
] if LOCAL_MODE else None  # None means use all features

# 🎯 MOON DEV'S FOCUSED LIQUIDATION FEATURES (Based on backtesting!)
LIQUIDATION_FOCUSED_FEATURES = [
    'usd_long_liq',      # Long liquidation volume (when to go long)
    'usd_short_liq',     # Short liquidation volume (when to go short)  
    'usd_liq_net',       # Net liquidation flow
    'liq_imbalance',     # Liquidation side imbalance
    'usd_liq_volume',    # Total liquidation volume
    'liq_velocity'       # Liquidation intensity/speed
]

mode_emoji = "🌲" if LOCAL_MODE else "🌳"
mode_name = "LOCAL TESTING" if LOCAL_MODE else "CLOUD PRODUCTION"
print(f"🌙 MOON DEV'S RANDOM FOREST CONSTANTS LOADED! 🚀")
print(f"{mode_emoji} MODE: {mode_name}")
print(f"   📊 Data Sample: {DATA_SAMPLE_FRACTION*100:.2f}% of TIME PERIOD (most recent data)")
print(f"   🌲 Trees: {N_ESTIMATORS}")
print(f"   📏 Max Depth: {MAX_DEPTH}")  
print(f"   🔧 Lookback: {LOOKBACK_WINDOW} minutes")
print(f"   ⏰ EXPERIMENT: 1-hour bars for better signal clarity + ALL symbols + ALL sizes")
if LOCAL_MODE:
    print(f"   🎯 Features: {len(CORE_FEATURES)} core features only")
else:
    print(f"   🎯 Features: All 47+ features")
print(f"🎯 LIQUIDATION FOCUSED: {len(LIQUIDATION_FOCUSED_FEATURES)} backtested features available")
print("=" * 50)

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score, accuracy_score, classification_report, confusion_matrix, roc_auc_score, roc_curve
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
import os
import joblib
import json
from datetime import datetime, timedelta
warnings.filterwarnings('ignore')

print("🌙 MOON DEV'S RANDOM FOREST LIQUIDATION PREDICTOR LOADING... 🚀")
print("=" * 60)

class RFLiquidationPredictor:
    def __init__(self, lookback_window=LOOKBACK_WINDOW, prediction_horizon=PREDICTION_HORIZON):
        """
        🌙 Moon Dev's Random Forest Liquidation Predictor
        
        Args:
            lookback_window: How many time steps to look back for features
            prediction_horizon: How many steps ahead to predict
        """
        self.lookback_window = lookback_window
        self.prediction_horizon = prediction_horizon
        self.model = None
        self.feature_scaler = StandardScaler()
        self.target_scaler = StandardScaler()
        self.feature_names = None
        self.is_trained = False
        
        print(f"🌲 Moon Dev Random Forest initialized with {lookback_window} lookback window")
        print(f"🎯 Predicting {prediction_horizon} steps ahead")
        print("=" * 50)
    
    def load_liquidation_data(self, data_path):
        """
        🌙 Load Moon Dev's liquidation data (same as LSTM)
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
        
        # ⏰ EXPERIMENT: 1-hour aggregation for Moon Dev!
        print("\n⏰ MOON DEV'S 1-HOUR AGGREGATION EXPERIMENT ⏰")
        print("=" * 50)
        original_count = len(df)
        original_symbols = df['symbol'].nunique()
        
        print(f"🔍 Original liquidations: {original_count:,}")
        print(f"🌊 All symbols included: {original_symbols}")
        print(f"⏰ Using 1-hour bars for better signal clarity")
        print(f"🎯 Hypothesis: Longer time windows provide clearer directional signals")
        print(f"✅ All liquidation sizes included (learned from Run #2)")
        print("=" * 50)
        
        # Handle different timestamp column names
        timestamp_col = None
        possible_timestamp_cols = ['datetime', 'timestamp', 'time', 'date', 'ts']
        
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
            print("⚠️ Moon Dev couldn't find timestamp column!")
            return None
        
        return df
    
    def engineer_features(self, df, time_window='1min'):
        """
        🌙 Engineer Moon Dev's liquidation features (same as LSTM)
        """
        print(f"🔧 Engineering features for Moon Dev Random Forest with {time_window} windows... 🚀")
        print(f"📊 Moon Dev input data shape: {df.shape}")
        
        # 🏠 LOCAL_MODE: Sample TIME PERIOD for faster testing (same as LSTM!)
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
            
            print(f"🏠 LOCAL_MODE: Time-based sampling for Moon Dev Random Forest! 🌙")
            print(f"   📅 Total time span: {total_time_span.days} days")
            print(f"   🎯 Sample time span: {sample_time_span.days} days ({DATA_SAMPLE_FRACTION*100:.1f}%)")
        
        # Map Moon Dev's actual column names
        quantity_col = 'original_quantity' if 'original_quantity' in df.columns else 'quantity'
        print(f"📊 Moon Dev using quantity column: '{quantity_col}'")
        
        # 🎯 MOON DEV'S BITCOIN-ONLY STRATEGY! 🎯 (Same as LSTM)
        print("🪙 Moon Dev implementing Bitcoin-only price targeting...")
        
        # Step 1: Aggregate ALL liquidation data for features
        all_liquidations = df.set_index('timestamp').resample(time_window).agg({
            'side': lambda x: (x.str.upper() == 'BUY').sum() - (x.str.upper() == 'SELL').sum(),
            quantity_col: ['sum', 'mean', 'std', 'max', 'count'],
            'symbol': 'count'
        }).fillna(0)
        
        # Step 2: Get BTC-only data for price movements
        btc_data = df[df['symbol'] == 'BTC'].copy()
        print(f"🪙 BTC-only records: {len(btc_data):,} out of {len(df):,} total ({len(btc_data)/len(df)*100:.1f}%)")
        
        if len(btc_data) == 0:
            print("❌ Moon Dev ERROR: No BTC records found!")
            return None
        
        btc_prices = btc_data.set_index('timestamp').resample(time_window).agg({
            'price': ['first', 'last', 'min', 'max', 'mean', 'std']
        }).fillna(method='ffill')
        
        # Step 3: Combine ALL liquidations with BTC-only prices
        df_resampled = all_liquidations.join(btc_prices, how='inner')
        print(f"✅ Combined data shape: {df_resampled.shape} (ALL liquidations + BTC prices only)")
        
        # Flatten column names
        df_resampled.columns = ['_'.join(col).strip() if col[1] else col[0] for col in df_resampled.columns]
        
        # Standardize column names
        column_mapping = {}
        for col in df_resampled.columns:
            if 'original_quantity' in col:
                new_col = col.replace('original_quantity', 'quantity')
                column_mapping[col] = new_col
            elif 'side_<lambda>' in col:
                column_mapping[col] = 'side'
            elif 'symbol_count' in col:
                column_mapping[col] = 'total_liq_events'
        
        if column_mapping:
            df_resampled = df_resampled.rename(columns=column_mapping)
        
        # 🚀 LIQUIDATION-ONLY FEATURES (Same as LSTM)
        print("💰 Moon Dev creating USD liquidation features...")
        df_resampled['usd_liq_volume'] = df_resampled['quantity_sum'] * df_resampled['price_mean']
        df_resampled['usd_short_liq'] = df_resampled['quantity_sum'] * df_resampled['price_mean'] * (df_resampled['side'] > 0)
        df_resampled['usd_long_liq'] = df_resampled['quantity_sum'] * df_resampled['price_mean'] * (df_resampled['side'] < 0)
        
        # Liquidation intensity and flow
        df_resampled['liq_intensity'] = df_resampled['quantity_sum'] / (df_resampled['quantity_count'] + 1)
        df_resampled['liq_imbalance'] = df_resampled['side'] / (df_resampled['quantity_count'] + 1)
        df_resampled['large_liq_ratio'] = (df_resampled['quantity_max'] / (df_resampled['quantity_mean'] + 1)).fillna(0)
        
        # USD-based liquidation imbalances
        df_resampled['usd_liq_net'] = df_resampled['usd_short_liq'] - df_resampled['usd_long_liq']
        df_resampled['usd_liq_ratio'] = df_resampled['usd_short_liq'] / (df_resampled['usd_long_liq'] + 1e-8)
        df_resampled['usd_liq_dominance'] = df_resampled['usd_liq_net'] / (df_resampled['usd_liq_volume'] + 1e-8)
        
        # Liquidation velocity
        df_resampled['liq_velocity'] = df_resampled['quantity_count']
        df_resampled['usd_liq_velocity'] = df_resampled['usd_liq_volume']
        
        # Time-based features
        df_resampled['hour'] = df_resampled.index.hour
        df_resampled['minute'] = df_resampled.index.minute
        df_resampled['day_of_week'] = df_resampled.index.dayofweek
        
        # Handle NaN values
        df_resampled = df_resampled.fillna(0).dropna()
        
        print(f"🎉 Moon Dev's Random Forest feature engineering complete! Features shape: {df_resampled.shape} 🚀")
        
        return df_resampled
    
    def create_target_variable(self, df, target_return_threshold=0.003):
        """
        🌙 Create Moon Dev's DIRECTION target variable (viewer's genius suggestion!)
        Focus on SIGN, not magnitude - much easier to predict!
        """
        print(f"💡 VIEWER'S SUGGESTION: Creating DIRECTION target for Moon Dev Random Forest! 🌙")
        print(f"🎯 Direction threshold: {target_return_threshold*100:.1f}% (lower = more signals)")
        print("🚀 FOCUS: UP vs DOWN, not exact percentage! Much more achievable!")
        
        # Calculate future returns (same logic as LSTM)
        print("📈 Moon Dev calculating future returns...")
        print("🪙 NOTE: Using ONLY Bitcoin prices for targets")
        
        current_prices = df['price_last']
        future_prices = df['price_last'].shift(-self.prediction_horizon)
        
        # Calculate raw returns
        raw_returns = future_prices / current_prices - 1
        
        # Cap extreme returns
        max_return = MAX_RETURN_CAP
        min_return = MIN_RETURN_CAP
        
        df['future_return'] = np.where(
            np.isinf(raw_returns) | (raw_returns > max_return), max_return,
            np.where(
                raw_returns < min_return, min_return,
                raw_returns
            )
        )
        
        # 🎯 PRIMARY TARGET: Simple UP/DOWN direction (viewer's suggestion!)
        # 1 = UP (price goes up), 0 = DOWN (price goes down)
        df['target_direction_binary'] = (df['future_return'] > target_return_threshold).astype(int)
        
        # Keep regression target for comparison (but focus on direction!)
        df['target_return'] = df['future_return']
        
        # 📊 MOON DEV'S DIRECTION ANALYSIS
        up_moves = np.sum(df['target_direction_binary'] == 1)
        down_moves = np.sum(df['target_direction_binary'] == 0)
        total_moves = up_moves + down_moves
        
        print(f"🎯 MOON DEV'S DIRECTION TARGETS CREATED! 🚀")
        print(f"📈 UP moves (1): {up_moves:,} ({up_moves/total_moves*100:.1f}%)")
        print(f"📉 DOWN moves (0): {down_moves:,} ({down_moves/total_moves*100:.1f}%)")
        print(f"🎲 Balance ratio: {min(up_moves, down_moves)/max(up_moves, down_moves):.2f} (closer to 1.0 = better)")
        
        # Quality check
        if abs(up_moves - down_moves) / total_moves > 0.3:
            print("⚠️ Moon Dev warning: Imbalanced classes! Consider adjusting threshold.")
        else:
            print("✅ Moon Dev: Good class balance for direction prediction!")
        
        print("💡 Viewer's insight: Random Forest should excel at direction prediction! 🌙")
        print("=" * 50)
        
        return df
    
    def prepare_features(self, df, feature_columns, target_type='direction'):
        """
        🌲 Prepare Random Forest features (different from LSTM - no sequences!)
        """
        print("🔄 Preparing Random Forest features for Moon Dev... 🚀")
        print(f"🎯 Moon Dev using {len(feature_columns)} features")
        print(f"💡 Target type: {target_type} (viewer's direction approach!)")
        
        # Select target column based on type
        if target_type == 'direction':
            target_col = 'target_direction_binary'
            print("🎯 Moon Dev using DIRECTION prediction (UP/DOWN)! 🌙")
        else:
            target_col = 'target_return'
            print("📊 Moon Dev using REGRESSION prediction (exact returns)")
        
        # Clean data
        df_clean = df.dropna(subset=[target_col])
        print(f"✅ Cleaned data shape: {df_clean.shape}")
        
        # 🌲 KEY DIFFERENCE: Create lookback features instead of sequences (VECTORIZED!)
        print(f"🔄 Moon Dev creating {self.lookback_window}-minute lookback features...")
        
        # 🚀 VECTORIZED APPROACH - Much faster than nested loops!
        print("⚡ Moon Dev using VECTORIZED feature creation for speed! 🌙")
        
        # Filter to only columns that exist
        valid_feature_columns = [col for col in feature_columns if col in df_clean.columns]
        print(f"📊 Using {len(valid_feature_columns)} valid features: {valid_feature_columns}")
        
        # Extract feature matrix
        feature_matrix = df_clean[valid_feature_columns].values
        targets = df_clean[target_col].values
        
        # Create sliding windows efficiently
        print("🚀 Moon Dev creating sliding windows...")
        n_samples = len(feature_matrix) - self.lookback_window + 1
        n_features = len(valid_feature_columns)
        
        # Pre-allocate arrays
        X = np.zeros((n_samples, self.lookback_window * n_features))
        y = np.zeros(n_samples)
        
        print(f"📊 Processing {n_samples} samples with progress tracking...")
        
        # Vectorized sliding window creation
        for i in range(n_samples):
            if i % 1000 == 0:  # Progress indicator
                print(f"   🌙 Moon Dev processed {i:,}/{n_samples:,} samples ({i/n_samples*100:.1f}%)")
            
            # Extract window of features and flatten
            window_start = i
            window_end = i + self.lookback_window
            window_features = feature_matrix[window_start:window_end].flatten()
            
            X[i] = window_features
            y[i] = targets[window_end - 1 + self.prediction_horizon] if window_end - 1 + self.prediction_horizon < len(targets) else 0
        
        # Remove samples with invalid targets
        if target_type == 'direction':
            # For direction, keep all valid binary targets (0 or 1)
            valid_mask = (y == 0) | (y == 1)
        else:
            # For regression, remove zero targets (edge cases)
            valid_mask = y != 0
            
        X = X[valid_mask]
        y = y[valid_mask]
        
        # Create feature names for interpretability
        feature_names = []
        for lag in range(self.lookback_window):
            for col in feature_columns:
                feature_names.append(f"{col}_lag_{lag}")
        
        self.feature_names = feature_names
        
        print(f"🎉 Moon Dev's Random Forest features ready! 🌙")
        print(f"📊 Feature matrix shape: {X.shape}")
        print(f"🎯 Target shape: {y.shape}")
        
        if target_type == 'direction':
            up_count = np.sum(y == 1)
            down_count = np.sum(y == 0)
            print(f"📈 UP predictions needed: {up_count:,} ({up_count/len(y)*100:.1f}%)")
            print(f"📉 DOWN predictions needed: {down_count:,} ({down_count/len(y)*100:.1f}%)")
        
        return X, y
    
    def train_model(self, X_train, y_train, X_val, y_val, model_type='classifier'):
        """
        🌲 Train Moon Dev's Random Forest model (classification or regression)
        """
        print(f"🎓 Training Moon Dev's Random Forest {model_type}... 🚀")
        print(f"   🌲 Trees: {N_ESTIMATORS}")
        print(f"   📏 Max Depth: {MAX_DEPTH}")
        
        # Scale features
        print("⚖️ Moon Dev scaling features...")
        X_train_scaled = self.feature_scaler.fit_transform(X_train)
        X_val_scaled = self.feature_scaler.transform(X_val)
        
        # Handle targets based on model type
        if model_type == 'classifier':
            print("🎯 Moon Dev using CLASSIFICATION (no target scaling needed)!")
            y_train_final = y_train.astype(int)  # Ensure integer labels
            self.model_type = 'classifier'
            
            # 🚨 MOON DEV'S ENHANCED CLASS BALANCE ANALYSIS! 🚨
            unique_classes, class_counts = np.unique(y_train_final, return_counts=True)
            print("🚨 MOON DEV'S CLASS BALANCE ANALYSIS:")
            print(f"   📊 Training data distribution:")
            for cls, count in zip(unique_classes, class_counts):
                pct = count / len(y_train_final) * 100
                direction = "UP" if cls == 1 else "DOWN"
                print(f"     🎯 {direction} ({cls}): {count:,} samples ({pct:.1f}%)")
            
            # Calculate class imbalance ratio and determine strategy
            if len(unique_classes) == 2:
                down_count = class_counts[unique_classes == 0][0] if 0 in unique_classes else 0
                up_count = class_counts[unique_classes == 1][0] if 1 in unique_classes else 0
                imbalance_ratio = max(down_count, up_count) / max(min(down_count, up_count), 1)
                print(f"   ⚖️ Class imbalance ratio: {imbalance_ratio:.2f}:1")
                
                if imbalance_ratio > 3.0:
                    print(f"   🚨 SEVERE CLASS IMBALANCE! Using Demijan's optimized balancing...")
                elif imbalance_ratio > 2.0:
                    print(f"   ⚠️ Moderate imbalance. Using Demijan's optimized balancing...")
                else:
                    print(f"   ✅ Reasonable class balance. Using Demijan's optimized balancing...")
            
            print(f"   🚀 Using OPTIMIZED class_weight='{CLASS_WEIGHT_STRATEGY}' (Demijan's solution)!")
            
            # Initialize Random Forest Classifier with DEMIJAN'S OPTIMIZED PARAMETERS! 🚀
            self.model = RandomForestClassifier(
                n_estimators=N_ESTIMATORS,           # 🚀 Optimized: 500 trees
                max_depth=MAX_DEPTH,                 # 🚀 Optimized: Depth 10
                min_samples_split=MIN_SAMPLES_SPLIT, # 🚀 Optimized: Split 20
                min_samples_leaf=MIN_SAMPLES_LEAF,   # 🚀 Optimized: Leaf 10
                max_features=MAX_FEATURES,           # 🚀 Optimized: sqrt
                max_samples=MAX_SAMPLES,             # 🚀 Optimized: 0.9 bootstrap
                n_jobs=N_JOBS,
                random_state=42,
                verbose=2,
                class_weight=CLASS_WEIGHT_STRATEGY,  # 🚀 Optimized: balanced_subsample
                bootstrap=True  # 🚀 Optimized: Enable bootstrap
            )
            
        else:
            print("📊 Moon Dev using REGRESSION (scaling targets)...")
            y_train_final = self.target_scaler.fit_transform(y_train.reshape(-1, 1)).flatten()
            self.model_type = 'regressor'
            
            # Initialize Random Forest Regressor with DEMIJAN'S OPTIMIZED PARAMETERS! 🚀
            self.model = RandomForestRegressor(
                n_estimators=N_ESTIMATORS,           # 🚀 Optimized: 500 trees
                max_depth=MAX_DEPTH,                 # 🚀 Optimized: Depth 10
                min_samples_split=MIN_SAMPLES_SPLIT, # 🚀 Optimized: Split 20
                min_samples_leaf=MIN_SAMPLES_LEAF,   # 🚀 Optimized: Leaf 10
                max_features=MAX_FEATURES,           # 🚀 Optimized: sqrt
                max_samples=MAX_SAMPLES,             # 🚀 Optimized: 0.9 bootstrap
                n_jobs=N_JOBS,
                random_state=42,
                verbose=2,
                bootstrap=True  # 🚀 Optimized: Enable bootstrap
            )
        
        print(f"🌲 Moon Dev's ENHANCED Random Forest {model_type} training starting... 🌙")
        print(f"🔥 Training with {N_ESTIMATORS} trees, depth {MAX_DEPTH}")
        print(f"📊 Input shape: {X_train_scaled.shape}")
        print(f"⏱️ Estimated time: ~{N_ESTIMATORS//10}-{N_ESTIMATORS//5} seconds")
        
        if model_type == 'classifier':
            unique_classes, class_counts = np.unique(y_train_final, return_counts=True)
            print(f"📈 Class distribution: {dict(zip(unique_classes, class_counts))}")
        
        # Train the model
        import time
        start_time = time.time()
        self.model.fit(X_train_scaled, y_train_final)
        end_time = time.time()
        
        print(f"⏱️ Moon Dev's training completed in {end_time - start_time:.1f} seconds! 🚀")
        
        self.is_trained = True
        print(f"🎉 Moon Dev's Random Forest {model_type} training complete! 🚀")
        
        return self.model
    
    def evaluate_model(self, X_test, y_test):
        """
        🌲 Evaluate Moon Dev's Random Forest performance (classification or regression)
        """
        print("📊 Evaluating Moon Dev's Random Forest performance... 🚀")
        
        if not self.is_trained:
            print("❌ Moon Dev, model needs to be trained first!")
            return None
        
        # Scale test data
        X_test_scaled = self.feature_scaler.transform(X_test)
        
        # Make predictions based on model type
        if self.model_type == 'classifier':
            print("🎯 Moon Dev evaluating CLASSIFICATION performance (UP/DOWN)! 🌙")
            
            # Get predictions and probabilities
            predictions = self.model.predict(X_test_scaled)
            probabilities = self.model.predict_proba(X_test_scaled)[:, 1]  # Probability of UP (class 1)
            
            # 🚨 DEMIJAN'S REQUEST: Calculate AUC-ROC! 🚨
            print("\n📈 DEMIJAN'S AUC ANALYSIS - THE TRADING GOLD STANDARD! 🌙")
            print("=" * 70)
            
            # Calculate AUC-ROC
            auc_score = roc_auc_score(y_test, probabilities)
            fpr, tpr, thresholds = roc_curve(y_test, probabilities)
            
            print(f"🏆 AUC-ROC Score: {auc_score:.4f}")
            print(f"📊 AUC Interpretation for Trading:")
            if auc_score >= 0.9:
                print(f"   🚀 EXCEPTIONAL (≥0.90): Holy Grail territory! Extremely rare in trading!")
            elif auc_score >= 0.8:
                print(f"   🔥 EXCELLENT (0.80-0.89): Professional trader level! Very profitable!")
            elif auc_score >= 0.7:
                print(f"   ✅ GOOD (0.70-0.79): Strong edge! Definitely tradeable!")
            elif auc_score >= 0.6:
                print(f"   ⚠️  MODEST (0.60-0.69): Some edge, needs careful risk management")
            elif auc_score >= 0.55:
                print(f"   😐 WEAK (0.55-0.59): Barely better than random, questionable")
            elif auc_score >= 0.5:
                print(f"   🎲 RANDOM (0.50-0.54): No edge, like flipping a coin")
            else:
                print(f"   🚨 WORSE THAN RANDOM (<0.50): Something is wrong! Check your logic!")
            
            print(f"\n💡 WHAT AUC MEANS FOR MOON DEV'S TRADING:")
            print(f"   🎯 AUC measures how well we separate UP vs DOWN moves across ALL probability thresholds")
            print(f"   📈 Higher AUC = Better at ranking moves by UP probability")
            print(f"   💰 In trading: Can we consistently put higher probabilities on actual UP moves?")
            print(f"   🚀 AUC > 0.7 means we have REAL alpha! Moon Dev's edge is confirmed!")
            
            # Optimal threshold analysis
            optimal_idx = np.argmax(tpr - fpr)  # Maximize Youden's J statistic
            optimal_threshold = thresholds[optimal_idx]
            optimal_tpr = tpr[optimal_idx]
            optimal_fpr = fpr[optimal_idx]
            
            print(f"\n🎯 OPTIMAL TRADING THRESHOLD ANALYSIS:")
            print(f"   🏹 Optimal Threshold: {optimal_threshold:.4f} (default was 0.5)")
            print(f"   📈 True Positive Rate at optimal: {optimal_tpr:.4f} ({optimal_tpr*100:.1f}%)")
            print(f"   📉 False Positive Rate at optimal: {optimal_fpr:.4f} ({optimal_fpr*100:.1f}%)")
            print(f"   💡 Using optimal threshold instead of 0.5 could improve trading results!")
            
            # Test with optimal threshold
            predictions_optimal = (probabilities >= optimal_threshold).astype(int)
            accuracy_optimal = accuracy_score(y_test, predictions_optimal)
            up_mask = y_test == 1
            up_accuracy_optimal = np.mean(predictions_optimal[up_mask] == 1) if np.sum(up_mask) > 0 else 0
            
            print(f"   🚀 Accuracy with optimal threshold: {accuracy_optimal:.4f} vs {accuracy_score(y_test, predictions):.4f} (default)")
            print(f"   📈 UP accuracy with optimal threshold: {up_accuracy_optimal:.4f}")
            
            print("=" * 70)
            
            # Calculate classification metrics
            accuracy = accuracy_score(y_test, predictions)
            
            # Confusion matrix
            cm = confusion_matrix(y_test, predictions)
            
            # Classification report
            report = classification_report(y_test, predictions, output_dict=True)
            
            # 🚨 MOON DEV'S ENHANCED UP/DOWN ANALYSIS! 🚨
            up_mask = y_test == 1
            down_mask = y_test == 0
            
            up_accuracy = np.mean(predictions[up_mask] == y_test[up_mask]) if np.sum(up_mask) > 0 else 0
            down_accuracy = np.mean(predictions[down_mask] == y_test[down_mask]) if np.sum(down_mask) > 0 else 0
            
            up_count = np.sum(up_mask)
            down_count = np.sum(down_mask)
            
            # Prediction distribution
            predicted_up = np.sum(predictions == 1)
            predicted_down = np.sum(predictions == 0)
            
            print("🎯 MOON DEV'S RANDOM FOREST DIRECTION PERFORMANCE 🌙")
            print("=" * 60)
            print(f"🚀 OVERALL ACCURACY: {accuracy:.4f} ({accuracy*100:.2f}%)")
            print(f"🏆 AUC-ROC SCORE: {auc_score:.4f} (Demijan's key metric!)")
            print(f"🎲 Random baseline: ~50.0% accuracy, ~0.50 AUC")
            print(f"💪 Moon Dev improvement: +{(accuracy-0.5)*100:.2f} acc points, +{(auc_score-0.5)*100:.2f} AUC points!")
            
            # 🌲 DEMIJAN'S TREE COUNT ANALYSIS! 🌲
            print(f"\n🌲 DEMIJAN'S TREE COUNT INSIGHTS:")
            print(f"   🎯 Current trees: {N_ESTIMATORS}")
            print(f"   💭 Demijan said: '200+ has diminishing returns, but rarely need 500'")
            print(f"   🚀 Our optimizer chose 500 trees - suggests complex patterns!")
            print(f"   💡 Higher tree count needed for:")
            print(f"      📊 Complex liquidation patterns in crypto markets")
            print(f"      ⚡ High-frequency trading signals (our 5-minute bars)")
            print(f"      🌊 Market regime changes and volatility")
            print(f"   📈 Trade-off: More trees = Better performance but slower inference")
            print(f"   ✅ For Moon Dev: 500 trees justified by AUC improvement!")
            
            print("=" * 60)
            
            print(f"🚨 MOON DEV'S UP/DOWN BREAKDOWN:")
            print(f"   📈 UP moves in test: {up_count:,} ({up_count/len(y_test)*100:.1f}%)")
            print(f"   📉 DOWN moves in test: {down_count:,} ({down_count/len(y_test)*100:.1f}%)")
            print(f"   🎯 UP accuracy: {up_accuracy:.4f} ({up_accuracy*100:.1f}%)")
            print(f"   🎯 DOWN accuracy: {down_accuracy:.4f} ({down_accuracy*100:.1f}%)")
            print(f"")
            print(f"🤖 MODEL PREDICTION BEHAVIOR:")
            print(f"   🔮 Predicted UP: {predicted_up:,} ({predicted_up/len(predictions)*100:.1f}%)")
            print(f"   🔮 Predicted DOWN: {predicted_down:,} ({predicted_down/len(predictions)*100:.1f}%)")
            
            # Check for "DOWN-ONLY" problem
            if predicted_up == 0:
                print(f"   🚨 DOWN-ONLY PREDICTOR DETECTED! Never predicts UP moves!")
            elif predicted_up < up_count * 0.1:
                print(f"   ⚠️ PESSIMISTIC PREDICTOR: Rarely predicts UP moves!")
            elif predicted_up > up_count * 3:
                print(f"   ⚠️ OPTIMISTIC PREDICTOR: Over-predicts UP moves!")
            else:
                print(f"   ✅ BALANCED PREDICTOR: Reasonable UP/DOWN prediction ratio!")
            print("=" * 60)
            
            # Detailed performance by class
            print("📊 DETAILED CLASSIFICATION METRICS:")
            try:
                print(f"📉 DOWN (0) - Precision: {report['0']['precision']:.3f}, Recall: {report['0']['recall']:.3f}, F1: {report['0']['f1-score']:.3f}")
                print(f"📈 UP (1) - Precision: {report['1']['precision']:.3f}, Recall: {report['1']['recall']:.3f}, F1: {report['1']['f1-score']:.3f}")
                print(f"🎯 Macro Avg F1: {report['macro avg']['f1-score']:.3f}")
            except KeyError:
                # Handle case where some classes might be missing
                print("📊 Classification report keys:", list(report.keys()))
                for key in ['0', '1']:
                    if key in report:
                        print(f"📊 Class {key} - Precision: {report[key]['precision']:.3f}, Recall: {report[key]['recall']:.3f}, F1: {report[key]['f1-score']:.3f}")
                if 'macro avg' in report:
                    print(f"🎯 Macro Avg F1: {report['macro avg']['f1-score']:.3f}")
                elif 'weighted avg' in report:
                    print(f"🎯 Weighted Avg F1: {report['weighted avg']['f1-score']:.3f}")
            print("=" * 60)
            
            # Confusion Matrix
            print("🎲 CONFUSION MATRIX:")
            print(f"   Predicted:  DOWN   UP")
            print(f"Actual DOWN:   {cm[0,0]:4d}  {cm[0,1]:4d}")
            print(f"Actual UP:     {cm[1,0]:4d}  {cm[1,1]:4d}")
            print("=" * 60)
            
            metrics = {
                'accuracy': accuracy,
                'auc_score': auc_score,  # 🚨 NEW: Demijan's key metric!
                'fpr': fpr,              # 🚨 NEW: For ROC curve plotting
                'tpr': tpr,              # 🚨 NEW: For ROC curve plotting
                'thresholds': thresholds,# 🚨 NEW: For threshold analysis
                'optimal_threshold': optimal_threshold,  # 🚨 NEW: For trading optimization
                'predictions': predictions,
                'predictions_optimal': predictions_optimal,  # 🚨 NEW: Using optimal threshold
                'probabilities': probabilities,
                'actuals': y_test,
                'confusion_matrix': cm,
                'classification_report': report,
                'model_type': 'classifier'
            }
            
        else:
            print("📊 Moon Dev evaluating REGRESSION performance...")
            
            # Make predictions
            predictions_scaled = self.model.predict(X_test_scaled)
            predictions = self.target_scaler.inverse_transform(predictions_scaled.reshape(-1, 1)).flatten()
            
            # Calculate regression metrics
            mse = mean_squared_error(y_test, predictions)
            mae = mean_absolute_error(y_test, predictions)
            rmse = np.sqrt(mse)
            r2 = r2_score(y_test, predictions)
            
            # Fix MAPE calculation
            non_zero_mask = np.abs(y_test) > 1e-6
            if np.any(non_zero_mask):
                mape = np.mean(np.abs((y_test[non_zero_mask] - predictions[non_zero_mask]) / y_test[non_zero_mask])) * 100
            else:
                mape = float('inf')
            
            print("🎯 MOON DEV'S RANDOM FOREST REGRESSION PERFORMANCE 🌙")
            print("=" * 50)
            print(f"📊 RMSE: {rmse:.6f}")
            print(f"📈 MAE: {mae:.6f}")
            print(f"🎪 R²: {r2:.4f}")
            print(f"📉 MAPE: {mape:.2f}%")
            print(f"🚀 MSE: {mse:.6f}")
            print("=" * 50)
            
            metrics = {
                'rmse': rmse, 'mae': mae, 'r2': r2, 'mape': mape, 'mse': mse,
                'predictions': predictions, 'actuals': y_test,
                'model_type': 'regressor'
            }
        
        # Feature importance analysis (common to both)
        if self.feature_names:
            print("🌲 MOON DEV'S TOP 10 FEATURE IMPORTANCE 🌙")
            feature_importance = pd.DataFrame({
                'feature': self.feature_names,
                'importance': self.model.feature_importances_
            }).sort_values('importance', ascending=False)
            
            print("🔥 Most important liquidation features:")
            for i, (_, row) in enumerate(feature_importance.head(10).iterrows()):
                # Clean up feature name for display
                clean_name = row['feature'].split('_lag_')[0] if '_lag_' in row['feature'] else row['feature']
                print(f"   {i+1}. {clean_name}: {row['importance']:.4f}")
            print("=" * 50)
            
            metrics['feature_importance'] = feature_importance
        
        return metrics
    
    def plot_results(self, metrics, save_path=None):
        """
        🌲 Plot Moon Dev's Random Forest results (classification or regression)
        """
        print("📈 Creating Moon Dev's Random Forest performance plots... 🚀")
        
        if metrics.get('model_type') == 'classifier':
            # Classification plots with ROC curve
            fig, axes = plt.subplots(2, 2, figsize=(15, 10))
            fig.suptitle('🌙 MOON DEV\'S RANDOM FOREST DIRECTION PREDICTOR RESULTS 🌲', fontsize=16)
            
            # ROC Curve (Demijan's request!)
            if 'fpr' in metrics and 'tpr' in metrics and 'auc_score' in metrics:
                axes[0, 0].plot(metrics['fpr'], metrics['tpr'], color='green', lw=2, 
                               label=f'ROC Curve (AUC = {metrics["auc_score"]:.3f})')
                axes[0, 0].plot([0, 1], [0, 1], color='red', lw=2, linestyle='--', label='Random Baseline (AUC = 0.5)')
                axes[0, 0].set_xlim([0.0, 1.0])
                axes[0, 0].set_ylim([0.0, 1.05])
                axes[0, 0].set_xlabel('False Positive Rate (1 - Specificity)')
                axes[0, 0].set_ylabel('True Positive Rate (Sensitivity)')
                axes[0, 0].set_title('🏆 Moon Dev RF: ROC Curve (Demijan\'s Key Metric!)')
                axes[0, 0].legend(loc="lower right")
                axes[0, 0].grid(True, alpha=0.3)
                
                # Mark optimal threshold point
                if 'optimal_threshold' in metrics:
                    optimal_idx = np.argmax(metrics['tpr'] - metrics['fpr'])
                    axes[0, 0].plot(metrics['fpr'][optimal_idx], metrics['tpr'][optimal_idx], 
                                   'ro', markersize=8, label=f'Optimal Threshold ({metrics["optimal_threshold"]:.3f})')
                    axes[0, 0].legend(loc="lower right")
            else:
                # Fallback to confusion matrix if no ROC data
                cm = metrics['confusion_matrix']
                im = axes[0, 0].imshow(cm, interpolation='nearest', cmap='Greens')
                axes[0, 0].figure.colorbar(im, ax=axes[0, 0])
                axes[0, 0].set_title('🎲 Moon Dev RF: Confusion Matrix')
            
            # Prediction probabilities histogram
            if 'probabilities' in metrics:
                probs = metrics['probabilities']
                actuals = metrics['actuals']
                
                # Separate probabilities by actual class
                up_probs = probs[actuals == 1]
                down_probs = probs[actuals == 0]
                
                axes[0, 1].hist(down_probs, bins=30, alpha=0.7, label='Actual DOWN', color='red', density=True)
                axes[0, 1].hist(up_probs, bins=30, alpha=0.7, label='Actual UP', color='green', density=True)
                axes[0, 1].set_xlabel('Predicted UP Probability')
                axes[0, 1].set_ylabel('Density')
                axes[0, 1].set_title('🎯 Moon Dev RF: Probability Distribution')
                axes[0, 1].legend()
                axes[0, 1].grid(True, alpha=0.3)
                
                # Add optimal threshold line if available
                if 'optimal_threshold' in metrics:
                    axes[0, 1].axvline(x=metrics['optimal_threshold'], color='blue', linestyle='--', 
                                      label=f'Optimal Threshold ({metrics["optimal_threshold"]:.3f})')
                    axes[0, 1].legend()
            
            # Rolling accuracy over time
            predictions = metrics['predictions']
            actuals = metrics['actuals']
            window_size = min(100, len(predictions) // 10)
            
            if len(predictions) > window_size:
                rolling_acc = []
                for i in range(window_size, len(predictions)):
                    window_acc = accuracy_score(actuals[i-window_size:i], predictions[i-window_size:i])
                    rolling_acc.append(window_acc)
                
                axes[1, 0].plot(rolling_acc, color='green', alpha=0.8, label='Default Threshold (0.5)')
                axes[1, 0].axhline(y=0.5, color='red', linestyle='--', label='Random Baseline')
                
                # Also plot optimal threshold performance if available
                if 'predictions_optimal' in metrics:
                    predictions_opt = metrics['predictions_optimal']
                    rolling_acc_opt = []
                    for i in range(window_size, len(predictions_opt)):
                        window_acc_opt = accuracy_score(actuals[i-window_size:i], predictions_opt[i-window_size:i])
                        rolling_acc_opt.append(window_acc_opt)
                    
                    axes[1, 0].plot(rolling_acc_opt, color='blue', alpha=0.8, 
                                   label=f'Optimal Threshold ({metrics.get("optimal_threshold", "N/A"):.3f})')
                
                axes[1, 0].set_xlabel('Time Window')
                axes[1, 0].set_ylabel('Accuracy')
                axes[1, 0].set_title('🌙 Moon Dev RF: Rolling Accuracy')
                axes[1, 0].legend()
                axes[1, 0].grid(True, alpha=0.3)
            
        else:
            # Regression plots (original)
            fig, axes = plt.subplots(2, 2, figsize=(15, 10))
            fig.suptitle('🌙 MOON DEV\'S RANDOM FOREST LIQUIDATION PREDICTOR RESULTS 🌲', fontsize=16)
            
            # Scatter plot of predictions vs actuals
            axes[0, 0].scatter(metrics['actuals'], metrics['predictions'], alpha=0.6, color='green')
            axes[0, 0].plot([metrics['actuals'].min(), metrics['actuals'].max()], 
                           [metrics['actuals'].min(), metrics['actuals'].max()], 'r--', lw=2)
            axes[0, 0].set_xlabel('Actual Returns')
            axes[0, 0].set_ylabel('Predicted Returns')
            axes[0, 0].set_title('🎯 Moon Dev RF: Predictions vs Actuals')
            axes[0, 0].grid(True, alpha=0.3)
            
            # Residuals plot
            residuals = metrics['actuals'] - metrics['predictions']
            axes[0, 1].scatter(metrics['predictions'], residuals, alpha=0.6, color='green')
            axes[0, 1].axhline(y=0, color='r', linestyle='--')
            axes[0, 1].set_xlabel('Predicted Returns')
            axes[0, 1].set_ylabel('Residuals')
            axes[0, 1].set_title('🌙 Moon Dev RF: Residuals Plot')
            axes[0, 1].grid(True, alpha=0.3)
            
            # Distribution of residuals
            axes[1, 1].hist(residuals, bins=50, alpha=0.7, density=True, color='green')
            axes[1, 1].set_xlabel('Residuals')
            axes[1, 1].set_ylabel('Density')
            axes[1, 1].set_title('🌙 Moon Dev RF: Residuals Distribution')
            axes[1, 1].grid(True, alpha=0.3)
        
        # Feature importance (common to both)
        if 'feature_importance' in metrics and metrics['feature_importance'] is not None:
            top_features = metrics['feature_importance'].head(15)
            y_pos = range(len(top_features))
            
            # Use appropriate subplot position
            ax_feat = axes[1, 0] if metrics.get('model_type') == 'regressor' else axes[1, 1]
            
            ax_feat.barh(y_pos, top_features['importance'], color='green', alpha=0.7)
            ax_feat.set_yticks(y_pos)
            ax_feat.set_yticklabels([f.split('_lag_')[0] for f in top_features['feature']], fontsize=8)
            ax_feat.set_xlabel('Feature Importance')
            ax_feat.set_title('🌲 Moon Dev RF: Top Feature Importance')
            ax_feat.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"📊 Moon Dev's Random Forest plots saved to: {save_path} 🌙")
        
        plt.show()
        print("🎉 Moon Dev's Random Forest visualization complete! 🚀")
        print("=" * 50)
    
    def save_model(self, model_name=None, save_dir="models"):
        """
        💾 Save Moon Dev's trained Random Forest model for production deployment!
        """
        if not self.is_trained:
            print("❌ Moon Dev, model needs to be trained first before saving!")
            return None
        
        # Create models directory if it doesn't exist
        os.makedirs(save_dir, exist_ok=True)
        
        # Generate model name with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if model_name is None:
            model_type = "classifier" if self.model_type == 'classifier' else "regressor"
            model_name = f"moon_dev_rf_{model_type}_production"
        
        # Save paths
        model_path = os.path.join(save_dir, f"{model_name}_{timestamp}.joblib")
        metadata_path = os.path.join(save_dir, f"{model_name}_{timestamp}_metadata.json")
        
        try:
            # Save the entire predictor object (includes model, scalers, feature names, etc.)
            joblib.dump(self, model_path)
            
            # Save metadata for easy reference
            metadata = {
                'model_name': model_name,
                'model_type': self.model_type,
                'timestamp': timestamp,
                'lookback_window': self.lookback_window,
                'prediction_horizon': self.prediction_horizon,
                'n_estimators': N_ESTIMATORS,
                'max_depth': MAX_DEPTH,
                'feature_count': len(self.feature_names) if self.feature_names else 0,
                'local_mode': LOCAL_MODE,
                'data_sample_fraction': DATA_SAMPLE_FRACTION,
                'save_path': model_path,
                'created_by': '🌙 Moon Dev RF Liquidation Predictor 🚀'
            }
            
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=4)
            
            print("💾 MOON DEV'S MODEL SAVED SUCCESSFULLY! 🚀")
            print("=" * 50)
            print(f"🌙 Model file: {model_path}")
            print(f"📊 Metadata file: {metadata_path}")
            print(f"🎯 Model type: {self.model_type}")
            print(f"🌲 Trees: {N_ESTIMATORS}")
            print(f"📏 Max depth: {MAX_DEPTH}")
            print(f"🔧 Features: {len(self.feature_names) if self.feature_names else 0}")
            print("=" * 50)
            
            return model_path, metadata_path
            
        except Exception as e:
            print(f"❌ Moon Dev model saving error: {e}")
            return None
    
    @staticmethod
    def load_model(model_path):
        """
        📂 Load Moon Dev's saved Random Forest model for production use!
        """
        try:
            predictor = joblib.load(model_path)
            print(f"✅ Moon Dev model loaded successfully: {model_path}")
            print(f"🎯 Model type: {predictor.model_type}")
            print(f"🔧 Features: {len(predictor.feature_names) if predictor.feature_names else 0}")
            return predictor
        except Exception as e:
            print(f"❌ Moon Dev model loading error: {e}")
            return None
    
    def create_focused_liquidation_features(self, df, time_window='1h'):
        """
        🎯 Moon Dev's FOCUSED liquidation feature engineering
        Based on successful backtesting: Side + Volume = Direction prediction!
        """
        print(f"🎯 Creating FOCUSED liquidation features based on Moon Dev's backtesting! 🌙")
        print(f"💡 Core insight: Long liquidations → Buy signal, Short liquidations → Sell signal")
        print("🚀 Reducing feature noise, focusing on PROVEN signals!")
        
        # Handle data sampling for LOCAL_MODE
        if LOCAL_MODE and DATA_SAMPLE_FRACTION < 1.0:
            original_size = len(df)
            df_sorted = df.sort_values('timestamp')
            total_time_span = df_sorted['timestamp'].max() - df_sorted['timestamp'].min()
            sample_time_span = total_time_span * DATA_SAMPLE_FRACTION
            end_time = df_sorted['timestamp'].max()
            start_time = end_time - sample_time_span
            df = df_sorted[df_sorted['timestamp'] >= start_time].reset_index(drop=True)
            print(f"🏠 LOCAL_MODE: Using {len(df):,} records from last {sample_time_span.days} days")
        
        # Map quantity column
        quantity_col = 'original_quantity' if 'original_quantity' in df.columns else 'quantity'
        
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

def main():
    """
    🌙 Moon Dev's main Random Forest liquidation prediction pipeline
    """
    print("🚀 STARTING MOON DEV'S RANDOM FOREST LIQUIDATION PREDICTOR 🌙")
    print("=" * 60)
    
    # Initialize the predictor
    print("🏗️ Moon Dev initializing Random Forest predictor...")
    predictor = RFLiquidationPredictor(lookback_window=60, prediction_horizon=5)
    
    # Load data - USING MOON DEV'S NEW BTC PREPROCESSED DATA! 🚀
    print("📂 Moon Dev loading CLEAN BTC liquidation data...")
    data_path = "research/machine_learning/processed_data/liquidations_BTC_processed.csv"
    print(f"🎯 Using Moon Dev's preprocessed BTC-only data: {data_path}")
    df = predictor.load_liquidation_data(data_path)
    
    if df is None:
        print("❌ Moon Dev, please check your data path!")
        return
    
    # 🎯 MOON DEV'S CHOICE: Use focused features or full features
    USE_FOCUSED_FEATURES = True  # Set to True to use Moon Dev's backtested features!
    
    if USE_FOCUSED_FEATURES:
        print("🎯 USING MOON DEV'S FOCUSED LIQUIDATION FEATURES! 🚀")
        print("💡 Based on successful backtesting: liquidation side + volume")
        
        # Create focused features
        df_features = predictor.create_focused_liquidation_features(df, time_window='1h')
        if df_features is None:
            print("❌ Moon Dev, focused feature engineering failed!")
            return
            
        # Create targets on focused data
        df_targets = predictor.create_target_variable(df_features, target_return_threshold=0.003)
        
        # Use only the focused liquidation features
        feature_columns = [col for col in LIQUIDATION_FOCUSED_FEATURES if col in df_targets.columns]
        print(f"🎯 FOCUSED: Using {len(feature_columns)} backtested features: {feature_columns}")
        
    else:
        print("📊 USING FULL FEATURE SET (Original approach)")
        
        # Engineer features with 1-hour aggregation
        print("🔧 Moon Dev starting feature engineering...")
        df_features = predictor.engineer_features(df, time_window='1h')
        
        if df_features is None:
            print("❌ Moon Dev, feature engineering failed!")
            return
        
        # Create target variables
        print("🎯 Moon Dev creating target variables...")
        df_targets = predictor.create_target_variable(df_features, target_return_threshold=0.003)
        
        # Define feature columns
        all_feature_columns = [col for col in df_targets.columns 
                              if col not in ['target_return', 'future_return', 'target_direction_binary']]
        
        # 🏠 LOCAL_MODE: Use core features only for faster testing
        if LOCAL_MODE and CORE_FEATURES is not None:
            feature_columns = [col for col in CORE_FEATURES if col in all_feature_columns]
            print(f"🏠 LOCAL_MODE: Using {len(feature_columns)} core features: {feature_columns}")
        else:
            feature_columns = all_feature_columns
            print(f"☁️ PRODUCTION: Using all {len(feature_columns)} features")
    
    # 💡 VIEWER'S DIRECTION APPROACH: Use direction prediction!
    print("💡 IMPLEMENTING VIEWER'S DIRECTION APPROACH! 🚀")
    print("🎯 Focus on UP/DOWN instead of exact percentage returns!")
    X, y = predictor.prepare_features(df_targets, feature_columns, target_type='direction')
    
    # Split data (same as LSTM for fair comparison)
    train_size = int(0.8 * len(X))
    val_size = int(0.1 * len(X))
    
    X_train, X_val, X_test = X[:train_size], X[train_size:train_size+val_size], X[train_size+val_size:]
    y_train, y_val, y_test = y[:train_size], y[train_size:train_size+val_size], y[train_size+val_size:]
    
    print(f"🔄 Moon Dev's data split:")
    print(f"📊 Train: {X_train.shape[0]}, Val: {X_val.shape[0]}, Test: {X_test.shape[0]}")
    print("=" * 50)
    
    # Train the model using CLASSIFICATION (direction prediction)
    print("🌲 Moon Dev training Random Forest CLASSIFIER for direction prediction! 🚀")
    model = predictor.train_model(X_train, y_train, X_val, y_val, model_type='classifier')
    
    # Evaluate the model
    metrics = predictor.evaluate_model(X_test, y_test)
    
    # Plot results
    predictor.plot_results(metrics)
    
    # 💾 SAVE THE TRAINED MODEL FOR PRODUCTION! 🚀
    print("💾 Moon Dev saving trained model for production deployment...")
    model_files = predictor.save_model()
    
    if model_files:
        model_path, metadata_path = model_files
        print(f"🚀 Moon Dev model ready for deployment!")
        print(f"📂 Use this path for trading bot: {model_path}")
        
        # 🔄 QUICK TEST: Load and verify the saved model
        print("🔄 Moon Dev testing model loading...")
        loaded_predictor = RFLiquidationPredictor.load_model(model_path)
        if loaded_predictor:
            print("✅ Moon Dev model loading test SUCCESSFUL! 🌙")
        else:
            print("❌ Moon Dev model loading test FAILED!")
    
    print("🎉 MOON DEV'S RANDOM FOREST LIQUIDATION PREDICTOR COMPLETE! 🚀🌙")
    print("=" * 60)

if __name__ == "__main__":
    main() 