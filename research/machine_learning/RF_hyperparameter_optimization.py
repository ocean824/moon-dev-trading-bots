#!/usr/bin/env python3
"""
🌙 MOON DEV'S RANDOM FOREST HYPERPARAMETER OPTIMIZATION FOR TIME SERIES 🌙
===========================================================================

DEMIJAN'S SUGGESTION: RF hyperparameter optimization for time series!
Your params might be off - let's find the OPTIMAL settings for liquidation prediction!

Key Time Series Considerations:
- Time-aware cross validation (no future data leakage!)
- Handling temporal dependencies 
- Optimizing for UP/DOWN prediction accuracy
- Balancing overfitting vs underfitting for market data

Author: Moon Dev 🚀 (Thanks Demijan!)
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import TimeSeriesSplit, GridSearchCV, RandomizedSearchCV
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.preprocessing import StandardScaler
import joblib
import matplotlib.pyplot as plt
import seaborn as sns

# Import Moon Dev's RF predictor
from RF_liquidation import RFLiquidationPredictor

# 🌙 MOON DEV'S OPTIMIZATION CONFIGURATION 🌙
OPTIMIZATION_MODE = 'grid'  # 'grid', 'random', or 'bayesian'
N_JOBS = -1  # Use all CPU cores
CV_FOLDS = 5  # Time series cross validation folds
SCORING_METRIC = 'f1_macro'  # Focus on balanced UP/DOWN performance
RANDOM_STATE = 42

# 🎯 HYPERPARAMETER SEARCH SPACES (Thanks Demijan!)
PARAM_GRID_FULL = {
    'n_estimators': [50, 100, 200, 300, 500],  # Demijan said 200+ has diminishing returns
    'max_depth': [5, 10, 15, 20, 25, None],
    'min_samples_split': [2, 5, 10, 20],
    'min_samples_leaf': [1, 2, 5, 10],
    'max_features': ['sqrt', 'log2', 0.3, 0.5, 0.7],
    'bootstrap': [True, False],
    'class_weight': ['balanced', 'balanced_subsample', None]
}

# 🏠 LOCAL MODE: Smaller grid for faster testing
PARAM_GRID_LOCAL = {
    'n_estimators': [50, 100, 200],  
    'max_depth': [10, 15, 20],
    'min_samples_split': [2, 5, 10],
    'min_samples_leaf': [1, 2, 5],
    'max_features': ['sqrt', 'log2', 0.5],
    'bootstrap': [True],
    'class_weight': ['balanced', 'balanced_subsample']
}

# 🎲 RANDOM SEARCH DISTRIBUTIONS
PARAM_DISTRIBUTIONS = {
    'n_estimators': [50, 100, 150, 200, 250, 300, 400, 500],
    'max_depth': [5, 10, 15, 20, 25, 30, None],
    'min_samples_split': [2, 5, 10, 15, 20, 25],
    'min_samples_leaf': [1, 2, 3, 5, 7, 10],
    'max_features': ['sqrt', 'log2', 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8],
    'bootstrap': [True, False],
    'class_weight': ['balanced', 'balanced_subsample', None]
}

class MoonDevRFOptimizer:
    """
    🌙 Moon Dev's Random Forest Hyperparameter Optimizer for Time Series
    
    Optimizes RF parameters specifically for liquidation prediction!
    """
    
    def __init__(self, local_mode=True):
        """
        🚀 Initialize Moon Dev's RF optimizer!
        """
        self.local_mode = local_mode
        self.best_params = None
        self.best_score = None
        self.optimization_results = None
        self.feature_scaler = StandardScaler()
        
        print("🌙 MOON DEV'S RF HYPERPARAMETER OPTIMIZER INITIALIZED! 🚀")
        print(f"   🏠 Local mode: {local_mode}")
        print(f"   🎯 Optimization focus: UP/DOWN prediction accuracy")
        print(f"   ⏰ Time series aware: No future data leakage!")
    
    def load_and_prepare_data(self, data_path=None):
        """
        📊 Load and prepare Moon Dev's liquidation data for optimization!
        """
        print("\n📊 MOON DEV LOADING DATA FOR OPTIMIZATION... 🌙")
        
        # Use preprocessed BTC data if available
        if data_path is None:
            data_path = "research/machine_learning/processed_data/liquidations_BTC_processed.csv"
            print(f"🎯 Using Moon Dev's preprocessed BTC data!")
        
        # Initialize predictor and load data
        predictor = RFLiquidationPredictor()
        df = predictor.load_liquidation_data(data_path)
        
        if df is None:
            print("❌ Failed to load data!")
            return None, None, None, None
        
        # Use focused features for faster optimization
        print("🎯 Creating focused liquidation features for optimization...")
        df_features = predictor.create_focused_liquidation_features(df, time_window='5min')
        
        if df_features is None:
            print("❌ Feature engineering failed!")
            return None, None, None, None
        
        # Create targets
        print("🎯 Creating direction targets...")
        df_targets = predictor.create_target_variable(df_features, target_return_threshold=0.003)
        
        # Prepare features
        feature_columns = [col for col in df_targets.columns 
                          if col not in ['target_return', 'future_return', 'target_direction_binary']]
        
        X, y = predictor.prepare_features(df_targets, feature_columns, target_type='direction')
        
        print(f"✅ Data prepared for optimization!")
        print(f"   📊 Samples: {len(X):,}")
        print(f"   🎯 Features: {X.shape[1]}")
        print(f"   📈 UP moves: {np.sum(y):,} ({np.mean(y)*100:.1f}%)")
        print(f"   📉 DOWN moves: {len(y)-np.sum(y):,} ({(1-np.mean(y))*100:.1f}%)")
        
        return X, y, predictor, feature_columns
    
    def create_time_series_cv(self, n_samples):
        """
        ⏰ Create time-aware cross validation (CRITICAL for time series!)
        """
        print(f"\n⏰ MOON DEV'S TIME-AWARE CROSS VALIDATION! 🌙")
        print(f"   🚨 NO FUTURE DATA LEAKAGE - Demijan approved!")
        
        # Use TimeSeriesSplit for proper time series validation
        tscv = TimeSeriesSplit(n_splits=CV_FOLDS)
        
        # Show split information
        splits = list(tscv.split(range(n_samples)))
        print(f"   📊 Time series splits ({CV_FOLDS} folds):")
        for i, (train_idx, val_idx) in enumerate(splits):
            train_pct = len(train_idx) / n_samples * 100
            val_pct = len(val_idx) / n_samples * 100
            print(f"     Fold {i+1}: Train {len(train_idx):,} ({train_pct:.1f}%) | Val {len(val_idx):,} ({val_pct:.1f}%)")
        
        return tscv
    
    def run_grid_search_optimization(self, X, y):
        """
        🔍 Run Grid Search optimization for Moon Dev's RF!
        """
        print(f"\n🔍 MOON DEV'S GRID SEARCH OPTIMIZATION! 🌙")
        
        # Choose parameter grid based on mode
        param_grid = PARAM_GRID_LOCAL if self.local_mode else PARAM_GRID_FULL
        total_combinations = np.prod([len(v) for v in param_grid.values()])
        
        print(f"   🎛️ Parameter combinations: {total_combinations:,}")
        print(f"   ⏱️ Estimated time: {total_combinations * CV_FOLDS * 30 / 60:.1f} minutes")
        
        # Create time series cross validator
        tscv = self.create_time_series_cv(len(X))
        
        # Initialize base classifier
        rf_base = RandomForestClassifier(
            random_state=RANDOM_STATE,
            n_jobs=1,  # GridSearchCV handles parallelization
            verbose=0
        )
        
        # Run grid search
        print(f"🚀 STARTING GRID SEARCH... (Thanks Demijan!)")
        grid_search = GridSearchCV(
            estimator=rf_base,
            param_grid=param_grid,
            cv=tscv,  # Time-aware CV!
            scoring=SCORING_METRIC,
            n_jobs=N_JOBS,
            verbose=1,
            return_train_score=True
        )
        
        # Fit the grid search
        grid_search.fit(X, y)
        
        self.best_params = grid_search.best_params_
        self.best_score = grid_search.best_score_
        self.optimization_results = grid_search
        
        print(f"✅ GRID SEARCH COMPLETE!")
        print(f"   🏆 Best {SCORING_METRIC}: {self.best_score:.4f}")
        print(f"   🎯 Best parameters: {self.best_params}")
        
        return grid_search
    
    def run_random_search_optimization(self, X, y, n_iter=100):
        """
        🎲 Run Random Search optimization for Moon Dev's RF!
        """
        print(f"\n🎲 MOON DEV'S RANDOM SEARCH OPTIMIZATION! 🌙")
        print(f"   🎛️ Random iterations: {n_iter}")
        print(f"   ⏱️ Estimated time: {n_iter * CV_FOLDS * 30 / 60:.1f} minutes")
        
        # Create time series cross validator
        tscv = self.create_time_series_cv(len(X))
        
        # Initialize base classifier
        rf_base = RandomForestClassifier(
            random_state=RANDOM_STATE,
            n_jobs=1,
            verbose=0
        )
        
        # Run random search
        print(f"🚀 STARTING RANDOM SEARCH... (Demijan's suggestion!)")
        random_search = RandomizedSearchCV(
            estimator=rf_base,
            param_distributions=PARAM_DISTRIBUTIONS,
            n_iter=n_iter,
            cv=tscv,  # Time-aware CV!
            scoring=SCORING_METRIC,
            n_jobs=N_JOBS,
            verbose=1,
            return_train_score=True,
            random_state=RANDOM_STATE
        )
        
        # Fit the random search
        random_search.fit(X, y)
        
        self.best_params = random_search.best_params_
        self.best_score = random_search.best_score_
        self.optimization_results = random_search
        
        print(f"✅ RANDOM SEARCH COMPLETE!")
        print(f"   🏆 Best {SCORING_METRIC}: {self.best_score:.4f}")
        print(f"   🎯 Best parameters: {self.best_params}")
        
        return random_search
    
    def analyze_optimization_results(self):
        """
        📊 Analyze Moon Dev's optimization results!
        """
        print(f"\n📊 MOON DEV'S OPTIMIZATION ANALYSIS! 🌙")
        
        if self.optimization_results is None:
            print("❌ No optimization results to analyze!")
            return
        
        results_df = pd.DataFrame(self.optimization_results.cv_results_)
        
        # Top 10 parameter combinations
        top_results = results_df.nlargest(10, 'mean_test_score')
        
        print(f"🏆 TOP 10 PARAMETER COMBINATIONS:")
        print("=" * 80)
        for i, (idx, row) in enumerate(top_results.iterrows()):
            print(f"Rank {i+1}: Score {row['mean_test_score']:.4f} (±{row['std_test_score']:.4f})")
            params = {k.replace('param_', ''): v for k, v in row.items() if k.startswith('param_')}
            print(f"   Params: {params}")
            print()
        
        # Parameter importance analysis
        print(f"🎯 PARAMETER IMPACT ANALYSIS:")
        print("=" * 50)
        
        # Analyze each parameter's effect on performance
        for param in ['n_estimators', 'max_depth', 'min_samples_split', 'min_samples_leaf', 'max_features']:
            param_col = f'param_{param}'
            if param_col in results_df.columns:
                param_impact = results_df.groupby(param_col)['mean_test_score'].agg(['mean', 'std', 'count'])
                print(f"\n{param.upper()}:")
                for val, stats in param_impact.iterrows():
                    print(f"  {val}: {stats['mean']:.4f} (±{stats['std']:.4f}) [{stats['count']} trials]")
        
        return results_df
    
    def evaluate_best_model(self, X, y, feature_columns):
        """
        🏆 Evaluate Moon Dev's best optimized model!
        """
        print(f"\n🏆 EVALUATING MOON DEV'S BEST MODEL! 🌙")
        
        if self.best_params is None:
            print("❌ No best parameters found! Run optimization first.")
            return None
        
        # Split data (time-aware split)
        split_point = int(0.8 * len(X))
        X_train, X_test = X[:split_point], X[split_point:]
        y_train, y_test = y[:split_point], y[split_point:]
        
        print(f"   📊 Train: {len(X_train):,} | Test: {len(X_test):,}")
        
        # Train best model
        print(f"🚀 Training optimized Random Forest...")
        print(f"   🎯 Best parameters: {self.best_params}")
        
        rf_best = RandomForestClassifier(
            **self.best_params,
            random_state=RANDOM_STATE,
            n_jobs=N_JOBS,
            verbose=1
        )
        
        # Scale features if needed
        X_train_scaled = self.feature_scaler.fit_transform(X_train)
        X_test_scaled = self.feature_scaler.transform(X_test)
        
        # Train the model
        rf_best.fit(X_train_scaled, y_train)
        
        # Make predictions
        y_pred = rf_best.predict(X_test_scaled)
        y_pred_proba = rf_best.predict_proba(X_test_scaled)[:, 1]
        
        # Calculate metrics
        accuracy = accuracy_score(y_test, y_pred)
        f1_macro = f1_score(y_test, y_pred, average='macro')
        
        # UP/DOWN analysis
        up_mask = y_test == 1
        down_mask = y_test == 0
        
        up_accuracy = np.mean(y_pred[up_mask] == y_test[up_mask]) if np.sum(up_mask) > 0 else 0
        down_accuracy = np.mean(y_pred[down_mask] == y_test[down_mask]) if np.sum(down_mask) > 0 else 0
        
        predicted_up = np.sum(y_pred == 1)
        predicted_down = np.sum(y_pred == 0)
        
        print(f"\n🎯 OPTIMIZED MODEL PERFORMANCE:")
        print("=" * 60)
        print(f"🚀 Overall Accuracy: {accuracy:.4f} ({accuracy*100:.2f}%)")
        print(f"🎯 F1-Macro Score: {f1_macro:.4f}")
        print(f"📈 UP Accuracy: {up_accuracy:.4f} ({up_accuracy*100:.1f}%)")
        print(f"📉 DOWN Accuracy: {down_accuracy:.4f} ({down_accuracy*100:.1f}%)")
        print(f"🔮 Predicted UP: {predicted_up:,} ({predicted_up/len(y_pred)*100:.1f}%)")
        print(f"🔮 Predicted DOWN: {predicted_down:,} ({predicted_down/len(y_pred)*100:.1f}%)")
        
        # Check for DOWN-only problem
        if predicted_up == 0:
            print(f"🚨 STILL DOWN-ONLY PREDICTOR! Need more aggressive balancing!")
        elif predicted_up < np.sum(up_mask) * 0.1:
            print(f"⚠️ Still pessimistic but improved!")
        else:
            print(f"✅ BALANCED PREDICTOR ACHIEVED! 🎉")
        
        # Confusion matrix
        cm = confusion_matrix(y_test, y_pred)
        print(f"\n🎲 CONFUSION MATRIX:")
        print(f"   Predicted:  DOWN   UP")
        print(f"Actual DOWN:   {cm[0,0]:4d}  {cm[0,1]:4d}")
        print(f"Actual UP:     {cm[1,0]:4d}  {cm[1,1]:4d}")
        
        # Feature importance from optimized model
        if hasattr(rf_best, 'feature_importances_') and feature_columns:
            print(f"\n🌲 OPTIMIZED FEATURE IMPORTANCE:")
            feature_importance = pd.DataFrame({
                'feature': feature_columns,
                'importance': rf_best.feature_importances_
            }).sort_values('importance', ascending=False)
            
            for i, (_, row) in enumerate(feature_importance.head(10).iterrows()):
                print(f"   {i+1}. {row['feature']}: {row['importance']:.4f}")
        
        results = {
            'model': rf_best,
            'accuracy': accuracy,
            'f1_macro': f1_macro,
            'up_accuracy': up_accuracy,
            'down_accuracy': down_accuracy,
            'predictions': y_pred,
            'probabilities': y_pred_proba,
            'confusion_matrix': cm,
            'best_params': self.best_params
        }
        
        return results
    
    def save_optimization_results(self, results=None):
        """
        💾 Save Moon Dev's optimization results!
        """
        print(f"\n💾 SAVING MOON DEV'S OPTIMIZATION RESULTS... 🌙")
        
        # Create results directory
        results_dir = "research/machine_learning/optimization_results"
        os.makedirs(results_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save best parameters
        if self.best_params:
            params_file = os.path.join(results_dir, f"best_params_{timestamp}.txt")
            with open(params_file, 'w') as f:
                f.write("🌙 MOON DEV'S OPTIMIZED RF PARAMETERS 🌙\n")
                f.write("=" * 50 + "\n\n")
                f.write(f"Optimization Score ({SCORING_METRIC}): {self.best_score:.4f}\n\n")
                f.write("Best Parameters:\n")
                for param, value in self.best_params.items():
                    f.write(f"  {param}: {value}\n")
            
            print(f"   📋 Parameters saved: {params_file}")
        
        # Save full results if available
        if self.optimization_results:
            results_file = os.path.join(results_dir, f"optimization_results_{timestamp}.pkl")
            joblib.dump(self.optimization_results, results_file)
            print(f"   🔬 Full results saved: {results_file}")
        
        # Save optimized model if provided
        if results and 'model' in results:
            model_file = os.path.join(results_dir, f"optimized_rf_model_{timestamp}.pkl")
            joblib.dump(results['model'], model_file)
            print(f"   🤖 Optimized model saved: {model_file}")
        
        print(f"✅ Optimization results saved to: {results_dir}")
        return results_dir
    
    def run_full_optimization(self, optimization_type='grid'):
        """
        🚀 Run Moon Dev's complete RF optimization pipeline!
        """
        print("🌙" * 60)
        print("🚀 MOON DEV'S RF HYPERPARAMETER OPTIMIZATION PIPELINE 🚀")
        print("🌙" * 60)
        print(f"Thanks to Demijan for the suggestion! Your params might be off! 🎯")
        
        # Step 1: Load and prepare data
        X, y, predictor, feature_columns = self.load_and_prepare_data()
        if X is None:
            print("❌ Data loading failed!")
            return None
        
        # Step 2: Run optimization
        if optimization_type == 'grid':
            optimization_results = self.run_grid_search_optimization(X, y)
        elif optimization_type == 'random':
            n_iter = 50 if self.local_mode else 200
            optimization_results = self.run_random_search_optimization(X, y, n_iter=n_iter)
        else:
            print(f"❌ Unknown optimization type: {optimization_type}")
            return None
        
        # Step 3: Analyze results
        analysis_df = self.analyze_optimization_results()
        
        # Step 4: Evaluate best model
        evaluation_results = self.evaluate_best_model(X, y, feature_columns)
        
        # Step 5: Save results
        self.save_optimization_results(evaluation_results)
        
        print(f"\n🎉 MOON DEV'S RF OPTIMIZATION COMPLETE! 🌙")
        print(f"🏆 Best Score: {self.best_score:.4f}")
        print(f"🎯 Best Params: {self.best_params}")
        
        return {
            'best_params': self.best_params,
            'best_score': self.best_score,
            'optimization_results': optimization_results,
            'evaluation_results': evaluation_results,
            'analysis_df': analysis_df
        }


def main():
    """
    🌙 Main execution function for Moon Dev's RF optimization!
    """
    print("🚀 STARTING MOON DEV'S RF HYPERPARAMETER OPTIMIZATION! 🌙")
    print("💡 Thanks to Demijan - your params might be off!")
    
    # Initialize optimizer
    optimizer = MoonDevRFOptimizer(local_mode=True)  # Set to False for full optimization
    
    # Run optimization
    optimization_type = 'random'  # 'grid' or 'random'
    results = optimizer.run_full_optimization(optimization_type=optimization_type)
    
    if results:
        print(f"\n✅ OPTIMIZATION SUCCESS!")
        print(f"🚀 Use these optimized parameters in your RF_liquidation.py!")
        print(f"📊 Best parameters: {results['best_params']}")
    else:
        print(f"\n❌ OPTIMIZATION FAILED!")
    
    return results


if __name__ == "__main__":
    main() 