from backtesting import Backtest, Strategy
from backtesting.lib import crossover
import pandas as pd
import numpy as np 
import talib 

print("🌙 Moon Dev's RSI Guppy Strategy Loading... 🚀")

def normalize_data(df):
    """Normalize different data formats to a standard format"""
    print("🔄 Normalizing data format...")
    
    # Create a mapping of expected columns to possible column names
    column_maps = {
        'Open': ['Open', 'open'],
        'High': ['High', 'high'],
        'Low': ['Low', 'low'],
        'Close': ['Close', 'close'],
        'Volume': ['Volume', 'volume']
    }
    
    # Create a new DataFrame with standardized column names
    normalized_df = pd.DataFrame()
    
    for standard_name, possible_names in column_maps.items():
        # Find the first matching column name that exists in the DataFrame
        found_col = next((col for col in possible_names if col in df.columns), None)
        if found_col:
            normalized_df[standard_name] = df[found_col]
        else:
            raise ValueError(f"Could not find a column matching {standard_name} in the data")
    
    # Handle different date formats
    if isinstance(df.index, pd.DatetimeIndex):
        normalized_df.index = df.index
    elif 'Date' in df.columns:
        normalized_df.index = pd.to_datetime(df['Date'])
    elif 'datetime' in df.columns:
        normalized_df.index = pd.to_datetime(df['datetime'])
    else:
        raise ValueError("Could not find date information in the data")
        
    print(f"✅ Data normalized successfully with columns: {list(normalized_df.columns)}")
    return normalized_df

class LSMAGuppyRSI(Strategy):
    lsma_period = 55
    rsi_period = 14 
    risk_multiplier = 2
    min_stop_distance = 0.002  # Increased to 0.2% minimum distance
    min_reward_ratio = 1.5  # Minimum reward:risk ratio

    def init(self):
        print("🎯 Moon Dev's Strategy Initialization")
        close = self.data.Close 
        time_period = np.arange(len(close))
        self.lsma = self.I(lambda x: self.calculate_lsma(x, self.lsma_period), close)
        self.rsi = self.I(talib.RSI, close, timeperiod=self.rsi_period)
        print("✨ Indicators Created Successfully!")

    def calculate_lsma(self, data, period):
        """ calculate linear regression moving average"""
        print("🧮 Calculating LSMA...")
        result = np.zeros_like(data)
        for i in range(period-1, len(data)):
            x = np.arange(period)
            y = data[i-period+1:i+1]
            slope, intercept = np.polyfit(x,y,1)
            result[i] = slope * (period -1 ) + intercept 
        return result 
    
    def validate_prices(self, entry, sl, tp, is_long):
        """Validate price levels for trade entry"""
        min_price_diff = entry * self.min_stop_distance
        
        if is_long:
            if not (0 < sl < entry < tp):
                return False
            if (entry - sl) < min_price_diff:
                return False
            if (tp - entry) < (entry - sl) * self.min_reward_ratio:
                return False
        else:  # Short
            if not (0 < tp < entry < sl):
                return False
            if (sl - entry) < min_price_diff:
                return False
            if (entry - tp) < (sl - entry) * self.min_reward_ratio:
                return False
        return True
    
    def next(self):
        price = self.data.Close[-1]
        
        if price <= 0:
            print(f"⚠️ Warning: Invalid price detected: {price}")
            return
            
        is_green_candle = self.data.Close[-1] > self.data.Open[-1]
        rsi_rising = self.rsi[-1] > self.rsi[-2]

        # check long conditions 
        long_conditions = (
            is_green_candle and 
            price > self.lsma[-1] and 
            rsi_rising
        )

        # check short conditions 
        short_conditions = (
            not is_green_candle and 
            price < self.lsma[-1] and 
            not rsi_rising
        )

        # entry signals
        if not self.position:
            if long_conditions:
                # Calculate stop loss with minimum distance
                sl_distance = max(self.min_stop_distance * price, price - self.lsma[-1])
                sl_price = price - sl_distance
                tp_distance = sl_distance * self.risk_multiplier
                tp_price = price + tp_distance

                if self.validate_prices(price, sl_price, tp_price, is_long=True):
                    print(f"🚀 LONG Entry - Price: {price:.4f}, SL: {sl_price:.4f}, TP: {tp_price:.4f}")
                    self.buy(sl=sl_price, tp=tp_price)
                else:
                    print(f"⚠️ Invalid long prices - Price: {price:.4f}, SL: {sl_price:.4f}, TP: {tp_price:.4f}")

            elif short_conditions:
                # Calculate stop loss with minimum distance
                sl_distance = max(self.min_stop_distance * price, self.lsma[-1] - price)
                sl_price = price + sl_distance
                tp_distance = sl_distance * self.risk_multiplier
                tp_price = price - (sl_distance * self.min_reward_ratio)  # Adjusted TP calculation

                if self.validate_prices(price, sl_price, tp_price, is_long=False):
                    print(f"🔻 SHORT Entry - Price: {price:.4f}, SL: {sl_price:.4f}, TP: {tp_price:.4f}")
                    self.sell(sl=sl_price, tp=tp_price)
                else:
                    print(f"⚠️ Skipping invalid short - Price: {price:.4f}, SL: {sl_price:.4f}, TP: {tp_price:.4f}")

        # exit signals 
        if self.position.is_long and price < self.lsma[-1]:
            print(f"🎯 Closing LONG position at {price:.4f}")
            self.position.close() 
        elif self.position.is_short and price > self.lsma[-1]:
            print(f"🎯 Closing SHORT position at {price:.4f}")
            self.position.close()

print("📊 Loading data...")
# load in the data 
data = pd.read_csv('/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/crypto_data/SOL-1d-1000wks-data.csv') 

# Normalize the data to handle different formats
data = normalize_data(data)

print(f"📈 Data loaded: {len(data)} candles from {data.index[0]} to {data.index[-1]}")
print(f"💰 Price range: ${data['Low'].min():.4f} - ${data['High'].max():.4f}")

bt = Backtest(data, LSMAGuppyRSI, cash=1000000, commission=0.002, exclusive_orders=True)

print("\n🎮 Starting backtest...")
stats = bt.run()
print(stats)

print("\n📈 Generating plot...")
bt.plot()
print("✨ Moon Dev's RSI Guppy Strategy Complete! ✨")