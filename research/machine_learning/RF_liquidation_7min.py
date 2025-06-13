"""
🌙 MOON DEV'S RANDOM FOREST LIQUIDATION PREDICTOR - 7 MINUTES 🚀
Predicting BTC price moves using liquidation data with Random Forest
🌲 7-Minute timeframe - SUPERIOR signal clarity and noise reduction! 🌲
⚡ Better than 3-min, cleaner than 4-min, more responsive than 15-min!
🎯 Premium timeframe for liquidation cascade analysis!
"""

# 🌙 MOON DEV'S TRAINING CONFIGURATION CONSTANTS 🚀
# ================================================

# 🏠 LOCAL MODE SWITCH - Change to False for full cloud runs! 🚀
LOCAL_MODE = True             # Set to True for faster testing

# Training Constants (scaled by LOCAL_MODE)
# 🚀 OPTIMIZED RF HYPERPARAMETERS FOR 7-MINUTE LIQUIDATION SIGNALS! 🚀
N_ESTIMATORS = 320 if LOCAL_MODE else 520      # Optimized trees for 7-min signals
MAX_DEPTH = 8                                  # Optimal depth for 7-min patterns  
MIN_SAMPLES_SPLIT = 18                         # Optimal splits for 7-min patterns
MIN_SAMPLES_LEAF = 9                           # Optimal leaves for 7-min sensitivity
MAX_FEATURES = 'sqrt'                          # Optimal: sqrt features per split
MAX_SAMPLES = 0.85                             # Higher sampling for cleaner signals
CLASS_WEIGHT_STRATEGY = 'balanced_subsample'   # Aggressive balancing for liquidations
N_JOBS = -1                                    # Use all CPU cores

# Data Processing Constants (optimized for 7-minute signals)
DATA_SAMPLE_FRACTION = 0.5 if LOCAL_MODE else 1.0  # 22% for local testing
LOOKBACK_WINDOW = 9           # ~1 hour of 7-minute data (9 × 7min = 63 min)
PREDICTION_HORIZON = 1        # 1 step ahead = 7 minutes prediction
MAX_RETURN_CAP = 6.0          # Higher cap for 7-min moves (600% max)
MIN_RETURN_CAP = -0.96        # 96% loss cap for 7-min
TARGET_THRESHOLD = 0.0025     # 0.25% threshold (premium sensitivity for 7-min)

# Feature Selection (scaled by LOCAL_MODE)
CORE_FEATURES = [
    'side', 'quantity_sum', 'quantity_mean', 'price_last', 'price_mean',
    'usd_liq_volume', 'usd_liq_net', 'liq_velocity', 'liq_imbalance',
    'total_liq_events', 'hour', 'minute', 'day_of_week'
] if LOCAL_MODE else None  # None means use all features

# 🎯 MOON DEV'S FOCUSED LIQUIDATION FEATURES (Optimized for 7-min!)
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
print(f"🌙 MOON DEV'S 7-MINUTE RANDOM FOREST CONSTANTS LOADED! 🚀")
print(f"{mode_emoji} MODE: {mode_name}")
print(f"   📊 Data Sample: {DATA_SAMPLE_FRACTION*100:.2f}% of TIME PERIOD (most recent data)")
print(f"   🌲 Trees: {N_ESTIMATORS}")
print(f"   📏 Max Depth: {MAX_DEPTH}")  
print(f"   🔧 Lookback: {LOOKBACK_WINDOW} periods (~1 hour of 7-min data)")
print(f"   ⏰ EXPERIMENT: 7-minute bars - SUPERIOR signal clarity and noise reduction!")
print(f"   🎯 Prediction: {PREDICTION_HORIZON} step ahead (7 minutes)")
print(f"   📈 Threshold: {TARGET_THRESHOLD*100:.2f}% (premium sensitivity for 7-min)")
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

print("🌙 MOON DEV'S 7-MINUTE RANDOM FOREST LIQUIDATION PREDICTOR LOADING... 🚀")
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
        
        print(f"🌲 Moon Dev 7-Min Random Forest initialized with {lookback_window} lookback window")
        print(f"🎯 Predicting {prediction_horizon} steps ahead (7 minutes)")
        print("=" * 50)
    
    def load_liquidation_data(self, data_path):
        """
        🌙 Load Moon Dev's liquidation data for 7-minute analysis
        """
        print("📊 Loading liquidation data for Moon Dev's 7-min RF... 🌙")
        print(f"🔍 Moon Dev checking file path: {data_path}")
        
        if not os.path.exists(data_path):
            print(f"❌ Moon Dev, data file not found: {data_path}")
            return None
            
        print("✅ Moon Dev found the data file! Loading now... 🚀")
        
        # Load the liquidation data
        df = pd.read_csv(data_path)
        print(f"🎉 Moon Dev loaded {len(df):,} liquidation records! 🚀")
        print(f"📊 Moon Dev's data shape: {df.shape}")
        
        # ⏰ EXPERIMENT: 7-minute aggregation for Moon Dev!
        print("\n⏰ MOON DEV'S 7-MINUTE AGGREGATION EXPERIMENT ⏰")
        print("=" * 50)
        original_count = len(df)
        original_symbols = df['symbol'].nunique()
        
        print(f"🔍 Original liquidations: {original_count:,}")
        print(f"🌊 All symbols included: {original_symbols}")
        print(f"⏰ Using 7-minute bars - SUPERIOR signal clarity and noise reduction!")
        print(f"🎯 Hypothesis: 7-min balances signal capture with noise reduction")
        print(f"⚡ Sweet spot between 3-min speed and 15-min stability!")
        print(f"✅ All liquidation sizes included (learned from previous runs)")
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
    
    def create_focused_liquidation_features(self, df, time_window='7min'):
        """
        🎯 Moon Dev's FOCUSED liquidation feature engineering for 7-minute signals
        Based on successful backtesting: Side + Volume = Direction prediction!
        """
        print(f"🎯 Creating FOCUSED liquidation features for 7-minute signals! 🌙")
        print(f"💡 Core insight: Long liquidations → Buy signal, Short liquidations → Sell signal")
        print("🚀 Reducing feature noise, focusing on PROVEN signals for 7-min timeframe!")
        
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
        
        # Get BTC prices for targets
        btc_data = df[df['symbol'] == 'BTC'].copy()
        print(f"🪙 BTC records: {len(btc_data):,} out of {len(df):,} total")
        
        if len(btc_data) == 0:
            print("❌ No BTC records found!")
            return None
        
        btc_prices = btc_data.set_index('timestamp').resample(time_window).agg({
            'price': ['first', 'last', 'mean']
        }).fillna(method='ffill')
        
        # Flatten BTC price columns
        btc_prices.columns = [f'{col[0]}_{col[1]}' for col in btc_prices.columns]
        
        # Combine liquidations with BTC prices
        df_focused = all_liquidations.join(btc_prices, how='inner')
        
        # Create Moon Dev's focused features
        print("💰 Creating USD liquidation features for 7-minute signals...")
        
        # Get column names
        buy_qty_col = f'buy_{quantity_col}_sum'
        sell_qty_col = f'sell_{quantity_col}_sum'
        total_count_col = f'total_{quantity_col}_count'
        
        # Use price column
        price_col = 'price_last' if 'price_last' in df_focused.columns else 'price_mean'
        
        # USD liquidation volumes (Moon Dev's core signal!)
        df_focused['usd_long_liq'] = df_focused.get(buy_qty_col, 0) * df_focused.get(price_col, 0)
        df_focused['usd_short_liq'] = df_focused.get(sell_qty_col, 0) * df_focused.get(price_col, 0)
        df_focused['usd_liq_volume'] = df_focused['usd_long_liq'] + df_focused['usd_short_liq']
        
        # Net liquidation flow
        df_focused['usd_liq_net'] = df_focused['usd_short_liq'] - df_focused['usd_long_liq']
        
        # Liquidation imbalance ratio
        df_focused['liq_imbalance'] = df_focused['usd_liq_net'] / (df_focused['usd_liq_volume'] + 1e-8)
        
        # Liquidation velocity
        df_focused['liq_velocity'] = df_focused.get(total_count_col, 0)
        
        # Select focused features
        focused_feature_cols = ['usd_long_liq', 'usd_short_liq', 'usd_liq_volume', 'usd_liq_net', 'liq_imbalance', 'liq_velocity', price_col]
        available_cols = [col for col in focused_feature_cols if col in df_focused.columns]
        
        df_result = df_focused[available_cols].fillna(0).dropna()
        
        print(f"🎯 FOCUSED 7-MIN FEATURES CREATED! Shape: {df_result.shape}")
        print(f"📊 Features: {list(df_result.columns)}")
        print(f"💡 These are the PROVEN liquidation signals optimized for 7-minute timeframe!")
        
        return df_result
    
    def create_target_variable(self, df, target_return_threshold=TARGET_THRESHOLD):
        """
        🌙 Create Moon Dev's DIRECTION target variable for 7-minute signals
        """
        print(f"💡 Creating DIRECTION target for 7-minute Random Forest! 🌙")
        print(f"🎯 Direction threshold: {target_return_threshold*100:.2f}% (premium sensitivity for 7-min)")
        print("🚀 FOCUS: UP vs DOWN for 7-minute moves!")
        
        current_prices = df['price_last']
        future_prices = df['price_last'].shift(-self.prediction_horizon)
        
        # Calculate raw returns
        raw_returns = future_prices / current_prices - 1
        
        # Cap extreme returns
        df['future_return'] = np.where(
            np.isinf(raw_returns) | (raw_returns > MAX_RETURN_CAP), MAX_RETURN_CAP,
            np.where(raw_returns < MIN_RETURN_CAP, MIN_RETURN_CAP, raw_returns)
        )
        
        # Create binary direction target
        df['target_direction_binary'] = (df['future_return'] > target_return_threshold).astype(int)
        df['target_return'] = df['future_return']
        
        # Analysis
        up_moves = np.sum(df['target_direction_binary'] == 1)
        down_moves = np.sum(df['target_direction_binary'] == 0)
        total_moves = up_moves + down_moves
        
        print(f"🎯 7-MINUTE DIRECTION TARGETS CREATED! 🚀")
        print(f"📈 UP moves (1): {up_moves:,} ({up_moves/total_moves*100:.1f}%)")
        print(f"📉 DOWN moves (0): {down_moves:,} ({down_moves/total_moves*100:.1f}%)")
        print(f"🎲 Balance ratio: {min(up_moves, down_moves)/max(up_moves, down_moves):.2f}")
        
        return df

def main():
    """
    🌙 Moon Dev's main 7-minute Random Forest liquidation prediction pipeline
    """
    print("🚀 STARTING MOON DEV'S 7-MINUTE RANDOM FOREST LIQUIDATION PREDICTOR 🌙")
    print("=" * 60)
    
    # Initialize the predictor
    print("🏗️ Moon Dev initializing 7-minute Random Forest predictor...")
    predictor = RFLiquidationPredictor(lookback_window=9, prediction_horizon=1)
    
    # Load data
    print("📂 Moon Dev loading CLEAN BTC liquidation data...")
    data_path = "research/machine_learning/processed_data/liquidations_BTC_processed.csv"
    df = predictor.load_liquidation_data(data_path)
    
    if df is None:
        print("❌ Moon Dev, please check your data path!")
        return
    
    # Create focused features for 7-minute signals
    print("🎯 USING MOON DEV'S FOCUSED LIQUIDATION FEATURES FOR 7-MINUTE! 🚀")
    df_features = predictor.create_focused_liquidation_features(df, time_window='7min')
    
    if df_features is None:
        print("❌ Moon Dev, focused feature engineering failed!")
        return
        
    # Create targets
    df_targets = predictor.create_target_variable(df_features, target_return_threshold=TARGET_THRESHOLD)
    
    # Use focused features
    feature_columns = [col for col in LIQUIDATION_FOCUSED_FEATURES if col in df_targets.columns]
    print(f"🎯 FOCUSED: Using {len(feature_columns)} features: {feature_columns}")
    
    print("💡 IMPLEMENTING 7-MINUTE DIRECTION APPROACH! 🚀")
    print("🎯 Focus on UP/DOWN for balanced 7-minute moves!")
    
    # Prepare features
    print("🔄 Preparing 7-minute Random Forest features...")
    feature_matrix = df_targets[feature_columns].values
    targets = df_targets['target_direction_binary'].values
    
    # Remove invalid samples
    valid_mask = ~np.isnan(targets) & ~np.isinf(targets)
    X = feature_matrix[valid_mask]
    y = targets[valid_mask]
    
    print(f"📊 Final data shape: X={X.shape}, y={y.shape}")
    
    # Split data
    train_size = int(0.8 * len(X))
    val_size = int(0.1 * len(X))
    
    X_train, X_val, X_test = X[:train_size], X[train_size:train_size+val_size], X[train_size+val_size:]
    y_train, y_val, y_test = y[:train_size], y[train_size:train_size+val_size], y[train_size+val_size:]
    
    print(f"🔄 Moon Dev's 7-minute data split:")
    print(f"📊 Train: {X_train.shape[0]}, Val: {X_val.shape[0]}, Test: {X_test.shape[0]}")
    
    # Train Random Forest for 7-minute signals
    from sklearn.ensemble import RandomForestClassifier
    
    print("🌲 Training 7-minute Random Forest classifier! 🚀")
    model = RandomForestClassifier(
        n_estimators=N_ESTIMATORS,
        max_depth=MAX_DEPTH,
        min_samples_split=MIN_SAMPLES_SPLIT,
        min_samples_leaf=MIN_SAMPLES_LEAF,
        class_weight=CLASS_WEIGHT_STRATEGY,
        random_state=42,
        n_jobs=N_JOBS
    )
    
    model.fit(X_train, y_train)
    
    # Evaluate
    predictions = model.predict(X_test)
    probabilities = model.predict_proba(X_test)[:, 1]
    
    accuracy = accuracy_score(y_test, predictions)
    auc_score = roc_auc_score(y_test, probabilities)
    
    # Analysis
    up_mask = y_test == 1
    down_mask = y_test == 0
    up_accuracy = np.mean(predictions[up_mask] == y_test[up_mask]) if np.sum(up_mask) > 0 else 0
    down_accuracy = np.mean(predictions[down_mask] == y_test[down_mask]) if np.sum(down_mask) > 0 else 0
    
    print("🎯 MOON DEV'S 7-MINUTE RANDOM FOREST RESULTS 🌙")
    print("=" * 60)
    print(f"🚀 OVERALL ACCURACY: {accuracy:.4f} ({accuracy*100:.2f}%)")
    print(f"🏆 AUC-ROC SCORE: {auc_score:.4f}")
    print(f"📈 UP moves in test: {np.sum(up_mask):,} ({np.sum(up_mask)/len(y_test)*100:.1f}%)")
    print(f"📉 DOWN moves in test: {np.sum(down_mask):,} ({np.sum(down_mask)/len(y_test)*100:.1f}%)")
    print(f"🎯 UP accuracy: {up_accuracy:.4f} ({up_accuracy*100:.1f}%)")
    print(f"🎯 DOWN accuracy: {down_accuracy:.4f} ({down_accuracy*100:.1f}%)")
    print(f"🔮 Predicted UP: {np.sum(predictions == 1):,} ({np.sum(predictions == 1)/len(predictions)*100:.1f}%)")
    print(f"🔮 Predicted DOWN: {np.sum(predictions == 0):,} ({np.sum(predictions == 0)/len(predictions)*100:.1f}%)")
    print("=" * 60)
    
    print("🎉 MOON DEV'S 7-MINUTE RANDOM FOREST COMPLETE! 🚀🌙")

if __name__ == "__main__":
    main() 