#!/usr/bin/env python3
"""
🌙 MOON DEV'S LSTM HYPERPARAMETER OPTIMIZER 🌙
==============================================

INSPIRED BY RF SUCCESS: Your LSTM params might be off for time series!
Let's find the OPTIMAL parameters for LSTM liquidation prediction!

Random Forest Results: UP accuracy 0.8% → 28.2% (282x improvement!)
Now let's fix the LSTM DOWN-ONLY predictor problem! 🚀

Author: Moon Dev 🚀 (Following RF success!)
"""

import pandas as pd
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, BatchNormalization
from tensorflow.keras.optimizers import Adam, RMSprop
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import f1_score, accuracy_score, confusion_matrix
from sklearn.preprocessing import StandardScaler, MinMaxScaler
import warnings
import os
import time
import json
from datetime import datetime
warnings.filterwarnings('ignore')

# 🌙 MOON DEV'S LSTM OPTIMIZATION CONFIGURATION 🌙
FAST_MODE = True  # Set to False for full optimization (much longer)
RANDOM_STATE = 42
CV_FOLDS = 1 if FAST_MODE else 5  # 🚀 SKIP CV: Just train/test split for speed!
SCORING_METRIC = 'f1_macro'

# 🎯 LSTM HYPERPARAMETER SEARCH SPACES - INSANELY FAST! ⚡
LSTM_PARAM_GRID = {
    # Architecture parameters - MINIMAL options for speed
    'lstm_units_1': [32, 64] if FAST_MODE else [32, 64, 128, 256],  
    'lstm_units_2': [16, 32] if FAST_MODE else [16, 32, 64, 128],   
    'lstm_units_3': [8, 16] if FAST_MODE else [8, 16, 32, 64],      
    'num_lstm_layers': [2] if FAST_MODE else [1, 2, 3],             
    
    # Regularization parameters - FIXED for speed
    'dropout_rate': [0.2] if FAST_MODE else [0.0, 0.1, 0.2, 0.3, 0.4, 0.5],          
    'recurrent_dropout_rate': [0.1] if FAST_MODE else [0.0, 0.1, 0.2, 0.3],           
    'dense_dropout_rate': [0.3] if FAST_MODE else [0.2, 0.3, 0.4, 0.5],               
    
    # Training parameters  
    'learning_rate': [0.001, 0.005] if FAST_MODE else [0.0001, 0.0005, 0.001, 0.005, 0.01],  
    'optimizer': ['adam'] if FAST_MODE else ['adam', 'rmsprop'],                               
    'batch_size': [32] if FAST_MODE else [16, 32, 64, 128],                                    
    
    # Sequence parameters - MUCH SHORTER for speed! ⚡
    'lookback_window': [10] if FAST_MODE else [30, 60, 90, 120],      # 🚀 30→10 for SPEED!
    'prediction_horizon': [5] if FAST_MODE else [1, 3, 5, 10],       
    
    # Data scaling
    'feature_scaler': ['standard'] if FAST_MODE else ['standard', 'minmax'],  
    
    # Advanced parameters
    'use_batch_norm': [True] if FAST_MODE else [True, False],         
    'gradient_clip_norm': [1.0] if FAST_MODE else [0.5, 1.0, 2.0]    
}

def load_lstm_data():
    """📊 Load data for LSTM optimization"""
    print("📊 Loading liquidation data for LSTM optimization...")
    
    # 🚨 FIX: Use the correct data path (same as RF model!)
    data_path = "/Users/md/Dropbox/dev/github/moon-dev-trading-bots/research/machine_learning/processed_data/liquidations_BTC_processed.csv"
    
    if not os.path.exists(data_path):
        print(f"❌ Data file not found: {data_path}")
        print("🔍 Let's check what data files we have...")
        return None, None
    
    df = pd.read_csv(data_path)
    print(f"✅ Loaded {len(df):,} liquidation records")
    
    # 🚨 FIX: Handle timestamp conversion more robustly
    if 'timestamp' not in df.columns:
        possible_cols = ['datetime', 'time', 'date', 'ts']
        timestamp_found = False
        for col in possible_cols:
            if col in df.columns:
                df['timestamp'] = pd.to_datetime(df[col])
                timestamp_found = True
                print(f"✅ Using timestamp column: {col}")
                break
        
        if not timestamp_found:
            print("❌ No timestamp column found! Creating artificial timestamps...")
            df['timestamp'] = pd.date_range(start='2024-01-01', periods=len(df), freq='5min')
    else:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Basic data validation
    if len(df) < 1000:
        print(f"❌ Not enough data: {len(df)} records (need at least 1000)")
        return None, None
    
    # 🚨 FIX: Handle BTC filtering more robustly
    if 'symbol' in df.columns:
        btc_data = df[df['symbol'] == 'BTC'].copy()
        print(f"🪙 BTC records: {len(btc_data):,}")
        if len(btc_data) == 0:
            print("❌ No BTC records found! Using all data instead...")
            btc_data = df.copy()
    else:
        btc_data = df.copy()
        print("📊 No symbol column found, using all data")
    
    if FAST_MODE:
        # Take most recent 2k records for INSANE speed! ⚡
        btc_data = btc_data.tail(2000).reset_index(drop=True)  # 🚀 10k→2k for INSANE speed!
        print(f"⚡ INSANE-SPEED mode: Using {len(btc_data):,} recent records")
    
    # Create basic features with proper error handling
    btc_data = btc_data.sort_values('timestamp').reset_index(drop=True)
    
    # 🚨 FIX: Robust price handling
    if 'price' not in btc_data.columns:
        print("❌ No price column found!")
        return None, None
    
    # Price features with NaN handling
    btc_data['price_change'] = btc_data['price'].pct_change().fillna(0)
    btc_data['price_ma_5'] = btc_data['price'].rolling(5, min_periods=1).mean()
    
    # 🚨 FIX: Robust quantity handling  
    qty_col = None
    for col in ['original_quantity', 'quantity', 'qty', 'amount']:
        if col in btc_data.columns:
            qty_col = col
            break
    
    if qty_col is None:
        print("❌ No quantity column found!")
        return None, None
    
    btc_data['quantity'] = pd.to_numeric(btc_data[qty_col], errors='coerce').fillna(0)
    btc_data['quantity_ma_5'] = btc_data['quantity'].rolling(5, min_periods=1).mean()
    
    # 🚨 FIX: Robust side handling
    if 'side' in btc_data.columns:
        btc_data['side_numeric'] = (btc_data['side'].str.upper() == 'BUY').astype(int)
    else:
        btc_data['side_numeric'] = np.random.randint(0, 2, size=len(btc_data))  # Random for demo
        print("⚠️ No side column found, using random values")
    
    # USD liquidation volume
    btc_data['usd_liq_volume'] = btc_data['quantity'] * btc_data['price']
    btc_data['usd_liq_ma_5'] = btc_data['usd_liq_volume'].rolling(5, min_periods=1).mean()
    
    # 🚨 FIX: Robust target creation with validation
    btc_data['target'] = (btc_data['price'].shift(-5) > btc_data['price']).astype(int)
    
    # Select features that exist
    all_features = ['price', 'price_change', 'price_ma_5', 'quantity', 'quantity_ma_5', 
                   'side_numeric', 'usd_liq_volume', 'usd_liq_ma_5']
    feature_columns = [col for col in all_features if col in btc_data.columns]
    
    # Remove NaN rows and validate
    initial_len = len(btc_data)
    btc_data = btc_data.dropna().reset_index(drop=True)
    final_len = len(btc_data)
    
    print(f"📊 Data cleaning: {initial_len:,} → {final_len:,} records ({final_len/initial_len*100:.1f}% kept)")
    
    if final_len < 500:
        print(f"❌ Not enough clean data: {final_len} records (need at least 500)")
        return None, None
    
    up_moves = np.sum(btc_data['target'])
    up_pct = up_moves / len(btc_data) * 100
    
    print(f"📊 Final data shape: {btc_data.shape}")
    print(f"📈 UP moves: {up_moves:,} ({up_pct:.1f}%)")
    print(f"🎯 Features: {feature_columns}")
    
    return btc_data, feature_columns

def prepare_lstm_sequences(df, feature_columns, lookback_window, prediction_horizon):
    """🔗 Prepare LSTM sequences with better error handling"""
    try:
        # Validate inputs
        if df is None or len(df) == 0:
            print("❌ Empty dataframe!")
            return None, None
        
        if not feature_columns:
            print("❌ No feature columns!")
            return None, None
        
        # Get features with validation
        missing_cols = [col for col in feature_columns if col not in df.columns]
        if missing_cols:
            print(f"⚠️ Missing columns: {missing_cols}")
            feature_columns = [col for col in feature_columns if col in df.columns]
        
        if not feature_columns:
            print("❌ No valid feature columns!")
            return None, None
        
        features = df[feature_columns].values
        targets = df['target'].values
        
        # 🚨 FIX: Better data validation
        if len(features) != len(targets):
            print(f"❌ Feature/target length mismatch: {len(features)} vs {len(targets)}")
            return None, None
        
        if len(features) < lookback_window + prediction_horizon + 10:
            print(f"❌ Not enough data for sequences: {len(features)} (need at least {lookback_window + prediction_horizon + 10})")
            return None, None
        
        # Scale features with better handling
        scaler = StandardScaler()
        
        # Handle potential NaN or infinite values
        features_clean = np.nan_to_num(features, nan=0.0, posinf=1e6, neginf=-1e6)
        features_scaled = scaler.fit_transform(features_clean)
        
        # 🚨 FIX: More robust sequence creation
        X, y = [], []
        max_idx = len(features_scaled) - prediction_horizon
        
        for i in range(lookback_window, max_idx):
            try:
                sequence = features_scaled[i-lookback_window:i]
                target = targets[i + prediction_horizon]
                
                # Validate sequence and target
                if sequence.shape[0] == lookback_window and not np.isnan(target):
                    X.append(sequence)
                    y.append(target)
            except Exception as e:
                continue  # Skip invalid sequences
        
        if len(X) == 0:
            print("❌ No valid sequences created!")
            return None, None
        
        X_array = np.array(X)
        y_array = np.array(y)
        
        print(f"✅ Created {len(X_array)} sequences: {X_array.shape}")
        print(f"📈 UP targets: {np.sum(y_array)} ({np.mean(y_array)*100:.1f}%)")
        
        return X_array, y_array
        
    except Exception as e:
        print(f"❌ Sequence preparation failed: {str(e)}")
        return None, None

def build_lstm_model(params, input_shape):
    """🏗️ Build LSTM model with better error handling"""
    try:
        # 🚨 FIX: Validate input shape
        if len(input_shape) != 2:
            print(f"❌ Invalid input shape: {input_shape}")
            return None
        
        lookback_steps, n_features = input_shape
        
        if lookback_steps <= 0 or n_features <= 0:
            print(f"❌ Invalid dimensions: steps={lookback_steps}, features={n_features}")
            return None
        
        model = Sequential()
        
        # 🚨 FIX: More robust LSTM layer construction
        # First LSTM layer
        return_sequences = (params['num_lstm_layers'] > 1)
        
        model.add(LSTM(
            int(params['lstm_units_1']),  # Ensure integer
            return_sequences=return_sequences,
            input_shape=input_shape,
            dropout=float(params['dropout_rate']),
            recurrent_dropout=float(params['recurrent_dropout_rate'])
        ))
        
        if params['use_batch_norm']:
            model.add(BatchNormalization())
        
        # Second LSTM layer (if needed)
        if params['num_lstm_layers'] >= 2:
            return_sequences = (params['num_lstm_layers'] > 2)
            model.add(LSTM(
                int(params['lstm_units_2']),
                return_sequences=return_sequences,
                dropout=float(params['dropout_rate']),
                recurrent_dropout=float(params['recurrent_dropout_rate'])
            ))
            
            if params['use_batch_norm']:
                model.add(BatchNormalization())
        
        # Third LSTM layer (if needed)
        if params['num_lstm_layers'] >= 3:
            model.add(LSTM(
                int(params['lstm_units_3']),
                return_sequences=False,
                dropout=float(params['dropout_rate']),
                recurrent_dropout=float(params['recurrent_dropout_rate'])
            ))
            
            if params['use_batch_norm']:
                model.add(BatchNormalization())
        
        # 🚨 FIX: More robust dense layers
        model.add(Dense(16, activation='relu'))
        model.add(Dropout(float(params['dense_dropout_rate'])))
        
        model.add(Dense(8, activation='relu'))
        model.add(Dropout(float(params['dense_dropout_rate'])))
        
        # Output layer
        model.add(Dense(1, activation='sigmoid'))
        
        # 🚨 FIX: Better optimizer configuration
        if params['optimizer'] == 'adam':
            optimizer = Adam(
                learning_rate=float(params['learning_rate']), 
                clipnorm=float(params['gradient_clip_norm'])
            )
        else:
            optimizer = RMSprop(
                learning_rate=float(params['learning_rate']),
                clipnorm=float(params['gradient_clip_norm'])
            )
        
        model.compile(
            optimizer=optimizer, 
            loss='binary_crossentropy', 
            metrics=['accuracy']
        )
        
        return model
        
    except Exception as e:
        print(f"❌ Model building failed: {str(e)}")
        return None

def evaluate_lstm_params(params, df, feature_columns):
    """📊 Evaluate LSTM parameters with better error handling"""
    try:
        print(f"🎯 Testing: {params['lstm_units_1']}/{params.get('lstm_units_2', 0)} units, LR: {params['learning_rate']}")
        
        # Prepare sequences with validation
        X, y = prepare_lstm_sequences(df, feature_columns, params['lookback_window'], params['prediction_horizon'])
        
        if X is None or y is None:
            print("   ❌ Failed: Sequence preparation failed")
            return 0.0
        
        if len(X) < 1000:
            print(f"   ❌ Failed: Not enough sequences ({len(X)} < 1000)")
            return 0.0
        
        # 🚨 FIX: Validate data before CV
        if np.any(np.isnan(X)) or np.any(np.isnan(y)):
            print("   ❌ Failed: NaN values in data")
            return 0.0
        
        # Time series cross validation - SKIP for speed!
        if CV_FOLDS > 1:
            tscv = TimeSeriesSplit(n_splits=CV_FOLDS)
            f1_scores = []
            
            for fold, (train_idx, val_idx) in enumerate(tscv.split(X)):
                try:
                    X_train, X_val = X[train_idx], X[val_idx]
                    y_train, y_val = y[train_idx], y[val_idx]
                    
                    # Validate fold data
                    if len(X_train) < 50 or len(X_val) < 10:
                        print(f"   ⚠️ Fold {fold}: Too little data")
                        continue
                    
                    # Build model
                    model = build_lstm_model(params, input_shape=(X_train.shape[1], X_train.shape[2]))
                    
                    if model is None:
                        print(f"   ❌ Fold {fold}: Model building failed")
                        continue
                    
                    # Callbacks
                    callbacks = [
                        EarlyStopping(monitor='val_loss', patience=2, restore_best_weights=True, verbose=0),
                        ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=1, min_lr=1e-7, verbose=0)
                    ]
                    
                    # Train with validation
                    epochs = 1 if FAST_MODE else 6  # 🚀 INSANE: 2→1 epoch for max speed!
                    history = model.fit(
                        X_train, y_train,
                        validation_data=(X_val, y_val),
                        epochs=epochs,
                        batch_size=int(params['batch_size']),
                        callbacks=callbacks,
                        verbose=0
                    )
                    
                    # Predict and evaluate
                    y_pred_prob = model.predict(X_val, verbose=0)
                    y_pred = (y_pred_prob > 0.5).astype(int).flatten()
                    
                    # Calculate F1 with validation
                    if len(np.unique(y_val)) > 1 and len(np.unique(y_pred)) > 1:
                        f1 = f1_score(y_val, y_pred, average='macro')
                        f1_scores.append(f1)
                    else:
                        print(f"   ⚠️ Fold {fold}: Only one class predicted")
                    
                    # Clean up
                    del model
                    tf.keras.backend.clear_session()
                    
                except Exception as fold_error:
                    print(f"   ⚠️ Fold {fold} failed: {str(fold_error)[:30]}...")
                    continue
            
            if len(f1_scores) == 0:
                print("   ❌ Failed: All folds failed")
                return 0.0
            
            avg_f1 = np.mean(f1_scores)
            print(f"   ✅ F1: {avg_f1:.4f} ({len(f1_scores)}/{CV_FOLDS} folds)")
            return avg_f1
        else:
            # 🚀 SKIP CV: Simple train/test split for INSANE speed!
            split_idx = int(0.8 * len(X))
            X_train, X_val = X[:split_idx], X[split_idx:]
            y_train, y_val = y[:split_idx], y[split_idx:]
            
            try:
                # Validate data
                if len(X_train) < 50 or len(X_val) < 10:
                    print(f"   ❌ Too little data: train={len(X_train)}, val={len(X_val)}")
                    return 0.0
                
                # Build model
                model = build_lstm_model(params, input_shape=(X_train.shape[1], X_train.shape[2]))
                
                if model is None:
                    print(f"   ❌ Model building failed")
                    return 0.0
                
                # Callbacks
                callbacks = [
                    EarlyStopping(monitor='val_loss', patience=1, restore_best_weights=True, verbose=0),
                    ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=1, min_lr=1e-7, verbose=0)
                ]
                
                # Train with validation
                epochs = 1 if FAST_MODE else 6  # 🚀 INSANE: 2→1 epoch for max speed!
                history = model.fit(
                    X_train, y_train,
                    validation_data=(X_val, y_val),
                    epochs=epochs,
                    batch_size=int(params['batch_size']),
                    callbacks=callbacks,
                    verbose=0
                )
                
                # Predict and evaluate
                y_pred_prob = model.predict(X_val, verbose=0)
                y_pred = (y_pred_prob > 0.5).astype(int).flatten()
                
                # Calculate F1 with validation
                if len(np.unique(y_val)) > 1 and len(np.unique(y_pred)) > 1:
                    f1 = f1_score(y_val, y_pred, average='macro')
                    f1_scores = [f1]  # Single score
                else:
                    print(f"   ⚠️ Only one class predicted")
                    f1_scores = []
                
                # Clean up
                del model
                tf.keras.backend.clear_session()
                
            except Exception as fold_error:
                print(f"   ⚠️ Training failed: {str(fold_error)[:30]}...")
                f1_scores = []
        
        # 🚨 FIX: Handle f1_scores result after the if/else block
        if len(f1_scores) == 0:
            print("   ❌ Failed: No valid F1 scores")
            return 0.0
        
        avg_f1 = np.mean(f1_scores)
        print(f"   ✅ F1: {avg_f1:.4f} ({len(f1_scores)} scores)")
        return avg_f1
        
    except Exception as e:
        print(f"   ❌ Failed: {str(e)[:50]}...")
        tf.keras.backend.clear_session()
        return 0.0

def generate_random_params():
    """🎲 Generate random parameters"""
    params = {}
    
    for param_name, param_values in LSTM_PARAM_GRID.items():
        params[param_name] = np.random.choice(param_values)
    
    # Ensure architectural consistency
    if params['num_lstm_layers'] == 1:
        params['lstm_units_2'] = 0
        params['lstm_units_3'] = 0
    elif params['num_lstm_layers'] == 2:
        params['lstm_units_3'] = 0
    
    # Ensure units decrease
    if params['num_lstm_layers'] >= 2:
        params['lstm_units_2'] = min(params['lstm_units_2'], params['lstm_units_1'])
    if params['num_lstm_layers'] >= 3:
        params['lstm_units_3'] = min(params['lstm_units_3'], params['lstm_units_2'])
    
    return params

def main():
    """🚀 Main LSTM optimization with better error handling"""
    print("🌙 MOON DEV'S LSTM HYPERPARAMETER OPTIMIZER! 🚀")
    print("💡 Following RF success - fixing DOWN-only predictor!")
    
    # Load data with validation
    df, feature_columns = load_lstm_data()
    if df is None or feature_columns is None:
        print("❌ Data loading failed - cannot continue!")
        return None, 0.0
    
    # Optimization settings
    n_trials = 5 if FAST_MODE else 50  # 🚀 REDUCED: 20→5 trials for speed
    max_time_minutes = 20 if FAST_MODE else 120  # 🚀 Time limit for FAST_MODE
    print(f"⚡ INSANE-SPEED MODE: {n_trials} trials with {max_time_minutes} min time limit!")
    
    best_score = 0.0
    best_params = None
    results = []
    successful_trials = 0
    
    start_time = time.time()
    
    for trial in range(n_trials):
        print(f"\n🎯 Trial {trial+1}/{n_trials}")
        
        # Generate and test parameters
        params = generate_random_params()
        f1_score = evaluate_lstm_params(params, df, feature_columns)
        
        # 🚨 FIX: Handle None return from evaluate_lstm_params
        if f1_score is None:
            f1_score = 0.0
            print(f"   ❌ Trial returned None - setting F1 to 0.0")
        
        # Track results
        results.append({'params': params.copy(), 'f1_score': f1_score})
        
        if f1_score > 0:  # Count successful trials
            successful_trials += 1
            
            if f1_score > best_score:
                best_score = f1_score
                best_params = params.copy()
                print(f"   🎉 NEW BEST: {f1_score:.4f}!")
        
        # Time estimate
        elapsed = time.time() - start_time
        avg_time = elapsed / (trial + 1)
        remaining = avg_time * (n_trials - trial - 1)
        print(f"   ⏱️ Remaining: {remaining/60:.1f} minutes | Success rate: {successful_trials}/{trial+1}")
        
        # Fast mode time limit
        if FAST_MODE and elapsed > (max_time_minutes * 60):  # Convert minutes to seconds
            print(f"⏰ Time limit reached ({max_time_minutes} minutes)! 🚀")
            break
    
    # 🚨 FIX: Handle case where no trials succeeded
    if best_params is None:
        print(f"\n💔 OPTIMIZATION FAILED!")
        print(f"❌ No successful trials out of {trial+1} attempts")
        print(f"🔍 Check your data and model configuration!")
        
        # Provide fallback parameters
        fallback_params = {
            'lstm_units_1': 64,
            'lstm_units_2': 32,
            'lstm_units_3': 16,
            'num_lstm_layers': 2,
            'dropout_rate': 0.2,
            'recurrent_dropout_rate': 0.1,
            'dense_dropout_rate': 0.3,
            'learning_rate': 0.001,
            'optimizer': 'adam',
            'batch_size': 32,
            'lookback_window': 60,
            'prediction_horizon': 5,
            'feature_scaler': 'standard',
            'use_batch_norm': True,
            'gradient_clip_norm': 1.0
        }
        
        print(f"\n🔧 USING FALLBACK PARAMETERS:")
        for param, value in fallback_params.items():
            print(f"   {param}: {value}")
        
        return fallback_params, 0.0
    
    # Success!
    print(f"\n🎉 OPTIMIZATION COMPLETE!")
    print(f"🏆 Best F1 score: {best_score:.4f}")
    print(f"✅ Success rate: {successful_trials}/{trial+1} ({successful_trials/(trial+1)*100:.1f}%)")
    print(f"🎯 Best parameters:")
    for param, value in best_params.items():
        print(f"   {param}: {value}")
    
    # Save results
    os.makedirs("optimization_results", exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # 🚨 FIX: Better file saving
    try:
        with open(f"optimization_results/lstm_params_{timestamp}.txt", "w") as f:
            f.write("🌙 MOON DEV'S OPTIMIZED LSTM PARAMETERS 🌙\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Best F1-Macro Score: {best_score:.4f}\n")
            f.write(f"Success Rate: {successful_trials}/{trial+1} trials\n\n")
            f.write("OPTIMAL PARAMETERS:\n")
            for param, value in best_params.items():
                f.write(f"{param} = {value}\n")
            f.write("\nUPDATE YOUR LSTM_liquidation.py WITH THESE VALUES! 🚀\n")
        
        print(f"💾 Results saved to optimization_results/lstm_params_{timestamp}.txt")
    except Exception as e:
        print(f"⚠️ Could not save results: {e}")
    
    print(f"🚀 UPDATE YOUR LSTM_liquidation.py WITH THESE OPTIMAL PARAMS!")
    
    return best_params, best_score

if __name__ == "__main__":
    # GPU setup
    gpus = tf.config.experimental.list_physical_devices('GPU')
    if gpus:
        try:
            for gpu in gpus:
                tf.config.experimental.set_memory_growth(gpu, True)
        except RuntimeError as e:
            print(f"GPU setup: {e}")
    
    main() 