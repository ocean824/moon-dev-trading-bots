'''
Building out a supply and demand zone for the hand-picked winners out of my copy and trending Solana bots. 

the idea is that some 'winners' will float to the top of my copy bot, sniper and trending solana bots
and those can be placed into this bot to trade a Supply and Demand Zone strategy 
this will allow for better entries and accumulation of free tokens 

'''

import nice_funcs2 as n
from termcolor import colored, cprint
import time
import schedule
from datetime import datetime
import requests
import json
import pandas as pd

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
timeframe = '4H'
days_back_4_data = 19# .2
SLIPPAGE = 99 # .99%

# Trend-based sell percentages
SELL_PERCENTAGE_TRENDING_UP = 0.50   # 50% sell in uptrend
SELL_PERCENTAGE_TRENDING_DOWN = 0.95  # 95% sell in downtrend

# Position thresholds
POSITION_SIZE_USD = 150  # Target position size in USD
MINIMUM_POSITION_PCT = 0.05  # 5% of target position size as minimum to consider trading
BUFFER_PCT = 0.05  # 5% buffer to account for price fluctuations

# Order execution settings
ORDERS_PER_OPEN = 1  # Number of buy orders to place when opening position
ORDERS_PER_SELL = 1  # Single sell order at a time
SELL_LOOKBACK_HOURS = 12  # Hours to look back for previous sells
DELAY_BETWEEN_ORDERS = 8  # Seconds to wait between order attempts

# SMA settings for trading symbols (Birdeye 1H data)
SMA_TIMEFRAME = '1H'  # Use 1H data directly from Birdeye
SMA_DAYS_BACK = 2     # Get 2 days of data to ensure enough bars
SMA_BARS = 10         # Use 10 bars for SMA
SMA_BUFFER_PCT = 0.15  # 15% buffer zone around SMA for trend determination

# Market condition settings (Hyperliquid daily data)
MARKET_SMA_SHORT = 20  # 20-day SMA
MARKET_SMA_LONG = 40   # 40-day SMA
MARKET_DAYS_BACK = 60  # Get enough days for 40 SMA calculation

# Add after other constants
MINIMUM_TOTAL_BALANCE = 100  # Minimum total balance in USD before closing all positions
ZONE_MEMORY = {}  # To track last sell time in each zone
POSITION_TARGET_THRESHOLD = 0.10  # Must be within 10% of target position size
SCHEDULE_INTERVAL_MINUTES = 15 # How often the bot should run its main logic

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

def get_hyperliquid_price(symbol):
    """
    Get price from Hyperliquid API for major coins (BTC, ETH, SOL)
    """
    try:
        url = 'https://api.hyperliquid.xyz/info'
        headers = {'Content-Type': 'application/json'}
        
        data = {
            'type': 'l2Book',
            'coin': symbol
        }
        
        response = requests.post(url, headers=headers, data=json.dumps(data))
        l2_data = response.json()['levels']
        
        # Get mid price from bid and ask
        bid = float(l2_data[0][0]['px'])
        ask = float(l2_data[1][0]['px'])
        mid_price = (bid + ask) / 2
        
        return mid_price
    except Exception as e:
        cprint(f'❌ Error getting Hyperliquid price for {symbol}: {str(e)}', 'red')
        return None

def check_trend(symbol):
    """
    Check if price is above/below SMA for trend determination using daily data
    Returns: 
        - 'up' if price > SMA * (1 - buffer)
        - 'down' if price < SMA * (1 - buffer)
        - None if there was an error checking trend
    """
    try:
        # For major coins (BTC, ETH, SOL), use Hyperliquid price
        if symbol in ['BTC', 'ETH', 'SOL']:
            price = get_hyperliquid_price(symbol)
        else:
            # For other tokens, use existing price function
            price = n.token_price_moralis(symbol)
            
        if price is None:
            cprint(f'❌ Could not get price for {symbol}', 'red')
            return None  # Return None instead of 'down' on price error
        
        cprint(f'🏷️ Current price for {symbol}: ${price:.8f}', 'cyan')
        
        # Get daily data for SMA calculation
        cprint(f'📊 Getting {SMA_DAYS_BACK} days of daily data for trend analysis...', 'cyan')
        df = n.get_data(symbol, SMA_DAYS_BACK, SMA_TIMEFRAME)  # Using 1D timeframe
        
        if df.empty:
            cprint(f'❌ No daily data available for trend analysis of {symbol}', 'red')
            return None  # Return None instead of 'down' on data error
            
        available_bars = len(df)
        if available_bars < 3:
            cprint(f'⚠️ Not enough daily bars for {symbol} - cannot determine trend', 'yellow')
            return None  # Return None instead of 'down' on insufficient data
            
        bars_to_use = min(available_bars, SMA_BARS)
        sma = df['Close'].tail(bars_to_use).mean()
        sma_lower = sma * (1 - SMA_BUFFER_PCT)
        
        cprint(f'📈 Current Price: ${price:.2f}', 'cyan')
        cprint(f'📉 SMA{bars_to_use}: ${sma:.2f}', 'cyan')
        cprint(f'📊 SMA Lower Band (buffer): ${sma_lower:.2f}', 'cyan')
        
        trend = 'up' if price > sma_lower else 'down'
        cprint(f'🌙 MoonDev Trend determined: {trend.upper()}', 'green' if trend == 'up' else 'red')
        
        return trend
        
    except Exception as e:
        cprint(f'❌ Error in trend analysis for {symbol}: {str(e)}', 'red')
        return None  # Return None instead of 'down' on any error

def try_position_entry(symbol, amount_to_buy_usdc):
    """
    Position entry that checks if we have a position close to target size
    Returns True only if we have a position within 10% of target
    """
    max_attempts = 3
    attempt = 0
    
    while attempt < max_attempts:
        # Check if we already have a position
        position = n.get_position(symbol)
        
        if position > 0:
            current_value = position * n.token_price_moralis(symbol)
            position_pct = current_value / POSITION_SIZE_USD
            
            # Only consider it a success if within 10% of target
            if abs(1 - position_pct) <= 0.10:  # Within 10% of target
                cprint(f'✅ Have full position: ${current_value:.2f} ({position_pct*100:.1f}% of target)', 'green')
                return True
            else:
                cprint(f'⚠️ Position only at ${current_value:.2f} ({position_pct*100:.1f}% of target) - need more', 'yellow')
        
        # No position or not enough, try to buy
        cprint(f'🌙 MoonDev Order Attempt {attempt + 1}/{max_attempts}', 'yellow')
        n.market_buy(symbol, amount_to_buy_usdc, SLIPPAGE)
        cprint(f'✨ Buy order placed', 'yellow')
        
        # Quick check if we got the position
        cprint(f'⏳ Waiting {DELAY_BETWEEN_ORDERS}s for order to process...', 'yellow')
        time.sleep(DELAY_BETWEEN_ORDERS)  # Wait for order to process
        position = n.get_position(symbol)
        if position > 0:
            current_value = position * n.token_price_moralis(symbol)
            position_pct = current_value / POSITION_SIZE_USD
            
            if abs(1 - position_pct) <= 0.10:  # Within 10% of target
                cprint(f'✅ Got full position: ${current_value:.2f} ({position_pct*100:.1f}% of target)', 'green')
                return True
            else:
                cprint(f'⚠️ Position at ${current_value:.2f} ({position_pct*100:.1f}% of target) - continuing attempts', 'yellow')
        
        attempt += 1
        if attempt < max_attempts:
            cprint(f'🔄 Position not at target size, trying again...', 'yellow')
            time.sleep(1)
    
    cprint(f'❌ Failed to get full position after {max_attempts} attempts', 'red')
    return False

def load_sell_history():
    """Load sell history from CSV, create if doesn't exist"""
    try:
        df = pd.read_csv('data/sell_history.csv')
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df
    except FileNotFoundError:
        df = pd.DataFrame(columns=['timestamp', 'symbol', 'zone_type', 'zone_min', 'zone_max', 
                                 'position_before', 'position_after', 'sell_percentage'])
        df.to_csv('data/sell_history.csv', index=False)
        return df

def save_sell_history(df):
    """Save sell history to CSV"""
    df.to_csv('data/sell_history.csv', index=False)

def check_recent_sell(symbol, zone_type, zone_min, zone_max, current_position, trend):
    """
    Check if we've sold in this zone in the last SELL_LOOKBACK_HOURS by verifying position reduction
    Returns True if we detect a successful sell based on position size change
    """
    df = load_sell_history()
    if df.empty:
        return False
        
    # Get recent sells for this symbol in this zone
    cutoff_time = pd.Timestamp.now() - pd.Timedelta(hours=SELL_LOOKBACK_HOURS)
    recent_sells = df[
        (df['timestamp'] > cutoff_time) & 
        (df['symbol'] == symbol) &
        (df['zone_type'] == zone_type) &
        (df['zone_min'] == zone_min) &
        (df['zone_max'] == zone_max)
    ]
    
    if recent_sells.empty:
        return False
        
    # Get the most recent sell attempt's position before
    last_sell = recent_sells.sort_values('timestamp').iloc[-1]
    position_before = last_sell['position_before']
    
    # Calculate expected position reduction based on trend
    expected_reduction = SELL_PERCENTAGE_TRENDING_UP if trend == 'up' else SELL_PERCENTAGE_TRENDING_DOWN
    expected_position = position_before * (1 - expected_reduction)
    
    # Add 10% buffer for position verification
    buffer = 0.10
    min_expected = expected_position * (1 - buffer)
    max_expected = expected_position * (1 + buffer)
    
    # If current position is within expected range after sell, we've sold successfully
    if min_expected <= current_position <= max_expected:
        cprint(f'✅ Detected successful sell: Position {position_before:.2f} -> {current_position:.2f} (expected ~{expected_position:.2f})', 'green')
        return True
        
    # If current position is higher, sell didn't go through
    if current_position > position_before * 0.9:  # Allow 10% price fluctuation
        cprint(f'⚠️ Previous sell may not have executed: Position {position_before:.2f} -> {current_position:.2f}', 'yellow')
        return False
        
    # If position is much lower than expected, something else happened
    cprint(f'⚠️ Position changed unexpectedly: {position_before:.2f} -> {current_position:.2f}', 'yellow')
    return True  # Don't sell again if position changed dramatically

def log_sell(symbol, zone_type, zone_min, zone_max, position_before, position_after, sell_percentage):
    """Log a sell to the history"""
    df = load_sell_history()
    new_row = pd.DataFrame([{
        'timestamp': pd.Timestamp.now(),
        'symbol': symbol,
        'zone_type': zone_type,
        'zone_min': zone_min,
        'zone_max': zone_max,
        'position_before': position_before,
        'position_after': position_after,
        'sell_percentage': sell_percentage
    }])
    df = pd.concat([df, new_row], ignore_index=True)
    save_sell_history(df)
    cprint('📝 Logged sell to history', 'green')

def verify_position_exit(symbol, expected_max_value):
    """
    Verify position was reduced and retry if needed
    Returns True if position is reduced to target
    """
    max_attempts = 5
    attempt = 0
    
    while attempt < max_attempts:
        # Get current position using fetch_wallet_holdings_og
        positions_df = n.fetch_wallet_holdings_og(MY_ADDRESS)
        if positions_df.empty:
            position = 0
        else:
            symbol_position = positions_df[positions_df['Mint Address'] == symbol]
            position = float(symbol_position['Amount'].iloc[0]) if not symbol_position.empty else 0
            
        current_value = position * n.token_price_moralis(symbol)
        
        if current_value <= expected_max_value:
            cprint(f'✅ Position reduction verified: ${current_value:.2f}', 'green')
            return True, position  # Return both success status and current position
            
        attempt += 1
        cprint(f'⏳ Waiting for position reduction (attempt {attempt}/{max_attempts})...', 'yellow')
        time.sleep(5)
    
    cprint(f'❌ Failed to verify position reduction after {max_attempts} attempts', 'red')
    return False, position  # Return both failure status and current position

def execute_sell(symbol, sell_size, slippage):
    """Execute single sell order"""
    n.market_sell(symbol, sell_size, slippage)
    time.sleep(5)  # Wait for order to process

def verify_and_sell(symbol, sell_size, expected_max_value, zone_type, zone_min, zone_max, position_before, sell_percentage):
    """Execute sell and verify position reduction"""
    attempts = 0
    max_attempts = 3
    
    while attempts < max_attempts:
        attempts += 1
        cprint(f'🔄 Sell attempt {attempts}...', 'yellow')
        
        # Execute single sell
        execute_sell(symbol, sell_size, SLIPPAGE)
        
        # Verify the position reduction
        success, position_after = verify_position_exit(symbol, expected_max_value)
        
        if success:
            # Log the sell attempt
            log_sell(symbol, zone_type, zone_min, zone_max, position_before, position_after, sell_percentage)
            return True
            
        if attempts < max_attempts:
            cprint('⚠️ Sell not fully executed, retrying...', 'yellow')
            time.sleep(5)
    
    cprint('❌ Max sell attempts reached', 'red')
    return False

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

def check_market_sma_conditions():
    """
    Check if major coins (BTC, ETH, SOL) are in favorable trend using daily 20/40 SMA
    Returns True if at least 2 out of 3 coins are above their SMAs
    """
    cprint('\n🌙 MoonDev Market SMA Check', 'cyan', attrs=['bold'])
    cprint('=' * 50, 'cyan')
    
    coins_above_sma = 0
    coins_checked = 0
    
    for coin in ['BTC', 'ETH', 'SOL']:
        try:
            # Get current price from Hyperliquid
            current_price = get_hyperliquid_price(coin)
            if current_price is None:
                cprint(f'⚠️ Could not get {coin} price from Hyperliquid', 'yellow')
                continue
                
            cprint(f'\n📊 Checking {coin} SMAs...', 'cyan')
            cprint(f'💰 Current {coin} Price: ${current_price:.2f}', 'cyan')
            
            # Get daily OHLCV data from Hyperliquid
            snapshot_data = n.get_ohlcv_hl(coin, '1d', MARKET_DAYS_BACK)
            if not snapshot_data:
                cprint(f'⚠️ Could not get {coin} daily data', 'yellow')
                continue
                
            # Process the data into a DataFrame - this function already handles numeric conversion
            df = n.process_data_to_df_hl(snapshot_data, time_period=max(MARKET_SMA_SHORT, MARKET_SMA_LONG))
            if df.empty:
                cprint(f'⚠️ Could not process {coin} data', 'yellow')
                continue
                
            # Calculate SMAs using the numeric 'close' column
            df['SMA20'] = df['close'].rolling(window=MARKET_SMA_SHORT).mean()
            df['SMA40'] = df['close'].rolling(window=MARKET_SMA_LONG).mean()
            
            # Get the most recent SMA values
            latest_sma20 = df['SMA20'].iloc[-1]
            latest_sma40 = df['SMA40'].iloc[-1]
            
            cprint(f'📈 {coin} SMA20: ${latest_sma20:.2f}', 'cyan')
            cprint(f'📉 {coin} SMA40: ${latest_sma40:.2f}', 'cyan')
            
            # Check if price is above both SMAs
            if current_price > latest_sma20 and current_price > latest_sma40:
                cprint(f'✅ {coin} above both SMAs', 'green')
                coins_above_sma += 1
            else:
                cprint(f'❌ {coin} below SMAs', 'red')
            
            coins_checked += 1
            
        except Exception as e:
            cprint(f'❌ Error checking {coin}: {str(e)}', 'red')
            continue
    
    if coins_checked < 2:
        cprint('\n⚠️ Could not check enough coins - proceeding with caution', 'yellow')
        return None
        
    # Need at least 2 coins above SMAs for favorable conditions
    is_favorable = coins_above_sma >= 2
    cprint(f'\n{"✅" if is_favorable else "❌"} {coins_above_sma}/{coins_checked} coins above SMAs', 
           'green' if is_favorable else 'red')
    
    return is_favorable

def get_usdc_balance():
    """Get available USDC balance with retries"""
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            positions_df = n.fetch_wallet_holdings_og(MY_ADDRESS)
            cprint(f'🔍 MoonDev Debug - Full Positions DataFrame:', 'cyan')
            cprint(positions_df, 'cyan')
            
            if not positions_df.empty:
                # Look for USDC using its contract address in Mint Address column
                usdc_position = positions_df[positions_df['Mint Address'] == 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v']
                cprint(f'\n💫 MoonDev Debug - USDC Position Filter Result:', 'yellow')
                cprint(usdc_position, 'yellow')
                
                if not usdc_position.empty:
                    usdc_balance = float(usdc_position['USD Value'].iloc[0])
                    cprint(f'🌙 MoonDev USDC Balance: ${usdc_balance:.2f} 💰', 'cyan')
                    return usdc_balance
                else:
                    cprint('⚠️ No USDC position found using contract address', 'yellow')
            
            retry_count += 1
            if retry_count < max_retries:
                cprint(f'⚠️ Failed to get USDC balance, attempt {retry_count}/{max_retries}', 'yellow')
                time.sleep(5)
        except Exception as e:
            cprint(f'❌ Error getting USDC balance: {str(e)}', 'red')
            cprint(f'🔍 MoonDev Debug - Exception info:', 'red')
            import traceback
            cprint(traceback.format_exc(), 'red')
            retry_count += 1
            if retry_count < max_retries:
                time.sleep(5)
    
    cprint('❌ Could not get USDC balance after all retries', 'red')
    return 0

def check_zone_and_trade(symbol):
    print(f'🌙 MoonDev checking {symbol[:4]}...')
    
    # Get all positions and check total balance with retries
    max_retries = 3
    retry_count = 0
    total_balance = 0
    
    while retry_count < max_retries and total_balance == 0:
        positions_df = n.fetch_wallet_holdings_og(MY_ADDRESS)
        
        # Calculate total balance
        if not positions_df.empty:
            total_balance = positions_df['USD Value'].sum()
        
        if total_balance == 0:
            retry_count += 1
            cprint(f'⚠️ Got $0 balance on attempt {retry_count}/{max_retries} - likely an API error', 'yellow')
            time.sleep(10)  # Wait 10 seconds before retry
    
    # Print balance info with MoonDev style
    cprint('\n🌙 MoonDev Balance Check', 'cyan', attrs=['bold'])
    cprint('=' * 50, 'cyan')
    cprint(f'💰 Current Total Balance: ${total_balance:.2f}', 'yellow')
    cprint(f'💵 Minimum Required: ${MINIMUM_TOTAL_BALANCE:.2f}', 'yellow')
    
    # Only check minimum balance if we got a non-zero response
    if total_balance > 0 and total_balance < MINIMUM_TOTAL_BALANCE:
        cprint('❌ Balance below minimum threshold!', 'red', attrs=['bold'])
        cprint('🚫 Closing all positions and stopping trading', 'red', attrs=['bold'])
        n.close_all_positions()
        return
    elif total_balance == 0:
        cprint('⚠️ Could not get accurate balance - continuing without balance check', 'yellow')
    else:
        cprint('✅ Balance above minimum threshold', 'green')
    
    trend = check_trend(symbol)
    sell_percentage = SELL_PERCENTAGE_TRENDING_UP if trend == 'up' else SELL_PERCENTAGE_TRENDING_DOWN
    
    # Get position for this specific symbol
    symbol_position = positions_df[positions_df['Mint Address'] == symbol] if not positions_df.empty else pd.DataFrame()
    position = float(symbol_position['Amount'].iloc[0]) if not symbol_position.empty else 0
    price = n.token_price_moralis(symbol)
    print(f'🌙 ******MoonDev price for {symbol[:4]}: ${price}')

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
    
    # Calculate zone averages for better entry/exit points
    demand_zone_avg = (demand_zone_min + demand_zone_max) / 2
    supply_zone_avg = (supply_zone_min + supply_zone_max) / 2
    
    position_pct = current_value / POSITION_SIZE_USD
    
    # Print zone averages in the info
    cprint('\n🎯 Zone Averages:', 'magenta')
    cprint(f'Demand Zone Avg: {demand_zone_avg:.8f}', 'blue')
    cprint(f'Supply Zone Avg: {supply_zone_avg:.8f}', 'red')
    
    # Check if price is in or below demand zone
    if price <= demand_zone_max:
        if price < demand_zone_min:
            cprint(f'🌙 Price below demand zone for {symbol[:4]} - even better entry point! 🎯', 'green', attrs=['bold'])
        else:
            cprint(f'🌙 Price within demand zone range for {symbol[:4]}! 🎯', 'green', attrs=['bold'])
        
        # Only buy if price is below the demand zone average
        if price > demand_zone_avg:
            cprint(f'⚠️ Price (${price:.8f}) above demand zone average (${demand_zone_avg:.8f}) - waiting for better entry', 'yellow')
            return
            
        if trend == 'up':
            # Calculate how far we are from target position size
            target_gap_pct = abs(1 - (current_value / POSITION_SIZE_USD))
            
            if target_gap_pct > POSITION_TARGET_THRESHOLD:
                # Get available USDC balance
                available_usdc = get_usdc_balance()
                
                # Calculate ideal amount to buy
                ideal_buy_usd = POSITION_SIZE_USD - current_value
                
                # Adjust buy amount based on available USDC
                amount_to_buy_usd = min(ideal_buy_usd, available_usdc)
                amount_to_buy_usdc = int(amount_to_buy_usd * 10**6)
                
                cprint(f'🌙 Current position value: ${current_value:.2f}', 'yellow')
                cprint(f'🎯 Target position value: ${POSITION_SIZE_USD:.2f}', 'yellow')
                cprint(f'📊 Gap to target: {target_gap_pct*100:.1f}%', 'yellow')
                cprint(f'💫 Ideal buy amount: ${ideal_buy_usd:.2f}', 'cyan')
                cprint(f'📉 Entry price below zone avg: ${price:.8f} < ${demand_zone_avg:.8f}', 'green')
                
                if amount_to_buy_usd < ideal_buy_usd:
                    cprint(f'⚠️ Limited by available USDC - can only buy ${amount_to_buy_usd:.2f}', 'yellow')
                
                if amount_to_buy_usdc > 0:
                    cprint(f'💰 Attempting to buy ${amount_to_buy_usd:.2f} worth', 'green')
                    try_position_entry(symbol, amount_to_buy_usdc)
                else:
                    cprint('⚠️ Calculated buy amount is zero or negative - skipping buy', 'yellow')
            else:
                cprint(f'✅ Position already within {POSITION_TARGET_THRESHOLD*100}% of target size', 'green')
                cprint(f'💰 Current: ${current_value:.2f} vs Target: ${POSITION_SIZE_USD:.2f}', 'green')
        else:
            cprint(f'⚠️ Not buying - Below SMA buffer zone', 'yellow')
    
    elif supply_zone_min <= price <= supply_zone_max:
        cprint(f'🎯 Price within supply zone range for {symbol[:4]}!', 'red', attrs=['bold'])
        
        # Only sell if price is above the supply zone average
        if price < supply_zone_avg:
            cprint(f'⚠️ Price (${price:.8f}) below supply zone average (${supply_zone_avg:.8f}) - waiting for better exit', 'yellow')
            return
            
        # Check if we've already sold in this zone recently by verifying position reduction
        has_sold = check_recent_sell(symbol, 'supply', supply_zone_min, supply_zone_max, position, trend)
        
        if has_sold:
            cprint(f'⏳ Already executed sell in this zone (position: {position:.2f})', 'yellow')
            return
            
        expected_position_value = current_value * (1 - sell_percentage)
        expected_position_pct = expected_position_value / POSITION_SIZE_USD
        
        if position > 0 and position_pct > (sell_percentage + MINIMUM_POSITION_PCT):
            cprint(f'💸 Selling {sell_percentage*100}% of position (Trend: {trend})', 'red')
            cprint(f'📈 Exit price above zone avg: ${price:.8f} > ${supply_zone_avg:.8f}', 'green')
            sell_size = position * sell_percentage
            decimals = n.get_decimals(symbol)
            sell_size = int(sell_size * 10 ** decimals)
            cprint(f'🧮 Sell size: {sell_size} tokens', 'yellow')
            cprint(f'📊 Expected position after sell: ${expected_position_value:.2f} ({expected_position_pct*100:.2f}% of target)', 'yellow')
            
            verify_and_sell(symbol, sell_size, expected_max_value=expected_position_value * 1.1,
                          zone_type='supply', zone_min=supply_zone_min, zone_max=supply_zone_max,
                          position_before=position, sell_percentage=sell_percentage)
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
        
        # First check overall market conditions
        market_status = check_market_sma_conditions()
        
        if market_status is False:
            cprint('🚫 Market conditions unfavorable - closing all positions', 'red', attrs=['bold'])
            n.close_all_positions()
            return
        elif market_status is None:
            cprint('⚠️ Could not verify market conditions - proceeding with caution', 'yellow')
        else:
            cprint('✅ Market conditions favorable - proceeding with trading', 'green')
        
        cprint('\n🚀 Supply/Demand Zone Bot Settings:', 'cyan', attrs=['bold'])
        cprint(f'💰 Target Position Size: ${POSITION_SIZE_USD}', 'cyan')
        cprint(f'📈 Sell Size Up Trend: {SELL_PERCENTAGE_TRENDING_UP*100}%', 'green')
        cprint(f'📉 Sell Size Down Trend: {SELL_PERCENTAGE_TRENDING_DOWN*100}%', 'red')
        cprint(f'📊 Using {SMA_BARS}-bar {SMA_TIMEFRAME} SMA for trading symbols', 'cyan')
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
    schedule.every(SCHEDULE_INTERVAL_MINUTES).minutes.do(run_bot)
    
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