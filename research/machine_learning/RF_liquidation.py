"""
🌙 MOON DEV'S RANDOM FOREST LIQUIDATION PREDICTOR 🚀
Predicting BTC price moves using liquidation data with Random Forest
🌲 Fast baseline for LSTM comparison! 🌲
"""

# 🌙 MOON DEV'S TRAINING CONFIGURATION CONSTANTS 🚀
# ================================================

# 🏠 LOCAL MODE SWITCH - Change to False for full cloud runs! 🚀
LOCAL_MODE = True             # Set to False for production cloud runs

# Training Constants (scaled by LOCAL_MODE)
N_ESTIMATORS = 300 if LOCAL_MODE else 1000          # More trees for better performance
MAX_DEPTH = 15 if LOCAL_MODE else 25                # Deeper trees
MIN_SAMPLES_SPLIT = 3 if LOCAL_MODE else 2          # More sensitive splitting
MIN_SAMPLES_LEAF = 1 if LOCAL_MODE else 1           # Allow smaller leaves
MAX_FEATURES = 'sqrt' if LOCAL_MODE else None      # Use sqrt for local, all features for cloud
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

mode_emoji = "🌲" if LOCAL_MODE else "🌳"
mode_name = "LOCAL TESTING" if LOCAL_MODE else "CLOUD PRODUCTION"
print(f"🌙 MOON DEV'S RANDOM FOREST CONSTANTS LOADED! 🚀")
print(f"{mode_emoji} MODE: {mode_name}")
print(f"   📊 Data Sample: {DATA_SAMPLE_FRACTION*100:.2f}% of TIME PERIOD (most recent data)")
print(f"   🌲 Trees: {N_ESTIMATORS}")
print(f"   📏 Max Depth: {MAX_DEPTH}")  
print(f"   🔧 Lookback: {LOOKBACK_WINDOW} minutes")
print(f"   ⏰ EXPERIMENT: 5-minute bars (vs 1-minute) + ALL symbols + ALL sizes")
if LOCAL_MODE:
    print(f"   🎯 Features: {len(CORE_FEATURES)} core features only")
else:
    print(f"   🎯 Features: All 47+ features")
print("=" * 50)

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
import os
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
        
        # ⏰ EXPERIMENT: 5-minute aggregation (vs 1-minute) for Moon Dev!
        print("\n⏰ MOON DEV'S 5-MINUTE AGGREGATION EXPERIMENT ⏰")
        print("=" * 50)
        original_count = len(df)
        original_symbols = df['symbol'].nunique()
        
        print(f"🔍 Original liquidations: {original_count:,}")
        print(f"🌊 All symbols included: {original_symbols}")
        print(f"⏰ Using 5-minute bars (vs 1-minute)")
        print(f"🎯 Hypothesis: Larger time windows capture liquidation waves better")
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
    
    def create_target_variable(self, df, target_return_threshold=0.005):
        """
        🌙 Create Moon Dev's target variable (same as LSTM)
        """
        print(f"🎯 Creating target variable for Moon Dev Random Forest... 🌙")
        
        # Calculate future returns (same logic as LSTM)
        print("📈 Moon Dev calculating future returns...")
        print("🪙 NOTE: Using ONLY Bitcoin prices for targets")
        
        current_prices = df['price_last']
        future_prices = df['price_last'].shift(-self.prediction_horizon)
        
        # Calculate raw returns
        raw_returns = future_prices / current_prices - 1
        
        # Cap extreme returns (same as LSTM)
        max_return = MAX_RETURN_CAP
        min_return = MIN_RETURN_CAP
        
        df['future_return'] = np.where(
            np.isinf(raw_returns) | (raw_returns > max_return), max_return,
            np.where(
                raw_returns < min_return, min_return,
                raw_returns
            )
        )
        
        # Create targets
        df['target_return'] = df['future_return']
        
        print(f"🚀 Moon Dev's Random Forest targets created!")
        
        return df
    
    def prepare_features(self, df, feature_columns):
        """
        🌲 Prepare Random Forest features (different from LSTM - no sequences!)
        """
        print("🔄 Preparing Random Forest features for Moon Dev... 🚀")
        print(f"🎯 Moon Dev using {len(feature_columns)} features")
        
        # Clean data
        df_clean = df.dropna(subset=['target_return'])
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
        targets = df_clean['target_return'].values
        
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
        
        # Remove samples with zero targets (edge cases)
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
        
        return X, y
    
    def train_model(self, X_train, y_train, X_val, y_val):
        """
        🌲 Train Moon Dev's Random Forest model
        """
        print(f"🎓 Training Moon Dev's Random Forest model... 🚀")
        print(f"   🌲 Trees: {N_ESTIMATORS}")
        print(f"   📏 Max Depth: {MAX_DEPTH}")
        
        # Scale features
        print("⚖️ Moon Dev scaling features...")
        X_train_scaled = self.feature_scaler.fit_transform(X_train)
        X_val_scaled = self.feature_scaler.transform(X_val)
        
        # Scale targets
        print("🎯 Moon Dev scaling targets...")
        y_train_scaled = self.target_scaler.fit_transform(y_train.reshape(-1, 1)).flatten()
        
        # Initialize Random Forest
        self.model = RandomForestRegressor(
            n_estimators=N_ESTIMATORS,
            max_depth=MAX_DEPTH,
            min_samples_split=MIN_SAMPLES_SPLIT,
            min_samples_leaf=MIN_SAMPLES_LEAF,
            max_features=MAX_FEATURES,
            n_jobs=N_JOBS,
            random_state=42,
            verbose=2  # More verbose output for Moon Dev!
        )
        
        print("🌲 Moon Dev's ENHANCED Random Forest training starting... 🌙")
        print(f"🔥 Training with {N_ESTIMATORS} trees, depth {MAX_DEPTH}")
        print(f"📊 Input shape: {X_train_scaled.shape}")
        print(f"⏱️ Estimated time: ~{N_ESTIMATORS//10}-{N_ESTIMATORS//5} seconds")
        
        # Train the model
        import time
        start_time = time.time()
        self.model.fit(X_train_scaled, y_train_scaled)
        end_time = time.time()
        
        print(f"⏱️ Moon Dev's training completed in {end_time - start_time:.1f} seconds! 🚀")
        
        self.is_trained = True
        print("🎉 Moon Dev's Random Forest training complete! 🚀")
        
        return self.model
    
    def evaluate_model(self, X_test, y_test):
        """
        🌲 Evaluate Moon Dev's Random Forest performance
        """
        print("📊 Evaluating Moon Dev's Random Forest performance... 🚀")
        
        if not self.is_trained:
            print("❌ Moon Dev, model needs to be trained first!")
            return None
        
        # Scale test data
        X_test_scaled = self.feature_scaler.transform(X_test)
        
        # Make predictions
        predictions_scaled = self.model.predict(X_test_scaled)
        
        # Unscale predictions
        predictions = self.target_scaler.inverse_transform(predictions_scaled.reshape(-1, 1)).flatten()
        
        # Calculate metrics
        mse = mean_squared_error(y_test, predictions)
        mae = mean_absolute_error(y_test, predictions)
        rmse = np.sqrt(mse)
        r2 = r2_score(y_test, predictions)
        # Fix MAPE calculation for Moon Dev (handle zero values properly)
        non_zero_mask = np.abs(y_test) > 1e-6  # Only calculate MAPE for non-zero values
        if np.any(non_zero_mask):
            mape = np.mean(np.abs((y_test[non_zero_mask] - predictions[non_zero_mask]) / y_test[non_zero_mask])) * 100
        else:
            mape = float('inf')  # All targets are near zero
        
        print("🎯 MOON DEV'S RANDOM FOREST PERFORMANCE METRICS 🌙")
        print("=" * 50)
        print(f"📊 RMSE (Root Mean Square Error): {rmse:.6f}")
        print(f"📈 MAE (Mean Absolute Error): {mae:.6f}")
        print(f"🎪 R² (R-squared): {r2:.4f}")
        print(f"📉 MAPE (Mean Absolute % Error): {mape:.2f}%")
        print(f"🚀 MSE (Mean Square Error): {mse:.6f}")
        print("=" * 50)
        
        # Feature importance analysis
        if self.feature_names:
            print("🌲 MOON DEV'S TOP 10 FEATURE IMPORTANCE 🌙")
            feature_importance = pd.DataFrame({
                'feature': self.feature_names,
                'importance': self.model.feature_importances_
            }).sort_values('importance', ascending=False)
            
            print("🔥 Most important liquidation features:")
            for i, (_, row) in enumerate(feature_importance.head(10).iterrows()):
                print(f"   {i+1}. {row['feature']}: {row['importance']:.4f}")
            print("=" * 50)
        
        metrics = {
            'rmse': rmse, 'mae': mae, 'r2': r2, 'mape': mape, 'mse': mse,
            'predictions': predictions, 'actuals': y_test,
            'feature_importance': feature_importance if self.feature_names else None
        }
        
        return metrics
    
    def plot_results(self, metrics, save_path=None):
        """
        🌲 Plot Moon Dev's Random Forest results
        """
        print("📈 Creating Moon Dev's Random Forest performance plots... 🚀")
        
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
        
        # Feature importance (top 15)
        if metrics['feature_importance'] is not None:
            top_features = metrics['feature_importance'].head(15)
            axes[1, 0].barh(range(len(top_features)), top_features['importance'], color='green', alpha=0.7)
            axes[1, 0].set_yticks(range(len(top_features)))
            axes[1, 0].set_yticklabels([f.split('_lag_')[0] for f in top_features['feature']], fontsize=8)
            axes[1, 0].set_xlabel('Feature Importance')
            axes[1, 0].set_title('🌲 Moon Dev RF: Top Feature Importance')
            axes[1, 0].grid(True, alpha=0.3)
        
        # Distribution of residuals
        axes[1, 1].hist(residuals, bins=50, alpha=0.7, density=True, color='green')
        axes[1, 1].set_xlabel('Residuals')
        axes[1, 1].set_ylabel('Density')
        axes[1, 1].set_title('🌙 Moon Dev RF: Residuals Distribution')
        axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"📊 Moon Dev's Random Forest plots saved to: {save_path} 🌙")
        
        plt.show()
        print("🎉 Moon Dev's Random Forest visualization complete! 🚀")
        print("=" * 50)

def main():
    """
    🌙 Moon Dev's main Random Forest liquidation prediction pipeline
    """
    print("🚀 STARTING MOON DEV'S RANDOM FOREST LIQUIDATION PREDICTOR 🌙")
    print("=" * 60)
    
    # Initialize the predictor
    print("🏗️ Moon Dev initializing Random Forest predictor...")
    predictor = RFLiquidationPredictor(lookback_window=60, prediction_horizon=5)
    
    # Load data
    print("📂 Moon Dev loading liquidation data...")
    data_path = "/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/moondev_api/liq_data.csv"
    df = predictor.load_liquidation_data(data_path)
    
    if df is None:
        print("❌ Moon Dev, please check your data path!")
        return
    
    # Engineer features with 5-minute aggregation
    print("🔧 Moon Dev starting feature engineering...")
    df_features = predictor.engineer_features(df, time_window='5min')
    
    if df_features is None:
        print("❌ Moon Dev, feature engineering failed!")
        return
    
    # Create target variables
    print("🎯 Moon Dev creating target variables...")
    df_targets = predictor.create_target_variable(df_features, target_return_threshold=TARGET_THRESHOLD)
    
    # Define feature columns
    all_feature_columns = [col for col in df_targets.columns 
                          if col not in ['target_return', 'future_return']]
    
    # 🏠 LOCAL_MODE: Use core features only for faster testing
    if LOCAL_MODE and CORE_FEATURES is not None:
        feature_columns = [col for col in CORE_FEATURES if col in all_feature_columns]
        print(f"🏠 LOCAL_MODE: Using {len(feature_columns)} core features: {feature_columns}")
    else:
        feature_columns = all_feature_columns
        print(f"☁️ PRODUCTION: Using all {len(feature_columns)} features")
    
    # Prepare features
    X, y = predictor.prepare_features(df_targets, feature_columns)
    
    # Split data (same as LSTM for fair comparison)
    train_size = int(0.8 * len(X))
    val_size = int(0.1 * len(X))
    
    X_train, X_val, X_test = X[:train_size], X[train_size:train_size+val_size], X[train_size+val_size:]
    y_train, y_val, y_test = y[:train_size], y[train_size:train_size+val_size], y[train_size+val_size:]
    
    print(f"🔄 Moon Dev's data split:")
    print(f"📊 Train: {X_train.shape[0]}, Val: {X_val.shape[0]}, Test: {X_test.shape[0]}")
    print("=" * 50)
    
    # Train the model
    model = predictor.train_model(X_train, y_train, X_val, y_val)
    
    # Evaluate the model
    metrics = predictor.evaluate_model(X_test, y_test)
    
    # Plot results
    predictor.plot_results(metrics)
    
    print("🎉 MOON DEV'S RANDOM FOREST LIQUIDATION PREDICTOR COMPLETE! 🚀🌙")
    print("=" * 60)

if __name__ == "__main__":
    main() 