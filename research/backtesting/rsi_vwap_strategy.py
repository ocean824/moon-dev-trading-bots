"""
🌙 MOON DEV'S RSI + VWAP TRADING STRATEGY BACKTEST 🚀
Advanced backtesting using RSI momentum and VWAP mean reversion
"""

import yfinance as yf
import pandas as pd
import numpy as np
import pandas_ta as ta
from backtesting import Backtest, Strategy
from backtesting.lib import crossover, crossunder
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print("🌙 MOON DEV'S RSI + VWAP STRATEGY LOADING... 🚀")
print("=" * 60)

class RSI_VWAP_Strategy(Strategy):
    """
    🌙 Moon Dev's RSI + VWAP Trading Strategy
    
    Entry Signals:
    - Long: RSI < 30 (oversold) AND price below VWAP (undervalued)
    - Short: RSI > 70 (overbought) AND price above VWAP (overvalued)
    
    Exit Signals:
    - Take profit at opposite RSI levels
    - Stop loss at 2% for risk management
    """
    
    # Strategy parameters (can be optimized)
    rsi_period = 14
    rsi_oversold = 30
    rsi_overbought = 70
    stop_loss_pct = 0.02  # 2% stop loss
    take_profit_pct = 0.04  # 4% take profit
    
    def init(self):
        """🚀 Initialize Moon Dev's indicators"""
        print("🔧 Moon Dev initializing RSI + VWAP indicators... 🌙")
        
        # Calculate RSI using pandas_ta (Moon Dev's preference!)
        self.rsi = self.I(ta.rsi, pd.Series(self.data.Close), length=self.rsi_period)
        
        # Calculate VWAP using pandas_ta
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low) 
        close = pd.Series(self.data.Close)
        volume = pd.Series(self.data.Volume)
        
        self.vwap = self.I(ta.vwap, high, low, close, volume)
        
        print(f"📊 Moon Dev's indicators ready! RSI period: {self.rsi_period}")
        print(f"🎯 Oversold threshold: {self.rsi_oversold}, Overbought: {self.rsi_overbought}")
        print(f"🛡️ Stop loss: {self.stop_loss_pct*100}%, Take profit: {self.take_profit_pct*100}%")
        print("=" * 50)
    
    def next(self):
        """🌙 Moon Dev's trading logic for each bar"""
        current_price = self.data.Close[-1]
        current_rsi = self.rsi[-1]
        current_vwap = self.vwap[-1]
        
        # Skip if indicators not ready
        if np.isnan(current_rsi) or np.isnan(current_vwap):
            return
        
        # Current position info
        if self.position.size == 0:
            position_status = "📊 No position"
        elif self.position.size > 0:
            position_status = f"📈 Long position: {self.position.size:.6f} BTC"
        else:
            position_status = f"📉 Short position: {abs(self.position.size):.6f} BTC"
        
        # 🚀 LONG ENTRY SIGNAL
        if (not self.position and 
            current_rsi < self.rsi_oversold and 
            current_price < current_vwap):
            
            self.buy(size=1.0)  # Full position
            print(f"🟢 MOON DEV LONG ENTRY! 🚀")
            print(f"   💰 Price: ${current_price:,.2f}")
            print(f"   📊 RSI: {current_rsi:.2f} (oversold)")
            print(f"   📈 VWAP: ${current_vwap:,.2f} (price below)")
            print(f"   🎯 Entry reason: RSI oversold + price below VWAP")
            print("=" * 50)
        
        # 🔴 SHORT ENTRY SIGNAL  
        elif (not self.position and 
              current_rsi > self.rsi_overbought and 
              current_price > current_vwap):
            
            self.sell(size=1.0)  # Full position
            print(f"🔴 MOON DEV SHORT ENTRY! 📉")
            print(f"   💰 Price: ${current_price:,.2f}")
            print(f"   📊 RSI: {current_rsi:.2f} (overbought)")
            print(f"   📈 VWAP: ${current_vwap:,.2f} (price above)")
            print(f"   🎯 Entry reason: RSI overbought + price above VWAP")
            print("=" * 50)
        
        # 🛡️ RISK MANAGEMENT & EXITS
        elif self.position:
            entry_price = self.position.entry_price
            current_pnl_pct = (current_price - entry_price) / entry_price
            
            if self.position.size > 0:  # Long position
                # Long take profit: RSI overbought OR +4% profit
                if (current_rsi > self.rsi_overbought or 
                    current_pnl_pct >= self.take_profit_pct):
                    
                    self.position.close()
                    print(f"🟢 MOON DEV LONG EXIT (PROFIT)! 🎉")
                    print(f"   💰 Exit price: ${current_price:,.2f}")
                    print(f"   📊 RSI: {current_rsi:.2f}")
                    print(f"   💵 PnL: {current_pnl_pct*100:+.2f}%")
                    reason = "RSI overbought" if current_rsi > self.rsi_overbought else "Take profit hit"
                    print(f"   🎯 Exit reason: {reason}")
                    print("=" * 50)
                
                # Long stop loss: -2% loss
                elif current_pnl_pct <= -self.stop_loss_pct:
                    self.position.close()
                    print(f"🛑 MOON DEV LONG STOP LOSS! 😢")
                    print(f"   💰 Exit price: ${current_price:,.2f}")
                    print(f"   📊 RSI: {current_rsi:.2f}")
                    print(f"   💵 PnL: {current_pnl_pct*100:+.2f}%")
                    print(f"   🎯 Exit reason: Stop loss triggered")
                    print("=" * 50)
            
            else:  # Short position
                # Short take profit: RSI oversold OR +4% profit (price dropped)
                if (current_rsi < self.rsi_oversold or 
                    current_pnl_pct <= -self.take_profit_pct):  # Negative PnL for shorts = profit
                    
                    self.position.close()
                    print(f"🔴 MOON DEV SHORT EXIT (PROFIT)! 🎉")
                    print(f"   💰 Exit price: ${current_price:,.2f}")
                    print(f"   📊 RSI: {current_rsi:.2f}")
                    print(f"   💵 PnL: {-current_pnl_pct*100:+.2f}%")  # Flip sign for short
                    reason = "RSI oversold" if current_rsi < self.rsi_oversold else "Take profit hit"
                    print(f"   🎯 Exit reason: {reason}")
                    print("=" * 50)
                
                # Short stop loss: +2% loss (price went up)
                elif current_pnl_pct >= self.stop_loss_pct:
                    self.position.close()
                    print(f"🛑 MOON DEV SHORT STOP LOSS! 😢")
                    print(f"   💰 Exit price: ${current_price:,.2f}")
                    print(f"   📊 RSI: {current_rsi:.2f}")
                    print(f"   💵 PnL: {-current_pnl_pct*100:+.2f}%")  # Flip sign for short
                    print(f"   🎯 Exit reason: Stop loss triggered")
                    print("=" * 50)

def download_bitcoin_data(period="2y", interval="1h"):
    """
    🌙 Download Moon Dev's Bitcoin data from Yahoo Finance
    """
    print(f"📥 Downloading Bitcoin data from Yahoo Finance... 🌙")
    print(f"⏰ Period: {period}, Interval: {interval}")
    
    try:
        # Download Bitcoin data
        ticker = "BTC-USD"
        btc = yf.Ticker(ticker)
        data = btc.history(period=period, interval=interval)
        
        if data.empty:
            print("❌ Moon Dev, no data received from Yahoo Finance!")
            return None
        
        # Clean up the data
        data = data.dropna()
        
        print(f"🎉 Moon Dev successfully downloaded {len(data):,} data points! 🚀")
        print(f"📅 Date range: {data.index[0].strftime('%Y-%m-%d')} to {data.index[-1].strftime('%Y-%m-%d')}")
        print(f"💰 Price range: ${data['Close'].min():,.2f} - ${data['Close'].max():,.2f}")
        print(f"📊 Data shape: {data.shape}")
        print("=" * 50)
        
        return data
        
    except Exception as e:
        print(f"❌ Error downloading data: {e}")
        return None

def run_backtest(data, cash=10000, commission=0.002):
    """
    🚀 Run Moon Dev's RSI + VWAP backtest
    """
    print(f"🎮 Starting Moon Dev's RSI + VWAP backtest... 🌙")
    print(f"💰 Starting cash: ${cash:,}")
    print(f"💸 Commission: {commission*100}%")
    print("=" * 60)
    
    # Initialize backtest
    bt = Backtest(data, RSI_VWAP_Strategy, cash=cash, commission=commission)
    
    # Run the backtest
    print("🚀 Moon Dev's backtest running...")
    stats = bt.run()
    
    # Print ALL stats (Moon Dev's rule!)
    print("\n🎯 MOON DEV'S COMPLETE BACKTEST RESULTS 🌙")
    print("=" * 60)
    print(stats)
    print("=" * 60)
    
    # Additional Moon Dev analysis
    print("\n📊 MOON DEV'S DETAILED ANALYSIS 🚀")
    print("=" * 40)
    
    total_return = stats['Return [%]']
    max_drawdown = stats['Max. Drawdown [%]']
    sharpe_ratio = stats['Sharpe Ratio']
    win_rate = stats['Win Rate [%]']
    num_trades = stats['# Trades']
    
    print(f"🎯 Total Return: {total_return:.2f}%")
    print(f"📉 Max Drawdown: {max_drawdown:.2f}%")
    print(f"📈 Sharpe Ratio: {sharpe_ratio:.2f}")
    print(f"🎲 Win Rate: {win_rate:.2f}%")
    print(f"🔄 Number of Trades: {num_trades}")
    
    # Moon Dev's performance rating
    if total_return > 20:
        print("🌙 Moon Dev says: EXCELLENT PERFORMANCE! 🚀🚀🚀")
    elif total_return > 10:
        print("🌙 Moon Dev says: Good performance! 🚀🚀")
    elif total_return > 0:
        print("🌙 Moon Dev says: Positive but could be better 🚀")
    else:
        print("🌙 Moon Dev says: Needs improvement 😅")
    
    # Risk assessment
    if max_drawdown < -30:
        print("⚠️ Moon Dev warning: High drawdown risk!")
    elif max_drawdown < -15:
        print("⚠️ Moon Dev: Moderate drawdown risk")
    else:
        print("✅ Moon Dev: Acceptable drawdown risk")
    
    print("=" * 60)
    
    # Plot results (but don't save - Moon Dev's rule!)
    print("📈 Showing Moon Dev's backtest plot...")
    bt.plot(show_legend=True, filename=None)  # filename=None means don't save
    plt.show()
    
    return stats, bt

def optimize_strategy(data):
    """
    🔧 Optimize Moon Dev's strategy parameters
    """
    print("🔧 Starting Moon Dev's strategy optimization... 🌙")
    
    bt = Backtest(data, RSI_VWAP_Strategy)
    
    # Optimize RSI parameters
    optimization_results = bt.optimize(
        rsi_period=range(10, 21, 2),           # RSI period: 10, 12, 14, 16, 18, 20
        rsi_oversold=range(25, 36, 5),         # Oversold: 25, 30, 35
        rsi_overbought=range(65, 76, 5),       # Overbought: 65, 70, 75
        stop_loss_pct=[0.015, 0.02, 0.025],   # Stop loss: 1.5%, 2%, 2.5%
        maximize='Sharpe Ratio',               # Optimize for risk-adjusted returns
        constraint=lambda p: p.rsi_overbought > p.rsi_oversold + 30  # Ensure proper spread
    )
    
    print("🎉 Moon Dev's optimization complete! 🚀")
    print("📊 Best parameters found:")
    print(f"   RSI Period: {optimization_results._strategy.rsi_period}")
    print(f"   RSI Oversold: {optimization_results._strategy.rsi_oversold}")
    print(f"   RSI Overbought: {optimization_results._strategy.rsi_overbought}")
    print(f"   Stop Loss: {optimization_results._strategy.stop_loss_pct*100}%")
    print("=" * 50)
    
    return optimization_results

def main():
    """
    🌙 Moon Dev's main RSI + VWAP backtesting pipeline
    """
    print("🚀 STARTING MOON DEV'S RSI + VWAP BACKTEST SYSTEM 🌙")
    print("=" * 60)
    
    # Download Bitcoin data
    data = download_bitcoin_data(period="2y", interval="1h")
    
    if data is None:
        print("❌ Moon Dev can't proceed without data!")
        return
    
    # Run basic backtest
    stats, bt = run_backtest(data, cash=10000, commission=0.002)
    
    # Ask user if they want to optimize
    print("\n🔧 Want to optimize the strategy? (This may take a few minutes)")
    optimize = input("Enter 'y' for yes, any other key to skip: ").lower()
    
    if optimize == 'y':
        print("🔧 Running optimization for Moon Dev...")
        optimized_stats = optimize_strategy(data)
        
        print("\n🎯 OPTIMIZED RESULTS:")
        print("=" * 40)
        print(optimized_stats)
        print("=" * 40)
    
    print("\n🎉 MOON DEV'S RSI + VWAP BACKTEST COMPLETE! 🚀🌙")
    print("Remember: Past performance doesn't guarantee future results!")
    print("Always consider transaction costs and slippage in live trading! 💰")
    print("=" * 60)

if __name__ == "__main__":
    main() 