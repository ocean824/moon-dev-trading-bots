"""
🌙 MOON DEV'S ADVANCED RANDOM FOREST - DOWN-ONLY PREDICTOR DESTROYER 🚀
Implementing neural network-inspired fixes adapted for Random Forest:
1. Advanced class balancing (SMOTE/ADASYN) 
2. Cost-sensitive learning with dynamic weights
3. Threshold optimization for trading P&L
4. Multi-specialist ensemble (equivalent to multi-task)
5. UP-focused feature engineering
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, roc_auc_score, roc_curve
from sklearn.model_selection import cross_val_score
from imblearn.over_sampling import SMOTE, ADASYN
from imblearn.combine import SMOTETomek
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
import os
from datetime import datetime
warnings.filterwarnings('ignore')

# 🚀 MOON DEV'S ADVANCED RF CONFIGURATION 🚀
LOCAL_MODE = True  # Quick testing mode
DATA_SAMPLE_FRACTION = 0.1 if LOCAL_MODE else 1.0
LOOKBACK_WINDOW = 30 if LOCAL_MODE else 60
PREDICTION_HORIZON = 5

print("🌙 MOON DEV'S ADVANCED RF LIQUIDATION DESTROYER LOADING... 🚀")
print("🎯 Target: Break the DOWN-only predictor curse!")
print("=" * 60)

class AdvancedRFLiquidationPredictor:
    def __init__(self):
        """🌙 Moon Dev's Advanced RF with DOWN-only destroyer techniques"""
        self.models = {}  # Multiple specialist models
        self.scalers = {}
        self.feature_names = None
        self.optimal_threshold = 0.5
        self.is_trained = False
        
        print("🚀 Moon Dev Advanced RF initialized!")
        print("💡 Features: SMOTE balancing + Cost-sensitive + Threshold optimization")
        
    def load_and_engineer_features(self, data_path):
        """🔧 Load data and create UP-focused features"""
        print("📊 Moon Dev loading and engineering UP-focused features... 🌙")
        
        if not os.path.exists(data_path):
            print(f"❌ Data file not found: {data_path}")
            return None
            
        df = pd.read_csv(data_path)
        print(f"✅ Loaded {len(df):,} records")
        
        # Sample data for LOCAL_MODE
        if LOCAL_MODE and DATA_SAMPLE_FRACTION < 1.0:
            df = df.sample(frac=DATA_SAMPLE_FRACTION, random_state=42).reset_index(drop=True)
            print(f"🏠 LOCAL_MODE: Using {len(df):,} samples")
        
        # Parse timestamp
        df['timestamp'] = pd.to_datetime(df['datetime'] if 'datetime' in df.columns else df['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        # 🎯 UP-FOCUSED FEATURE ENGINEERING
        print("🎯 Creating UP-detection focused features...")
        
        # Price momentum features (crucial for UP detection)
        df['price_pct_change'] = df['price'].pct_change()
        df['price_momentum_3'] = df['price'].pct_change(3)
        df['price_momentum_5'] = df['price'].pct_change(5)
        df['price_acceleration'] = df['price_pct_change'].diff()
        
        # Volume-price interaction (UP moves need volume confirmation)
        df['volume_price_product'] = df['original_quantity'] * df['price']
        df['volume_momentum'] = df['original_quantity'].pct_change()
        df['volume_price_correlation'] = df['volume_price_product'].rolling(10).corr(df['price'])
        
        # Liquidation pressure features (contrarian signals)
        df['is_long_liq'] = (df['side'].str.upper() == 'BUY').astype(int)
        df['is_short_liq'] = (df['side'].str.upper() == 'SELL').astype(int)
        df['long_liq_pressure'] = df['is_long_liq'].rolling(10).sum()
        df['short_liq_pressure'] = df['is_short_liq'].rolling(10).sum()
        df['liq_imbalance'] = df['short_liq_pressure'] - df['long_liq_pressure']
        
        # Time-based features (UP moves cluster in certain periods)
        df['hour'] = df['timestamp'].dt.hour
        df['minute'] = df['timestamp'].dt.minute
        df['is_high_volatility_hour'] = df['hour'].isin([0, 1, 8, 9, 16, 17]).astype(int)  # Market open/close times
        
        # Recent UP/DOWN pattern features  
        df['recent_up_count'] = df['price_pct_change'].rolling(5).apply(lambda x: (x > 0.001).sum())
        df['recent_down_count'] = df['price_pct_change'].rolling(5).apply(lambda x: (x < -0.001).sum())
        df['trend_strength'] = df['recent_up_count'] - df['recent_down_count']
        
        # Clean data
        df = df.fillna(0).dropna()
        
        print(f"🎉 UP-focused features created! Shape: {df.shape}")
        return df
    
    def create_targets_and_sequences(self, df):
        """🎯 Create targets and sequence features"""
        print("🎯 Creating targets and sequences for Moon Dev...")
        
        # Calculate future returns
        future_prices = df['price'].shift(-PREDICTION_HORIZON)
        current_prices = df['price']
        future_returns = (future_prices / current_prices - 1).fillna(0)
        
        # Create binary UP/DOWN targets (threshold = 0.3% for more UP signals)
        threshold = 0.003
        df['target_direction'] = (future_returns > threshold).astype(int)
        
        # 📊 Class distribution analysis
        up_count = df['target_direction'].sum()
        down_count = len(df) - up_count
        print(f"📈 UP moves: {up_count:,} ({up_count/len(df)*100:.1f}%)")
        print(f"📉 DOWN moves: {down_count:,} ({down_count/len(df)*100:.1f}%)")
        print(f"⚖️ Imbalance ratio: {down_count/up_count:.1f}:1")
        
        # Select features for Moon Dev
        feature_cols = [
            'price_pct_change', 'price_momentum_3', 'price_momentum_5', 'price_acceleration',
            'volume_price_product', 'volume_momentum', 'volume_price_correlation',
            'long_liq_pressure', 'short_liq_pressure', 'liq_imbalance',
            'hour', 'minute', 'is_high_volatility_hour',
            'recent_up_count', 'recent_down_count', 'trend_strength'
        ]
        
        # Create sequences (simplified for speed)
        print(f"🔄 Creating {LOOKBACK_WINDOW}-step sequences...")
        sequences = []
        targets = []
        
        for i in range(LOOKBACK_WINDOW, len(df) - PREDICTION_HORIZON):
            if i % 1000 == 0:
                print(f"   🌙 Processed {i:,} sequences")
            
            # Get sequence window
            seq = df[feature_cols].iloc[i-LOOKBACK_WINDOW:i].values.flatten()
            target = df['target_direction'].iloc[i]
            
            sequences.append(seq)
            targets.append(target)
        
        X = np.array(sequences)
        y = np.array(targets)
        
        # Create feature names
        self.feature_names = []
        for lag in range(LOOKBACK_WINDOW):
            for col in feature_cols:
                self.feature_names.append(f"{col}_lag_{lag}")
        
        print(f"✅ Sequences ready! X: {X.shape}, y: {y.shape}")
        print(f"📈 Final UP targets: {np.sum(y)} ({np.sum(y)/len(y)*100:.1f}%)")
        
        return X, y
    
    def apply_advanced_balancing(self, X, y, method='smote'):
        """🔄 Apply advanced class balancing techniques"""
        print(f"🔄 Moon Dev applying {method.upper()} balancing... 🚀")
        
        original_up = np.sum(y)
        original_down = len(y) - original_up
        print(f"📊 Original: UP={original_up}, DOWN={original_down}")
        
        if method == 'smote':
            # SMOTE - Synthetic Minority Oversampling
            balancer = SMOTE(random_state=42, k_neighbors=3)
        elif method == 'adasyn':
            # ADASYN - Adaptive Synthetic Sampling
            balancer = ADASYN(random_state=42, n_neighbors=3)
        elif method == 'smote_tomek':
            # SMOTE + Tomek Links (removes borderline samples)
            balancer = SMOTETomek(random_state=42)
        else:
            print(f"⚠️ Unknown balancing method: {method}")
            return X, y
        
        try:
            X_balanced, y_balanced = balancer.fit_resample(X, y)
            
            balanced_up = np.sum(y_balanced)
            balanced_down = len(y_balanced) - balanced_up
            print(f"✅ Balanced: UP={balanced_up}, DOWN={balanced_down}")
            print(f"🚀 UP samples increased by {balanced_up - original_up:,}!")
            
            return X_balanced, y_balanced
        except Exception as e:
            print(f"❌ Balancing failed: {e}")
            return X, y
    
    def calculate_cost_sensitive_weights(self, y):
        """💰 Calculate cost-sensitive class weights for trading P&L"""
        print("💰 Moon Dev calculating cost-sensitive weights for trading...")
        
        up_count = np.sum(y)
        down_count = len(y) - up_count
        
        # Trading-focused weights (missing UP costs more than missing DOWN)
        up_weight = len(y) / (2 * up_count) * 3.0  # 3x penalty for missing UP moves
        down_weight = len(y) / (2 * down_count) * 1.0
        
        print(f"🎯 UP weight: {up_weight:.2f} (3x penalty for missing profitable moves)")
        print(f"🎯 DOWN weight: {down_weight:.2f}")
        
        return {0: down_weight, 1: up_weight}
    
    def train_specialist_ensemble(self, X_train, y_train, X_val, y_val):
        """🎓 Train ensemble of specialist models (multi-task equivalent)"""
        print("🎓 Moon Dev training specialist ensemble... 🚀")
        
        # Scale features
        self.scalers['main'] = StandardScaler()
        X_train_scaled = self.scalers['main'].fit_transform(X_train)
        X_val_scaled = self.scalers['main'].transform(X_val)
        
        # Calculate cost-sensitive weights
        class_weights = self.calculate_cost_sensitive_weights(y_train)
        
        # 🌲 Model 1: Balanced Random Forest (SMOTE + cost-sensitive)
        print("🌲 Training Model 1: Balanced RF...")
        X_balanced, y_balanced = self.apply_advanced_balancing(X_train_scaled, y_train, 'smote')
        
        self.models['balanced'] = RandomForestClassifier(
            n_estimators=100,
            max_depth=8,
            min_samples_split=10,
            min_samples_leaf=5,
            class_weight=class_weights,
            random_state=42,
            n_jobs=-1
        )
        self.models['balanced'].fit(X_balanced, y_balanced)
        
        # 🎯 Model 2: UP-focused specialist (ADASYN + aggressive weights)
        print("🎯 Training Model 2: UP-focused specialist...")
        X_adasyn, y_adasyn = self.apply_advanced_balancing(X_train_scaled, y_train, 'adasyn')
        
        # Even more aggressive UP weighting
        up_specialist_weights = {0: 1.0, 1: 5.0}  # 5x penalty for missing UP
        
        self.models['up_specialist'] = RandomForestClassifier(
            n_estimators=150,
            max_depth=12,
            min_samples_split=5,
            min_samples_leaf=2,
            class_weight=up_specialist_weights,
            random_state=42,
            n_jobs=-1
        )
        self.models['up_specialist'].fit(X_adasyn, y_adasyn)
        
        # 🚀 Model 3: Conservative baseline (original data + light weights)
        print("🚀 Training Model 3: Conservative baseline...")
        self.models['conservative'] = RandomForestClassifier(
            n_estimators=200,
            max_depth=6,
            min_samples_split=20,
            min_samples_leaf=10,
            class_weight='balanced',
            random_state=42,
            n_jobs=-1
        )
        self.models['conservative'].fit(X_train_scaled, y_train)
        
        # Evaluate each model
        print("\n📊 MOON DEV'S SPECIALIST MODEL EVALUATION:")
        print("=" * 50)
        
        for name, model in self.models.items():
            pred = model.predict(X_val_scaled)
            prob = model.predict_proba(X_val_scaled)[:, 1]
            acc = accuracy_score(y_val, pred)
            auc = roc_auc_score(y_val, prob)
            
            # UP/DOWN breakdown
            up_mask = y_val == 1
            up_acc = np.mean(pred[up_mask] == 1) if np.sum(up_mask) > 0 else 0
            pred_up_count = np.sum(pred == 1)
            
            print(f"🌲 {name.upper()}:")
            print(f"   Accuracy: {acc:.3f}, AUC: {auc:.3f}")
            print(f"   UP accuracy: {up_acc:.3f} ({up_acc*100:.1f}%)")
            print(f"   Predicted UP: {pred_up_count} moves")
        
        self.is_trained = True
        print("🎉 Specialist ensemble training complete!")
        
    def optimize_threshold_for_trading(self, X_val, y_val):
        """🎯 Optimize threshold for maximum trading P&L"""
        print("🎯 Moon Dev optimizing threshold for trading P&L... 💰")
        
        X_val_scaled = self.scalers['main'].transform(X_val)
        
        # Get probabilities from ensemble (weighted average)
        prob_balanced = self.models['balanced'].predict_proba(X_val_scaled)[:, 1]
        prob_specialist = self.models['up_specialist'].predict_proba(X_val_scaled)[:, 1]
        prob_conservative = self.models['conservative'].predict_proba(X_val_scaled)[:, 1]
        
        # Weighted ensemble (favor UP specialist)
        ensemble_probs = (0.3 * prob_balanced + 0.5 * prob_specialist + 0.2 * prob_conservative)
        
        # Test different thresholds
        thresholds = np.linspace(0.1, 0.9, 50)
        best_score = -float('inf')
        best_threshold = 0.5
        
        print("🔍 Testing thresholds for optimal trading performance...")
        
        for threshold in thresholds:
            predictions = (ensemble_probs >= threshold).astype(int)
            
            # Calculate trading-focused score
            tp = np.sum((predictions == 1) & (y_val == 1))  # Correct UP predictions
            fp = np.sum((predictions == 1) & (y_val == 0))  # False UP predictions
            fn = np.sum((predictions == 0) & (y_val == 1))  # Missed UP moves
            tn = np.sum((predictions == 0) & (y_val == 0))  # Correct DOWN predictions
            
            # Trading P&L score (reward correct UP, penalize false UP, heavily penalize missed UP)
            pnl_score = tp * 3.0 - fp * 1.0 - fn * 2.0 + tn * 0.1
            
            if pnl_score > best_score:
                best_score = pnl_score
                best_threshold = threshold
        
        self.optimal_threshold = best_threshold
        
        # Test optimal threshold performance
        optimal_predictions = (ensemble_probs >= best_threshold).astype(int)
        optimal_acc = accuracy_score(y_val, optimal_predictions)
        optimal_auc = roc_auc_score(y_val, ensemble_probs)
        
        up_mask = y_val == 1
        optimal_up_acc = np.mean(optimal_predictions[up_mask] == 1) if np.sum(up_mask) > 0 else 0
        predicted_up = np.sum(optimal_predictions == 1)
        
        print(f"🏆 OPTIMAL THRESHOLD FOUND: {best_threshold:.3f}")
        print(f"✅ Optimal accuracy: {optimal_acc:.3f}")
        print(f"🌟 Optimal AUC: {optimal_auc:.3f}")
        print(f"📈 Optimal UP accuracy: {optimal_up_acc:.3f} ({optimal_up_acc*100:.1f}%)")
        print(f"🎯 Predicted UP moves: {predicted_up}")
        print(f"💰 Trading P&L score: {best_score:.1f}")
        
        return best_threshold
    
    def evaluate_final_model(self, X_test, y_test):
        """📊 Final evaluation with ensemble + optimal threshold"""
        print("📊 Moon Dev final evaluation with optimized ensemble... 🚀")
        
        X_test_scaled = self.scalers['main'].transform(X_test)
        
        # Ensemble predictions
        prob_balanced = self.models['balanced'].predict_proba(X_test_scaled)[:, 1]
        prob_specialist = self.models['up_specialist'].predict_proba(X_test_scaled)[:, 1]
        prob_conservative = self.models['conservative'].predict_proba(X_test_scaled)[:, 1]
        
        # Weighted ensemble
        ensemble_probs = (0.3 * prob_balanced + 0.5 * prob_specialist + 0.2 * prob_conservative)
        
        # Predictions with optimal threshold
        predictions = (ensemble_probs >= self.optimal_threshold).astype(int)
        
        # Calculate metrics
        accuracy = accuracy_score(y_test, predictions)
        auc_score = roc_auc_score(y_test, ensemble_probs)
        
        # UP/DOWN breakdown
        up_mask = y_test == 1
        down_mask = y_test == 0
        
        up_accuracy = np.mean(predictions[up_mask] == 1) if np.sum(up_mask) > 0 else 0
        down_accuracy = np.mean(predictions[down_mask] == 0) if np.sum(down_mask) > 0 else 0
        
        up_count = np.sum(up_mask)
        down_count = np.sum(down_mask)
        predicted_up = np.sum(predictions == 1)
        predicted_down = np.sum(predictions == 0)
        
        # Confusion matrix
        cm = confusion_matrix(y_test, predictions)
        
        print("🏆 MOON DEV'S ADVANCED RF FINAL RESULTS 🚀")
        print("=" * 60)
        print(f"🎯 OVERALL ACCURACY: {accuracy:.4f} ({accuracy*100:.2f}%)")
        print(f"🌟 AUC-ROC SCORE: {auc_score:.4f}")
        print(f"🎲 Random baseline: ~50.0% accuracy, ~0.50 AUC")
        print(f"💪 Moon Dev improvement: +{(accuracy-0.5)*100:.2f} acc points, +{(auc_score-0.5)*100:.2f} AUC points!")
        
        print(f"\n🚨 UP/DOWN BREAKDOWN:")
        print(f"   📈 UP moves in test: {up_count:,} ({up_count/len(y_test)*100:.1f}%)")
        print(f"   📉 DOWN moves in test: {down_count:,} ({down_count/len(y_test)*100:.1f}%)")
        print(f"   🎯 UP accuracy: {up_accuracy:.4f} ({up_accuracy*100:.1f}%)")
        print(f"   🎯 DOWN accuracy: {down_accuracy:.4f} ({down_accuracy*100:.1f}%)")
        
        print(f"\n🤖 MODEL PREDICTION BEHAVIOR:")
        print(f"   🔮 Predicted UP: {predicted_up:,} ({predicted_up/len(predictions)*100:.1f}%)")
        print(f"   🔮 Predicted DOWN: {predicted_down:,} ({predicted_down/len(predictions)*100:.1f}%)")
        print(f"   🎯 Optimal threshold: {self.optimal_threshold:.3f}")
        
        # Check for DOWN-only problem
        if predicted_up == 0:
            print(f"   🚨 DOWN-ONLY PREDICTOR STILL DETECTED!")
            success = False
        elif predicted_up < up_count * 0.1:
            print(f"   ⚠️ Still pessimistic but some UP predictions!")
            success = True
        else:
            print(f"   ✅ BALANCED PREDICTOR: Good UP/DOWN prediction ratio!")
            success = True
        
        print(f"\n🎲 CONFUSION MATRIX:")
        print(f"   Predicted:  DOWN   UP")
        print(f"Actual DOWN:   {cm[0,0]:4d}  {cm[0,1]:4d}")
        print(f"Actual UP:     {cm[1,0]:4d}  {cm[1,1]:4d}")
        
        # 🚨 SUCCESS METRICS
        print(f"\n🚨 DOWN-ONLY DESTROYER SUCCESS METRICS:")
        if up_accuracy > 0.2:
            print(f"   ✅ UP accuracy > 20%: CURSE BROKEN! 🎉")
        elif up_accuracy > 0.1:
            print(f"   ⚠️ UP accuracy > 10%: Good progress! 📈")
        elif up_accuracy > 0.05:
            print(f"   📊 UP accuracy > 5%: Some improvement 🔧")
        else:
            print(f"   🚨 UP accuracy < 5%: Curse persists 😤")
        
        if auc_score > 0.65:
            print(f"   ✅ AUC > 0.65: Strong trading edge! 💰")
        elif auc_score > 0.58:
            print(f"   ⚠️ AUC > 0.58: Decent edge, needs work 🔧")
        else:
            print(f"   📊 AUC < 0.58: Weak edge, keep optimizing 🛠️")
        
        print("=" * 60)
        
        return {
            'accuracy': accuracy,
            'auc_score': auc_score,
            'up_accuracy': up_accuracy,
            'predictions': predictions,
            'probabilities': ensemble_probs,
            'confusion_matrix': cm,
            'success': success and up_accuracy > 0.1 and auc_score > 0.55
        }
    
    def plot_results(self, metrics):
        """📈 Plot Moon Dev's advanced results"""
        print("📈 Creating Moon Dev's advanced RF performance plots... 🚀")
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('🌙 MOON DEV\'S ADVANCED RF - DOWN-ONLY DESTROYER RESULTS 🚀', fontsize=16)
        
        # ROC Curve
        from sklearn.metrics import roc_curve
        fpr, tpr, _ = roc_curve(metrics['actuals'], metrics['probabilities'])
        
        axes[0, 0].plot(fpr, tpr, color='green', lw=2, label=f'Advanced RF (AUC = {metrics["auc_score"]:.3f})')
        axes[0, 0].plot([0, 1], [0, 1], color='red', lw=2, linestyle='--', label='Random (AUC = 0.5)')
        axes[0, 0].axhline(y=0.7, color='gold', linestyle=':', label='Target AUC = 0.7')
        axes[0, 0].set_title('🏆 ROC Curve - Trading Viability')
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)
        
        # Probability distributions
        probs = metrics['probabilities']
        actuals = metrics['actuals']
        
        up_probs = probs[actuals == 1]
        down_probs = probs[actuals == 0]
        
        axes[0, 1].hist(down_probs, bins=30, alpha=0.7, label='Actual DOWN', color='red', density=True)
        axes[0, 1].hist(up_probs, bins=30, alpha=0.7, label='Actual UP', color='green', density=True)
        axes[0, 1].axvline(x=self.optimal_threshold, color='blue', linestyle='--', 
                          label=f'Optimal Threshold ({self.optimal_threshold:.3f})')
        axes[0, 1].set_title('🎯 Probability Separation')
        axes[0, 1].legend()
        axes[0, 1].grid(True, alpha=0.3)
        
        # Confusion Matrix
        cm = metrics['confusion_matrix']
        sns.heatmap(cm, annot=True, fmt='d', cmap='Greens', ax=axes[1, 0])
        axes[1, 0].set_title('🎲 Confusion Matrix')
        axes[1, 0].set_ylabel('Actual')
        axes[1, 0].set_xlabel('Predicted')
        
        # Success indicators
        success_metrics = {
            'UP Accuracy': metrics['up_accuracy'],
            'Overall Accuracy': metrics['accuracy'],
            'AUC Score': metrics['auc_score'],
            'Target AUC (0.7)': 0.7,
            'Random Baseline': 0.5
        }
        
        metric_names = list(success_metrics.keys())
        metric_values = list(success_metrics.values())
        colors = ['green' if v > 0.6 else 'orange' if v > 0.5 else 'red' for v in metric_values]
        
        axes[1, 1].barh(metric_names, metric_values, color=colors, alpha=0.7)
        axes[1, 1].set_xlim(0, 1)
        axes[1, 1].set_title('🚀 Performance vs Targets')
        axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.show()
        
        print("🎉 Moon Dev's advanced visualization complete! 🚀")

def main():
    """🌙 Moon Dev's main advanced RF pipeline"""
    print("🚀 STARTING MOON DEV'S ADVANCED RF DOWN-ONLY DESTROYER 🌙")
    print("=" * 60)
    
    # Initialize predictor
    predictor = AdvancedRFLiquidationPredictor()
    
    # Load and engineer features
    data_path = "processed_data/liquidations_BTC_processed.csv"
    df = predictor.load_and_engineer_features(data_path)
    
    if df is None:
        print("❌ Data loading failed!")
        return
    
    # Create sequences and targets
    X, y = predictor.create_targets_and_sequences(df)
    
    # Split data
    train_size = int(0.7 * len(X))
    val_size = int(0.15 * len(X))
    
    X_train, X_val, X_test = X[:train_size], X[train_size:train_size+val_size], X[train_size+val_size:]
    y_train, y_val, y_test = y[:train_size], y[train_size:train_size+val_size], y[train_size+val_size:]
    
    print(f"🔄 Data split - Train: {len(X_train)}, Val: {len(X_val)}, Test: {len(X_test)}")
    
    # Train specialist ensemble
    predictor.train_specialist_ensemble(X_train, y_train, X_val, y_val)
    
    # Optimize threshold for trading
    predictor.optimize_threshold_for_trading(X_val, y_val)
    
    # Final evaluation
    metrics = predictor.evaluate_final_model(X_test, y_test)
    metrics['actuals'] = y_test  # Add for plotting
    
    # Plot results
    predictor.plot_results(metrics)
    
    # Final verdict
    if metrics['success']:
        print("🎉 MOON DEV'S DOWN-ONLY CURSE SUCCESSFULLY BROKEN! 🚀🌙")
    else:
        print("🔧 MOON DEV'S CURSE STILL FIGHTING - NEED MORE FIREPOWER! 🛠️")
    
    print("=" * 60)

if __name__ == "__main__":
    main() 