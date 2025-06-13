"""
🌙 MOON DEV'S BALANCED RANDOM FOREST - FIXED OVERCORRECTION 🚀
The advanced version went from DOWN-only to UP-only. This finds the sweet spot:
- Moderate class weights (2x instead of 5x)
- No synthetic oversampling (SMOTE caused issues)
- Precision-recall balanced threshold optimization
- Trading P&L focused but not extreme
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, roc_auc_score, roc_curve, precision_score, recall_score, f1_score, confusion_matrix
import matplotlib.pyplot as plt
import warnings
import os
warnings.filterwarnings('ignore')

# 🚀 MOON DEV'S BALANCED CONFIGURATION 🚀
LOCAL_MODE = True
DATA_SAMPLE_FRACTION = 0.1 if LOCAL_MODE else 1.0
LOOKBACK_WINDOW = 20 if LOCAL_MODE else 60  # Smaller for speed
PREDICTION_HORIZON = 5

print("🌙 MOON DEV'S BALANCED RF - FIXING THE OVERCORRECTION 🚀")
print("⚖️ Goal: Find sweet spot between DOWN-only and UP-only curse!")
print("=" * 60)

class BalancedRFPredictor:
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.optimal_threshold = 0.5
        self.is_trained = False
        
        print("⚖️ Balanced RF initialized - moderate approach!")
        
    def load_and_engineer_features(self, data_path):
        print("📊 Loading data for balanced approach... 🌙")
        
        if not os.path.exists(data_path):
            print(f"❌ Data file not found: {data_path}")
            return None
            
        df = pd.read_csv(data_path)
        print(f"✅ Loaded {len(df):,} records")
        
        if LOCAL_MODE:
            df = df.sample(frac=DATA_SAMPLE_FRACTION, random_state=42).reset_index(drop=True)
            print(f"🏠 LOCAL_MODE: Using {len(df):,} samples")
        
        # Parse timestamp
        df['timestamp'] = pd.to_datetime(df['datetime'] if 'datetime' in df.columns else df['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        # Simple, effective features (no overengineering)
        df['price_change'] = df['price'].pct_change()
        df['price_momentum'] = df['price'].pct_change(5)
        df['volume_ma'] = df['original_quantity'].rolling(10).mean()
        df['volume_ratio'] = df['original_quantity'] / (df['volume_ma'] + 1e-8)
        df['is_long_liq'] = (df['side'].str.upper() == 'BUY').astype(int)
        df['liq_pressure'] = df['is_long_liq'].rolling(5).mean() - 0.5  # -0.5 to +0.5
        df['hour'] = df['timestamp'].dt.hour
        df['volatility'] = df['price_change'].rolling(10).std()
        
        df = df.fillna(0).dropna()
        print(f"⚖️ Simple features created! Shape: {df.shape}")
        return df
    
    def create_sequences(self, df):
        print("🎯 Creating balanced targets...")
        
        # Future returns with conservative threshold
        future_prices = df['price'].shift(-PREDICTION_HORIZON)
        returns = (future_prices / df['price'] - 1).fillna(0)
        
        # Conservative threshold for better balance
        threshold = 0.002  # 0.2%
        df['target'] = (returns > threshold).astype(int)
        
        up_count = df['target'].sum()
        down_count = len(df) - up_count
        print(f"📈 UP: {up_count:,} ({up_count/len(df)*100:.1f}%)")
        print(f"📉 DOWN: {down_count:,} ({down_count/len(df)*100:.1f}%)")
        print(f"⚖️ Ratio: {down_count/up_count:.1f}:1")
        
        # Simple feature selection
        feature_cols = ['price_change', 'price_momentum', 'volume_ratio', 'liq_pressure', 'hour', 'volatility']
        
        # Create sequences efficiently
        X, y = [], []
        for i in range(LOOKBACK_WINDOW, len(df) - PREDICTION_HORIZON, 10):  # Skip every 10 for speed
            seq = df[feature_cols].iloc[i-LOOKBACK_WINDOW:i].values.flatten()
            target = df['target'].iloc[i]
            X.append(seq)
            y.append(target)
        
        X, y = np.array(X), np.array(y)
        print(f"✅ Sequences: {X.shape}, targets: {y.shape}")
        print(f"📈 Final UP ratio: {np.mean(y)*100:.1f}%")
        
        return X, y
    
    def train_balanced_model(self, X_train, y_train):
        print("🎓 Training balanced model with moderate weights... ⚖️")
        
        X_train_scaled = self.scaler.fit_transform(X_train)
        
        # MODERATE class weights (not extreme like before)
        up_count = np.sum(y_train)
        down_count = len(y_train) - up_count
        up_weight = len(y_train) / (2 * up_count) * 2.0  # 2x instead of 5x
        down_weight = len(y_train) / (2 * down_count) * 1.0
        
        print(f"⚖️ Moderate weights - UP: {up_weight:.2f}x, DOWN: {down_weight:.2f}x")
        
        # Single balanced model (not ensemble to avoid complexity)
        self.model = RandomForestClassifier(
            n_estimators=200,
            max_depth=10,
            min_samples_split=20,
            min_samples_leaf=10,
            class_weight={0: down_weight, 1: up_weight},
            random_state=42,
            n_jobs=-1
        )
        
        self.model.fit(X_train_scaled, y_train)
        self.is_trained = True
        print("✅ Balanced model trained!")
    
    def optimize_threshold(self, X_val, y_val):
        print("💰 Optimizing threshold for balanced performance... ⚖️")
        
        X_val_scaled = self.scaler.transform(X_val)
        probs = self.model.predict_proba(X_val_scaled)[:, 1]
        
        best_score = 0
        best_threshold = 0.5
        
        # Test thresholds focusing on F1 score (balance of precision and recall)
        for threshold in np.linspace(0.3, 0.8, 50):
            preds = (probs >= threshold).astype(int)
            
            # Use F1 score as balanced metric
            f1 = f1_score(y_val, preds, zero_division=0)
            
            if f1 > best_score:
                best_score = f1
                best_threshold = threshold
        
        self.optimal_threshold = best_threshold
        
        # Test performance with optimal threshold
        optimal_preds = (probs >= best_threshold).astype(int)
        acc = accuracy_score(y_val, optimal_preds)
        auc = roc_auc_score(y_val, probs)
        precision = precision_score(y_val, optimal_preds, zero_division=0)
        recall = recall_score(y_val, optimal_preds, zero_division=0)
        
        up_mask = y_val == 1
        down_mask = y_val == 0
        up_acc = np.mean(optimal_preds[up_mask] == 1) if np.sum(up_mask) > 0 else 0
        down_acc = np.mean(optimal_preds[down_mask] == 0) if np.sum(down_mask) > 0 else 0
        
        pred_up = np.sum(optimal_preds == 1)
        pred_down = np.sum(optimal_preds == 0)
        
        print(f"🏆 OPTIMAL THRESHOLD: {best_threshold:.3f}")
        print(f"⚖️ Accuracy: {acc:.3f}, AUC: {auc:.3f}")
        print(f"🎯 Precision: {precision:.3f}, Recall: {recall:.3f}, F1: {best_score:.3f}")
        print(f"📈 UP accuracy: {up_acc:.3f}, DOWN accuracy: {down_acc:.3f}")
        print(f"🔮 Predicted UP: {pred_up}, DOWN: {pred_down}")
        
        return best_threshold
    
    def evaluate_final(self, X_test, y_test):
        print("📊 Final balanced evaluation... 💰")
        
        X_test_scaled = self.scaler.transform(X_test)
        probs = self.model.predict_proba(X_test_scaled)[:, 1]
        preds = (probs >= self.optimal_threshold).astype(int)
        
        # Calculate all metrics
        acc = accuracy_score(y_test, preds)
        auc = roc_auc_score(y_test, probs)
        precision = precision_score(y_test, preds, zero_division=0)
        recall = recall_score(y_test, preds, zero_division=0)
        f1 = f1_score(y_test, preds, zero_division=0)
        
        up_mask = y_test == 1
        down_mask = y_test == 0
        up_acc = np.mean(preds[up_mask] == 1) if np.sum(up_mask) > 0 else 0
        down_acc = np.mean(preds[down_mask] == 0) if np.sum(down_mask) > 0 else 0
        
        up_count = np.sum(up_mask)
        down_count = np.sum(down_mask)
        pred_up = np.sum(preds == 1)
        pred_down = np.sum(preds == 0)
        
        cm = confusion_matrix(y_test, preds)
        
        print("🏆 MOON DEV'S BALANCED RF FINAL RESULTS ⚖️")
        print("=" * 60)
        print(f"💰 OVERALL PERFORMANCE:")
        print(f"   🎯 Accuracy: {acc:.4f} ({acc*100:.2f}%)")
        print(f"   🌟 AUC: {auc:.4f}")
        print(f"   🎯 Precision: {precision:.4f}")
        print(f"   📈 Recall: {recall:.4f}")
        print(f"   ⚖️ F1 Score: {f1:.4f}")
        
        print(f"\n⚖️ CLASS PERFORMANCE:")
        print(f"   📈 UP moves: {up_count:,} ({up_count/len(y_test)*100:.1f}%)")
        print(f"   📉 DOWN moves: {down_count:,} ({down_count/len(y_test)*100:.1f}%)")
        print(f"   🎯 UP accuracy: {up_acc:.4f} ({up_acc*100:.1f}%)")
        print(f"   🎯 DOWN accuracy: {down_acc:.4f} ({down_acc*100:.1f}%)")
        
        print(f"\n🤖 PREDICTION BEHAVIOR:")
        print(f"   🔮 Predicted UP: {pred_up:,} ({pred_up/len(preds)*100:.1f}%)")
        print(f"   🔮 Predicted DOWN: {pred_down:,} ({pred_down/len(preds)*100:.1f}%)")
        print(f"   ⚖️ Threshold: {self.optimal_threshold:.3f}")
        
        # Balance assessment
        if pred_up == 0:
            balance_status = "🚨 DOWN-ONLY CURSE STILL ACTIVE!"
        elif pred_down == 0:
            balance_status = "🚨 UP-ONLY CURSE (OVERCORRECTED)!"
        elif pred_up < up_count * 0.5:
            balance_status = "⚠️ Conservative (slight under-prediction of UP)"
        elif pred_up > up_count * 2:
            balance_status = "⚠️ Aggressive (over-predicting UP moves)"
        else:
            balance_status = "✅ BALANCED! Good prediction distribution!"
        
        print(f"\n⚖️ BALANCE ASSESSMENT:")
        print(f"   {balance_status}")
        
        # Trading viability
        if f1 > 0.4 and auc > 0.6:
            trading_status = "✅ TRADING READY!"
        elif f1 > 0.3 and auc > 0.55:
            trading_status = "⚠️ Needs refinement but promising"
        else:
            trading_status = "❌ Not ready for trading"
        
        print(f"   💰 Trading viability: {trading_status}")
        
        print(f"\n🎲 CONFUSION MATRIX:")
        print(f"   Predicted:  DOWN   UP")
        print(f"Actual DOWN:   {cm[0,0]:4d}  {cm[0,1]:4d}")
        print(f"Actual UP:     {cm[1,0]:4d}  {cm[1,1]:4d}")
        print("=" * 60)
        
        return {
            'accuracy': acc, 'auc': auc, 'precision': precision, 
            'recall': recall, 'f1': f1, 'up_accuracy': up_acc, 
            'down_accuracy': down_acc, 'balance_status': balance_status,
            'trading_status': trading_status, 'predictions': preds, 
            'probabilities': probs, 'actuals': y_test
        }
    
    def plot_results(self, metrics):
        print("📈 Creating balanced results plot... ⚖️")
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('🌙 MOON DEV\'S BALANCED RF - FIXED OVERCORRECTION ⚖️', fontsize=16)
        
        # ROC Curve
        fpr, tpr, _ = roc_curve(metrics['actuals'], metrics['probabilities'])
        axes[0, 0].plot(fpr, tpr, 'b-', lw=2, label=f'Balanced RF (AUC = {metrics["auc"]:.3f})')
        axes[0, 0].plot([0, 1], [0, 1], 'r--', label='Random (0.5)')
        axes[0, 0].axhline(y=0.7, color='gold', linestyle=':', label='Target (0.7)')
        axes[0, 0].set_title('🏆 ROC Curve')
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)
        
        # Probability distributions
        probs = metrics['probabilities']
        actuals = metrics['actuals']
        up_probs = probs[actuals == 1]
        down_probs = probs[actuals == 0]
        
        axes[0, 1].hist(down_probs, bins=20, alpha=0.7, label='DOWN', color='red', density=True)
        axes[0, 1].hist(up_probs, bins=20, alpha=0.7, label='UP', color='green', density=True)
        axes[0, 1].axvline(x=self.optimal_threshold, color='blue', linestyle='--', 
                          label=f'Threshold ({self.optimal_threshold:.3f})')
        axes[0, 1].set_title('⚖️ Probability Separation')
        axes[0, 1].legend()
        axes[0, 1].grid(True, alpha=0.3)
        
        # Performance metrics
        performance = {
            'Accuracy': metrics['accuracy'],
            'AUC': metrics['auc'],
            'Precision': metrics['precision'],
            'Recall': metrics['recall'],
            'F1 Score': metrics['f1'],
            'UP Acc': metrics['up_accuracy'],
            'DOWN Acc': metrics['down_accuracy']
        }
        
        names = list(performance.keys())
        values = list(performance.values())
        colors = ['green' if v > 0.5 else 'orange' if v > 0.3 else 'red' for v in values]
        
        axes[1, 0].bar(names, values, color=colors, alpha=0.7)
        axes[1, 0].set_ylim(0, 1)
        axes[1, 0].set_title('📊 Performance Metrics')
        axes[1, 0].tick_params(axis='x', rotation=45)
        axes[1, 0].grid(True, alpha=0.3)
        
        # Prediction vs actual distribution
        pred_up_pct = np.mean(metrics['predictions']) * 100
        actual_up_pct = np.mean(actuals) * 100
        
        categories = ['Actual UP%', 'Predicted UP%']
        percentages = [actual_up_pct, pred_up_pct]
        
        axes[1, 1].bar(categories, percentages, color=['blue', 'orange'], alpha=0.7)
        axes[1, 1].set_ylim(0, 100)
        axes[1, 1].set_title('⚖️ Prediction Balance')
        axes[1, 1].set_ylabel('Percentage')
        axes[1, 1].grid(True, alpha=0.3)
        
        # Add balance line
        axes[1, 1].axhline(y=actual_up_pct, color='blue', linestyle='--', alpha=0.5, label='Target')
        
        plt.tight_layout()
        plt.show()
        print("✅ Balanced visualization complete! ⚖️")

def main():
    print("🚀 MOON DEV'S BALANCED RF - FIXING OVERCORRECTION ⚖️")
    print("=" * 60)
    
    predictor = BalancedRFPredictor()
    
    # Load data
    data_path = "/Users/md/Dropbox/dev/github/moon-dev-trading-bots/research/machine_learning/processed_data/liquidations_BTC_processed.csv"
    df = predictor.load_and_engineer_features(data_path)
    
    if df is None:
        return
    
    # Create sequences
    X, y = predictor.create_sequences(df)
    
    # Split data
    train_size = int(0.7 * len(X))
    val_size = int(0.15 * len(X))
    
    X_train = X[:train_size]
    X_val = X[train_size:train_size+val_size]
    X_test = X[train_size+val_size:]
    y_train = y[:train_size]
    y_val = y[train_size:train_size+val_size]
    y_test = y[train_size+val_size:]
    
    print(f"⚖️ Data split - Train: {len(X_train)}, Val: {len(X_val)}, Test: {len(X_test)}")
    
    # Train model
    predictor.train_balanced_model(X_train, y_train)
    
    # Optimize threshold
    predictor.optimize_threshold(X_val, y_val)
    
    # Final evaluation
    metrics = predictor.evaluate_final(X_test, y_test)
    
    # Plot results
    predictor.plot_results(metrics)
    
    print("🎉 MOON DEV'S BALANCED RF COMPLETE! ⚖️")
    print(f"📊 Result: {metrics['balance_status']}")
    print(f"💰 Trading: {metrics['trading_status']}")

if __name__ == "__main__":
    main() 