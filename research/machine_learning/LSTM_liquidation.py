"""
🌙 MOON DEV'S LSTM LIQUIDATION PREDICTOR 🚀
Predicting BTC price moves using liquidation data with LSTM neural networks
"""

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
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
import os
from datetime import datetime, timedelta
warnings.filterwarnings('ignore')

print("🌙 MOON DEV'S LSTM LIQUIDATION PREDICTOR LOADING... 🚀")
print("=" * 60)

class LSTMLiquidationPredictor:
    def __init__(self, lookback_window=60, prediction_horizon=5):
        """
        🌙 Moon Dev's LSTM Liquidation Predictor
        
        Args:
            lookback_window: How many time steps to look back (default 60)
            prediction_horizon: How many steps ahead to predict (default 5)
        """
        self.lookback_window = lookback_window
        self.prediction_horizon = prediction_horizon
        self.model = None
        self.price_scaler = MinMaxScaler()
        self.feature_scaler = StandardScaler()
        self.is_trained = False
        
        print(f"🚀 Moon Dev LSTM initialized with {lookback_window} lookback window")
        print(f"🎯 Predicting {prediction_horizon} steps ahead")
        print("=" * 50)
    
    def load_liquidation_data(self, data_path):
        """
        🌙 Load Moon Dev's liquidation data
        """
        print("📊 Loading liquidation data for Moon Dev... 🌙")
        
        if not os.path.exists(data_path):
            print(f"❌ Moon Dev, data file not found: {data_path}")
            return None
            
        # Load the liquidation data
        df = pd.read_csv(data_path)
        print(f"🎉 Moon Dev loaded {len(df):,} liquidation records! 🚀")
        
        # Convert timestamp if needed
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp').reset_index(drop=True)
            print("⏰ Moon Dev's data sorted by timestamp! 🌙")
        
        print(f"📈 Data shape: {df.shape}")
        print(f"🕐 Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        print("=" * 50)
        
        return df
    
    def engineer_features(self, df, time_window='1min'):
        """
        🌙 Engineer Moon Dev's liquidation features
        """
        print(f"🔧 Engineering features for Moon Dev with {time_window} windows... 🚀")
        
        # Set timestamp as index for resampling
        df_resampled = df.set_index('timestamp').resample(time_window).agg({
            'side': lambda x: (x.str.upper() == 'BUY').sum() - (x.str.upper() == 'SELL').sum(),  # Net short/long liquidations
            'quantity': ['sum', 'mean', 'std', 'max', 'count'],
            'price': ['first', 'last', 'min', 'max', 'mean', 'std']
        }).fillna(0)
        
        # Flatten column names
        df_resampled.columns = ['_'.join(col).strip() if col[1] else col[0] for col in df_resampled.columns]
        
        print("🎯 Moon Dev's basic aggregations complete! 🌙")
        
        # 🚀 LIQUIDATION-ONLY FEATURES (The Real Alpha!)
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
        for window in [5, 10, 20]:
            df_resampled[f'liq_volume_ma_{window}'] = df_resampled['quantity_sum'].rolling(window).mean()
            df_resampled[f'liq_count_ma_{window}'] = df_resampled['quantity_count'].rolling(window).mean()
            df_resampled[f'usd_liq_ma_{window}'] = df_resampled['usd_liq_volume'].rolling(window).mean()
            df_resampled[f'liq_velocity_ma_{window}'] = df_resampled['liq_velocity'].rolling(window).mean()
            df_resampled[f'liq_imbalance_ma_{window}'] = df_resampled['liq_imbalance'].rolling(window).mean()
        
        # Liquidation acceleration (velocity changes)
        df_resampled['liq_acceleration'] = df_resampled['liq_velocity'] - df_resampled['liq_velocity_ma_5']
        df_resampled['usd_liq_acceleration'] = df_resampled['usd_liq_velocity'] - df_resampled['usd_liq_ma_5']
        
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
    
    def create_target_variable(self, df, target_return_threshold=0.005):
        """
        🌙 Create Moon Dev's target variable for prediction
        """
        print(f"🎯 Creating target variable for Moon Dev (threshold: {target_return_threshold*100:.1f}%)... 🌙")
        
        # Calculate future returns
        df['future_return'] = df['price_last'].shift(-self.prediction_horizon) / df['price_last'] - 1
        
        # Create binary target: 1 if move > threshold, 0 otherwise
        df['target_binary'] = (abs(df['future_return']) > target_return_threshold).astype(int)
        
        # Create directional target: 1 for up, -1 for down, 0 for sideways
        df['target_direction'] = np.where(df['future_return'] > target_return_threshold, 1,
                                 np.where(df['future_return'] < -target_return_threshold, -1, 0))
        
        # Regression target (actual future return)
        df['target_return'] = df['future_return']
        
        print(f"🚀 Moon Dev's targets created!")
        print(f"📊 Binary target distribution: {df['target_binary'].value_counts().to_dict()}")
        print(f"📈 Direction target distribution: {df['target_direction'].value_counts().to_dict()}")
        print("=" * 50)
        
        return df
    
    def prepare_sequences(self, df, feature_columns):
        """
        🌙 Prepare LSTM sequences for Moon Dev
        """
        print("🔄 Preparing LSTM sequences for Moon Dev... 🚀")
        
        # Remove rows with NaN targets
        df_clean = df.dropna(subset=['target_return', 'target_binary', 'target_direction'])
        print(f"🧹 Cleaned data shape: {df_clean.shape} (Moon Dev approved!)")
        
        # Prepare features and targets
        features = df_clean[feature_columns].values
        targets_return = df_clean['target_return'].values
        targets_binary = df_clean['target_binary'].values
        targets_direction = df_clean['target_direction'].values
        
        # Scale features
        features_scaled = self.feature_scaler.fit_transform(features)
        
        # Create sequences
        X, y_return, y_binary, y_direction = [], [], [], []
        
        for i in range(self.lookback_window, len(features_scaled)):
            X.append(features_scaled[i-self.lookback_window:i])
            y_return.append(targets_return[i])
            y_binary.append(targets_binary[i])
            y_direction.append(targets_direction[i])
        
        X = np.array(X)
        y_return = np.array(y_return)
        y_binary = np.array(y_binary)
        y_direction = np.array(y_direction)
        
        print(f"🎉 Moon Dev's sequences ready! Shape: {X.shape} 🌙")
        print(f"📊 Feature sequences: {X.shape}")
        print(f"🎯 Target shapes - Return: {y_return.shape}, Binary: {y_binary.shape}, Direction: {y_direction.shape}")
        print("=" * 50)
        
        return X, y_return, y_binary, y_direction, df_clean.index[self.lookback_window:]
    
    def build_model(self, input_shape, model_type='regression'):
        """
        🌙 Build Moon Dev's LSTM model
        """
        print(f"🏗️ Building Moon Dev's LSTM model ({model_type})... 🚀")
        
        model = Sequential([
            LSTM(128, return_sequences=True, input_shape=input_shape, dropout=0.2, recurrent_dropout=0.2),
            BatchNormalization(),
            
            LSTM(64, return_sequences=True, dropout=0.2, recurrent_dropout=0.2),
            BatchNormalization(),
            
            LSTM(32, return_sequences=False, dropout=0.2, recurrent_dropout=0.2),
            BatchNormalization(),
            
            Dense(16, activation='relu'),
            Dropout(0.3),
            Dense(8, activation='relu'),
            Dropout(0.2),
        ])
        
        if model_type == 'regression':
            model.add(Dense(1, activation='linear'))  # For return prediction
            model.compile(optimizer=Adam(learning_rate=0.001), 
                         loss='mse', 
                         metrics=['mae'])
            print("📈 Moon Dev's regression model compiled! 🌙")
            
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
    
    def train_model(self, X_train, y_train, X_val, y_val, model_type='regression', epochs=100):
        """
        🌙 Train Moon Dev's LSTM model
        """
        print(f"🎓 Training Moon Dev's LSTM model ({model_type})... 🚀")
        
        # Build model
        self.model = self.build_model(input_shape=(X_train.shape[1], X_train.shape[2]), model_type=model_type)
        
        # Callbacks for Moon Dev's training
        callbacks = [
            EarlyStopping(monitor='val_loss', patience=15, restore_best_weights=True, verbose=1),
            ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=8, min_lr=1e-6, verbose=1)
        ]
        
        print("🚂 Moon Dev's training starting... 🌙")
        
        # Train the model
        history = self.model.fit(
            X_train, y_train,
            validation_data=(X_val, y_val),
            epochs=epochs,
            batch_size=32,
            callbacks=callbacks,
            verbose=1
        )
        
        self.is_trained = True
        print("🎉 Moon Dev's LSTM training complete! 🚀")
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
            else:
                predictions_binary = np.argmax(predictions, axis=1)
            
            accuracy = np.mean(predictions_binary == y_test)
            
            print("🎯 MOON DEV'S CLASSIFICATION METRICS 🌙")
            print("=" * 50)
            print(f"🎪 Accuracy: {accuracy:.4f}")
            
            metrics = {
                'accuracy': accuracy,
                'predictions': predictions_binary,
                'actuals': y_test
            }
        
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
    predictor = LSTMLiquidationPredictor(lookback_window=60, prediction_horizon=5)
    
    # Load data (adjust path as needed)
    data_path = "/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/moondev_api/liq_data.csv"  # Adjust this path
    df = predictor.load_liquidation_data(data_path)
    
    if df is None:
        print("❌ Moon Dev, please check your data path!")
        return
    
    # Engineer features
    df_features = predictor.engineer_features(df, time_window='1min')
    
    # Create target variables
    df_targets = predictor.create_target_variable(df_features, target_return_threshold=0.005)
    
    # Define feature columns (exclude target columns and timestamp)
    feature_columns = [col for col in df_targets.columns 
                      if col not in ['target_return', 'target_binary', 'target_direction', 'future_return']]
    
    print(f"🎯 Moon Dev using {len(feature_columns)} features: {feature_columns[:10]}..." if len(feature_columns) > 10 else f"🎯 Moon Dev using features: {feature_columns}")
    
    # Prepare sequences
    X, y_return, y_binary, y_direction, timestamps = predictor.prepare_sequences(df_targets, feature_columns)
    
    # Split data (80% train, 10% val, 10% test) - time series split
    train_size = int(0.8 * len(X))
    val_size = int(0.1 * len(X))
    
    X_train, X_val, X_test = X[:train_size], X[train_size:train_size+val_size], X[train_size+val_size:]
    y_train, y_val, y_test = y_return[:train_size], y_return[train_size:train_size+val_size], y_return[train_size+val_size:]
    
    print(f"🔄 Moon Dev's data split:")
    print(f"📊 Train: {X_train.shape[0]}, Val: {X_val.shape[0]}, Test: {X_test.shape[0]}")
    print("=" * 50)
    
    # Train the model
    history = predictor.train_model(X_train, y_train, X_val, y_val, model_type='regression', epochs=50)
    
    # Evaluate the model
    metrics = predictor.evaluate_model(X_test, y_test, model_type='regression')
    
    # Plot results
    predictor.plot_results(metrics, model_type='regression')
    
    print("🎉 MOON DEV'S LSTM LIQUIDATION PREDICTOR COMPLETE! 🚀🌙")
    print("=" * 60)

if __name__ == "__main__":
    main() 