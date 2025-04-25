'''
This bot is intended for people just getting started with algorithmic trading 
If you top blast meaning by at the point of the top of the market, you could be getting a 50% worse price. 
for example i could buy a million of a token and if i would have just waited 30 minutes i could have bought a million and a half 
But humans don't have that patience. So this bot will go ahead and buy the demand zones and other ways to buy that will essentially have them wait 
It will help humans average in, average in at good places. 

'''

import nice_funcs as n  # Import nice_funcs.py from the same directory
import time 
from termcolor import colored, cprint 
import schedule 

CONTRACT_ADDRESS = '7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr'
TOTAL_USD_POSITION_SIZE = 10000
MAX_USD_ORDER_SIZE = 50
SLEEP_BETWEEN_ORDERS = 600 # the time betweens orders is important... this works for entries AND exits to get the BEST price
SLIPPAGE = 49 # 5000 is 50%, 500 is 5% and 50 is .5%
PRIORITY_FEE = 20000 # 200000 is about .035 usd at 150 sol, after a bit of testing 100000 is sufficient and is .02 usd
ORDERS_PER_OPEN = 2

# 2 SDZ Zones
SD_DZ_DAYS_BACK = 1
SDDZ_TIMEFRAME = '15m'
SDZ_SLEEP_BETWEEN_ORDERS = 15 

action = 0 
action = input('0 to close, 1 to buy, 2 to demand zone buy, 3 supply zone close: ')
action = int(action) 

def bot():
    
    while True:

        # price of the token 
        price = n.token_price(CONTRACT_ADDRESS)

        if action == 0: 
            print(f'closing position for {CONTRACT_ADDRESS[:4]} at {price}')
            pos = n.get_position(CONTRACT_ADDRESS)

            while pos > 0:
                print(f'contract_address: {CONTRACT_ADDRESS}, max_usd_order_size: {MAX_USD_ORDER_SIZE}, sleep_between_orders: {SLEEP_BETWEEN_ORDERS}, slippage: {SLIPPAGE}')
                n.chunk_kill(CONTRACT_ADDRESS, MAX_USD_ORDER_SIZE, SLEEP_BETWEEN_ORDERS, SLIPPAGE)
                pos = n.get_position(CONTRACT_ADDRESS)
                time.sleep(1)

            if pos < .9:
                time.sleep(15)
                pos = n.get_position(CONTRACT_ADDRESS)
                if pos < .9:
                    print('position closed.... thanks moon dev... ')
                break 
            print('bot successfully closed position')

        elif action == 1:
            print(f'buying {CONTRACT_ADDRESS[:4]} at {price}')
            pos = n.get_position(CONTRACT_ADDRESS)
            price = n.token_price(CONTRACT_ADDRESS)
            pos_usd = pos * price
            size_needed = TOTAL_USD_POSITION_SIZE - pos_usd

            chunk_size = min(size_needed, MAX_USD_ORDER_SIZE)
            chunk_size = int(chunk_size  * 10**6)
            chunk_size = str(chunk_size)

            if pos_usd > (.97 * TOTAL_USD_POSITION_SIZE):
                print('position is filled...')
                time.sleep(8987879)
            
            while TOTAL_USD_POSITION_SIZE < (.97 * TOTAL_USD_POSITION_SIZE):
                print(f'position {round(pos_usd, 2)} is less than {round(TOTAL_USD_POSITION_SIZE, 2)} buying... ')

                try:
                    for i in range(ORDERS_PER_OPEN):
                        n.market_buy(CONTRACT_ADDRESS, chunk_size, SLIPPAGE)
                        cprint(f'just made an order {CONTRACT_ADDRESS[:4]} buying {chunk_size} ...', 'white', 'on_blue')
                        time.sleep(SLEEP_BETWEEN_ORDERS)

                        pos = n.get_position(CONTRACT_ADDRESS)
                        price = n.token_price(CONTRACT_ADDRESS)
                        pos_usd = pos * price
                        size_needed = TOTAL_USD_POSITION_SIZE - pos_usd
                        chunk_size = min(size_needed, MAX_USD_ORDER_SIZE)
                        chunk_size = int(chunk_size, 10**6)
                        chunk_size = str(chunk_size)

                except Exception as e:
                    cprint(f'error buying... {e}.. trying again in 15 seconds', 'white', 'on_red')
                    time.sleep(15)
                    continue 
                time.sleep(3)

            cprint(f'position {round(pos_usd, 2)} is filled...', 'white', 'on_green')
            break 

        elif action == 2:
            pos = n.get_position(CONTRACT_ADDRESS)
            price = n.token_price(CONTRACT_ADDRESS)
            pos_usd = pos * price
            size_needed = TOTAL_USD_POSITION_SIZE - pos_usd

            chunk_size = min(size_needed, MAX_USD_ORDER_SIZE)
            chunk_size = int(chunk_size  * 10**6)
            chunk_size = str(chunk_size)

            if pos_usd > (.97 * TOTAL_USD_POSITION_SIZE):
                print('position is filled...')
                time.sleep(8987879)

            # GET SUPPLY AND DEMAND ZONES
            sd_df = n.supply_demand_zones(CONTRACT_ADDRESS, SD_DZ_DAYS_BACK, SDDZ_TIMEFRAME)
            
            # Get the demand zone values
            dz_low = sd_df['dz'].iloc[0]  # Lower demand zone
            dz_high = sd_df['dz'].iloc[1]  # Higher demand zone
            
            print(f'🌙 MoonDev checking demand zones:')
            print(f'Current price: {price}')
            print(f'Demand zone range: {dz_low} - {dz_high}')
            
            # Check if price is within demand zone
            if dz_low <= price <= dz_high:
                print(f'🎯 Price is in demand zone! Executing buy orders...')
                while pos_usd < (.97 * TOTAL_USD_POSITION_SIZE):
                    # Get fresh price and demand zones
                    price = n.token_price(CONTRACT_ADDRESS)
                    sd_df = n.supply_demand_zones(CONTRACT_ADDRESS, SD_DZ_DAYS_BACK, SDDZ_TIMEFRAME)
                    dz_low = sd_df['dz'].iloc[0]
                    dz_high = sd_df['dz'].iloc[1]
                    
                    # Check if still in demand zone
                    if not (dz_low <= price <= dz_high):
                        print(f'⚠️ Price moved outside demand zone! Stopping buy orders...')
                        print(f'Current price: {price}')
                        print(f'Demand zone range: {dz_low} - {dz_high}')
                        break
                        
                    print(f'position {round(pos_usd, 2)} is less than {round(TOTAL_USD_POSITION_SIZE, 2)} buying... ')

                    try:
                        for i in range(ORDERS_PER_OPEN):
                            n.market_buy(CONTRACT_ADDRESS, chunk_size, SLIPPAGE)
                            cprint(f'just made an order {CONTRACT_ADDRESS[:4]} buying {chunk_size} ...', 'white', 'on_blue')
                            time.sleep(SDZ_SLEEP_BETWEEN_ORDERS)

                            pos = n.get_position(CONTRACT_ADDRESS)
                            price = n.token_price(CONTRACT_ADDRESS)
                            pos_usd = pos * price
                            size_needed = TOTAL_USD_POSITION_SIZE - pos_usd
                            chunk_size = min(size_needed, MAX_USD_ORDER_SIZE)
                            chunk_size = int(chunk_size * 10**6)
                            chunk_size = str(chunk_size)

                    except Exception as e:
                        cprint(f'error buying... {e}.. trying again in 15 seconds', 'white', 'on_red')
                        time.sleep(15)
                        continue 
                    time.sleep(3)
            else:
                print(f'⏳ Price is not in demand zone. Waiting for better entry...')
                time.sleep(60)  # Wait a minute before checking again

        elif action == 3:
            print(f'🌙 MoonDev checking supply zones for closing position...')
            pos = n.get_position(CONTRACT_ADDRESS)
            price = n.token_price(CONTRACT_ADDRESS)
            
            # GET SUPPLY AND DEMAND ZONES
            sd_df = n.supply_demand_zones(CONTRACT_ADDRESS, SD_DZ_DAYS_BACK, SDDZ_TIMEFRAME)
            
            # Get the supply zone values
            sz_low = sd_df['sz'].iloc[0]  # Lower supply zone
            sz_high = sd_df['sz'].iloc[1]  # Higher supply zone
            
            print(f'Current price: {price}')
            print(f'Supply zone range: {sz_low} - {sz_high}')
            
            # Check if price is within supply zone
            if sz_low <= price <= sz_high:
                print(f'🎯 Price is in supply zone! Executing close orders...')
                while pos > 0:
                    # Get fresh price and supply zones
                    price = n.token_price(CONTRACT_ADDRESS)
                    sd_df = n.supply_demand_zones(CONTRACT_ADDRESS, SD_DZ_DAYS_BACK, SDDZ_TIMEFRAME)
                    sz_low = sd_df['sz'].iloc[0]
                    sz_high = sd_df['sz'].iloc[1]
                    
                    # Check if still in supply zone
                    if not (sz_low <= price <= sz_high):
                        print(f'⚠️ Price moved outside supply zone! Stopping close orders...')
                        print(f'Current price: {price}')
                        print(f'Supply zone range: {sz_low} - {sz_high}')
                        break
                        
                    print(f'closing position for {CONTRACT_ADDRESS[:4]} at {price}')
                    n.chunk_kill(CONTRACT_ADDRESS, MAX_USD_ORDER_SIZE, SDZ_SLEEP_BETWEEN_ORDERS, SLIPPAGE)
                    pos = n.get_position(CONTRACT_ADDRESS)
                    time.sleep(1)

                if pos < .9:
                    time.sleep(15)
                    pos = n.get_position(CONTRACT_ADDRESS)
                    if pos < .9:
                        print('position closed.... thanks moon dev... ')
                    break 
                print('bot successfully closed position')
            else:
                print(f'⏳ Price is not in supply zone. Waiting for better exit...')
                time.sleep(60)  # Wait a minute before checking again

bot()
schedule.every(30).seconds.do(bot)

while True:
    try:
        schedule.run_pending()
        time.sleep(3)
    except Exception as e:
        print(f'error: {e}')
        time.sleep(3)