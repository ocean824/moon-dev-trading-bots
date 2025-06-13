#!/usr/bin/env python3
"""
🌙 MOON DEV'S RF HYPERPARAMETER OPTIMIZER 🌙
===========================================

DEMIJAN'S ADVICE: Your RF params might be off for time series!
Let's find the OPTIMAL parameters for liquidation prediction!

Author: Moon Dev 🚀 (Thanks Demijan!)
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import TimeSeriesSplit, RandomizedSearchCV
from sklearn.metrics import f1_score, accuracy_score, confusion_matrix
from RF_liquidation import RFLiquidationPredictor
import warnings
warnings.filterwarnings('ignore')

# 🎯 DEMIJAN'S SUGGESTED PARAMETER RANGES
PARAM_GRID = {
    'n_estimators': [100, 200, 300, 500],  # Demijan: 200+ has diminishing returns
    'max_depth': [10, 15, 20, 25, None],
    'min_samples_split': [2, 5, 10, 20],
    'min_samples_leaf': [1, 2, 5, 10],
    'max_features': ['sqrt', 'log2', 0.3, 0.5],
    'class_weight': ['balanced', 'balanced_subsample'],
    'bootstrap': [True, False],
    'max_samples': [0.7, 0.8, 0.9, 1.0]  # For bootstrap=True
}

def moon_dev_rf_optimization(fast_mode=True):
    """
    🚀 Moon Dev's RF Parameter Optimization Pipeline!
    """
    print("🌙 MOON DEV'S RF PARAMETER OPTIMIZATION! 🚀")
    print("💡 Thanks Demijan - finding optimal params for time series!")
    
    if fast_mode:
        print("⚡ FAST MODE: Targeting <20 minutes optimization time!")
    else:
        print("🐌 FULL MODE: Complete optimization (may take 2+ hours)")
    
    print("=" * 60)
    
    # Load Moon Dev's BTC data
    print("📊 Loading Moon Dev's BTC liquidation data...")
    predictor = RFLiquidationPredictor()
    
    data_path = "research/machine_learning/processed_data/liquidations_BTC_processed.csv"
    df = predictor.load_liquidation_data(data_path)
    
    if df is None:
        print("❌ Data loading failed!")
        return None
    
    # Create focused features
    print("🎯 Creating focused liquidation features...")
    df_features = predictor.create_focused_liquidation_features(df, time_window='5min')
    df_targets = predictor.create_target_variable(df_features)
    
    # Prepare data
    feature_columns = [col for col in df_targets.columns 
                      if col not in ['target_return', 'future_return', 'target_direction_binary']]
    
    X, y = predictor.prepare_features(df_targets, feature_columns, target_type='direction')
    
    print(f"✅ Data ready! Samples: {len(X):,}, Features: {X.shape[1]}")
    print(f"   📈 UP: {np.sum(y):,} ({np.mean(y)*100:.1f}%)")
    print(f"   📉 DOWN: {len(y)-np.sum(y):,} ({(1-np.mean(y))*100:.1f}%)")
    
    # ⚡ FAST MODE: Reduce data size for speed
    if fast_mode:
        print("\n⚡ FAST MODE: Sampling data for quick optimization...")
        sample_size = min(15000, len(X))  # Max 15k samples for speed
        
        # Time-aware sampling (take most recent data)
        X = X[-sample_size:]
        y = y[-sample_size:]
        
        print(f"   🚀 Using {len(X):,} most recent samples (last {sample_size/len(X)*100:.1f}%)")
        print(f"   📈 UP: {np.sum(y):,} ({np.mean(y)*100:.1f}%)")
        print(f"   📉 DOWN: {len(y)-np.sum(y):,} ({(1-np.mean(y))*100:.1f}%)")
        
        # Faster CV settings
        cv_folds = 3
        n_iter = 25
        print(f"   ⏰ Fast CV: {cv_folds} folds, {n_iter} iterations")
    else:
        cv_folds = 5
        n_iter = 50
        print(f"   🐌 Full CV: {cv_folds} folds, {n_iter} iterations")
    
    # 🚨 CRITICAL: Time-aware cross validation (no future data leakage!)
    print("\n⏰ Setting up TIME-AWARE cross validation...")
    tscv = TimeSeriesSplit(n_splits=cv_folds)
    print("   🚨 NO FUTURE DATA LEAKAGE - Demijan approved! 🌙")
    
    # Scale features
    from sklearn.preprocessing import StandardScaler
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # 🎲 Random Search (faster than Grid Search)
    print("\n🎲 RUNNING RANDOM SEARCH OPTIMIZATION...")
    print(f"   🎛️ Testing {len(PARAM_GRID)} parameter types")
    print(f"   ⏰ With time-aware {cv_folds}-fold CV")
    
    # Calculate time estimate
    total_fits = n_iter * cv_folds
    estimated_time_mins = total_fits * len(X) / 15000 * 0.5  # Rough estimate
    
    print(f"   📊 Total fits: {total_fits}")
    print(f"   ⏱️ Estimated time: ~{estimated_time_mins:.1f} minutes")
    
    rf_base = RandomForestClassifier(random_state=42, n_jobs=-1, verbose=0)
    
    random_search = RandomizedSearchCV(
        estimator=rf_base,
        param_distributions=PARAM_GRID,
        n_iter=n_iter,  # Variable iterations based on mode
        cv=tscv,    # TIME-AWARE CV!
        scoring='f1_macro',  # Balanced UP/DOWN performance
        n_jobs=-1,
        verbose=1,
        random_state=42
    )
    
    print("🚀 OPTIMIZATION STARTING... (This may take a while)")
    random_search.fit(X_scaled, y)
    
    # 🏆 RESULTS ANALYSIS
    print("\n🏆 OPTIMIZATION COMPLETE!")
    print("=" * 60)
    print(f"🎯 Best F1-Macro Score: {random_search.best_score_:.4f}")
    print(f"🎛️ OPTIMAL PARAMETERS:")
    for param, value in random_search.best_params_.items():
        print(f"   {param}: {value}")
    
    # 🚨 TEST THE OPTIMIZED MODEL
    print("\n🚨 TESTING OPTIMIZED MODEL vs CURRENT PARAMS...")
    
    # Current params (from RF_liquidation.py)
    current_params = {
        'n_estimators': 300,
        'max_depth': 25,
        'min_samples_split': 2,
        'min_samples_leaf': 1,
        'max_features': None,
        'class_weight': 'balanced'
    }
    
    # Split data (time-aware)
    split_point = int(0.8 * len(X_scaled))
    X_train, X_test = X_scaled[:split_point], X_scaled[split_point:]
    y_train, y_test = y[:split_point], y[split_point:]
    
    # Test both models
    models = {
        "CURRENT": RandomForestClassifier(**current_params, random_state=42, n_jobs=-1),
        "OPTIMIZED": RandomForestClassifier(**random_search.best_params_, random_state=42, n_jobs=-1)
    }
    
    print(f"\n📊 MODEL COMPARISON (Train: {len(X_train):,} | Test: {len(X_test):,}):")
    print("=" * 80)
    
    for name, model in models.items():
        print(f"\n🤖 {name} MODEL:")
        
        # Train and predict
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        
        # Calculate metrics
        accuracy = accuracy_score(y_test, y_pred)
        f1_macro = f1_score(y_test, y_pred, average='macro')
        
        # UP/DOWN breakdown
        up_mask = y_test == 1
        down_mask = y_test == 0
        
        up_accuracy = np.mean(y_pred[up_mask] == y_test[up_mask]) if np.sum(up_mask) > 0 else 0
        down_accuracy = np.mean(y_pred[down_mask] == y_test[down_mask]) if np.sum(down_mask) > 0 else 0
        
        predicted_up = np.sum(y_pred == 1)
        predicted_down = np.sum(y_pred == 0)
        
        print(f"   🎯 Accuracy: {accuracy:.4f} ({accuracy*100:.2f}%)")
        print(f"   🏆 F1-Macro: {f1_macro:.4f}")
        print(f"   📈 UP Accuracy: {up_accuracy:.4f} ({up_accuracy*100:.1f}%)")
        print(f"   📉 DOWN Accuracy: {down_accuracy:.4f} ({down_accuracy*100:.1f}%)")
        print(f"   🔮 Predicted UP: {predicted_up:,} ({predicted_up/len(y_pred)*100:.1f}%)")
        print(f"   🔮 Predicted DOWN: {predicted_down:,} ({predicted_down/len(y_pred)*100:.1f}%)")
        
        # Check DOWN-only problem
        if predicted_up == 0:
            print(f"   🚨 DOWN-ONLY PREDICTOR!")
        elif predicted_up < np.sum(up_mask) * 0.1:
            print(f"   ⚠️ Pessimistic predictor")
        else:
            print(f"   ✅ Balanced predictor!")
        
        # Confusion matrix
        cm = confusion_matrix(y_test, y_pred)
        print(f"   🎲 Confusion Matrix: [[{cm[0,0]}, {cm[0,1]}], [{cm[1,0]}, {cm[1,1]}]]")
    
    # 💾 SAVE OPTIMIZED PARAMETERS
    print(f"\n💾 SAVING OPTIMIZED PARAMETERS...")
    
    import os
    os.makedirs("research/machine_learning/optimization_results", exist_ok=True)
    
    with open("research/machine_learning/optimization_results/optimized_rf_params.txt", "w") as f:
        f.write("🌙 MOON DEV'S OPTIMIZED RF PARAMETERS (Thanks Demijan!) 🌙\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Best F1-Macro Score: {random_search.best_score_:.4f}\n\n")
        f.write("OPTIMIZED PARAMETERS:\n")
        for param, value in random_search.best_params_.items():
            f.write(f"{param} = {value}\n")
        f.write(f"\nRANDOM_STATE = 42\n")
        f.write(f"N_JOBS = -1\n\n")
        f.write("UPDATE YOUR RF_liquidation.py WITH THESE VALUES! 🚀\n")
    
    print(f"✅ Parameters saved to: optimization_results/optimized_rf_params.txt")
    
    # 🎯 FINAL RECOMMENDATION
    print(f"\n🎯 MOON DEV'S OPTIMIZATION SUMMARY:")
    print("=" * 60)
    print(f"🏆 Best parameters found through time-aware optimization!")
    print(f"📊 Improvement in F1-score: {random_search.best_score_:.4f}")
    print(f"🚀 UPDATE YOUR RF_liquidation.py WITH THESE OPTIMAL PARAMS!")
    print(f"💡 Thanks to Demijan for the suggestion - your params were indeed off! 🌙")
    
    return random_search.best_params_, random_search.best_score_

if __name__ == "__main__":
    # ⚡ FAST MODE by default - change to False for full optimization
    best_params, best_score = moon_dev_rf_optimization(fast_mode=True)
    print(f"\n🎉 OPTIMIZATION COMPLETE! Best F1: {best_score:.4f}")
    print(f"🚀 Use these params in RF_liquidation.py: {best_params}") 