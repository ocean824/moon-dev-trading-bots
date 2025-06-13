"""
🌙 MOON DEV'S MINIMAL 2-FEATURE LSTM LIQUIDATION PREDICTOR - 15 MINUTE VERSION 🚀
Based on Moon Dev's insight: Only Long Liquidations + Short Liquidations
🎯 HYPOTHESIS: 15-minute timeframes capture liquidation effects before they dissipate!
⚡ FAST enough to catch liquidation cascades, SLOW enough to filter noise!
"""

# 🌙 MOON DEV'S MINIMAL CONFIGURATION 🚀
LOCAL_MODE = True
EPOCHS = 10 if LOCAL_MODE else 50
BATCH_SIZE = 32
LEARNING_RATE = 0.001
DATA_SAMPLE_FRACTION = 0.1 if LOCAL_MODE else 1.0  # 10% for testing
LOOKBACK_WINDOW = 24  # 6 hours of 15-minute data (24 × 15min = 6 hours)
PREDICTION_HORIZON = 1  # Predict 15 minutes ahead
TARGET_THRESHOLD = 0.003  # 0.3% threshold

# 🚨 MOON DEV'S CLASS IMBALANCE SOLUTIONS! 🚨
USE_CLASS_WEIGHTS = True  # Add class weights to combat imbalance
USE_SMOTE = False  # SMOTE oversampling (experimental)
FOCAL_LOSS_ALPHA = 0.9  # Higher alpha = more focus on minority class (UP moves)

# 🎯 MOON DEV'S 2-FEATURE APPROACH - FLIPPED LOGIC!
MINIMAL_FEATURES = [
    'usd_long_liquidations',   # SELL orders - Long liquidations (BEARISH signal - selling pressure)
    'usd_short_liquidations'   # BUY orders - Short liquidations (BULLISH signal - forced covering)
]

print("🌙 MOON DEV'S MINIMAL 2-FEATURE LSTM PREDICTOR - 15 MINUTE VERSION! 🚀")
print(f"🎯 Features: {MINIMAL_FEATURES}")
print(f"⏰ Timeframe: 15-minute bars (FAST liquidation effects!)")
print(f"🔄 Lookback: {LOOKBACK_WINDOW} periods (6 hours of 15-min data)")
print("=" * 60)

import pandas as pd
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, BatchNormalization
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.metrics import accuracy_score, confusion_matrix, roc_auc_score, roc_curve
import matplotlib.pyplot as plt
import warnings
import os
from datetime import datetime
warnings.filterwarnings('ignore')

class MinimalLSTMLiquidationPredictor:
    def __init__(self, lookback_window=LOOKBACK_WINDOW, prediction_horizon=PREDICTION_HORIZON, scaler_type='minmax'):
        """
        🌙 Moon Dev's Minimal 2-Feature LSTM Predictor
        
        Args:
            scaler_type: 'standard' for StandardScaler, 'minmax' for MinMaxScaler (better for LSTM!)
        """
        self.lookback_window = lookback_window
        self.prediction_horizon = prediction_horizon
        self.model = None
        
        # 🎯 MOON DEV'S SCALER CHOICE! MinMax is often better for LSTM! 🚀
        if scaler_type == 'minmax':
            self.feature_scaler = MinMaxScaler(feature_range=(0, 1))  # Perfect for LSTM activations!
            print("⚖️ Moon Dev using MinMaxScaler [0,1] - OPTIMAL for LSTM! 🌙")
        else:
            self.feature_scaler = StandardScaler()
            print("⚖️ Moon Dev using StandardScaler (mean=0, std=1)")
        
        self.scaler_type = scaler_type
        self.is_trained = False
        
        print(f"🎯 Moon Dev Minimal LSTM initialized:")
        print(f"   📊 Features: 2 only (long + short liquidations)")
        print(f"   ⚖️ Scaler: {scaler_type.upper()} ({'[0,1] range' if scaler_type == 'minmax' else 'mean=0, std=1'})")
        print(f"   ⏰ Lookback: {lookback_window} periods (15-minute bars)")
        print(f"   🔮 Prediction: {prediction_horizon} period ahead (15 minutes)")
        print("=" * 50)
    
    def load_liquidation_data(self, data_path):
        """🌙 Load Moon Dev's liquidation data"""
        print("📂 Loading liquidation data for Moon Dev's minimal model... 🌙")
        
        if not os.path.exists(data_path):
            print(f"❌ Moon Dev, data file not found: {data_path}")
            return None
            
        df = pd.read_csv(data_path)
        print(f"✅ Moon Dev loaded {len(df):,} liquidation records! 🚀")
        print(f"📊 Data shape: {df.shape}")
        
        # Handle timestamp
        if 'datetime' in df.columns:
            df['timestamp'] = pd.to_datetime(df['datetime'])
        elif 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        else:
            print("❌ No timestamp column found!")
            return None
            
        df = df.sort_values('timestamp').reset_index(drop=True)
        print(f"📅 Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        
        return df
    
    def create_minimal_features(self, df, time_window='15min'):
        """
        🎯 Moon Dev's MINIMAL feature engineering - ONLY 2 features!
        Based on YOUR liquidation classification logic!
        """
        print("🎯 Creating Moon Dev's MINIMAL 2-feature dataset... 🌙")
        print(f"💡 Using YOUR liquidation logic: SELL=Long Liq (bullish), BUY=Short Liq (bearish)")
        
        # LOCAL_MODE sampling
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
        print(f"📊 Using quantity column: '{quantity_col}'")
        
        # Set timestamp as index
        df_indexed = df.set_index('timestamp')
        
        # 🔄 MOON DEV'S FLIPPED LIQUIDATION CLASSIFICATION! (Testing opposite logic)
        print("🔄 Applying Moon Dev's FLIPPED liquidation classification...")
        print("   💚 BUY orders = Short liquidations (bullish - shorts forced to cover)")
        print("   ❤️ SELL orders = Long liquidations (bearish - more selling pressure)")
        
        # Separate liquidations by FLIPPED classification
        long_liquidations = df_indexed[df_indexed['side'].str.upper() == 'SELL'].resample(time_window).agg({
            quantity_col: 'sum',
            'price': 'mean'
        }).fillna(0)
        
        short_liquidations = df_indexed[df_indexed['side'].str.upper() == 'BUY'].resample(time_window).agg({
            quantity_col: 'sum', 
            'price': 'mean'
        }).fillna(0)
        
        # Get BTC prices for targets (using BTC only for price movements)
        btc_data = df[df['symbol'] == 'BTC'].copy()
        print(f"🪙 BTC records: {len(btc_data):,} out of {len(df):,} total")
        
        if len(btc_data) == 0:
            print("❌ No BTC records found!")
            return None
        
        btc_prices = btc_data.set_index('timestamp').resample(time_window).agg({
            'price': ['first', 'last', 'mean']
        }).fillna(method='ffill')
        
        # Create the minimal dataset
        df_minimal = pd.DataFrame(index=btc_prices.index)
        
        # 🚀 MOON DEV'S 2 FEATURES (USD VALUES) - FLIPPED LOGIC!
        print("💰 Creating the 2 core liquidation features with FLIPPED logic...")
        
        # Feature 1: USD Long Liquidations (SELL orders - BEARISH signal - selling pressure)
        long_qty = long_liquidations[quantity_col] if quantity_col in long_liquidations.columns else 0
        long_price = long_liquidations['price'] if 'price' in long_liquidations.columns else btc_prices[('price', 'mean')]
        df_minimal['usd_long_liquidations'] = (long_qty * long_price).fillna(0)
        
        # Feature 2: USD Short Liquidations (BUY orders - BULLISH signal - forced covering)  
        short_qty = short_liquidations[quantity_col] if quantity_col in short_liquidations.columns else 0
        short_price = short_liquidations['price'] if 'price' in short_liquidations.columns else btc_prices[('price', 'mean')]
        df_minimal['usd_short_liquidations'] = (short_qty * short_price).fillna(0)
        
        # Price targets (only BTC)
        df_minimal['price_last'] = btc_prices[('price', 'last')]
        
        # Clean data
        df_minimal = df_minimal.fillna(0).dropna()
        
        print(f"🎉 Moon Dev's MINIMAL features created! Shape: {df_minimal.shape}")
        print(f"📊 Features: {list(df_minimal.columns)}")
        print(f"💡 Long liquidations range: ${df_minimal['usd_long_liquidations'].min():,.0f} - ${df_minimal['usd_long_liquidations'].max():,.0f}")
        print(f"💡 Short liquidations range: ${df_minimal['usd_short_liquidations'].min():,.0f} - ${df_minimal['usd_short_liquidations'].max():,.0f}")
        
        return df_minimal
    
    def create_target_variable(self, df, target_return_threshold=TARGET_THRESHOLD):
        """🎯 Create direction targets for Moon Dev with threshold analysis"""
        print(f"🎯 Creating direction targets with threshold analysis... 🌙")
        
        # Calculate future returns
        future_prices = df['price_last'].shift(-self.prediction_horizon)
        current_prices = df['price_last']
        
        # Calculate returns with extreme value capping
        raw_returns = future_prices / current_prices - 1
        df['future_return'] = np.where(
            np.isinf(raw_returns) | (raw_returns > 10), 10,
            np.where(raw_returns < -0.99, -0.99, raw_returns)
        )
        
        # 🚨 MOON DEV'S THRESHOLD ANALYSIS! 🚨
        print("🔍 THRESHOLD ANALYSIS - Finding optimal balance:")
        test_thresholds = [0.001, 0.002, 0.003, 0.005, 0.01]  # 0.1% to 1.0%
        
        for thresh in test_thresholds:
            test_targets = (df['future_return'] > thresh).astype(int)
            up_pct = np.mean(test_targets) * 100
            down_pct = 100 - up_pct
            balance_ratio = min(up_pct, down_pct) / max(up_pct, down_pct)
            
            print(f"   📊 {thresh*100:.1f}% threshold: UP {up_pct:.1f}% | DOWN {down_pct:.1f}% | Balance: {balance_ratio:.2f}")
        
        # 🎯 ADAPTIVE THRESHOLD SELECTION!
        print("🎯 Moon Dev's adaptive threshold selection...")
        best_threshold = target_return_threshold
        best_balance = 0
        
        for thresh in test_thresholds:
            test_targets = (df['future_return'] > thresh).astype(int)
            up_pct = np.mean(test_targets) * 100
            down_pct = 100 - up_pct
            balance_ratio = min(up_pct, down_pct) / max(up_pct, down_pct)
            
            if balance_ratio > best_balance and up_pct >= 25:  # At least 25% UP moves
                best_balance = balance_ratio
                best_threshold = thresh
        
        if best_threshold != target_return_threshold:
            print(f"🚀 BETTER THRESHOLD FOUND: {best_threshold*100:.1f}% (balance: {best_balance:.2f})")
            target_return_threshold = best_threshold
        else:
            print(f"✅ Using original threshold: {target_return_threshold*100:.1f}%")
        
        # Binary direction target (UP/DOWN) with chosen threshold
        df['target_direction'] = (df['future_return'] > target_return_threshold).astype(int)
        
        # Analysis
        up_moves = np.sum(df['target_direction'] == 1)
        down_moves = np.sum(df['target_direction'] == 0)
        total_moves = up_moves + down_moves
        
        print(f"📈 FINAL TARGETS - UP moves (1): {up_moves:,} ({up_moves/total_moves*100:.1f}%)")
        print(f"📉 FINAL TARGETS - DOWN moves (0): {down_moves:,} ({down_moves/total_moves*100:.1f}%)")
        print(f"⚖️ Balance ratio: {min(up_moves, down_moves)/max(up_moves, down_moves):.2f}")
        
        return df
    
    def prepare_sequences(self, df):
        """🔄 Prepare LSTM sequences with ONLY 2 features"""
        print("🔄 Preparing minimal LSTM sequences... 🚀")
        
        # Use only the 2 features
        feature_columns = MINIMAL_FEATURES
        
        # Clean data
        df_clean = df.dropna(subset=['target_direction'])
        print(f"✅ Clean data shape: {df_clean.shape}")
        
        # Extract features and targets
        features = df_clean[feature_columns].values
        targets = df_clean['target_direction'].values
        
        print(f"📊 Feature matrix shape: {features.shape}")
        print(f"🎯 Target shape: {targets.shape}")
        
        # Scale features
        print("⚖️ Moon Dev scaling features...")
        print(f"📊 Original feature ranges:")
        print(f"   💰 Long liquidations: ${features[:, 0].min():,.0f} - ${features[:, 0].max():,.0f}")
        print(f"   💰 Short liquidations: ${features[:, 1].min():,.0f} - ${features[:, 1].max():,.0f}")
        
        features_scaled = self.feature_scaler.fit_transform(features)
        
        print(f"📊 Scaled feature ranges ({self.scaler_type}):")
        print(f"   ⚖️ Long liquidations: {features_scaled[:, 0].min():.4f} - {features_scaled[:, 0].max():.4f}")
        print(f"   ⚖️ Short liquidations: {features_scaled[:, 1].min():.4f} - {features_scaled[:, 1].max():.4f}")
        print(f"🚀 Scaling helps LSTM gates work optimally! 🌙")
        
        # Create sequences
        X, y = [], []
        
        for i in range(self.lookback_window, len(features_scaled)):
            X.append(features_scaled[i-self.lookback_window:i])
            y.append(targets[i])
        
        X = np.array(X)
        y = np.array(y)
        
        print(f"🎉 Minimal sequences ready! Shape: {X.shape}")
        print(f"🎯 Target shape: {y.shape}")
        print(f"📊 Each sequence: {self.lookback_window} periods × 2 features (15-min bars)")
        
        return X, y
    
    def build_minimal_model(self, input_shape):
        """🏗️ Build Moon Dev's minimal LSTM model with enhanced class balancing"""
        print("🏗️ Building Moon Dev's ENHANCED MINIMAL LSTM model... 🌙")
        
        model = Sequential([
            # Smaller architecture for 2 features
            LSTM(32, return_sequences=True, input_shape=input_shape, dropout=0.2),
            BatchNormalization(),
            
            LSTM(16, return_sequences=False, dropout=0.2),  
            BatchNormalization(),
            
            Dense(8, activation='relu'),
            Dropout(0.3),
            Dense(1, activation='sigmoid')  # Binary classification
        ])
        
        # 🎯 ENHANCED Focal Loss for severe class imbalance
        def focal_loss(alpha=FOCAL_LOSS_ALPHA, gamma=2.0):
            def loss_fn(y_true, y_pred):
                epsilon = tf.keras.backend.epsilon()
                y_pred = tf.clip_by_value(y_pred, epsilon, 1. - epsilon)
                
                pt_1 = tf.where(tf.equal(y_true, 1), y_pred, tf.ones_like(y_pred))
                pt_0 = tf.where(tf.equal(y_true, 0), y_pred, tf.zeros_like(y_pred))
                
                loss = -alpha * tf.pow(1. - pt_1, gamma) * tf.math.log(pt_1) - \
                       (1 - alpha) * tf.pow(pt_0, gamma) * tf.math.log(1. - pt_0)
                return tf.reduce_mean(loss)
            return loss_fn
        
        model.compile(
            optimizer=Adam(learning_rate=LEARNING_RATE),
            loss=focal_loss(alpha=FOCAL_LOSS_ALPHA, gamma=2.0),  # Enhanced focus on UP moves
            metrics=['accuracy']
        )
        
        print(f"🎯 Enhanced model compiled with Focal Loss (alpha={FOCAL_LOSS_ALPHA})!")
        model.summary()
        return model
    
    def train_model(self, X_train, y_train, X_val, y_val):
        """🎓 Train Moon Dev's minimal model with enhanced class balancing"""
        print("🎓 Training Moon Dev's ENHANCED MINIMAL model... 🚀")
        
        # 🚨 CALCULATE CLASS WEIGHTS FOR SEVERE IMBALANCE! 🚨
        if USE_CLASS_WEIGHTS:
            from sklearn.utils.class_weight import compute_class_weight
            
            # Calculate class weights
            classes = np.unique(y_train)
            class_weights = compute_class_weight('balanced', classes=classes, y=y_train)
            class_weight_dict = dict(zip(classes, class_weights))
            
            print("🚨 MOON DEV'S CLASS IMBALANCE ANALYSIS:")
            up_count = np.sum(y_train == 1)
            down_count = np.sum(y_train == 0)
            total_count = len(y_train)
            
            print(f"   📈 UP moves: {up_count:,} ({up_count/total_count*100:.1f}%)")
            print(f"   📉 DOWN moves: {down_count:,} ({down_count/total_count*100:.1f}%)")
            print(f"   ⚖️ Imbalance ratio: {max(up_count, down_count)/min(up_count, down_count):.1f}:1")
            print(f"   🎯 Class weights: {class_weight_dict}")
            print(f"   🚀 This will make UP moves {class_weight_dict.get(1, 1):.1f}x more important!")
        else:
            class_weight_dict = None
            print("⚠️ Training WITHOUT class weights (may struggle with imbalance)")
        
        # Build model
        self.model = self.build_minimal_model(input_shape=(X_train.shape[1], X_train.shape[2]))
        
        # Callbacks
        callbacks = [
            EarlyStopping(monitor='val_loss', patience=7, restore_best_weights=True),  # More patience
            ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=3, min_lr=1e-7)
        ]
        
        # Train with class weights
        history = self.model.fit(
            X_train, y_train,
            validation_data=(X_val, y_val),
            epochs=EPOCHS,
            batch_size=BATCH_SIZE,
            callbacks=callbacks,
            class_weight=class_weight_dict,  # 🚀 KEY ADDITION!
            verbose=1
        )
        
        self.is_trained = True
        print("🎉 Moon Dev's enhanced training complete! 🚀")
        return history
    
    def evaluate_model(self, X_test, y_test):
        """📊 Evaluate Moon Dev's minimal model"""
        print("📊 Evaluating Moon Dev's MINIMAL model... 🚀")
        
        # Make predictions
        predictions_prob = self.model.predict(X_test).flatten()
        predictions = (predictions_prob > 0.5).astype(int)
        
        # Calculate metrics
        accuracy = accuracy_score(y_test, predictions)
        
        # UP/DOWN analysis
        up_mask = y_test == 1
        down_mask = y_test == 0
        
        up_accuracy = np.mean(predictions[up_mask] == y_test[up_mask]) if np.sum(up_mask) > 0 else 0
        down_accuracy = np.mean(predictions[down_mask] == y_test[down_mask]) if np.sum(down_mask) > 0 else 0
        
        up_count = np.sum(up_mask)
        down_count = np.sum(down_mask)
        predicted_up = np.sum(predictions == 1)
        predicted_down = np.sum(predictions == 0)
        
        # AUC-ROC
        auc_score = roc_auc_score(y_test, predictions_prob)
        
        print("🎯 MOON DEV'S MINIMAL MODEL RESULTS 🌙")
        print("=" * 60)
        print(f"🎪 Overall Accuracy: {accuracy:.4f}")
        print(f"🏆 AUC-ROC Score: {auc_score:.4f}")
        print(f"🎯 Goal: AUC ≥ 0.70 {'✅ ACHIEVED!' if auc_score >= 0.70 else '❌ MISSED'}")
        print("")
        print(f"📈 UP moves in test: {up_count:,} ({up_count/len(y_test)*100:.1f}%)")
        print(f"📉 DOWN moves in test: {down_count:,} ({down_count/len(y_test)*100:.1f}%)")
        print(f"🎯 UP accuracy: {up_accuracy:.4f} ({up_accuracy*100:.1f}%)")
        print(f"🎯 DOWN accuracy: {down_accuracy:.4f} ({down_accuracy*100:.1f}%)")
        print("")
        print(f"🔮 Predicted UP: {predicted_up:,} ({predicted_up/len(predictions)*100:.1f}%)")
        print(f"🔮 Predicted DOWN: {predicted_down:,} ({predicted_down/len(predictions)*100:.1f}%)")
        
        if predicted_up == 0:
            print("🚨 DOWN-ONLY PREDICTOR! (Bad)")
        elif predicted_up > 0:
            print("✅ PREDICTS BOTH DIRECTIONS! (Good)")
        
        print("=" * 60)
        
        return {
            'accuracy': accuracy,
            'auc_score': auc_score,
            'up_accuracy': up_accuracy,
            'down_accuracy': down_accuracy,
            'predictions': predictions,
            'predictions_prob': predictions_prob,
            'actuals': y_test
        }

def main():
    """🌙 Moon Dev's minimal 2-feature pipeline"""
    print("🚀 STARTING MOON DEV'S MINIMAL 2-FEATURE PREDICTOR 🌙")
    print("=" * 60)
    
    # Initialize
    predictor = MinimalLSTMLiquidationPredictor()
    
    # Load data
    data_path = "/Users/md/Dropbox/dev/github/moon-dev-trading-bots/research/machine_learning/processed_data/liquidations_BTC_processed.csv"
    df = predictor.load_liquidation_data(data_path)
    
    if df is None:
        print("❌ Please check data path!")
        return
    
    # Create minimal features (15-minute timeframe)
    df_features = predictor.create_minimal_features(df, time_window='15min')
    if df_features is None:
        return
    
    # Create targets
    df_targets = predictor.create_target_variable(df_features)
    
    # Prepare sequences
    X, y = predictor.prepare_sequences(df_targets)
    
    # Split data
    train_size = int(0.8 * len(X))
    val_size = int(0.1 * len(X))
    
    X_train = X[:train_size]
    X_val = X[train_size:train_size+val_size] 
    X_test = X[train_size+val_size:]
    
    y_train = y[:train_size]
    y_val = y[train_size:train_size+val_size]
    y_test = y[train_size+val_size:]
    
    print(f"📊 Data split: Train: {len(X_train)}, Val: {len(X_val)}, Test: {len(X_test)}")
    
    # Train
    history = predictor.train_model(X_train, y_train, X_val, y_val)
    
    # Evaluate
    metrics = predictor.evaluate_model(X_test, y_test)
    
    print("🎉 MOON DEV'S MINIMAL MODEL COMPLETE! 🚀🌙")
    print("=" * 60)

if __name__ == "__main__":
    main() 