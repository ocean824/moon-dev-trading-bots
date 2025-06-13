"""
🌙 MOON DEV'S RANDOM FOREST LIQUIDATION PREDICTOR - 15 MINUTES 🚀
Predicting BTC price moves using liquidation data with Random Forest
🌲 15-Minute timeframe - OPTIMAL for liquidation signals! 🌲
⚡ FAST enough to catch liquidation cascades, SLOW enough to filter noise!
"""

# 🌙 MOON DEV'S TRAINING CONFIGURATION CONSTANTS 🚀
# ================================================

# 🏠 LOCAL MODE SWITCH - Change to False for full cloud runs! 🚀
LOCAL_MODE = True             # Set to True for faster testing

# Training Constants (scaled by LOCAL_MODE)
# 🚀 OPTIMIZED RF HYPERPARAMETERS FOR 15-MINUTE LIQUIDATION SIGNALS! 🚀
N_ESTIMATORS = 300 if LOCAL_MODE else 500      # Fewer trees for faster 15-min signals
MAX_DEPTH = 8                                  # Shallower for faster timeframe  
MIN_SAMPLES_SPLIT = 15                         # Smaller splits for more granular patterns
MIN_SAMPLES_LEAF = 8                           # Smaller leaves for 15-min sensitivity
MAX_FEATURES = 'sqrt'                          # Optimal: sqrt features per split
MAX_SAMPLES = 0.8                              # Slightly less sampling for speed
CLASS_WEIGHT_STRATEGY = 'balanced_subsample'   # Aggressive balancing for liquidations
N_JOBS = -1                                    # Use all CPU cores

# Data Processing Constants (optimized for 15-minute signals)
DATA_SAMPLE_FRACTION = 0.3 if LOCAL_MODE else 1.0  # 30% for local testing
LOOKBACK_WINDOW = 24          # 6 hours of 15-minute data (24 × 15min = 6 hours)
PREDICTION_HORIZON = 1        # 1 step ahead = 15 minutes prediction
MAX_RETURN_CAP = 5.0          # Lower cap for 15-min moves (500% max)
MIN_RETURN_CAP = -0.95        # 95% loss cap for 15-min
TARGET_THRESHOLD = 0.002      # 0.2% threshold (lower for 15-min sensitivity)

# Feature Selection (scaled by LOCAL_MODE)
CORE_FEATURES = [
    'side', 'quantity_sum', 'quantity_mean', 'price_last', 'price_mean',
    'usd_liq_volume', 'usd_liq_net', 'liq_velocity', 'liq_imbalance',
    'total_liq_events', 'hour', 'minute', 'day_of_week'
] if LOCAL_MODE else None  # None means use all features

# 🎯 MOON DEV'S FOCUSED LIQUIDATION FEATURES (Optimized for 15-min!)
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
print(f"🌙 MOON DEV'S 15-MINUTE RANDOM FOREST CONSTANTS LOADED! 🚀")
print(f"{mode_emoji} MODE: {mode_name}")
print(f"   📊 Data Sample: {DATA_SAMPLE_FRACTION*100:.2f}% of TIME PERIOD (most recent data)")
print(f"   🌲 Trees: {N_ESTIMATORS}")
print(f"   📏 Max Depth: {MAX_DEPTH}")  
print(f"   🔧 Lookback: {LOOKBACK_WINDOW} periods (6 hours of 15-min data)")
print(f"   ⏰ EXPERIMENT: 15-minute bars - OPTIMAL for liquidation signals!")
print(f"   🎯 Prediction: {PREDICTION_HORIZON} step ahead (15 minutes)")
print(f"   📈 Threshold: {TARGET_THRESHOLD*100:.1f}% (optimized for 15-min sensitivity)")
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

print("🌙 MOON DEV'S 15-MINUTE RANDOM FOREST LIQUIDATION PREDICTOR LOADING... 🚀")
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
        
        print(f"🌲 Moon Dev 15-Min Random Forest initialized with {lookback_window} lookback window")
        print(f"🎯 Predicting {prediction_horizon} steps ahead (15 minutes)")
        print("=" * 50)
    
    def load_liquidation_data(self, data_path):
        """
        🌙 Load Moon Dev's liquidation data for 15-minute analysis
        """
        print("📊 Loading liquidation data for Moon Dev's 15-min RF... 🌙")
        print(f"🔍 Moon Dev checking file path: {data_path}")
        
        if not os.path.exists(data_path):
            print(f"❌ Moon Dev, data file not found: {data_path}")
            return None
            
        print("✅ Moon Dev found the data file! Loading now... 🚀")
        
        # Load the liquidation data
        df = pd.read_csv(data_path)
        print(f"🎉 Moon Dev loaded {len(df):,} liquidation records! 🚀")
        print(f"📊 Moon Dev's data shape: {df.shape}")
        
        # ⏰ EXPERIMENT: 15-minute aggregation for Moon Dev!
        print("\n⏰ MOON DEV'S 15-MINUTE AGGREGATION EXPERIMENT ⏰")
        print("=" * 50)
        original_count = len(df)
        original_symbols = df['symbol'].nunique()
        
        print(f"🔍 Original liquidations: {original_count:,}")
        print(f"🌊 All symbols included: {original_symbols}")
        print(f"⏰ Using 15-minute bars - OPTIMAL for liquidation signals!")
        print(f"🎯 Hypothesis: 15-min captures liquidation cascades before they dissipate")
        print(f"⚡ Fast enough for signals, slow enough to filter noise")
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