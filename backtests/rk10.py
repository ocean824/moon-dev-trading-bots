# Install necessary libraries first (if you haven't already):
# !pip install backtesting pandas numpy talib

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
from backtesting.lib import crossover
import talib

# Load data from provided CSV path
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/crypto_data/BTC-1h-1000wks-data.csv'
data = pd.read_csv(data_path)

# Normalize data columns to standard names
def normalize_data(df):
    column_maps = {
        'Open': ['Open', 'open'],
        'High': ['High', 'high'],
        'Low': ['Low', 'low'],
        'Close': ['Close', 'close'],
        'Volume': ['Volume', 'volume']
    }
    normalized_df = pd.DataFrame()
    for standard_name, possible_names in column_maps.items():
        found_col = next((col for col in possible_names if col in df.columns), None)
        if found_col:
            normalized_df[standard_name] = df[found_col]
        else:
            raise ValueError(f"Could not find column {standard_name}")
    if 'datetime' in df.columns:
        normalized_df.index = pd.to_datetime(df['datetime'])
    else:
        raise ValueError("Could not find 'datetime' column in data")
    return normalized_df

data = normalize_data(data)
data.dropna(inplace=True)

class EMA_Stochastic_Strategy(Strategy):

    def init(self):
        close = self.data.Close
        high = self.data.High
        low = self.data.Low

        # EMA indicators
        self.ema50 = self.I(talib.EMA, close, timeperiod=50)
        self.ema200 = self.I(talib.EMA, close, timeperiod=200)

        # Stochastic Oscillator
        self.slowk, self.slowd = self.I(talib.STOCH, high, low, close, fastk_period=14, slowk_period=3, slowd_period=3)

    def next(self):
        price = self.data.Close[-1]

        # Long Entry Conditions
        if (price > self.ema50[-1] and price > self.ema200[-1] and
            crossover(self.slowk, 20) and not self.position):

            recent_lows = self.data.Low[-10:-1]
            stop_loss = recent_lows.min() - (0.002 * price)
            if stop_loss >= price:
                stop_loss = price * 0.995

            take_profit = price + 1.5 * (price - stop_loss)
            if take_profit <= price:
                take_profit = price * 1.005

            print(f"Attempting Long | Price: {price}, SL: {stop_loss}, TP: {take_profit}")

            self.buy(sl=stop_loss, tp=take_profit)

        # Short Entry Conditions
        elif (price < self.ema50[-1] and price < self.ema200[-1] and
              crossover(80, self.slowk) and not self.position):

            recent_highs = self.data.High[-10:-1]
            stop_loss = recent_highs.max() + (0.002 * price)
            if stop_loss <= price:
                stop_loss = price * 1.005

            take_profit = price - 1.5 * (stop_loss - price)
            if take_profit >= price:
                take_profit = price * 0.995

            print(f"Attempting Short | Price: {price}, SL: {stop_loss}, TP: {take_profit}")

            self.sell(sl=stop_loss, tp=take_profit)

        # Exit Conditions
        if self.position:
            if self.position.is_long and self.slowk[-1] > 80:
                print(f"Closing Long Position at Price: {price}")
                self.position.close()

            elif self.position.is_short and self.slowk[-1] < 20:
                print(f"Closing Short Position at Price: {price}")
                self.position.close()

# Run the backtest
bt = Backtest(data, EMA_Stochastic_Strategy, cash=100000, commission=0.0006)
stats = bt.run()

# Output results
print(stats)
bt.plot()