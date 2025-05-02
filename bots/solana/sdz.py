'''
Building out a supply and demand zone for the hand-picked winners out of my copy and trending Solana bots. 

the idea is that some 'winners' will float to the top of my copy bot, sniper and trending solana bots
and those can be placed into this bot to trade a Supply and Demand Zone strategy 
this will allow for better entries and accumulation of free tokens 
'''

import nice_funcs as n
from termcolor import colored, cprint
import time
import schedule
from datetime import datetime

# motion - FFVcrc7wxCQ2HsxY6jhKNPwWUeKJsL472K28Vw16pump
# housecoin - DitHyRMQiSDhn5cnKMJV2CDDt6sVct96YrECiM49pump

# Moon Dev's public address
MY_ADDRESS = "G1vNV2SkzGPTBTDd7c3iypL4TPNGbe37rEbJb7cxVTQS"

symbols = [
    'DitHyRMQiSDhn5cnKMJV2CDDt6sVct96YrECiM49pump',  # housecoin
#     '8BtoThi2ZoXnF7QQK1Wjmh2JuBw9FjVvhnGMVZ2vpump',
#     'Df6yfrKC8kZE3KNkrHERKzAetSxbrWeniQfyJY4Jpump',
#     'Hax9LTgsQkze1YFychnBLtFH8gYbQKtKfWKKg2SP6gdD',
#     'C3DwDjT17gDvvCYC2nsdGHxDHVmQRdhKfpAdqQ29pump',
#     'FtUEW73K6vEYHfbkfpdBZfWpxgQar2HipGdbutEhpump',
#     'A8C3xuqscfmyLrte3VmTqrAq8kgMASius9AFNANwpump',
#     'HeLp6NuQkmYB4pYWo2zYs22mESHXPQYzXbB8n4V98jwC',
]
timeframe = '1m'
days_back_4_data = .2
SLIPPAGE = 99 # .99%

# Trend-based sell percentages
SELL_PERCENTAGE_TRENDING_UP = 0.50   # 50% sell in uptrend
SELL_PERCENTAGE_TRENDING_DOWN = 0.95  # 95% sell in downtrend

# Position thresholds
POSITION_SIZE_USD = 50  # Target position size in USD
MINIMUM_POSITION_PCT = 0.05  # 5% of target position size as minimum to consider trading
BUFFER_PCT = 0.05  # 5% buffer to account for price fluctuations

# Order execution settings
ORDERS_PER_OPEN = 2  # Number of buy orders to place when opening position
ORDERS_PER_SELL = 3  # Number of sell orders to place in each sell attempt

# SMA settings
SMA_TIMEFRAME = '1H'  # Use 1H data directly from Birdeye
SMA_DAYS_BACK = 2     # Get 2 days of data to ensure enough bars
SMA_BARS = 10         # Use 10 bars for SMA
SMA_BUFFER_PCT = 0.10  # 10% buffer zone around SMA for trend determination

def aggregate_to_2h(df):
    """
    Aggregate 1H data into 2H bars
    """
    # Set the datetime column as index if it isn't already
    if 'Datetime (UTC)' in df.columns:
        df = df.set_index('Datetime (UTC)')
    
    # Resample to 2H
    df_2h = df.resample('2H', closed='left', label='left').agg({
        'Open': 'first',
        'High': 'max',
        'Low': 'min',
        'Close': 'last',
        'Volume': 'sum'
    })
    return df_2h

def check_trend(symbol):
    """
    Check if price is above/below SMA for trend determination
    Returns: 
        - 'up' if price > SMA * (1 - buffer)
        - 'down' if price < SMA * (1 - buffer)
    """
    try:
        price = n.token_price(symbol)
        if price is None:
            cprint(f'❌ Could not get price for {symbol[:4]}', 'red')
            return 'down'
        
        cprint(f'🏷️ Current price for {symbol[:4]}: ${price:.8f}', 'cyan')
        
        df = n.get_data(symbol, SMA_DAYS_BACK, SMA_TIMEFRAME)
        if df.empty:
            cprint(f'❌ No data available for trend analysis of {symbol[:4]}', 'red')
            return 'down'
            
        available_bars = len(df)
        if available_bars < 3:
            cprint(f'⚠️ Not enough bars for {symbol[:4]} - defaulting to down trend', 'yellow')
            return 'down'
            
        bars_to_use = min(available_bars, SMA_BARS)
        sma = df['Close'].tail(bars_to_use).mean()
        sma_lower = sma * (1 - SMA_BUFFER_PCT)
        
        trend = 'up' if price > sma_lower else 'down'
        cprint(f'🌙 MoonDev Trend determined: {trend.upper()}', 'green' if trend == 'up' else 'red')
        
        return trend
        
    except Exception as e:
        cprint(f'❌ Error in trend analysis for {symbol[:4]}: {str(e)}', 'red')
        return 'down'

def verify_position_entry(symbol, expected_min_value):
    """
    Verify position was entered and retry if needed
    Returns True if position is established
    """
    max_attempts = 5
    attempt = 0
    
    while attempt < max_attempts:
        position = n.get_position(symbol)
        current_value = position * n.token_price(symbol)
        
        if current_value >= expected_min_value:
            cprint(f'✅ Position verified: ${current_value:.2f}', 'green')
            return True
            
        attempt += 1
        cprint(f'⏳ Waiting for position entry (attempt {attempt}/{max_attempts})...', 'yellow')
        time.sleep(5)
    
    cprint(f'❌ Failed to verify position entry after {max_attempts} attempts', 'red')
    return False

def verify_position_exit(symbol, expected_max_value):
    """
    Verify position was reduced and retry if needed
    Returns True if position is reduced to target
    """
    max_attempts = 5
    attempt = 0
    
    while attempt < max_attempts:
        position = n.get_position(symbol)
        current_value = position * n.token_price(symbol)
        
        if current_value <= expected_max_value:
            cprint(f'✅ Position reduction verified: ${current_value:.2f}', 'green')
            return True
            
        attempt += 1
        cprint(f'⏳ Waiting for position reduction (attempt {attempt}/{max_attempts})...', 'yellow')
        time.sleep(5)
    
    cprint(f'❌ Failed to verify position reduction after {max_attempts} attempts', 'red')
    return False

def execute_triple_sell(symbol, sell_size, slippage):
    """Execute three sell orders in quick succession"""
    for _ in range(ORDERS_PER_SELL):
        n.market_sell(symbol, sell_size, slippage)
        time.sleep(1)  # Small delay between orders
    time.sleep(5)  # Longer delay after triple-sell to let orders process

def verify_and_sell(symbol, sell_size, expected_max_value):
    """Execute triple-sells until position is reduced"""
    attempts = 0
    original_sell_size = sell_size  # Store original sell size to maintain percentage
    
    while True:  # Keep trying until position is reduced
        attempts += 1
        cprint(f'🔄 Sell attempt {attempts}...', 'yellow')
        execute_triple_sell(symbol, sell_size, SLIPPAGE)
        
        # Check if position is reduced
        position = n.get_position(symbol)
        current_value = position * n.token_price(symbol)
        
        if current_value <= expected_max_value:
            cprint('✅ Position successfully reduced!', 'green')
            return True
            
        # If not reduced enough, calculate remaining percentage to sell
        if position > 0:
            decimals = n.get_decimals(symbol)
            # Calculate how much of our intended sale is left to do
            remaining_to_sell = (original_sell_size - ((original_sell_size - (position * 10**decimals))))
            sell_size = int(min(remaining_to_sell, position * 10**decimals))  # Ensure we don't try to sell more than we have
            cprint(f'⚠️ Position not fully reduced. Trying again with {sell_size} tokens...', 'yellow')
            
            if attempts >= 3:  # Prevent infinite loops
                cprint('⚠️ Max sell attempts reached', 'yellow')
                return False
        else:
            cprint('✅ Position fully closed!', 'green')
            return True

def print_zone_info(symbol, zones, price, position, trend, current_value):
    cprint(f'\n🌙 MoonDev Zone Analysis for {symbol}', 'cyan', attrs=['bold'])
    cprint('=' * 50, 'cyan')
    
    cprint(f'📝 Contract: {symbol}', 'yellow')
    cprint(f'💰 Current Price: {price}', 'green')
    cprint(f'📊 Current Position: {position} tokens', 'magenta')
    cprint(f'💵 Position Value: ${current_value:.2f}', 'magenta')
    cprint(f'📈 Trend: {trend.upper()}', 'green' if trend == 'up' else 'red')
    
    position_pct = (current_value / POSITION_SIZE_USD) * 100
    cprint(f'📏 Position is at {position_pct:.1f}% of target size', 'yellow')
    
    cprint('\n🎯 Zone Ranges:', 'magenta')
    cprint(f'Demand Zone: {zones["dz"].min():.8f} - {zones["dz"].max():.8f}', 'blue')
    cprint(f'Supply Zone: {zones["sz"].min():.8f} - {zones["sz"].max():.8f}', 'red')
    cprint('=' * 50, 'cyan')

def check_zone_and_trade(symbol):
    print(f'🌙 MoonDev checking {symbol[:4]}...')
    
    trend = check_trend(symbol)
    sell_percentage = SELL_PERCENTAGE_TRENDING_UP if trend == 'up' else SELL_PERCENTAGE_TRENDING_DOWN
    
    position = n.get_position(symbol)
    price = n.token_price(symbol)
    current_value = position * price
    
    zones = n.supply_demand_zones(symbol, days_back_4_data, timeframe)
    if zones is None:
        cprint(f'❌ Not enough data for {symbol[:4]}', 'red')
        return
    
    print_zone_info(symbol, zones, price, position, trend, current_value)
    
    demand_zone_min = zones['dz'].min()
    demand_zone_max = zones['dz'].max()
    supply_zone_min = zones['sz'].min()
    supply_zone_max = zones['sz'].max()
    
    position_pct = current_value / POSITION_SIZE_USD
    
    if demand_zone_min <= price <= demand_zone_max:
        cprint(f'🎯 Price within demand zone range for {symbol[:4]}!', 'green', attrs=['bold'])
        
        if trend == 'up' and position_pct < (1 - BUFFER_PCT):
            if current_value < POSITION_SIZE_USD:
                amount_to_buy_usd = POSITION_SIZE_USD - current_value
                amount_to_buy_usdc = int(amount_to_buy_usd * 10**6)
                
                cprint(f'🛒 Need to buy ${amount_to_buy_usd:.2f} worth of tokens', 'green')
                
                for i in range(ORDERS_PER_OPEN):
                    n.market_buy(symbol, amount_to_buy_usdc, SLIPPAGE)
                    cprint(f'✨ Buy order {i+1}/{ORDERS_PER_OPEN} placed', 'yellow')
                    time.sleep(1)
                
                verify_position_entry(symbol, expected_min_value=POSITION_SIZE_USD * 0.9)
            else:
                cprint(f'✅ Already at or above target position size', 'green')
        else:
            if trend != 'up':
                cprint(f'⚠️ Not buying - Below SMA buffer zone', 'yellow')
            else:
                cprint(f'⚠️ Not buying - Position already near target size', 'yellow')
    
    elif supply_zone_min <= price <= supply_zone_max:
        cprint(f'🎯 Price within supply zone range for {symbol[:4]}!', 'red', attrs=['bold'])
        
        expected_position_value = current_value * (1 - sell_percentage)
        expected_position_pct = expected_position_value / POSITION_SIZE_USD
        
        if position > 0 and position_pct > (sell_percentage + MINIMUM_POSITION_PCT):
            cprint(f'💸 Selling {sell_percentage*100}% of position (Trend: {trend})', 'red')
            sell_size = position * sell_percentage
            decimals = n.get_decimals(symbol)
            sell_size = int(sell_size * 10 ** decimals)
            cprint(f'🧮 Sell size: {sell_size} tokens', 'yellow')
            cprint(f'📊 Expected position after sell: ${expected_position_value:.2f} ({expected_position_pct*100:.2f}% of target)', 'yellow')
            
            verify_and_sell(symbol, sell_size, expected_max_value=expected_position_value * 1.1)
        else:
            if position == 0:
                cprint(f'❌ No position to sell for {symbol[:4]}', 'red')
            else:
                cprint(f'⚠️ Position already sold down to target percentage', 'yellow')
    
    else:
        cprint(f'⏳ Price not in any zone range for {symbol[:4]}', 'yellow')

def run_bot():
    try:
        cprint('\n' + '='*50, 'cyan')
        cprint(f'🌙 MoonDev Bot Run at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', 'cyan', attrs=['bold'])
        cprint('='*50, 'cyan')
        
        cprint('🚀 Supply/Demand Zone Bot Settings:', 'cyan', attrs=['bold'])
        cprint(f'💰 Target Position Size: ${POSITION_SIZE_USD}', 'cyan')
        cprint(f'📈 Sell Size Up Trend: {SELL_PERCENTAGE_TRENDING_UP*100}%', 'green')
        cprint(f'📉 Sell Size Down Trend: {SELL_PERCENTAGE_TRENDING_DOWN*100}%', 'red')
        cprint(f'📊 Using 10-bar SMA for trend', 'cyan')
        cprint(f'🔒 Minimum Position: {MINIMUM_POSITION_PCT*100}%', 'yellow')
        cprint(f'📏 Position Buffer: {BUFFER_PCT*100}%', 'yellow')

        for symbol in symbols:
            try:
                check_zone_and_trade(symbol)
                time.sleep(5)  # Small delay between symbols
            except Exception as e:
                cprint(f'❌ Error processing symbol {symbol[:4]}: {str(e)}', 'red')
                continue  # Continue with next symbol even if one fails
                
    except Exception as e:
        cprint(f'❌ Major error in bot run: {str(e)}', 'red', attrs=['bold'])
        cprint('🔄 Bot will continue on next scheduled run', 'yellow')

if __name__ == "__main__":
    # Run immediately on start
    run_bot()
    
    # Schedule to run every 30 seconds
    schedule.every(30).seconds.do(run_bot)
    
    # Keep running forever
    while True:
        try:
            schedule.run_pending()
            time.sleep(3)
        except KeyboardInterrupt:
            break
        except Exception as e:
            cprint(f'❌ Error in main loop: {str(e)}', 'red')
            cprint('🔄 Restarting in 60 seconds...', 'yellow')
            time.sleep(60)  # Wait a minute before retrying on error