# this is a second nice_funcs file to be used with a diff solana wallet

from CONFIG import *
from termcolor import colored, cprint 
from datetime import datetime, timedelta
import requests
import pandas as pd
import pprint
import re as reggie
import json
import numpy as np
import time
import pandas_ta as ta
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Keys from environment variables
API_KEY = os.getenv('BIRDEYE_KEY')
SOL_KEY = os.getenv('SOL_KEY2')
RPC_URL = os.getenv('RPC_URL')

sample_address = "2yXTyarttn2pTZ6cwt4DqmrRuBw1G7pmFv9oT6MStdKP"

BASE_URL = "https://public-api.birdeye.so/defi"

# Custom function to print JSON in a human-readable format
def print_pretty_json(data):
    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(data)

# Function to print JSON in a human-readable format - assuming you already have it as print_pretty_json
# Helper function to find URLs in text
def find_urls(string):
    # Regex to extract URLs
    return reggie.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', string)

# UPDATED TO RMEOVE THE OTHER ONE so now we can just use this filter instead of filtering twice
def token_overview(address):
    """
    Fetch token overview for a given address and return structured information, including specific links,
    and assess if any price change suggests a rug pull.
    """
    
    #print(f'Getting the token overview for {address}')
    BASE_URL = "https://public-api.birdeye.so/defi"
    overview_url = f"{BASE_URL}/token_overview?address={address}"
    headers = {"X-API-KEY": API_KEY}

    response = requests.get(overview_url, headers=headers)
    result = {}

    if response.status_code == 200:
        overview_data = response.json().get('data', {})
        
        # Retrieve buy1h, sell1h, and calculate trade1h
        buy1h = overview_data.get('buy1h', 0)
        sell1h = overview_data.get('sell1h', 0)
        trade1h = buy1h + sell1h

        # Add the calculated values to the result
        result['buy1h'] = buy1h
        result['sell1h'] = sell1h
        result['trade1h'] = trade1h

        # Calculate buy and sell percentages
        total_trades = trade1h  # Assuming total_trades is the sum of buy and sell
        buy_percentage = (buy1h / total_trades * 100) if total_trades else 0
        sell_percentage = (sell1h / total_trades * 100) if total_trades else 0
        result['buy_percentage'] = buy_percentage
        result['sell_percentage'] = sell_percentage

        # Check if trade1h is bigger than MIN_TRADES_LAST_HOUR
        result['minimum_trades_met'] = True if trade1h >= MIN_TRADES_LAST_HOUR else False

        # Extract price changes over different timeframes
        price_changes = {k: v for k, v in overview_data.items() if 'priceChange' in k}
        result['priceChangesXhrs'] = price_changes

        # Check for rug pull indicator
        rug_pull = any(value < -80 for key, value in price_changes.items() if value is not None)
        result['rug_pull'] = rug_pull
        if rug_pull:
            print("Warning: Price change percentage below -80%, potential rug pull")

        # Extract other metrics
        unique_wallet2hr = overview_data.get('uniqueWallet24h', 0)
        v24USD = overview_data.get('v24hUSD', 0)
        watch = overview_data.get('watch', 0)
        view24h = overview_data.get('view24h', 0)
        liquidity = overview_data.get('liquidity', 0)

        # Add the retrieved data to result
        result.update({
            'uniqueWallet2hr': unique_wallet2hr,
            'v24USD': v24USD,
            'watch': watch,
            'view24h': view24h,
            'liquidity': liquidity,
        })

        # Extract and process description links if extensions are not None
        extensions = overview_data.get('extensions', {})
        description = extensions.get('description', '') if extensions else ''
        urls = find_urls(description)
        links = []
        for url in urls:
            if 't.me' in url:
                links.append({'telegram': url})
            elif 'twitter.com' in url:
                links.append({'twitter': url})
            elif 'youtube' not in url:  # Assume other URLs are for website
                links.append({'website': url})

        # Add extracted links to result
        result['description'] = links


        # Return result dictionary with all the data
        return result
    else:
        print(f"Failed to retrieve token overview for address {address}: HTTP status code {response.status_code}")
        return None


def token_security_info(address):

    '''

    bigmatter
​freeze authority is like renouncing ownership on eth

    Token Security Info:
{   'creationSlot': 242801308,
    'creationTime': 1705679481,
    'creationTx': 'ZJGoayaNDf2dLzknCjjaE9QjqxocA94pcegiF1oLsGZ841EMWBEc7TnDKLvCnE8cCVfkvoTNYCdMyhrWFFwPX6R',
    'creatorAddress': 'AGWdoU4j4MGJTkSor7ZSkNiF8oPe15754hsuLmwcEyzC',
    'creatorBalance': 0,
    'creatorPercentage': 0,
    'freezeAuthority': None,
    'freezeable': None,
    'isToken2022': False,
    'isTrueToken': None,
    'lockInfo': None,
    'metaplexUpdateAuthority': 'AGWdoU4j4MGJTkSor7ZSkNiF8oPe15754hsuLmwcEyzC',
    'metaplexUpdateAuthorityBalance': 0,
    'metaplexUpdateAuthorityPercent': 0,
    'mintSlot': 242801308,
    'mintTime': 1705679481,
    'mintTx': 'ZJGoayaNDf2dLzknCjjaE9QjqxocA94pcegiF1oLsGZ841EMWBEc7TnDKLvCnE8cCVfkvoTNYCdMyhrWFFwPX6R',
    'mutablefrom sMetadata': True,
    'nonTransferable': None,
    'ownerAddress': None,
    'ownerBalance': None,
    'ownerPercentage': None,
    'preMarketHolder': [],
    'top10HolderBalance': 357579981.3372284,
    'top10HolderPercent': 0.6439307358062863,
    'top10UserBalance': 138709981.9366756,
    'top10UserPercent': 0.24978920911102176,
    'totalSupply': 555308143.3354646,
    'transferFeeData': None,
    'transferFeeEnable': None}
    '''

    # API endpoint for getting token security information
    url = f"{BASE_URL}/token_security?address={address}"
    headers = {"X-API-KEY": API_KEY}

    # Sending a GET request to the API
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        # Parse the JSON response
        security_data = response.json()['data']
        print_pretty_json(security_data)
    else:
        print("Failed to retrieve token security info:", response.status_code)

def token_creation_info(address):

    '''
    output sampel = 

    Token Creation Info:
{   'decimals': 9,
    'owner': 'AGWdoU4j4MGJTkSor7ZSkNiF8oPe15754hsuLmwcEyzC',
    'slot': 242801308,
    'tokenAddress': '9dQi5nMznCAcgDPUMDPkRqG8bshMFnzCmcyzD8afjGJm',
    'txHash': 'ZJGoayaNDf2dLzknCjjaE9QjqxocA94pcegiF1oLsGZ841EMWBEc7TnDKLvCnE8cCVfkvoTNYCdMyhrWFFwPX6R'}
    '''
    # API endpoint for getting token creation information
    url = f"{BASE_URL}/token_creation_info?address={address}"
    headers = {"X-API-KEY": API_KEY}

    # Sending a GET request to the API
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        # Parse the JSON response
        creation_data = response.json()['data']
        print_pretty_json(creation_data)
    else:
        print("Failed to retrieve token creation info:", response.status_code)

def market_buy(token, amount, slippage=SLIPPAGE):
    import requests
    import sys
    import json
    import base64
    from solders.keypair import Keypair
    from solders.transaction import VersionedTransaction
    from solana.rpc.api import Client
    from solana.rpc.types import TxOpts
    import time

    KEY = Keypair.from_base58_string(SOL_KEY)
    # SLIPPAGE AND PRIORITY FEE ARE IN CONFIG.PY
    QUOTE_TOKEN = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # usdc

    # Use RPC endpoint
    http_client = Client(RPC_URL)


    #quote_url = f'https://quote-api.jup.ag/v6/quote?inputMint={QUOTE_TOKEN}&outputMint={token}&amount={amount}&slippageBps={SLIPPAGE}'
    # testing &restrictIntermediateTokens=true which only allows routes that are with liquid tokens
    quote_url = f'https://quote-api.jup.ag/v6/quote?inputMint={QUOTE_TOKEN}&outputMint={token}&amount={amount}&slippageBps={SLIPPAGE}&restrictIntermediateTokens=true'
    swap_url = 'https://quote-api.jup.ag/v6/swap'
    
    while True:
        try:
            quote = requests.get(quote_url).json()
            #print(quote)

            txRes = requests.post(swap_url,
                                  headers={"Content-Type": "application/json"},
                                  data=json.dumps({
                                      "quoteResponse": quote,
                                      "userPublicKey": str(KEY.pubkey()),
                                      "prioritizationFeeLamports": PRIORITY_FEE  # Hardcoded fee
                                  })).json()
            # print(txRes)
            swapTx = base64.b64decode(txRes['swapTransaction'])
            #print(swapTx)
            tx1 = VersionedTransaction.from_bytes(swapTx)
            #print(tx1)
            tx = VersionedTransaction(tx1.message, [KEY])
            txId = http_client.send_raw_transaction(bytes(tx), TxOpts(skip_preflight=True)).value
            print(f"https://solscan.io/tx/{str(txId)}")
            break
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            time.sleep(5)  # Wait for 5 seconds before retrying
        except Exception as e:
            print(f"An error occurred: {e}")
            time.sleep(5)  # Wait for 5 seconds before retrying


def market_sell(QUOTE_TOKEN, amount, slippage=SLIPPAGE):
    import requests
    import json
    import base64
    from solders.keypair import Keypair
    from solders.transaction import VersionedTransaction
    from solana.rpc.api import Client
    from solana.rpc.types import TxOpts

    print(f'selling {QUOTE_TOKEN[:4]} at {amount}')
    KEY = Keypair.from_base58_string(SOL_KEY)
    token = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # usdc

    http_client = Client(RPC_URL)
    #quote_url = f'https://quote-api.jup.ag/v6/quote?inputMint={QUOTE_TOKEN}&outputMint={token}&amount={amount}&restrictIntermediateTokens=true'
    quote_url = f'https://quote-api.jup.ag/v6/quote?inputMint={QUOTE_TOKEN}&outputMint={token}&amount={amount}'
    #print('we here.. quate don')
    #print(quote_url)
    # Fixed minimum slippage
    min_slippage = 5

    quote = requests.get(quote_url).json()
    #print(quote)
    
    # Post request to swap with dynamic slippage
    txRes = requests.post('https://quote-api.jup.ag/v6/swap',
                          headers={"Content-Type": "application/json"},
                          data=json.dumps({
                              "quoteResponse": quote,
                              "userPublicKey": str(KEY.pubkey()),
                              "prioritizationFeeLamports": PRIORITY_FEE,
                              "dynamicSlippage": {"minBps": min_slippage, "maxBps": SLIPPAGE},
                          })).json() 

    swapTx = base64.b64decode(txRes['swapTransaction'])
    #print(swapTx)
    tx1 = VersionedTransaction.from_bytes(swapTx)
    #print(tx1)
    tx = VersionedTransaction(tx1.message, [KEY])
    #print(tx)
    txId = http_client.send_raw_transaction(bytes(tx), TxOpts(skip_preflight=True)).value
    #print(txId)



def get_token_overview(address):

    '''
    update this function so that i can cache it and not call it as much

    '''
    url = f"https://public-api.birdeye.so/defi/token_overview?address={address}"
    headers = {"X-API-KEY": API_KEY}
    response = requests.get(url, headers=headers)
    if response.ok:
        json_response = response.json()
        return json_response['data']
    else:
        # Return empty dict if there's an error
        print(f"Error fetching data for address {address}: {response.status_code}")
        return {}
    
def get_names_nosave(df):
    names = []  # Lista para guardar los nombres recolectados
    low_volume_tokens = []  # Lista para direcciones de tokens con bajo volumen de trading

    for index, row in df.iterrows():
        token_mint_address = row['Mint Address']
        token_data = get_token_overview(token_mint_address)

        # Extraer el nombre del token usando la clave 'name' de token_data
        token_name = token_data.get('name', 'N/A')  # Usar 'N/A' si no se proporciona el nombre
        names.append(token_name)
        
        # Verificar el volumen de trading en los últimos 30 minutos
        trade30m = token_data.get('trade30m', 0)
        print(f'{token_name} has {trade30m} trades in the last 30 mins')
        
        # First check if token is in DO_NOT_TRADE_LIST
        from CONFIG import DO_NOT_TRADE_LIST as CONFIG_DO_NOT_TRADE_LIST
        is_protected = token_mint_address in CONFIG_DO_NOT_TRADE_LIST
        
        # Check if it's low volume AND not in the DO_NOT_TRADE_LIST
        if trade30m < MIN_TRADES_30M_ONCE_IN_POSITION:
            if not is_protected:
                print(f'🔍 Low volume token: {token_mint_address} detected - WILL be added to kill list')
                low_volume_tokens.append(token_mint_address)
            else:
                print(f'🚫 Low volume token: {token_mint_address} is PROTECTED in DO_NOT_TRADE_LIST - WILL NOT be killed')
    
    # Show all tokens considered for killing
    if low_volume_tokens:
        print(f"⚠️ TOKENS CONSIDERED FOR KILLING: {low_volume_tokens}")
    
    # Verificar si la columna 'name' ya existe, actualizarla si es así, de lo contrario insertarla
    if 'name' in df.columns:
        df['name'] = names  # Actualizar la columna 'name' existente
    else:
        df.insert(0, 'name', names)  # Insertar 'name' como la primera columna

    # Eliminar las columnas 'Mint Address' y 'Amount'
    df.drop('Mint Address', axis=1, inplace=True)
    df.drop('Amount', axis=1, inplace=True)

    print(f'low_volume_tokens: {low_volume_tokens}')
    return df, low_volume_tokens

from typing import Dict, List
# Assuming DO_NOT_TRADE_LIST, cprint, get_names_nosave, kill_switch, and other utilities are globally available.
# 
import requests
import pandas as pd
import time


def kill_switch(token_mint_address):

    # FIRST safety check: Never process tokens in DO_NOT_TRADE_LIST
    from CONFIG import DO_NOT_TRADE_LIST as CONFIG_DO_NOT_TRADE_LIST
    if token_mint_address in CONFIG_DO_NOT_TRADE_LIST:
        print(f'🛑 PROTECTED TOKEN: {token_mint_address} is in CONFIG.DO_NOT_TRADE_LIST - NOT killing!')
        return

    print(f'kill switch for {token_mint_address[:4]}')

    # if time is on the 5 minute do the balance check, if not grab from data/current_position.csv
    balance = fetch_wallet_holdings_nosaving_names(MY_ADDRESS, token_mint_address)
    try:
        balance = balance['Amount'].iloc[0]
        #print(f'balance: {balance}')
    except:
        #print(f'no balance for {token_mint_address[:4]}')
        balance = 0
        return
    
    # save to data/current_position.csv w/ pandas
    sell_size = balance 
    decimals = 0
    decimals = get_decimals(token_mint_address)
    #print(f'for {token_mint_address[:4]} decimals is {decimals}')

    sell_size = int(sell_size * 10 **decimals)
    
    #print(f'bal: {balance} price: {price} usdVal: {usd_value} TP: {tp} sell size: {sell_size} decimals: {decimals}')

    while sell_size > 0:

        # log this mint address to a file and save as a new line, keep the old lines there, so it will continue to grow this file is called data/closed_positions.txt
        # only add it to the file if it's not already there
        with open(CLOSED_POSITIONS_TXT, 'r') as f:
            lines = [line.strip() for line in f.readlines()]  # Strip the newline character from each line
            if token_mint_address not in lines:  # Now the comparison should work as expected
                with open(CLOSED_POSITIONS_TXT, 'a') as f:
                    f.write(token_mint_address + '\n')

        #print(f'closing {token_mint_address[:4]}')
        try:

            market_sell(token_mint_address, sell_size)
            #cprint(f'just made an order {token_mint_address[:4]} selling {sell_size} ...', 'white', 'on_green')
            time.sleep(1)
            market_sell(token_mint_address, sell_size)
            #cprint(f'just made an order {token_mint_address[:4]} selling {sell_size} ...', 'white', 'on_green')
            time.sleep(1)
            market_sell(token_mint_address, sell_size)
            cprint(f'just made 3 orders {token_mint_address[:4]} selling {sell_size} ...', 'white', 'on_blue')
            time.sleep(15)
            
        except:
            cprint('order error.. trying again', 'white', 'on_red')
            # time.sleep(7)

        # if time is on the 5 minute do the balance check, if not grab from data/current_position.csv
        balance = fetch_wallet_holdings_nosaving_names(MY_ADDRESS, token_mint_address)
        try:
            balance = balance['Amount'].iloc[0]
            #print(f'balance: {balance}')
        except:
            #print(f'no balance for {token_mint_address[:4]}')
            balance = 0
            return

        sell_size = balance 
        # decimals = 0
        # decimals = get_decimals(token_mint_address)
        #print(f'xxxxxxxxx for {token_mint_address[:4]} decimals is {decimals}')
        sell_size = int(sell_size * 10 **decimals)
        #print(f'sell size: {sell_size}')


    else:
        #print(f'for {token_mint_address[:4]} value is {usd_value} and tp is {tp} so not closing...')
        print('looks like its been closed')
        #time.sleep(10)




def fetch_wallet_holdings_nosaving_names(address, token_mint_address):
    API_KEY = os.getenv('BIRDEYE_KEY')  # Use environment variable

    # Initialize an empty DataFrame
    df = pd.DataFrame(columns=['Mint Address', 'Amount', 'USD Value'])

    url = f"https://public-api.birdeye.so/v1/wallet/token_list?wallet={address}"
    headers = {"x-chain": "solana", "X-API-KEY": API_KEY}
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        json_response = response.json()

        if 'data' in json_response and 'items' in json_response['data']:
            df = pd.DataFrame(json_response['data']['items'])

          
            
            try:
                df = df[['address', 'uiAmount', 'valueUsd']]
                df = df.rename(columns={'address': 'Mint Address', 'uiAmount': 'Amount', 'valueUsd': 'USD Value'})
                df = df.dropna()
                df = df[df['USD Value'] > 0.05]
            except KeyError as e:
                cprint(f"Error processing data: {e}. Available columns: {df.columns}", 'white', 'on_red')
                return pd.DataFrame(columns=['Mint Address', 'Amount', 'USD Value'])  # Return an empty DataFrame
        else:
            cprint("No data available in the response.", 'white', 'on_red')
            return pd.DataFrame(columns=['Mint Address', 'Amount', 'USD Value'])  # Return an empty DataFrame
    else:
        cprint(f"Failed to retrieve token list for {address[-3:]}.", 'white', 'on_magenta')
        time.sleep(10)
        return pd.DataFrame(columns=['Mint Address', 'Amount', 'USD Value'])  # Return an empty DataFrame

 
    # drop any row that is on the do not trade list
    # but keep these two tokens 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v' and Solana contract address
    
    # Addresses to exclude from the "do not trade list"
    exclude_addresses = ['EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', 'So11111111111111111111111111111111111111112']

    # Update the "do not trade list" by removing the excluded addresses
    updated_dont_trade_list = [mint for mint in DO_NOT_TRADE_LIST if mint not in exclude_addresses]

    # Filter the dataframe
    for mint in updated_dont_trade_list:
        df = df[df['Mint Address'] != mint]

    # filter by token mint address
    df = df[df['Mint Address'] == token_mint_address]

    return df



def get_decimals(token_mint_address):
    import requests
    import base64
    import json
    # Solana Mainnet RPC endpoint
    url = "https://api.mainnet-beta.solana.com/"
    
    headers = {"Content-Type": "application/json"}

    # Request payload to fetch account information
    payload = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getAccountInfo",
        "params": [
            token_mint_address,
            {
                "encoding": "jsonParsed"
            }
        ]
    })

    # Make the request to Solana RPC
    response = requests.post(url, headers=headers, data=payload)
    response_json = response.json()

    # Parse the response to extract the number of decimals
    decimals = response_json['result']['value']['data']['parsed']['info']['decimals']
    #print(f"Decimals for {token_mint_address[:4]} token: {decimals}")

    return decimals



# kill_switch('HuAncxDEsakCDgZS2Yfo9xJbHmtHXMnxxkT9jqdXnHhm')
# time.sleep(8978)


def fetch_wallet_new25(wallet_address):
    """
    New BirdEye API endpoint test for Solana wallets
    """
    API_KEY = os.getenv('BIRDEYE_KEY')
    url = f"https://public-api.birdeye.so/v1/wallet/token_list?wallet={wallet_address}"
    
    headers = {
        "accept": "application/json",
        "x-chain": "solana",
        "X-API-KEY": API_KEY
    }
    
    try:
        response = requests.get(url, headers=headers)
        print("\n🔍 DEBUG: API Response")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("\n🔄 Sample of Available Fields:")
            if 'data' in data and 'items' in data['data'] and data['data']['items']:
                sample_item = data['data']['items'][0]
                print("\n📊 Sample Token Data Fields:")
                for key, value in sample_item.items():
                    print(f"{key}: {value}")
                
                print("\n💰 Converting to DataFrame for analysis...")
                df = pd.DataFrame(data['data']['items'])
                print("\nColumns in response:")
                print(df.columns.tolist())
                
                print("\nFirst few rows of data:")
                print(df.head())
                
                return df
            else:
                print("❌ No token data found in response")
                return None
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None

# Test the new endpoint
# print("\n🧪 Testing new BirdEye API endpoint...")
# test_wallet = MY_ADDRESS
# result = fetch_wallet_new25(test_wallet)
# print("\n💫 Test complete!")
# time.sleep(1000)  # Wait to examine the output

def fetch_wallet_holdings_og(address):
    API_KEY = os.getenv('BIRDEYE_KEY')  # Use environment variable

    # Initialize an empty DataFrame
    df = pd.DataFrame(columns=['Mint Address', 'Amount', 'USD Value'])

    url = f"https://public-api.birdeye.so/v1/wallet/token_list?wallet={address}"
    headers = {"x-chain": "solana", "X-API-KEY": API_KEY}
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        json_response = response.json()

        if 'data' in json_response and 'items' in json_response['data']:
            df = pd.DataFrame(json_response['data']['items'])

            # print(df.head(50))
            # print(df.columns)
            # time.sleep(100)
            
            try:
                df = df[['address', 'uiAmount', 'valueUsd']]
                df = df.rename(columns={'address': 'Mint Address', 'uiAmount': 'Amount', 'valueUsd': 'USD Value'})
                df = df.dropna()
                df = df[df['USD Value'] > 0.05]
            except KeyError as e:
                cprint(f"Error processing data: {e}. Available columns: {df.columns}", 'white', 'on_red')
                return pd.DataFrame(columns=['Mint Address', 'Amount', 'USD Value'])  # Return an empty DataFrame
        else:
            cprint("No data available in the response.", 'white', 'on_red')
            return pd.DataFrame(columns=['Mint Address', 'Amount', 'USD Value'])  # Return an empty DataFrame
    else:
        cprint(f"Failed to retrieve token list for {address[-3:]}.", 'white', 'on_magenta')
        time.sleep(10)
        return pd.DataFrame(columns=['Mint Address', 'Amount', 'USD Value'])  # Return an empty DataFrame

 
    # drop any row that is on the do not trade list
    # but keep these two tokens 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v' and Solana contract address
    
    # Addresses to exclude from the "do not trade list"
    exclude_addresses = ['EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', 'So11111111111111111111111111111111111111112']

    # Update the "do not trade list" by removing the excluded addresses
    updated_dont_trade_list = [mint for mint in DO_NOT_TRADE_LIST if mint not in exclude_addresses]

    # Filter the dataframe
    for mint in updated_dont_trade_list:
        df = df[df['Mint Address'] != mint]


    # Print the DataFrame if it's not empty
    if not df.empty:
        
        # Save the filtered DataFrame to a CSV file
        TOKEN_PER_ADDY_CSV = 'filtered_wallet_holdings.csv'  # Define your CSV file name
        df.to_csv(TOKEN_PER_ADDY_CSV, index=False)
        # update the df so Mint_address so it's just the last 2
        
        df2, low_volume_tokens = get_names_nosave(df.copy())

        # Show what low volume tokens were found
        if low_volume_tokens:
            print(f"Final low_volume_tokens in OG function: {[token[:4] for token in low_volume_tokens]}")
        
        # Only kill switch tokens that are NOT in DO_NOT_TRADE_LIST from CONFIG.py
        from CONFIG import DO_NOT_TRADE_LIST as CONFIG_DO_NOT_TRADE_LIST
        for token in low_volume_tokens:
            if token not in CONFIG_DO_NOT_TRADE_LIST:
                print(f'🔄 Closing low volume token in OG function: {token} - NOT protected')
                kill_switch(token)
            else:
                print(f'🚫 PROTECTED low volume token in OG function: {token} - in CONFIG.DO_NOT_TRADE_LIST')



        #df['Mint Address'] = df['Mint Address'].str[:4]
        # print the df in reverse
        #df2 = df2.iloc[::-1]
        print('')
        #print(df2.tail(20))
        print(df2.head(50))
        # Assuming cprint is a function you have for printing in color
        #print('moondev.sol wallet')
        #cprint(f'** Current: ${round(df2["USD Value"].sum(),2)}', 'white', 'on_green')
        print(' ')
        time.sleep(7)
    else:
        # If the DataFrame is empty, print a message or handle it as needed
        cprint("No wallet holdings to display.", 'white', 'on_red')
        time.sleep(30)

    return df



def fetch_wallet_token_single(wallet_address, token_mint_address):
    API_KEY = os.getenv('BIRDEYE_KEY')  # Use environment variable
    
    url = f"https://public-api.birdeye.so/v1/wallet/token_list?wallet={wallet_address}"
    
    headers = {
        "accept": "application/json",
        "x-chain": "solana",
        "X-API-KEY": API_KEY
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Esto levantará una excepción para códigos de estado HTTP no exitosos
        
        data = response.json()
        
        #print("API Response:")
        #print(data)  # Imprime la respuesta completa de la API
        
        if 'data' in data and 'items' in data['data']:
            df = pd.DataFrame(data['data']['items'])
            
            
            # Filtra por el token_mint_address específico
            if 'address' in df.columns:
                df = df[df['address'] == token_mint_address]
            elif 'tokenAddress' in df.columns:
                df = df[df['tokenAddress'] == token_mint_address]
            else:
                #print(f"No se encontró columna 'address' o 'tokenAddress'. Columnas disponibles: {df.columns}")
                return pd.DataFrame()
            
            if not df.empty:
                # Renombra las columnas para mantener la consistencia con el formato anterior
                df = df.rename(columns={
                    'address': 'Mint Address',
                    'uiAmount': 'Amount',
                    'valueUsd': 'USD Value'
                })
                
                # Selecciona solo las columnas necesarias
                df = df[['Mint Address', 'Amount', 'USD Value']]
                
                #print(f'Data found for {token_mint_address[:4]}:')
                #print(df)
                return df
            else:
                #print(f'No data found for token {token_mint_address[:4]}')
                return pd.DataFrame(columns=['Mint Address', 'Amount', 'USD Value'])
        else:
            #print("No data available in the response.")
            return pd.DataFrame(columns=['Mint Address', 'Amount', 'USD Value'])
    
    except requests.RequestException as e:
        #print(f"Error fetching data for token {token_mint_address[:4]}: {e}")
        return pd.DataFrame(columns=['Mint Address', 'Amount', 'USD Value'])

def get_position(token_mint_address):
    #print(f'getting position for {token_mint_address[:4]}')
    dataframe = fetch_wallet_token_single(MY_ADDRESS2, token_mint_address)

    if dataframe.empty:
        #print(f"No se encontró posición para {token_mint_address}")
        return 0
    
    # Asumiendo que 'Amount' es la columna correcta (con A mayúscula)
    if 'Amount' in dataframe.columns:
        return float(dataframe['Amount'].values[0])
    else:
        #print(f"No se encontró columna 'Amount'. Columnas disponibles: {dataframe.columns}")
        return 0


def token_price(address):
    API_KEY = os.getenv('BIRDEYE_KEY')  # Use environment variable
    url = f"https://public-api.birdeye.so/defi/price?address={address}"
    headers = {"X-API-KEY": API_KEY}
    response = requests.get(url, headers=headers)
    price_data = response.json()
    
    if price_data['success']:
        return price_data['data']['value']
    else:
        return None


def ask_bid(token_mint_address):
    API_KEY = os.getenv('BIRDEYE_KEY')  # Use environment variable
    
    url = f"https://public-api.birdeye.so/defi/price?address={token_mint_address}"
    headers = {"X-API-KEY": API_KEY}
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        json_response = response.json()  # Parse the JSON response
        if 'data' in json_response and 'value' in json_response['data']:
            return json_response['data']['value']  # Return the price value
        else:
            return "Price information not available"  # Return a message if 'data' or 'value' is missing
    else:
        return None  # Return None if there's an error with the API call


def pnl_close(token_mint_address):
    print(f'Checking PNL close for {token_mint_address[:4]}')
    balance = get_position(token_mint_address)
    print(f'Balance for {token_mint_address[:4]}: {balance}')

    price = token_price(token_mint_address)
    print(f'Price for {token_mint_address[:4]}: {price}')

    try:
        usd_value = float(balance) * float(price)
        print(f'USD value for {token_mint_address[:4]}: {usd_value}')
    except:
        usd_value = 0
        print(f'Error calculating USD value for {token_mint_address[:4]}')

    tp = ((1+TP) * USDC_SIZE)
    sl = ((1-SL) * USDC_SIZE)
    sell_size = balance * SELL_AMOUNT_PERC
    decimals = get_decimals(token_mint_address)
    sell_size = int(sell_size * 10 **decimals)
    
    print(f'For {token_mint_address[:4]}: USD value is {usd_value}, TP is {tp}, SL is {sl}')

    while usd_value > tp:
        with open(CLOSED_POSITIONS_TXT, 'r') as f:
            lines = [line.strip() for line in f.readlines()]
            if token_mint_address not in lines:
                with open(CLOSED_POSITIONS_TXT, 'a') as f:
                    f.write(token_mint_address + '\n')

        cprint(f'for {token_mint_address[:4]} value is {usd_value} and tp is {tp} so closing...', 'white', 'on_green')
        try:
            for _ in range(3):
                market_sell(token_mint_address, sell_size)
                cprint(f'just made an order {token_mint_address[:4]} selling {sell_size} ...', 'white', 'on_green')
                time.sleep(1)
            time.sleep(15)
        except:
            cprint('order error.. trying again', 'white', 'on_red')

        balance = get_position(token_mint_address)
        price = token_price(token_mint_address)
        usd_value = balance * price
        tp = TP * USDC_SIZE
        sell_size = balance * SELL_AMOUNT_PERC
        sell_size = int(sell_size * 10 **decimals)
        print(f'USD Value is {usd_value} | TP is {tp} ')

    else:
        hi = 'hi'

    if usd_value != 0:
        while usd_value < sl and usd_value > 0:
            sell_size = balance 
            sell_size = int(sell_size * 10 **decimals)

            cprint(f'for {token_mint_address[:4]} value is {usd_value} and sl is {sl} so closing as a loss...', 'white', 'on_blue')
            print(token_mint_address)
            with open(CLOSED_POSITIONS_TXT, 'r') as f:
                lines = [line.strip() for line in f.readlines()]
                if token_mint_address not in lines:
                    with open(CLOSED_POSITIONS_TXT, 'a') as f:
                        f.write(token_mint_address + '\n')

            try:
                for _ in range(3):
                    market_sell(token_mint_address, sell_size)
                    cprint(f'just made an order {token_mint_address[:4]} selling {sell_size} ...', 'white', 'on_blue')
                    time.sleep(1)
                time.sleep(15)
            except:
                cprint('order error.. trying again', 'white', 'on_red')

            balance = get_position(token_mint_address)
            price = token_price(token_mint_address)
            usd_value = balance * price
            tp = TP * USDC_SIZE
            sl = ((1+SL) * USDC_SIZE)
            sell_size = balance 
            sell_size = int(sell_size * 10 **decimals)
            print(f'balance is {balance} and price is {price} and usd_value is {usd_value} and tp is {tp} and sell_size is {sell_size} decimals is {decimals}')

            if usd_value == 0:
                print(f'successfully closed {token_mint_address[:4]} usd_value is {usd_value} so breaking loop...')
                break

        else:
            print(f'for {token_mint_address[:4]} value is {usd_value} and tp is {tp} so not closing...')
            time.sleep(10)
    else:
        print(f'for {token_mint_address[:4]} value is {usd_value} and tp is {tp} so not closing...')
        time.sleep(10)

def get_token_owner(token_mint_address):
    try:
        df = pd.read_csv(ALL_TRENDING_EVER_CSV)
        matching_rows = df[df['contract_address'] == token_mint_address]
        
        if not matching_rows.empty:
            owners = matching_rows['owner'].tolist()
            #print(f"Dueño(s) encontrado(s) para {token_mint_address[:4]}: {', '.join(owners)}")
            return owners
        else:
            #print(f"No se encontró el token {token_mint_address[:4]} en {ALL_TRENDING_EVER_CSV}")
            return ["No encontrado"]
    except Exception as e:
        #print(f"Error al obtener el dueño del token: {e}")
        return ["Error"]

def update_leaderboard(owner, pnl):
    try:
        df = pd.read_csv(LEADERBOARD_CSV, header=None, names=['owner', 'pnl'])
    except FileNotFoundError:
        df = pd.DataFrame(columns=['owner', 'pnl'])
    
    if owner in df['owner'].values:
        df.loc[df['owner'] == owner, 'pnl'] += pnl
    else:
        new_row = pd.DataFrame({'owner': [owner], 'pnl': [pnl]})
        df = pd.concat([df, new_row], ignore_index=True)
    
    df = df.sort_values('pnl', ascending=False)
    df.to_csv(LEADERBOARD_CSV, index=False, header=False)
    #print(f"Leaderboard actualizado: {owner} {'ganó' if pnl > 0 else 'perdió'} ${abs(pnl):.2f}")


def get_names(df):
    names = []  # List to hold the collected names

    for index, row in df.iterrows():
        token_mint_address = row['contract_address']
        token_data = get_token_overview(token_mint_address)
        time.sleep(2)
        
        # Extract the token name using the 'name' key from the token_data
        token_name = token_data.get('name', 'N/A')  # Use 'N/A' if name isn't provided
        print(f'Name for {token_mint_address[:4]}: {token_name}')
        names.append(token_name)
    
    # Check if 'name' column already exists, update it if it does, otherwise insert it
    if 'name' in df.columns:
        df['name'] = names  # Update existing 'name' column
    else:
        df.insert(0, 'name', names)  # Insert 'name' as the first column

    # Save df to vibe_check.csv
    df.to_csv(READY_TO_BUY_CSV, index=False)
    
    return df


def open_position(token_mint_address):
    cprint(f'🌙 MoonDev opening position for {token_mint_address}...', 'white', 'on_blue')
    
    try:
        # Check if token is in closed positions FIRST
        with open(CLOSED_POSITIONS_TXT, 'r') as f:
            closed_positions = [line.strip() for line in f.readlines()]
            if token_mint_address in closed_positions:
                cprint(f'🚫 Token {token_mint_address[:4]} already in closed positions, skipping...', 'white', 'on_red')
                return False

        balance = get_position(token_mint_address)
        price = ask_bid(token_mint_address)
        
        if price is None or balance is None:
            cprint(f"❌ Could not get price/balance for {token_mint_address[:4]}", 'white', 'on_red')
            return False
            
        try:
            balance = float(price * balance)  # Convert balance to USDC value
        except (TypeError, ValueError) as e:
            cprint(f"❌ Error calculating balance: price={price}, balance={balance}", 'white', 'on_red')
            return False
            
        token_size = float(USDC_SIZE)
        size_needed = token_size - balance

        print(f'📊 Current balance: ${balance:.2f} USDC | Target size: ${token_size:.2f} USDC')

        position_filled = False
        while balance < (0.9 * token_size):  # 90% of target size
            try:
                size_needed = int(size_needed * 10**6)
                size_needed = str(size_needed)
                
                # Try just one order first to check if blacklisted
                print(f'🎯 Attempting buy: {size_needed} USDC worth of {token_mint_address[:4]}')
                order = market_buy_swap_tx(token_mint_address, size_needed)
                
                # Break immediately if order failed (blacklisted)
                if order is None:
                    cprint(f'🚫 Order failed or token blacklisted, stopping attempts...', 'white', 'on_red')
                    return False
                    
                # If first order succeeded, do the remaining orders
                for _ in range(ORDERS_PER_OPEN - 1):
                    order = market_buy_swap_tx(token_mint_address, size_needed)
                    time.sleep(1)
                
                # Update balance after orders
                price = ask_bid(token_mint_address)
                if price is None:
                    cprint(f'❌ Could not get price, stopping attempts...', 'white', 'on_red')
                    return False
                    
                balance = float(get_position(token_mint_address))
                balance = float(get_position(token_mint_address))
                balance = price * balance
                size_needed = token_size - balance
                
                # Check if we've filled enough
                if balance >= (0.9 * token_size):
                    position_filled = True
                    break
                    
            except Exception as e:
                cprint(f'❌ Error during buy: {str(e)}', 'white', 'on_red')
                break

        # Only add to closed positions if we successfully filled the position
        if position_filled:
            cprint(f'✅ Position filled for {token_mint_address[:4]}!', 'white', 'on_green')
            with open(CLOSED_POSITIONS_TXT, 'a') as file:
                file.write(f'{token_mint_address}\n')
            return True
        else:
            cprint(f'❌ Failed to fill position for {token_mint_address[:4]}', 'white', 'on_red')
            return False

    except Exception as e:
        cprint(f"❌ Error in open_position: {str(e)}", 'white', 'on_red')
        return False

#open_position('5SXx7DqZAwnYwRxhBdkcV78RdJrzvCJjRxLmoXdbpump')

def get_time_range(days_back_4_data):
    now = datetime.now()
    time_back = now - timedelta(days=days_back_4_data)
    time_to = int(now.timestamp())
    time_from = int(time_back.timestamp())
    return time_from, time_to



def get_data(address, days_back_4_data, timeframe):
    time_from, time_to = get_time_range(days_back_4_data)

    url = f"https://public-api.birdeye.so/defi/ohlcv?address={address}&type={timeframe}&time_from={time_from}&time_to={time_to}"
    headers = {"X-API-KEY": API_KEY}
    
    try:
        cprint(f'🔍 MoonDev fetching data for {address[:4]}...', 'cyan')
        cprint(f'⏰ Timeframe: {timeframe}', 'cyan')
        cprint(f'📅 From: {datetime.fromtimestamp(time_from).strftime("%Y-%m-%d %H:%M:%S")}', 'cyan')
        cprint(f'📅 To: {datetime.fromtimestamp(time_to).strftime("%Y-%m-%d %H:%M:%S")}', 'cyan')
        
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            cprint(f'❌ API Error: Status {response.status_code}', 'red')
            cprint(f'❌ Response: {response.text}', 'red')
            cprint(f'❌ URL: {url}', 'red')
            return pd.DataFrame()
            
        json_response = response.json()
        
        if 'success' in json_response and not json_response['success']:
            cprint(f'❌ API Error: {json_response.get("message", "Unknown error")}', 'red')
            return pd.DataFrame()
            
        items = json_response.get('data', {}).get('items', [])
        
        if not items:
            cprint(f'⚠️ No data returned for {address[:4]}', 'yellow')
            return pd.DataFrame()

        # Create DataFrame with OHLCV data
        processed_data = [{
            'Datetime (UTC)': datetime.utcfromtimestamp(item['unixTime']).strftime('%Y-%m-%d %H:%M:%S'),
            'Open': item['o'],
            'High': item['h'],
            'Low': item['l'],
            'Close': item['c'],
            'Volume': item['v']
        } for item in items]

        df = pd.DataFrame(processed_data)
        
        cprint(f'✅ Successfully fetched {len(df)} bars of data', 'green')
        # print(df.head())

        # Calculate technical indicators
        df['MA20'] = ta.sma(df['Close'], length=20)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['MA40'] = ta.sma(df['Close'], length=40)
        
        # Handle NaN values in comparisons
        df['Price_above_MA20'] = df.apply(lambda x: False if pd.isna(x['MA20']) else x['Close'] > x['MA20'], axis=1)
        df['Price_above_MA40'] = df.apply(lambda x: False if pd.isna(x['MA40']) else x['Close'] > x['MA40'], axis=1)
        df['MA20_above_MA40'] = df.apply(lambda x: False if pd.isna(x['MA20']) or pd.isna(x['MA40']) else x['MA20'] > x['MA40'], axis=1)

        return df
        
    except requests.exceptions.RequestException as e:
        cprint(f'❌ Network error fetching data for {address[:4]}: {str(e)}', 'red')
        return pd.DataFrame()
    except Exception as e:
        cprint(f'❌ Unexpected error fetching data for {address[:4]}: {str(e)}', 'red')
        return pd.DataFrame()

def check_trend(symbol):
    """
    Check if price is above/below SMA for trend determination
    Returns: 
        - 'up' if price > SMA
        - 'down' if price < SMA
    """
    try:
        # Get current price
        price = token_price(symbol)
        if price is None:
            cprint(f'❌ Could not get price for {symbol[:4]}', 'red')
            return 'down'
        
        cprint(f'🏷️ Current price for {symbol[:4]}: ${price:.8f}', 'cyan')
        
        # Get data
        cprint(f'📊 Fetching data for trend analysis...', 'cyan')
        df = get_data(symbol, SMA_DAYS_BACK, SMA_TIMEFRAME)
        
        if df.empty:
            cprint(f'❌ No data available for trend analysis of {symbol[:4]}', 'red')
            return 'down'
        
        # Use MA for trend determination
        sma = df['MA20'].iloc[-1]
        trend = 'up' if price > sma else 'down'
        cprint(f'🎯 Trend determined: {trend.upper()}', 'green' if trend == 'up' else 'red')
        
        return trend
        
    except Exception as e:
        cprint(f'❌ Error in trend analysis for {symbol[:4]}: {str(e)}', 'red')
        return 'down'  # Default to down trend on error

def supply_demand_zones(CONTRACT_ADDRESS, days_back_4_data, timeframe):
    cprint('🌙 MoonDev starting supply and demand zones calculation...', 'cyan')

    sd_df = pd.DataFrame()

    df = get_data(CONTRACT_ADDRESS, days_back_4_data, timeframe)
    
    if df.empty:
        cprint('❌ No data returned from get_data', 'red')
        return None
        
    cprint(f'📊 Got {len(df)} bars of data', 'cyan')

    if len(df) > 2: 
        try:
            support = df[:-2]['Close'].min()
            resistance = df[:-2]['Close'].max()
            support_low = df[:-2]['Low'].min()
            resistance_high = df[:-2]['High'].max()

            sd_df['dz'] = [support_low, support]
            sd_df['sz'] = [resistance_high, resistance]

            cprint('\n🎯 Supply & Demand Zones:', 'green')
            cprint(f'Demand Zone: {support_low:.8f} - {support:.8f}', 'blue')
            cprint(f'Supply Zone: {resistance:.8f} - {resistance_high:.8f}', 'red')

            return sd_df
            
        except Exception as e:
            cprint(f'❌ Error calculating zones: {str(e)}', 'red')
            return None
    else:
        cprint(f'❌ Not enough data - only {len(df)} bars available', 'red')
        return None

# supply_demand_zones('7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr', .5, '15m')
# time.sleep(8987879)

def round_down(value, decimals):
    import math
    factor = 10 ** decimals
    return math.floor(value * factor) / factor
    
def chunk_kill(CONTRACT_ADDRESS, MAX_USD_ORDER_SIZE, SLEEP_BETWEEN_ORDERS, SLIPPAGE):

    balance = get_position(CONTRACT_ADDRESS)
    price = token_price(CONTRACT_ADDRESS)
    price = float(price)
    balance = float(balance)
    usd_value = balance * price
    print(f'balance: {balance} price: {price} usdVal: {usd_value}')

    if usd_value < MAX_USD_ORDER_SIZE:
        sell_size = balance 
    else:
        sell_size = MAX_USD_ORDER_SIZE / price
    
    print(f'balance size {balance} and selling this amount {sell_size}')

    sell_size = round_down(sell_size, 2)
    decimals = 0 
    decimals = get_decimals(CONTRACT_ADDRESS)
    sell_size = int(sell_size * 10 ** decimals)

    while usd_value > 0:
        try:
            market_sell(CONTRACT_ADDRESS, sell_size, SLIPPAGE)
            cprint(f'just made an order {CONTRACT_ADDRESS[:4]} selling {sell_size} ...', 'white', 'on_blue')
            time.sleep(SLEEP_BETWEEN_ORDERS)
            market_sell(CONTRACT_ADDRESS, sell_size, SLIPPAGE)
            cprint(f'just made an order {CONTRACT_ADDRESS[:4]} selling {sell_size} ...', 'white', 'on_blue')
            time.sleep(SLEEP_BETWEEN_ORDERS)
            market_sell(CONTRACT_ADDRESS, sell_size, SLIPPAGE)
            cprint(f'just made an order {CONTRACT_ADDRESS[:4]} selling {sell_size} ...', 'white', 'on_blue')
            time.sleep(SLEEP_BETWEEN_ORDERS)
        except Exception as e:
            cprint(f'order error.. trying again {e}', 'white', 'on_red')

        balance = get_position(CONTRACT_ADDRESS)
        price = token_price(CONTRACT_ADDRESS)
        usd_value = balance * price
        print(f'balance: {balance} price: {price} usdVal: {usd_value}')

        if usd_value < MAX_USD_ORDER_SIZE:
            sell_size = balance 
        else:
            sell_size = MAX_USD_ORDER_SIZE / price

        sell_size = round_down(balance, 2)
        decimals = 0 
        decimals = get_decimals(CONTRACT_ADDRESS)
        sell_size = int(sell_size * 10 ** decimals)

    else:
        print(f'for {CONTRACT_ADDRESS[:4]} value is {usd_value}')


def close_all_positions():
    """
    Close all positions in the wallet except for tokens in DO_NOT_TRADE_LIST
    """
    cprint('🌙 MoonDev closing all positions...', 'cyan', attrs=['bold'])
    
    # Get all positions
    open_positions = fetch_wallet_holdings_og(MY_ADDRESS)
    
    if open_positions.empty:
        cprint('No positions to close', 'yellow')
        return
        
    # Loop through all positions and close them
    for index, row in open_positions.iterrows():
        token_mint_address = row['Mint Address']
        
        # Skip protected tokens
        if token_mint_address in DO_NOT_TRADE_LIST:
            cprint(f'🔒 Skipping protected token: {token_mint_address[:4]}', 'yellow')
            continue
            
        cprint(f'📉 Closing position for {token_mint_address[:4]}...', 'red')
        kill_switch(token_mint_address)
        time.sleep(2)  # Small delay between closures
        
    cprint('✅ Finished closing all positions', 'green')




    


    

def get_ohlcv_hl(symbol, interval, lookback_days):
    """
    Get OHLCV data from Hyperliquid
    """
    end_time = datetime.now()
    start_time = end_time - timedelta(days=lookback_days)
    
    url = 'https://api.hyperliquid.xyz/info'
    headers = {'Content-Type': 'application/json'}
    data = {
        "type": "candleSnapshot",
        "req": {
            "coin": symbol,
            "interval": interval,
            "startTime": int(start_time.timestamp() * 1000),
            "endTime": int(end_time.timestamp() * 1000)
        }
    }

    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        snapshot_data = response.json()
        return snapshot_data
    else:
        print(f"Error fetching data for {symbol}: {response.status_code}")
        return None

def process_data_to_df_hl(snapshot_data, time_period=20):
    """
    Process Hyperliquid OHLCV data into a DataFrame
    """
    if snapshot_data:
        try:
            # Assuming the response contains a list of candles
            columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
            data = []
            for snapshot in snapshot_data:
                timestamp = datetime.fromtimestamp(snapshot['t'] / 1000).strftime('%Y-%m-%d %H:%M:%S')
                # Explicitly convert to float
                open_price = float(snapshot['o'])
                high_price = float(snapshot['h'])
                low_price = float(snapshot['l'])
                close_price = float(snapshot['c'])
                volume = float(snapshot['v'])
                data.append([timestamp, open_price, high_price, low_price, close_price, volume])

            df = pd.DataFrame(data, columns=columns)
            df.set_index('timestamp', inplace=True)
            df.sort_index(inplace=True)  # Ensure data is sorted by time

            # Calculate rolling support and resistance
            df['support'] = df['close'].rolling(window=time_period, min_periods=1).min().shift(1)
            df['resis'] = df['close'].rolling(window=time_period, min_periods=1).max().shift(1)

            return df
        except Exception as e:
            cprint(f'❌ Error processing Hyperliquid data: {str(e)}', 'red')
            return pd.DataFrame()  # Return empty DataFrame on error
    else:
        return pd.DataFrame()  # Return empty DataFrame if no data

def ask_bid_hl(symbol):
    """
    Get ask/bid data from Hyperliquid
    """
    url = 'https://api.hyperliquid.xyz/info'
    headers = {'Content-Type': 'application/json'}

    data = {
        'type': 'l2Book',
        'coin': symbol
    }

    response = requests.post(url, headers=headers, data=json.dumps(data))
    l2_data = response.json()
    l2_data = l2_data['levels']

    # get bid and ask 
    bid = float(l2_data[0][0]['px'])
    ask = float(l2_data[1][0]['px'])

    return ask, bid, l2_data

# Update check_market_conditions to use the new HL functions
def check_market_conditions():
    """
    Check if price is above BOTH 20 AND 40 SMA on the daily timeframe for ETH, SOL, and BTC.
    A symbol must be above both SMAs to be considered bullish.
    Returns True if at least 2 out of 3 symbols are above both SMAs.
    """
    major_symbols = ['ETH', 'SOL', 'BTC']
    fully_above_count = 0
    SMA_20 = 20
    SMA_40 = 40
    TIMEFRAME = '1d'
    LOOKBACK_DAYS = 60  # Get enough days for SMA calculation
    
    cprint('\n🌙 MoonDev Major Market Analysis - 20 & 40 SMA Daily', 'cyan', attrs=['bold'])
    cprint('=' * 50, 'cyan')
    cprint(f'📊 Checking both {SMA_20} & {SMA_40} SMA on Daily timeframe', 'yellow')
    cprint('Must be above BOTH SMAs to be considered bullish', 'yellow')
    
    for symbol in major_symbols:
        try:
            # Get daily OHLCV data for the symbol using Hyperliquid
            snapshot_data = get_ohlcv_hl(symbol, TIMEFRAME, LOOKBACK_DAYS)
            if not snapshot_data:
                cprint(f'❌ Could not get daily data for {symbol}', 'red')
                continue
                
            df = process_data_to_df_hl(snapshot_data)
            if df.empty:
                cprint(f'❌ Empty dataframe for {symbol}', 'red')
                continue
            
            # Calculate both SMAs
            df[f'SMA_{SMA_20}'] = df['close'].rolling(window=SMA_20).mean()
            df[f'SMA_{SMA_40}'] = df['close'].rolling(window=SMA_40).mean()
            
            # Get current price and SMAs
            current_price = float(df['close'].iloc[-1])
            current_sma_20 = float(df[f'SMA_{SMA_20}'].iloc[-1])
            current_sma_40 = float(df[f'SMA_{SMA_40}'].iloc[-1])
            
            # Check if price is above both SMAs
            above_sma_20 = current_price > current_sma_20
            above_sma_40 = current_price > current_sma_40
            is_fully_above = above_sma_20 and above_sma_40
            
            if is_fully_above:
                fully_above_count += 1
                cprint(f'✅ {symbol} above BOTH SMAs:', 'green')
                cprint(f'   Price: ${current_price:.2f}', 'green')
                cprint(f'   20 SMA: ${current_sma_20:.2f}', 'green')
                cprint(f'   40 SMA: ${current_sma_40:.2f}', 'green')
            else:
                status_20 = "✅" if above_sma_20 else "❌"
                status_40 = "✅" if above_sma_40 else "❌"
                cprint(f'❌ {symbol} not above both SMAs:', 'red')
                cprint(f'   Price: ${current_price:.2f}', 'yellow')
                cprint(f'   20 SMA: ${current_sma_20:.2f} {status_20}', 'yellow')
                cprint(f'   40 SMA: ${current_sma_40:.2f} {status_40}', 'yellow')
                
        except Exception as e:
            cprint(f'❌ Error processing {symbol}: {str(e)}', 'red')
            continue
    
    market_conditions_good = fully_above_count >= 2
    cprint(f'\n{"✅ Market conditions favorable" if market_conditions_good else "❌ Market conditions unfavorable"}', 
           'green' if market_conditions_good else 'red', attrs=['bold'])
    cprint(f'📊 {fully_above_count}/3 major symbols above BOTH 20 & 40 SMA Daily', 'yellow')
    
    return market_conditions_good




    


    

def get_hyperliquid_daily_data(symbol, lookback_days):
    """
    Get daily OHLCV data from Hyperliquid and return as pandas DataFrame
    """
    try:
        # Get raw data from Hyperliquid
        snapshot_data = get_ohlcv_hl(symbol, '1d', lookback_days)
        if not snapshot_data:
            cprint(f'❌ No data returned from Hyperliquid for {symbol}', 'red')
            return None

        # Convert to DataFrame
        data = []
        for candle in snapshot_data:
            data.append({
                'timestamp': datetime.fromtimestamp(candle['t'] / 1000),
                'Open': float(candle['o']),
                'High': float(candle['h']),
                'Low': float(candle['l']),
                'Close': float(candle['c']),
                'Volume': float(candle['v'])
            })

        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        df.sort_index(inplace=True)  # Ensure data is sorted by time

        cprint(f'✅ Got {len(df)} days of data for {symbol}', 'green')
        return df

    except Exception as e:
        cprint(f'❌ Error getting daily data for {symbol}: {str(e)}', 'red')
        return None




    


    